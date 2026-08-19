from __future__ import annotations

import logging
import os

from datetime import timedelta, datetime, timezone
from typing import Any, Dict, Optional, Tuple, List
from flask import g
from sqlalchemy.orm import Session

from cmcp.common.cache import cached_list
from cmcp.common.email.outbox_model import EmailOutboxStatus
from cmcp.config.database import db
from cmcp.core.base_service import BaseService
import calendar as py_calendar
from cmcp.modules.auth.models import User, UserAffiliation, UserStatusEnum, UserTypeEnum, LinkedEntityTypeEnum
from cmcp.modules.education_people.models import StudentProfile, Classroom, StaffProfile
from cmcp.modules.academic.models import Faculty, Department
from cmcp.modules.education_people.onboarding_repository import OnboardingQueueRepository
from cmcp.common.email.service import EmailService, _utcnow
from cmcp.common.security.tokens import generate_email_verify_token, verify_token
from cmcp.common.security.passwords import generate_temp_password, hash_password
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from cmcp.common.cache import bump_user_profile
from cmcp.common.cache.session_manager import remove_session
from cmcp.modules.education_people.repository import EducationPeopleRepo
from cmcp.modules.education_people.validation import (
    require_text,
    ERR_CLASSROOM_NOT_FOUND,
    ERR_CLASSROOM_EXISTS,
    ERR_ADMIN_REJECTED,
    ERR_DEPARTMENT_NOT_FOUND,
    ERR_EMAIL_EXISTS,
    ERR_FACULTY_NOT_FOUND,
    ERR_PENDING_APPROVAL,
    ERR_STUDENT_ID_EXISTS,
    ERR_VERIFY_EXPIRED,
    ERR_SEMESTER_NOT_FOUND,
    normalize_email,
)
from cmcp.modules.materials.service import _encode_cursor, _decode_cursor
from cmcp.modules.rbac.models import Role, UserRole

log = logging.getLogger(__name__)

