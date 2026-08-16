from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

from flask import Blueprint, request, session, make_response, current_app

from cmcp.api.material_api import _external_base
from cmcp.common.api_response import api_success, api_error
from cmcp.common.decorators import rate_limit
from cmcp.common.email.outbox_model import EmailOutboxStatus, EmailOutbox
from cmcp.common.email.service import EmailService
from cmcp.common.security.tokens import generate_email_verify_token
from cmcp.config.database import db
from cmcp.core.auth import public
from cmcp.core.exceptions import BusinessValidationError, NotFoundError
from cmcp.core.tenant_resolver import resolve_company_id_for_public
from cmcp.modules.auth.deps import get_current_user
from cmcp.modules.auth.models import UserStatusEnum, User, UserAffiliation
from cmcp.security.rbac_guards import require_company_and_permission, require_permission
from pydantic import BaseModel, Field, ValidationError
from typing import List
from cmcp.common.validation.pydantic_errors import clean_pydantic_error
from cmcp.modules.education_people.schemas import (
    BulkDeleteIn,
    ClassroomCreate, ClassroomUpdate, StudentRegisterIn, BulkApproveIn,

)
from cmcp.modules.education_people.service import EducationPeopleService

bp = Blueprint("education_people", __name__, url_prefix="/api/education_people")
svc = EducationPeopleService()


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "y", "on")
    return bool(v)


def _parse_filters() -> Dict[str, Any] | None:
    raw = request.args.get("filters")
    if raw:
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    filters: Dict[str, Any] = {}
    if "is_enabled" in request.args:
        filters["is_enabled"] = _as_bool(request.args.get("is_enabled"))
    return filters or None


def _list_args() -> Tuple[str | None, str | None, str | None, int, int, Optional[int], Optional[int], Dict[str, Any] | None]:
    q = request.args.get("q")
    sort_key = request.args.get("sort_key")
    sort_order = request.args.get("sort_order")

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    limit = request.args.get("limit", type=int)
    offset = request.args.get("offset", type=int)

    return q, sort_key, sort_order, page, per_page, limit, offset, _parse_filters()


def _list_mode(limit: Optional[int], offset: Optional[int]) -> str:
    return "scroll" if (limit is not None or offset is not None) else "page"


def _commit_ok(ok: bool):
    if ok:
        db.session.commit()
    else:
        db.session.rollback()


def _handle_error(e: Exception):
    db.session.rollback()
    if isinstance(e, NotFoundError):
        return api_error(str(e), status_code=404)
    if isinstance(e, BusinessValidationError):
        return api_error(str(e), status_code=400)
    if isinstance(e, ValidationError):
        return api_error(clean_pydantic_error(e), status_code=400)
    return api_error(str(e), status_code=400)

class ResendApprovalEmailIn(BaseModel):
    send_now: bool = True


class BulkResendApprovalEmailIn(BaseModel):
    user_ids: List[int] = Field(default_factory=list)
    send_now: bool = False
# =========================================================
# CLASSROOM
# =========================================================
@bp.post("/classrooms/create")
@require_company_and_permission(doctype="Classroom", action="CREATE")
def create_classroom(company_id: int):
    try:
        payload = ClassroomCreate.model_validate(request.get_json(silent=True) or {})
        ok, msg, out = svc.create_classroom(company_id=company_id, data=payload.model_dump())
        _commit_ok(ok)
        return api_success(message=msg, data=out, status_code=201) if ok else api_error(msg, status_code=400)
    except Exception as e:
        return _handle_error(e)


@bp.put("/classrooms/<int:classroom_id>/update")
@require_company_and_permission(doctype="Classroom", action="UPDATE")
def update_classroom(company_id: int, classroom_id: int):
    try:
        payload = ClassroomUpdate.model_validate(request.get_json(silent=True) or {})
        ok, msg, out = svc.update_classroom(
            company_id=company_id,
            classroom_id=classroom_id,
            data=payload.model_dump(exclude_unset=True),
        )
        _commit_ok(ok)
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)
    except Exception as e:
        return _handle_error(e)


