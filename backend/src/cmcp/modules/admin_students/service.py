from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.exc import IntegrityError

from cmcp.common.cache import bump_list, bump_detail, bump_user_profile
from cmcp.common.cache.session_manager import remove_session
from cmcp.common.email.service import EmailService
from cmcp.common.security.passwords import generate_temp_password, hash_password
from cmcp.common.security.password_rules import ensure_password_ok
from cmcp.core.exceptions import BusinessValidationError, NotFoundError
from cmcp.modules.admin_students.repository import AdminStudentsRepository
from cmcp.modules.auth.models import User, UserStatusEnum
from cmcp.modules.education_people.models import StudentProfile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AdminStudentsService:
    def __init__(self):
        self.repo = AdminStudentsRepository()

    def list_students(self, company_id: int, page: int, limit: int, filters: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        from cmcp.common.cache import cached_list

        params = {
            "mode": "page",
            "page": page,
            "limit": limit,
            "filters": filters,
        }

        def builder():
            offset = (page - 1) * limit
            rows, total = self.repo.list_students(company_id, limit, offset, filters)
            return {
                "data": rows,
                "meta": {"total_count": total},
                "pagination": {
                    "limit": limit,
                    "next_cursor": None,
                    "has_more": (offset + limit) < total,
                },
            }

        out = cached_list(
            entity="admin_students:list",
            company_id=company_id,
            params=params,
            scope="default",
            ttl=20,
            builder=builder,
        )
        return True, "OK", out

    def get_student(self, company_id: int, student_profile_id: int) -> Tuple[bool, str, Dict[str, Any]]:
        from cmcp.common.cache import cached_detail

        def builder():
            return self.repo.get_student(company_id, student_profile_id)

        data = cached_detail(
            entity="admin_students:detail",
            company_id=company_id,
            record_id=student_profile_id,
            ttl=20,
            builder=builder,
        )
        if not data:
            raise NotFoundError("Student not found")
        return True, "OK", {"data": data}

    def update_student(
        self,
        company_id: int,
        student_profile_id: int,
        data: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        prof = self.repo.profiles.get(int(student_profile_id), company_id=int(company_id))
        if not prof:
            return False, "Student not found.", {}

        user = self.repo.s.get(User, int(prof.user_id))
        if not user:
            return False, "Student user account not found.", {}

        try:
            if "full_name" in data and data["full_name"]:
                prof.full_name = str(data["full_name"]).strip()

            if "student_id" in data and data["student_id"]:
                prof.student_id = str(data["student_id"]).strip()

            if "username" in data and data["username"]:
                user.username = str(data["username"]).strip()

            if "email" in data and data["email"]:
                user.email = str(data["email"]).strip().lower()

            faculty_id = int(data["faculty_id"]) if data.get("faculty_id") else int(prof.faculty_id)
            if "faculty_id" in data and data["faculty_id"]:
                prof.faculty_id = faculty_id

            if "department_id" in data and data["department_id"]:
                dept_id = int(data["department_id"])
                if not self.repo.department_belongs_to_faculty(
                    company_id=company_id,
                    department_id=dept_id,
                    faculty_id=faculty_id,
                ):
                    raise BusinessValidationError(
                        "Selected department does not belong to the selected faculty."
                    )
                prof.department_id = dept_id

            if "semester_id" in data:
                prof.semester_id = int(data["semester_id"]) if data["semester_id"] else None

            if "classroom_id" in data:
                prof.classroom_id = int(data["classroom_id"]) if data["classroom_id"] else None

            if "profile_enabled" in data:
                prof.is_enabled = bool(data["profile_enabled"])
            elif "is_enabled" in data and "account_enabled" not in data and "user_is_enabled" not in data:
                prof.is_enabled = bool(data["is_enabled"])

            if "account_enabled" in data or "user_is_enabled" in data:
                user.is_enabled = bool(
                    data.get("account_enabled", data.get("user_is_enabled"))
                )
                if not user.is_enabled:
                    remove_session(int(user.id))

            self.repo.s.flush()
            bump_list("admin_students:list", company_id)
            bump_detail("admin_students:detail", company_id, student_profile_id)
            bump_user_profile(int(user.id), company_id)

            updated = self.repo.get_student(company_id, student_profile_id)
            return True, "Student updated successfully.", {"data": updated}
        except BusinessValidationError as e:
            return False, str(e), {}
        except IntegrityError:
            return False, "Duplicate username, email, or student ID.", {}
        except Exception as e:
            return False, f"Unexpected error: {e}", {}

    def reset_student_password(
        self,
        *,
        company_id: int,
        student_profile_id: int,
        mode: str = "email",
        new_password: Optional[str] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        prof = self.repo.profiles.get(int(student_profile_id), company_id=int(company_id))
        if not prof:
            return False, "Student not found.", {}

        user = self.repo.s.get(User, int(prof.user_id))
        if not user:
            return False, "Student user account not found.", {}

        if user.status != UserStatusEnum.ACTIVE:
            return False, "Student must be approved and active before resetting password.", {}

        if mode == "manual":
            if not new_password:
                return False, "New password is required for manual reset.", {}
            ensure_password_ok(new_password)
            temp_pw = str(new_password)
        else:
            temp_pw = generate_temp_password(8)
            ensure_password_ok(temp_pw)

        user.password_hash = hash_password(temp_pw)
        user.must_change_password = True
        user.temp_password_expires_at = _utcnow() + timedelta(hours=int(os.getenv("TEMP_PASSWORD_EXPIRES_HOURS", "72")))
        self.repo.s.flush()

        remove_session(int(user.id))
        bump_user_profile(int(user.id), company_id)

        queued = None
        if mode == "email":
            email_svc = EmailService(
                session=self.repo.s,
                provider=os.getenv("MAIL_PROVIDER", "smtp"),
                from_email=os.getenv("MAIL_FROM_EMAIL", ""),
                from_name=os.getenv("MAIL_FROM_NAME", "JustClick"),
            )
            login_link = (os.getenv("APP_BASE_URL") or os.getenv("FRONTEND_BASE_URL") or "http://localhost:3000").rstrip("/")
            row = email_svc.enqueue(
                to_email=user.email,
                subject="Your password has been reset",
                template="student_password_reset",
                payload={
                    "full_name": prof.full_name,
                    "student_id": prof.student_id,
                    "username": user.username,
                    "temp_password": temp_pw,
                    "login_link": login_link,
                    "expires_hours": int(os.getenv("TEMP_PASSWORD_EXPIRES_HOURS", "72")),
                },
                ref_type="User",
                ref_id=int(user.id),
            )
            queued = int(row.id)

        msg = (
            "Password reset and email queued."
            if mode == "email"
            else "Password updated manually."
        )
        out = {
            "user_id": int(user.id),
            "mode": mode,
            "email_outbox_id": queued,
        }
        if mode == "manual":
            out["temp_password"] = temp_pw
        return True, msg, out