class EducationPeopleService:
    """
     Same architecture as AcademicService:
     - Repo for existence checks / uniqueness validations
     - BaseService for create/update/delete/list/get (Classroom etc)
     - Custom business methods for registration + verification + approval
     """

    def __init__(self, repo: Optional[EducationPeopleRepo] = None, session: Optional[Session] = None):
        self.repo = repo or EducationPeopleRepo(session=session)
        self.s: Session = self.repo.s
        self.onboarding_repo = OnboardingQueueRepository(self.s)
        self.classroom_svc = BaseService(Classroom, session=self.s)
        self.student_svc = BaseService(StudentProfile, session=self.s)
        self.staff_svc = BaseService(StaffProfile, session=self.s)

        self.email_svc = EmailService(
            session=self.s,
            provider=os.getenv("MAIL_PROVIDER", "smtp"),
            from_email=os.getenv("MAIL_FROM_EMAIL", ""),
            from_name=os.getenv("MAIL_FROM_NAME", "Jamhuriya University"),
            max_tries=int(os.getenv("EMAIL_OUTBOX_MAX_TRIES", "5")),
        )
    # =========================================================
    # CLASSROOM
    # =========================================================
    def create_classroom(self, *, company_id: int, data: Dict[str, Any]):
        from cmcp.common.validation.text import validate_readable_name

        name = validate_readable_name(data.get("name"), field_label="Classroom name")

        if self.repo.classroom_name_exists(company_id=company_id, name=name):
            return False, ERR_CLASSROOM_EXISTS, None

        payload = {
            "name": name,
            "room_number": (data.get("room_number") or "").strip() or None,
            "is_enabled": bool(data.get("is_enabled", True)),
        }
        return self.classroom_svc.create(company_id=company_id, data=payload)

    def update_classroom(self, *, company_id: int, classroom_id: int, data: Dict[str, Any]):
        obj = self.repo.classrooms.get(int(classroom_id), company_id=int(company_id))
        if not obj:
            return False, ERR_CLASSROOM_NOT_FOUND, None

        patch: Dict[str, Any] = {}
        if "name" in data and data["name"] is not None:
            from cmcp.common.validation.text import validate_readable_name

            name = validate_readable_name(data.get("name"), field_label="Classroom name")
            if self.repo.classroom_name_exists(company_id=company_id, name=name, exclude_id=obj.id):
                return False, ERR_CLASSROOM_EXISTS, None
            patch["name"] = name

        if "room_number" in data:
            patch["room_number"] = (data.get("room_number") or "").strip() or None

        if "is_enabled" in data:
            patch["is_enabled"] = bool(data["is_enabled"])

        return self.classroom_svc.update(company_id=company_id, id=classroom_id, data=patch)

    def delete_classroom(self, *, company_id: int, classroom_id: int, soft: bool = True):
        obj = self.repo.classrooms.get(int(classroom_id), company_id=int(company_id))
        if not obj:
            return False, ERR_CLASSROOM_NOT_FOUND, None
        return self.classroom_svc.delete(company_id=company_id, id=classroom_id, soft=soft)

    def bulk_delete_classrooms(self, *, company_id: int, ids: List[int], soft: bool = True):
        return self.classroom_svc.bulk_delete(company_id=company_id, ids=ids, soft=soft)

    def list_classrooms(self, *, company_id: int, mode: str, args: Dict[str, Any]) -> Dict[str, Any]:
        allowed_filters = {"is_enabled": Classroom.is_enabled, "name": Classroom.name}
        sort_fields = {"id": Classroom.id, "name": Classroom.name, "created_at": getattr(Classroom, "created_at", Classroom.id)}

        if mode == "scroll":
            return self.classroom_svc.list_scroll(
                company_id=company_id,
                limit=args["limit"],
                offset=args["offset"],
                search=args.get("q"),
                search_columns=[Classroom.name, Classroom.room_number],
                filters=args.get("filters"),
                allowed_filters=allowed_filters,
                sort_key=args.get("sort_key"),
                sort_order=args.get("sort_order"),
                sort_fields=sort_fields,
                default_sort=[Classroom.name.asc()],
                only_enabled=False,
            )

        return self.classroom_svc.list_page(
            company_id=company_id,
            page=args["page"],
            per_page=args["per_page"],
            search=args.get("q"),
            search_columns=[Classroom.name, Classroom.room_number],
            filters=args.get("filters"),
            allowed_filters=allowed_filters,
            sort_key=args.get("sort_key"),
            sort_order=args.get("sort_order"),
            sort_fields=sort_fields,
            default_sort=[Classroom.name.asc()],
            only_enabled=False,
        )

    def get_classroom(self, *, company_id: int, classroom_id: int) -> Optional[Dict[str, Any]]:
        return self.classroom_svc.get_one(company_id=company_id, id=classroom_id)

        # =========================================================
        # STEP 1-3: Register student -> enqueue verify email
        # =========================================================

    def _send_verification_email_best_effort(self, row) -> None:
        try:
            self.email_svc.send_outbox_row_now(row)
        except Exception:
            log.warning(
                "Verification email immediate send failed; outbox worker will retry. outbox_id=%s",
                getattr(row, "id", None),
                exc_info=True,
            )

    def register_student(self, *, company_id: int, data: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        from cmcp.common.validation.text import validate_readable_name, validate_student_id

        student_id = validate_student_id(data.get("student_id"))
        email = normalize_email(data.get("email"))
        full_name = validate_readable_name(data.get("full_name"), field_label="Full name")

        faculty_id = int(data.get("faculty_id") or 0)
        department_id = int(data.get("department_id") or 0)
        semester_id = int(data.get("semester_id") or 0)

        classroom_id = data.get("classroom_id")
        classroom_id = int(classroom_id) if classroom_id else None

        if not semester_id:
            return False, "Current semester is required.", None

        # validations
        if not self.repo.faculty_exists(company_id=company_id, faculty_id=faculty_id):
            return False, ERR_FACULTY_NOT_FOUND, None
        if not self.repo.department_exists(company_id=company_id, department_id=department_id, faculty_id=faculty_id):
            return False, ERR_DEPARTMENT_NOT_FOUND, None
        if not self.repo.semester_exists(company_id=company_id, semester_id=semester_id):
            return False, ERR_SEMESTER_NOT_FOUND, None
        if classroom_id and not self.repo.classroom_exists(company_id=company_id, classroom_id=classroom_id):
            return False, ERR_CLASSROOM_NOT_FOUND, None

        if self.repo.user_by_username(student_id=student_id) or self.repo.student_profile_by_student_id(
                company_id=company_id, student_id=student_id
        ):
            return False, ERR_STUDENT_ID_EXISTS, None

        if self.repo.user_by_email(email=email):
            return False, ERR_EMAIL_EXISTS, None

        ttl = int(os.getenv("EMAIL_VERIFY_TOKEN_TTL_MINUTES", "30"))
        base_url = (os.getenv("APP_BASE_URL", "").rstrip("/")) or "http://localhost:5000"

        try:
            with self.s.begin_nested():
                user = User(
                    username=student_id,
                    password_hash="!DISABLED!",
                    email=email,
                    user_type=UserTypeEnum.STUDENT,
                    status=UserStatusEnum.PENDING_EMAIL,
                    is_enabled=False,
                    must_change_password=False,
                )
                self.s.add(user)
                self.s.flush()

                prof = StudentProfile(
                    user_id=user.id,
                    company_id=int(company_id),
                    full_name=full_name,
                    student_id=student_id,
                    faculty_id=faculty_id,
                    department_id=department_id,
                    classroom_id=classroom_id,
                    semester_id=semester_id,
                    is_enabled=True,
                )
                self.s.add(prof)
                self.s.flush()

                aff = UserAffiliation(
                    user_id=user.id,
                    company_id=int(company_id),
                    is_primary=True,
                    is_enabled=False,
                    linked_entity_type=LinkedEntityTypeEnum.STUDENT_PROFILE,
                    linked_entity_id=prof.id,
                )
                self.s.add(aff)

                tok = generate_email_verify_token(ttl_minutes=ttl)
                user.email_verify_token_hash = tok.token_hash
                user.email_verify_expires_at = tok.expires_at

                verify_link = f"{base_url}/verify-email?username={student_id}&token={tok.token}"

                self.email_svc.enqueue(
                    to_email=user.email,
                    subject="Verify your JustClick student email",
                    template="verify_email",
                    payload={
                        "full_name": prof.full_name,
                        "student_id": student_id,
                        "verify_link": verify_link,
                        "expires_minutes": ttl,
                    },
                    ref_type="User",
                    ref_id=user.id,
                )

            return True, "Registration submitted. Please check your email to verify your address.", {
                "student_id": student_id,
                "email": email,
                "status": UserStatusEnum.PENDING_EMAIL.value,
            }

        except Exception as e:
            log.exception("register_student failed. student_id=%s email=%s", student_id, email)
            try:
                self.s.rollback()
            except Exception:
                pass
            return False, "Registration could not be completed. Please try again.", None


        # =========================================================
        # STEP 4: Verify email
        # =========================================================

    def verify_email(self, *, username: str, token: str) -> Tuple[bool, str]:
        username = (username or "").strip()
        token = (token or "").strip()
        if not username or not token:
            return False, "Invalid verification request."

        user = self.s.query(User).filter(User.username == username).first()
        if not user:
            return False, "Invalid verification request."

        if user.status == UserStatusEnum.REJECTED:
            return False, ERR_ADMIN_REJECTED

        if user.status == UserStatusEnum.PENDING_APPROVAL:
            return False, ERR_PENDING_APPROVAL

        if user.status != UserStatusEnum.PENDING_EMAIL:
            return True, "Email already verified."

        if not user.email_verify_token_hash or not user.email_verify_expires_at:
            return False, ERR_VERIFY_EXPIRED

        if _utcnow() > user.email_verify_expires_at:
            return False, ERR_VERIFY_EXPIRED

        if not verify_token(token, user.email_verify_token_hash):
            return False, "Invalid verification token."

        user.email_verified_at = _utcnow()
        user.email_verify_token_hash = None
        user.email_verify_expires_at = None
        user.status = UserStatusEnum.PENDING_APPROVAL
        self.s.commit()

        return True, "✅ Email Verified Successfully! Your account is now pending admin approval."

    # =========================================================
    # STEP 6: Admin approve (temp password length 6)
    # =========================================================

    def _approval_email_payload_for_student(
            self,
            *,
            user: User,
            prof: StudentProfile,
            temp_pw: str,
    ) -> Dict[str, Any]:
        faculty_name = ""
        department_name = ""

        fac = self.s.query(Faculty).filter(
            Faculty.id == prof.faculty_id,
            Faculty.company_id == prof.company_id,
        ).first()

        dep = self.s.query(Department).filter(
            Department.id == prof.department_id,
            Department.company_id == prof.company_id,
        ).first()

        if fac:
            faculty_name = fac.name or ""

        if dep:
            department_name = dep.name or ""

        base_url = (os.getenv("APP_BASE_URL", "").rstrip("/")) or "http://localhost:3000"

        return {
            "full_name": prof.full_name,
            "student_id": user.username,
            "temp_password": temp_pw,
            "login_link": f"{base_url}/login",
            "expires_hours": int(os.getenv("TEMP_PASSWORD_TTL_HOURS", "24")),
            "faculty_name": faculty_name,
            "department_name": department_name,
        }

    def _enqueue_approval_email(
            self,
            *,
            user: User,
            prof: StudentProfile,
            temp_pw: str,
    ):
        row = self.email_svc.enqueue(
            to_email=user.email,
            subject="Your Jamhuriya University Portal Account is Approved!",
            template="approved",
            payload=self._approval_email_payload_for_student(
                user=user,
                prof=prof,
                temp_pw=temp_pw,
            ),
            ref_type="User",
            ref_id=int(user.id),
        )
        self.s.flush([row])
        return row

    def _send_approval_email_best_effort(self, row) -> None:
        try:
            self.email_svc.send_outbox_row_now(row)
        except Exception:
            log.warning(
                "Approval email immediate send failed; outbox worker will retry. outbox_id=%s",
                getattr(row, "id", None),
                exc_info=True,
            )

    def _set_new_temp_password(self, *, user: User) -> str:
        temp_pw = generate_temp_password(6)

        user.password_hash = hash_password(temp_pw)
        user.must_change_password = True
        user.temp_password_expires_at = _utcnow() + timedelta(
            hours=int(os.getenv("TEMP_PASSWORD_TTL_HOURS", "24"))
        )

        return temp_pw

    def _ensure_user_role_by_name(
            self,
            *,
            company_id: int,
            user_id: int,
            role_name: str,
    ) -> None:
        """
        Assign a global Role to a user inside this company.

        Important:
        - Role has NO company_id in your setup.
        - UserRole has company_id because assignment is company-scoped.
        """
        role = self.s.scalar(
            select(Role).where(
                func.lower(Role.name) == str(role_name).strip().lower(),
                Role.is_enabled.is_(True),
            )
        )

        if not role:
            raise ValueError(f"Required role '{role_name}' does not exist or is disabled.")

        existing = self.s.scalar(
            select(UserRole).where(
                UserRole.company_id == int(company_id),
                UserRole.user_id == int(user_id),
                UserRole.role_id == int(role.id),
            )
        )

        if existing:
            existing.is_enabled = True
            return

        self.s.add(
            UserRole(
                company_id=int(company_id),
                user_id=int(user_id),
                role_id=int(role.id),
                is_enabled=True,
            )
        )
    def admin_approve(
            self,
            *,
            user_id: int,
            admin_user_id: int,
            send_now: bool = True,
    ) -> Tuple[bool, str]:
        user = (
            self.s.query(User)
            .options(joinedload(User.affiliations))
            .filter(User.id == int(user_id))
            .first()
        )

        if not user:
            return False, "User not found."

        if user.user_type != UserTypeEnum.STUDENT:
            return False, "Only student accounts can be approved here."

        if user.status != UserStatusEnum.PENDING_APPROVAL:
            return False, "User is not pending approval."

        prof = (
            self.s.query(StudentProfile)
            .filter(StudentProfile.user_id == int(user.id))
            .first()
        )

        if not prof:
            return False, "Student profile not found."

        try:
            with self.s.begin_nested():
                temp_pw = self._set_new_temp_password(user=user)

                user.is_enabled = True
                user.status = UserStatusEnum.ACTIVE
                user.approved_at = _utcnow()
                user.approved_by = int(admin_user_id)

                for aff in user.affiliations or []:
                    if int(aff.company_id) == int(prof.company_id):
                        aff.is_enabled = True

                self._ensure_user_role_by_name(
                    company_id=int(prof.company_id),
                    user_id=int(user.id),
                    role_name="Student",
                )

                row = self._enqueue_approval_email(
                    user=user,
                    prof=prof,
                    temp_pw=temp_pw,
                )

                if send_now:
                    self._send_approval_email_best_effort(row)

                self.s.flush()

            try:
                bump_user_profile(int(user.id), int(prof.company_id))
                remove_session(int(user.id))
            except Exception:
                log.warning("Post-approval cache/session cleanup failed.", exc_info=True)

            return True, "Approved and approval email sent."

        except Exception as e:
            log.exception("admin_approve failed user_id=%s", user_id)
            try:
                self.s.rollback()
            except Exception:
                pass
            return False, f"Approval failed: {str(e)}"

    def resend_student_approval_email(
            self,
            *,
            company_id: int,
            user_id: int,
            admin_user_id: int,
            send_now: bool = True,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        row = (
            self.s.query(User, StudentProfile)
            .join(StudentProfile, StudentProfile.user_id == User.id)
            .filter(
                User.id == int(user_id),
                StudentProfile.company_id == int(company_id),
                User.user_type == UserTypeEnum.STUDENT,
            )
            .first()
        )

        if not row:
            return False, "Student user not found.", None

        user, prof = row

        if user.status != UserStatusEnum.ACTIVE or not user.is_enabled:
            return False, "Student must be approved and active before resending login email.", None

        if not user.email_verified_at:
            return False, "Student email is not verified yet.", None

        try:
            with self.s.begin_nested():
                temp_pw = self._set_new_temp_password(user=user)

                self._ensure_user_role_by_name(
                    company_id=int(company_id),
                    user_id=int(user.id),
                    role_name="Student",
                )

                email_row = self._enqueue_approval_email(
                    user=user,
                    prof=prof,
                    temp_pw=temp_pw,
                )

                if send_now:
                    self._send_approval_email_best_effort(email_row)

                self.s.flush()

            try:
                bump_user_profile(int(user.id), int(company_id))
                remove_session(int(user.id))
            except Exception:
                log.warning("Post-resend cache/session cleanup failed.", exc_info=True)

            return True, "Approval email resent with a new temporary password.", {
                "user_id": int(user.id),
                "email": user.email,
            }

        except Exception as e:
            log.exception("resend_student_approval_email failed user_id=%s", user_id)
            try:
                self.s.rollback()
            except Exception:
                pass
            return False, f"Could not resend approval email. ({str(e)})", None

    def bulk_resend_student_approval_emails(
            self,
            *,
            company_id: int,
            user_ids: List[int],
            admin_user_id: int,
            send_now: bool = False,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        clean_ids = sorted({int(x) for x in (user_ids or []) if int(x or 0) > 0})

        if not clean_ids:
            return False, "No student users selected.", {
                "queued": 0,
                "sent": 0,
                "skipped": [],
            }

        max_bulk = int(os.getenv("APPROVAL_EMAIL_BULK_MAX", "200"))
        if len(clean_ids) > max_bulk:
            return False, f"Cannot process more than {max_bulk} students at once.", {
                "queued": 0,
                "sent": 0,
                "skipped": [],
            }

        rows = (
            self.s.query(User, StudentProfile)
            .join(StudentProfile, StudentProfile.user_id == User.id)
            .filter(
                User.id.in_(clean_ids),
                StudentProfile.company_id == int(company_id),
                User.user_type == UserTypeEnum.STUDENT,
            )
            .all()
        )

        found_by_id = {int(user.id): (user, prof) for user, prof in rows}
        skipped = []
        processed = 0

        try:
            with self.s.begin_nested():
                for uid in clean_ids:
                    pair = found_by_id.get(uid)

                    if not pair:
                        skipped.append({
                            "user_id": uid,
                            "reason": "Student user not found.",
                        })
                        continue

                    user, prof = pair

                    if user.status != UserStatusEnum.ACTIVE or not user.is_enabled:
                        skipped.append({
                            "user_id": uid,
                            "reason": "Student is not approved and active.",
                        })
                        continue

                    if not user.email_verified_at:
                        skipped.append({
                            "user_id": uid,
                            "reason": "Student email is not verified.",
                        })
                        continue

                    temp_pw = self._set_new_temp_password(user=user)

                    self._ensure_user_role_by_name(
                        company_id=int(company_id),
                        user_id=int(user.id),
                        role_name="Student",
                    )

                    email_row = self._enqueue_approval_email(
                        user=user,
                        prof=prof,
                        temp_pw=temp_pw,
                    )

                    if send_now:
                        self._send_approval_email_best_effort(email_row)

                    processed += 1

                self.s.flush()

            for uid in clean_ids:
                try:
                    bump_user_profile(int(uid), int(company_id))
                    remove_session(int(uid))
                except Exception:
                    pass

            return True, "Approval emails processed.", {
                "queued": 0 if send_now else processed,
                "sent": processed if send_now else 0,
                "skipped": skipped,
            }

        except Exception as e:
            log.exception("bulk_resend_student_approval_emails failed")
            try:
                self.s.rollback()
            except Exception:
                pass

            return False, f"Could not process approval emails. ({str(e)})", {
                "queued": 0,
                "sent": 0,
                "skipped": skipped,
            }
    # =========================================================
    # LIST (CURSOR)
    # =========================================================

    def list_students_cursor(
            self,
            *,
            company_id: int,
            limit: int,
            cursor: Optional[str],
            filters: Dict[str, Any],
            is_enabled: Optional[bool],
            external_base: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        limit = max(1, min(int(limit or 20), 100))

        cur = _decode_cursor(cursor or "")
        last_id = cur.get("last_id")
        try:
            last_id = int(last_id) if last_id is not None else None
        except Exception:
            last_id = None

        user_id = getattr(getattr(g, "auth", None), "user_id", None)

        params = {
            "mode": "cursor",
            "limit": limit,
            "last_id": last_id,
            "filters": filters,
            "is_enabled": is_enabled,
            "external_base": external_base,
            "user_id": int(user_id) if user_id is not None else None,
        }

        def builder():
            rows, total_count, has_more = self.repo.list_students_cursor(
                company_id=company_id,
                limit=limit,
                last_id=last_id,
                filters=filters,
                is_enabled=is_enabled,
            )

            data = [self.repo.shape_student_list_row(r, external_base=external_base) for r in rows]

            next_cursor = None
            if has_more and rows:
                next_cursor = _encode_cursor({"last_id": int(rows[-1].id)})

            return {
                "data": data,
                "pagination": {
                    "limit": limit,
                    "next_cursor": next_cursor,
                    "has_more": bool(has_more),
                },
                "meta": {"total_count": int(total_count)},
            }

        out = cached_list(
            entity="students:list",
            company_id=company_id,
            params=params,
            scope="default",
            ttl=20,
            builder=builder,
        )

        return True, "OK", out

        # =========================================================
        # LIST (PAGE)
        # =========================================================

    def list_students_page(
            self,
            *,
            company_id: int,
            page: int,
            per_page: int,
            filters: Dict[str, Any],
            is_enabled: Optional[bool],
            external_base: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        allowed = {10, 20, 50, 500}
        per_page = per_page if int(per_page or 20) in allowed else 20
        page = max(int(page or 1), 1)

        user_id = getattr(getattr(g, "auth", None), "user_id", None)

        params = {
            "mode": "page",
            "page": page,
            "per_page": per_page,
            "filters": filters,
            "is_enabled": is_enabled,
            "external_base": external_base,
            "user_id": int(user_id) if user_id is not None else None,
        }

        def builder():
            rows, total_count, pages = self.repo.list_students_page(
                company_id=company_id,
                page=page,
                per_page=per_page,
                filters=filters,
                is_enabled=is_enabled,
            )

            data = [self.repo.shape_student_list_row(r, external_base=external_base) for r in rows]

            return {
                "data": data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "pages": int(pages),
                    "total_count": int(total_count),
                },
            }

        out = cached_list(
            entity="students:list",
            company_id=company_id,
            params=params,
            scope="default",
            ttl=20,
            builder=builder,
        )

        return True, "OK", out




    # =========================================================
    # DASHBOARD HELPERS
    # =========================================================
    def _trend_payload(self, *, current: int, previous: int) -> Dict[str, Any]:
        current = int(current or 0)
        previous = int(previous or 0)

        if previous <= 0 and current <= 0:
            return {"change_percent": 0.0, "trend": "flat"}

        if previous <= 0 and current > 0:
            return {"change_percent": 100.0, "trend": "up"}

        pct = ((current - previous) / previous) * 100.0
        trend = "up" if pct > 0 else "down" if pct < 0 else "flat"
        return {
            "change_percent": round(abs(pct), 1),
            "trend": trend,
        }

    def _month_start(self, dt: datetime) -> datetime:
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    def _add_months(self, dt: datetime, months: int) -> datetime:
        year = dt.year + ((dt.month - 1 + months) // 12)
        month = ((dt.month - 1 + months) % 12) + 1
        return dt.replace(year=year, month=month, day=1)

    # =========================================================
    # DASHBOARD
    # =========================================================
    def get_admin_dashboard(self, *, company_id: int, months: int = 4) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Dashboard summary for admin.
        - cards use current totals
        - trend compares last 30 days vs previous 30 days
        - user growth chart uses monthly buckets
        """
        now = datetime.now(timezone.utc)

        current_period_start = now - timedelta(days=30)
        previous_period_start = now - timedelta(days=60)
        previous_period_end = current_period_start

        # -------------------------
        # users
        # -------------------------
        user_type_counts = self.repo.dashboard_user_type_counts(company_id=company_id)
        total_users = self.repo.dashboard_total_users(company_id=company_id)

        current_new_users = self.repo.dashboard_new_user_counts_between(
            company_id=company_id,
            start_dt=current_period_start,
            end_dt=now,
        )
        previous_new_users = self.repo.dashboard_new_user_counts_between(
            company_id=company_id,
            start_dt=previous_period_start,
            end_dt=previous_period_end,
        )
        total_users_trend = self._trend_payload(
            current=current_new_users["total"],
            previous=previous_new_users["total"],
        )

        # -------------------------
        # pending approvals
        # -------------------------
        pending = self.repo.dashboard_pending_approval_counts(company_id=company_id)

        current_pending_new = self.repo.dashboard_pending_new_between(
            company_id=company_id,
            start_dt=current_period_start,
            end_dt=now,
        )
        previous_pending_new = self.repo.dashboard_pending_new_between(
            company_id=company_id,
            start_dt=previous_period_start,
            end_dt=previous_period_end,
        )
        pending_trend = self._trend_payload(
            current=current_pending_new,
            previous=previous_pending_new,
        )

        # -------------------------
        # materials
        # -------------------------
        material_type_counts = self.repo.dashboard_material_type_counts(company_id=company_id)
        total_materials = self.repo.dashboard_total_materials(company_id=company_id)

        current_new_materials = self.repo.dashboard_new_materials_between(
            company_id=company_id,
            start_dt=current_period_start,
            end_dt=now,
        )
        previous_new_materials = self.repo.dashboard_new_materials_between(
            company_id=company_id,
            start_dt=previous_period_start,
            end_dt=previous_period_end,
        )
        materials_trend = self._trend_payload(
            current=current_new_materials,
            previous=previous_new_materials,
        )

        analytics = self.repo.dashboard_global_material_analytics(company_id=company_id)
        analytics_value = int(analytics["total_views"] + analytics["total_downloads"])

        total_students = self.repo.dashboard_total_students(company_id=company_id)
        students_by_department = self.repo.dashboard_students_by_department(company_id=company_id)
        materials_by_department = self.repo.dashboard_materials_by_department(company_id=company_id)

        current_new_students = int(current_new_users.get("students") or 0)
        previous_new_students = int(previous_new_users.get("students") or 0)
        students_trend = self._trend_payload(
            current=current_new_students,
            previous=previous_new_students,
        )

        # NOTE:
        # This trend is a best-effort proxy from recent interaction timestamps.
        # For true monthly views/downloads trend, use an event log or daily snapshot table.
        current_activity_proxy = self.repo.dashboard_recent_material_activity_proxy_between(
            company_id=company_id,
            start_dt=current_period_start,
            end_dt=now,
        )
        previous_activity_proxy = self.repo.dashboard_recent_material_activity_proxy_between(
            company_id=company_id,
            start_dt=previous_period_start,
            end_dt=previous_period_end,
        )
        analytics_trend = self._trend_payload(
            current=current_activity_proxy,
            previous=previous_activity_proxy,
        )

        # -------------------------
        # chart: user growth
        # -------------------------
        months = max(1, min(int(months or 4), 12))
        chart_start = self._add_months(self._month_start(now), -(months - 1))
        chart_end = self._add_months(self._month_start(now), 1)

        growth_rows = self.repo.dashboard_user_growth_monthly(
            company_id=company_id,
            start_dt=chart_start,
            end_dt=chart_end,
        )

        growth_map: Dict[str, Dict[str, int]] = {}
        for row in growth_rows:
            month_key = row["month_start"].strftime("%Y-%m")
            if month_key not in growth_map:
                growth_map[month_key] = {
                    "students": 0,
                    "lecturers": 0,
                    "staff": 0,
                    "admins": 0,
                    "new_users": 0,
                }

            total = int(row["total"] or 0)
            growth_map[month_key]["new_users"] += total

            if row["user_type"] == UserTypeEnum.STUDENT.value:
                growth_map[month_key]["students"] += total
            elif row["user_type"] == UserTypeEnum.TEACHER.value:
                growth_map[month_key]["lecturers"] += total
            elif row["user_type"] == UserTypeEnum.STAFF.value:
                growth_map[month_key]["staff"] += total
            elif row["user_type"] == UserTypeEnum.ADMIN.value:
                growth_map[month_key]["admins"] += total

        chart_points = []
        cur = chart_start
        while cur < chart_end:
            key = cur.strftime("%Y-%m")
            item = growth_map.get(key, {
                "students": 0,
                "lecturers": 0,
                "staff": 0,
                "admins": 0,
                "new_users": 0,
            })

            chart_points.append({
                "label": py_calendar.month_abbr[cur.month],
                "new_users": int(item["new_users"]),
                "students": int(item["students"]),
                "lecturers": int(item["lecturers"]),
                "staff": int(item["staff"]),
                "admins": int(item["admins"]),
            })
            cur = self._add_months(cur, 1)

        data = {
            "summary_cards": {
                "total_users": {
                    "value": int(total_users),
                    "change_percent": total_users_trend["change_percent"],
                    "trend": total_users_trend["trend"],
                    "meta": {
                        "student_count": int(user_type_counts["students"]),
                        "admin_count": int(user_type_counts["admins"]),
                    },
                },
                "pending_user_approvals": {
                    "value": int(pending["value"]),
                    "change_percent": pending_trend["change_percent"],
                    "trend": pending_trend["trend"],
                    "meta": {
                        "student_count": int(pending["students"]),
                        "admin_count": int(pending["admins"]),
                        "approval_stages": {
                            "pending_email_verification": int(
                                pending["approval_stages"]["pending_email_verification"]
                            ),
                            "pending_admin_approval": int(
                                pending["approval_stages"]["pending_admin_approval"]
                            ),
                        },
                    },
                },
                "total_materials": {
                    "value": int(total_materials),
                    "change_percent": materials_trend["change_percent"],
                    "trend": materials_trend["trend"],
                    "meta": {
                        "slides": int(material_type_counts["slides"]),
                        "pdf": int(material_type_counts["pdf"]),
                        "doc": int(material_type_counts["doc"]),
                        "video": int(material_type_counts["video"]),
                        "link": int(material_type_counts["link"]),
                        "other": int(material_type_counts["other"]),
                    },
                },
                "global_material_analytics": {
                    "value": int(analytics_value),
                    "change_percent": analytics_trend["change_percent"],
                    "trend": analytics_trend["trend"],
                    "meta": {
                        "total_views": int(analytics["total_views"]),
                        "total_downloads": int(analytics["total_downloads"]),
                    },
                },
                "total_students": {
                    "value": int(total_students),
                    "change_percent": students_trend["change_percent"],
                    "trend": students_trend["trend"],
                    "meta": {
                        "departments": int(len(students_by_department)),
                    },
                },
            },
            "charts": {
                "user_growth": chart_points,
                "materials_by_department": materials_by_department,
                "students_by_department": students_by_department,
            },
        }

        return True, "Dashboard data fetched successfully", {
            "data": data,
            "generated_at": now.isoformat(),
        }

    def list_onboarding_students_page(
            self,
            *,
            company_id: int,
            page: int,
            per_page: int,
            filters: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        rows, total, pages = self.onboarding_repo.list_onboarding_students_page(
            company_id=int(company_id),
            page=int(page or 1),
            per_page=int(per_page or 20),
            filters=filters or {},
        )

        data = [self.onboarding_repo.shape_onboarding_list_row(r) for r in rows]

        message = "OK"
        if not data:
            status = (filters.get("status") or "pending_approval").strip().lower()
            if status == "pending_email":
                message = "No students are waiting for email verification."
            elif status in {"pending", "pending_approval"}:
                message = "No students are waiting for approval."
            else:
                message = "No students found."

        return True, message, {
            "data": data,
            "message": None if data else message,
            "pagination": {
                "page": int(page or 1),
                "limit": int(per_page or 20),
                "total": int(total),
                "has_more": int(page or 1) < int(pages),
            },
        }

    def get_onboarding_student_detail(
            self,
            *,
            company_id: int,
            user_id: int,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        row = self.onboarding_repo.get_onboarding_student_detail(
            company_id=int(company_id),
            user_id=int(user_id),
        )

        if not row:
            return False, "Student onboarding record not found.", {}

        return True, "OK", {
            "data": self.onboarding_repo.shape_onboarding_detail_row(row)
        }