@bp.delete("/classrooms/<int:classroom_id>/delete")
@require_company_and_permission(doctype="Classroom", action="DELETE")
def delete_classroom(company_id: int, classroom_id: int):
    try:
        ok, msg, out = svc.delete_classroom(company_id=company_id, classroom_id=classroom_id, soft=True)
        _commit_ok(ok)
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)
    except Exception as e:
        return _handle_error(e)


@bp.post("/classrooms/bulk-delete")
@require_company_and_permission(doctype="Classroom", action="DELETE")
def bulk_delete_classrooms(company_id: int):
    try:
        payload = BulkDeleteIn.model_validate(request.get_json(silent=True) or {})
        ok, msg, out = svc.bulk_delete_classrooms(company_id=company_id, ids=payload.ids, soft=True)
        _commit_ok(ok)
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)
    except Exception as e:
        return _handle_error(e)


@bp.get("/classrooms/list")
@require_company_and_permission(doctype="Classroom", action="READ")
def list_classrooms(company_id: int):
    try:
        q, sort_key, sort_order, page, per_page, limit, offset, filters = _list_args()
        mode = _list_mode(limit, offset)

        args = {
            "q": q,
            "sort_key": sort_key,
            "sort_order": sort_order,
            "page": page,
            "per_page": per_page,
            "limit": int(limit or 20),
            "offset": int(offset or 0),
            "filters": filters,
        }
        data = svc.list_classrooms(company_id=company_id, mode=mode, args=args)
        return api_success(message="OK", data=data, status_code=200)
    except Exception as e:
        return _handle_error(e)


@bp.get("/classrooms/<int:classroom_id>/get")
@require_company_and_permission(doctype="Classroom", action="READ")
def get_classroom(company_id: int, classroom_id: int):
    try:
        rec = svc.get_classroom(company_id=company_id, classroom_id=classroom_id)
        return api_success(message="OK", data=rec, status_code=200) if rec else api_error("Classroom not found.", status_code=404)
    except Exception as e:
        return _handle_error(e)


@bp.post("/public/students/register")
@public
@rate_limit(key_prefix="student_register", limit=10, window=60)
def public_student_register():
    try:
        company_id = resolve_company_id_for_public()

        payload = StudentRegisterIn.model_validate(request.get_json(silent=True) or {})
        ok, msg, out = svc.register_student(company_id=company_id, data=payload.model_dump())

        _commit_ok(ok)

        session.clear()
        session.permanent = False

        if not ok:
            return api_error(msg, status_code=400)

        resp = make_response(api_success(message=msg, data=out, status_code=201))
        cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session")
        resp.delete_cookie(
            cookie_name,
            domain=current_app.config.get("SESSION_COOKIE_DOMAIN", None),
            path=current_app.config.get("SESSION_COOKIE_PATH", "/"),
            secure=bool(current_app.config.get("SESSION_COOKIE_SECURE")),
            httponly=bool(current_app.config.get("SESSION_COOKIE_HTTPONLY", True)),
            samesite=current_app.config.get("SESSION_COOKIE_SAMESITE") or "lax",
        )
        return resp

    except Exception as e:
        return _handle_error(e)
@bp.post("/students/<int:user_id>/approve")
@require_company_and_permission(doctype="Student", action="APPROVE")  # or doctype="User"
def approve_student(company_id: int, user_id: int):
    try:
        admin = get_current_user()  # must exist for admin session
        ok, msg = svc.admin_approve(user_id=int(user_id), admin_user_id=int(admin["user_id"]))

        _commit_ok(ok)
        return api_success(message=msg, data={"user_id": user_id}, status_code=200) if ok else api_error(msg, status_code=400)
    except Exception as e:
        return _handle_error(e)


@bp.post("/students/<int:user_id>/approval-email/resend")
@require_company_and_permission(doctype="Student Profile", action="UPDATE")
def resend_student_approval_email(company_id: int, user_id: int):
    admin = get_current_user()
    payload = request.get_json(silent=True) or {}

    try:
        req = ResendApprovalEmailIn(**payload)

        ok, msg, out = svc.resend_student_approval_email(
            company_id=int(company_id),
            user_id=int(user_id),
            admin_user_id=int(admin["user_id"]),
            send_now=bool(req.send_now),
        )

        if ok:
            db.session.commit()
            return api_success(message=msg, data=out or {}, status_code=200)

        db.session.rollback()
        return api_error(msg, status_code=400)

    except Exception as e:
        db.session.rollback()
        return api_error(str(e), status_code=400)


@bp.post("/students/approval-email/resend-bulk")
@require_company_and_permission(doctype="Student Profile", action="UPDATE")
def bulk_resend_student_approval_emails(company_id: int):
    admin = get_current_user()
    payload = request.get_json(silent=True) or {}

    try:
        req = BulkResendApprovalEmailIn(**payload)

        ok, msg, out = svc.bulk_resend_student_approval_emails(
            company_id=int(company_id),
            user_ids=req.user_ids,
            admin_user_id=int(admin["user_id"]),
            send_now=bool(req.send_now),
        )

        if ok:
            db.session.commit()
            return api_success(message=msg, data=out or {}, status_code=200)

        db.session.rollback()
        return api_error(msg, data=out or {}, status_code=400)

    except Exception as e:
        db.session.rollback()
        return api_error(str(e), status_code=400)


@bp.post("/students/bulk-approve")
@require_company_and_permission(doctype="Student", action="APPROVE")
def bulk_approve_students(company_id: int):
    try:
        admin = get_current_user()
        payload = BulkApproveIn.model_validate(request.get_json(silent=True) or {})

        results = []
        ok_all = True

        for uid in payload.user_ids:
            ok, msg = svc.admin_approve(user_id=int(uid), admin_user_id=int(admin["user_id"]))
            results.append({"user_id": int(uid), "ok": ok, "message": msg})
            if not ok:
                ok_all = False

        # Commit once for all (better UX)
        if ok_all:
            db.session.commit()
        else:
            # optional: still commit successes, but keep consistent:
            db.session.commit()

        return api_success("Bulk approve done.", data={"results": results}, status_code=200)

    except Exception as e:
        return _handle_error(e)

MAX_MANUAL_RESENDS = 5
@bp.post("/email/outbox/<int:outbox_id>/resend")
@require_company_and_permission(doctype="EmailOutbox", action="MANAGE")
@rate_limit(key_prefix="outbox_resend", limit=5, window=60)
def resend_outbox(company_id: int, outbox_id: int):
    try:
        # ---------------------------------------------------------
        # 1) Load original outbox row (do NOT tenant-filter first, legacy rows may have NULL company_id)
        # ---------------------------------------------------------
        row = db.session.query(EmailOutbox).filter(EmailOutbox.id == int(outbox_id)).first()
        if not row:
            return api_error("Outbox not found.", status_code=404)

        # ---------------------------------------------------------
        # 2) Tenant enforcement
        # ---------------------------------------------------------
        if hasattr(row, "company_id"):
            if row.company_id is not None:
                if int(row.company_id) != int(company_id):
                    return api_error("Out of scope.", status_code=403)
            else:
                # legacy row => validate via ref (only safe if tied to User)
                if row.ref_type == "User" and row.ref_id:
                    aff = db.session.query(UserAffiliation).filter(
                        UserAffiliation.user_id == int(row.ref_id),
                        UserAffiliation.company_id == int(company_id),
                    ).first()
                    if not aff:
                        return api_error("Out of scope.", status_code=403)
                else:
                    return api_error("Out of scope (legacy outbox row missing company_id).", status_code=403)

        # ---------------------------------------------------------
        # 3) Policy: never resend approval emails
        # ---------------------------------------------------------
        template = (row.template or "").strip()
        if template == "approved":
            return api_error("Cannot resend approval email.", status_code=400)

        # ---------------------------------------------------------
        # 4) Manual resend limit (count rows for same ref/template within this company)
        # ---------------------------------------------------------
        ref_type = (row.ref_type or "").strip()
        ref_id = row.ref_id

        if ref_type and ref_id:
            q2 = db.session.query(EmailOutbox).filter(
                EmailOutbox.ref_type == ref_type,
                EmailOutbox.ref_id == int(ref_id),
                EmailOutbox.template == row.template,
            )
            if hasattr(EmailOutbox, "company_id"):
                q2 = q2.filter(EmailOutbox.company_id == int(company_id))

            # count includes the original
            resend_count = int(q2.count() - 1)
            if resend_count >= MAX_MANUAL_RESENDS:
                return api_error(f"Resend limit reached ({MAX_MANUAL_RESENDS}).", status_code=429)

        # ---------------------------------------------------------
        # 5) Build payload (and refresh token+expiry for verify_email)
        # ---------------------------------------------------------
        payload = json.loads(row.payload_json or "{}")

        # We want same behavior as register_student:
        # update User token hash + expires_at, and email a fresh link
        if template == "verify_email":
            if row.ref_type != "User" or not row.ref_id:
                return api_error("Cannot resend: verify email outbox row missing User reference.", status_code=400)

            user = db.session.query(User).filter(User.id == int(row.ref_id)).first()
            if not user:
                return api_error("User not found for this outbox email.", status_code=400)

            # must still be pending email
            if user.email_verified_at:
                return api_error("User already verified.", status_code=400)
            if user.status != UserStatusEnum.PENDING_EMAIL:
                return api_error("User is not pending email verification.", status_code=400)

            ttl = int(os.getenv("EMAIL_VERIFY_TOKEN_TTL_MINUTES", "30"))
            tok = generate_email_verify_token(ttl_minutes=ttl)

            # ✅ IMPORTANT: update DB fields
            user.email_verify_token_hash = tok.token_hash
            user.email_verify_expires_at = tok.expires_at

            # Use same base url logic as your registration flow (frontend link)
            base_url = (os.getenv("FRONTEND_BASE_URL", "").rstrip("/")) or "http://localhost:3000"
            verify_link = f"{base_url}/verify-email?username={user.username}&token={tok.token}"

            payload["verify_link"] = verify_link
            payload["expires_minutes"] = ttl

        # ---------------------------------------------------------
        # 6) Create NEW outbox row (do not reuse SENT row)
        # ---------------------------------------------------------
        new_row = EmailOutbox(
            to_email=row.to_email,
            subject=row.subject,
            template=row.template,
            payload_json=json.dumps(payload, ensure_ascii=False),
            status=EmailOutboxStatus.PENDING,
            tries=0,
            last_error=None,
            locked_at=None,
            sent_at=None,
            ref_type=row.ref_type,
            ref_id=row.ref_id,
            from_email=row.from_email,
            from_name=row.from_name,
        )
        if hasattr(new_row, "company_id"):
            new_row.company_id = int(company_id)

        # ---------------------------------------------------------
        # 7) Send immediately (register_student style: use savepoint)
        # ---------------------------------------------------------
        with db.session.begin_nested():  # SAVEPOINT
            db.session.add(new_row)
            db.session.flush([new_row])

            svc = EmailService(
                session=db.session,
                provider=os.getenv("MAIL_PROVIDER", "smtp"),
                from_email=os.getenv("MAIL_FROM_EMAIL", ""),
                from_name=os.getenv("MAIL_FROM_NAME", ""),
            )
            svc.send_outbox_row_now(new_row)

        # commit once at end
        db.session.commit()

        return api_success(
            message="Resent",
            data={
                "original_outbox_id": int(outbox_id),
                "new_outbox_id": int(new_row.id),
                "status": new_row.status,
                "template": new_row.template,
            },
            status_code=200,
        )

    except Exception as e:
        db.session.rollback()
        return api_error(f"Resend failed: {str(e)}", status_code=400)


# ------------------------------
# LIST (Students)
# ------------------------------
@bp.get("/students/list")
@require_company_and_permission(doctype="StudentProfile", action="READ")
def list_students(company_id: int):
    try:
        q = request.args

        mode = (q.get("mode") or "cursor").strip().lower()  # cursor|page
        external_base = _external_base()

        filters: Dict[str, Any] = {
            "department_id": q.get("department_id", type=int),
            "search": (q.get("search") or "").strip() or None,
        }

        is_enabled_raw = q.get("is_enabled")
        is_enabled: Optional[bool] = None
        if is_enabled_raw is not None:
            s = str(is_enabled_raw).strip().lower()
            if s in {"1", "true", "yes"}:
                is_enabled = True
            elif s in {"0", "false", "no"}:
                is_enabled = False

        if mode == "page":
            page = q.get("page", type=int) or 1
            per_page = q.get("per_page", type=int) or 20

            ok, msg, out = svc.list_students_page(
                company_id=company_id,
                page=page,
                per_page=per_page,
                filters=filters,
                is_enabled=is_enabled,
                external_base=external_base,
            )
            return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

        limit = q.get("limit", type=int) or 20
        cursor = (q.get("cursor") or "").strip() or None

        ok, msg, out = svc.list_students_cursor(
            company_id=company_id,
            limit=limit,
            cursor=cursor,
            filters=filters,
            is_enabled=is_enabled,
            external_base=external_base,
        )
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)




# =========================================================
# DASHBOARD
# =========================================================
@bp.get("/dashboard/admin-summary")
@require_company_and_permission(doctype="User", action="READ")
def admin_dashboard_summary(company_id: int):
    try:
        months = request.args.get("months", type=int) or 4

        ok, msg, out = svc.get_admin_dashboard(
            company_id=company_id,
            months=months,
        )

        if not ok:
            return api_error(msg, status_code=400)

        return api_success(
            message=msg,
            data=out["data"],
            meta={"generated_at": out["generated_at"]},
            status_code=200,
        )
    except Exception as e:
        return _handle_error(e)



@bp.get("/onboarding/students/list")
@require_company_and_permission(
    doctype="Student Profile",
    action="READ",
    admin_only=True,
)
def list_onboarding_students(company_id: int):
    try:
        q = request.args

        filters = {
            "status": (q.get("status") or "pending_approval").strip(),
            "faculty_id": q.get("faculty_id", type=int),
            "department_id": q.get("department_id", type=int),
            "semester_id": q.get("semester_id", type=int),
            "classroom_id": q.get("classroom_id", type=int),
            "search": (q.get("search") or "").strip() or None,
        }

        verified_raw = q.get("email_verified")
        if verified_raw is not None:
            s = str(verified_raw).strip().lower()
            if s in {"1", "true", "yes"}:
                filters["email_verified"] = True
            elif s in {"0", "false", "no"}:
                filters["email_verified"] = False

        page = q.get("page", type=int) or 1
        per_page = q.get("limit", type=int) or 20

        ok, msg, out = svc.list_onboarding_students_page(
            company_id=int(company_id),
            page=page,
            per_page=per_page,
            filters=filters,
        )

        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)


@bp.get("/onboarding/students/<int:user_id>")
@require_company_and_permission(
    doctype="Student Profile",
    action="READ",
    admin_only=True,
)
def get_onboarding_student_detail(company_id: int, user_id: int):
    try:
        ok, msg, out = svc.get_onboarding_student_detail(
            company_id=int(company_id),
            user_id=int(user_id),
        )

        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=404)

    except Exception as e:
        return _handle_error(e)