from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import Blueprint, request
from pydantic import BaseModel, Field, field_validator

from cmcp.common.api_response import api_success, api_error
from cmcp.config.database import db
from cmcp.modules.auth.deps import get_current_user
from cmcp.modules.notifications.service import NotificationService
from cmcp.security.rbac_guards import require_company_and_permission


bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")
svc = NotificationService()


def _commit_ok(ok: bool):
    if ok:
        db.session.commit()
    else:
        db.session.rollback()


def _json_body() -> Dict[str, Any]:
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return {}
    return payload


class AdminSendIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    channels: List[str] = Field(default_factory=lambda: ["in_app", "email", "push"])
    recipient_mode: str = Field(default="all")
    user_ids: Optional[List[int]] = None
    material_id: Optional[int] = None

    @field_validator("recipient_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        mode = (v or "all").strip().lower()
        if mode not in ("all", "selected"):
            raise ValueError("recipient_mode must be 'all' or 'selected'")
        return mode

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Select at least one channel")
        return v


class DeviceRegisterIn(BaseModel):
    token: str = Field(..., min_length=10, max_length=512)
    platform: str = Field(default="android")

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        p = (v or "android").strip().lower()
        if p not in ("android", "ios", "web"):
            raise ValueError("platform must be android, ios, or web")
        return p


class MarkReadIn(BaseModel):
    notification_id: int


# ---------------------------------------------------------------------------
# Mobile / student in-app APIs
# ---------------------------------------------------------------------------

@bp.get("/list")
@require_company_and_permission(doctype="Student Material Interaction", action="READ")
def list_notifications(company_id: int):
    user = get_current_user()
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    unread_only = request.args.get("unread_only", default=False, type=bool)

    ok, msg, out = svc.list_notifications(
        company_id=int(company_id),
        user_id=int(user["user_id"]),
        unread_only=bool(unread_only),
        page=max(1, page),
        per_page=max(1, min(per_page, 100)),
    )
    return api_success(message=msg, data=out) if ok else api_error(msg)


@bp.get("/unread-count")
@require_company_and_permission(doctype="Student Material Interaction", action="READ")
def unread_count(company_id: int):
    user = get_current_user()
    count = svc.get_unread_count(company_id=int(company_id), user_id=int(user["user_id"]))
    return api_success(message="OK", data={"unread_count": count})


@bp.post("/read")
@require_company_and_permission(doctype="Student Material Interaction", action="UPDATE")
def mark_read(company_id: int):
    user = get_current_user()
    payload = _json_body()
    try:
        req = MarkReadIn(**payload)
    except Exception as e:
        return api_error(str(e), status_code=400)

    ok, msg = svc.mark_read(
        company_id=int(company_id),
        user_id=int(user["user_id"]),
        notification_id=int(req.notification_id),
    )
    _commit_ok(ok)
    return api_success(message=msg) if ok else api_error(msg, status_code=404)


@bp.post("/read-all")
@require_company_and_permission(doctype="Student Material Interaction", action="UPDATE")
def mark_all_read(company_id: int):
    user = get_current_user()
    ok, msg, count = svc.mark_all_read(
        company_id=int(company_id),
        user_id=int(user["user_id"]),
    )
    _commit_ok(ok)
    return api_success(message=msg, data={"marked": count})


@bp.post("/devices/register")
@require_company_and_permission(doctype="Student Material Interaction", action="CREATE")
def register_device(company_id: int):
    user = get_current_user()
    payload = _json_body()
    try:
        req = DeviceRegisterIn(**payload)
    except Exception as e:
        return api_error(str(e), status_code=400)

    ok, msg, out = svc.register_device(
        company_id=int(company_id),
        user_id=int(user["user_id"]),
        token=req.token,
        platform=req.platform,
    )
    _commit_ok(ok)
    return api_success(message=msg, data=out) if ok else api_error(msg, status_code=400)


# ---------------------------------------------------------------------------
# Admin APIs
# ---------------------------------------------------------------------------

@bp.get("/admin/batches")
@require_company_and_permission(doctype="Material", action="READ", admin_only=True)
def list_batches_admin(company_id: int):
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=20, type=int)
    ok, msg, out = svc.list_batches_admin(
        company_id=int(company_id),
        page=max(1, page),
        per_page=max(1, min(per_page, 100)),
    )
    return api_success(message=msg, data=out) if ok else api_error(msg)


@bp.get("/admin/recipients")
@require_company_and_permission(doctype="Material", action="READ", admin_only=True)
def list_recipients_admin(company_id: int):
    limit = request.args.get("limit", default=500, type=int)
    ok, msg, rows = svc.list_recipients_admin(
        company_id=int(company_id),
        limit=max(1, min(limit, 2000)),
    )
    return api_success(message=msg, data={"recipients": rows}) if ok else api_error(msg)


@bp.post("/admin/send")
@require_company_and_permission(doctype="Material", action="MANAGE", admin_only=True)
def admin_send(company_id: int):
    admin = get_current_user()
    payload = _json_body()
    try:
        req = AdminSendIn(**payload)
    except Exception as e:
        return api_error(str(e), status_code=400)

    ok, msg, out = svc.admin_send(
        company_id=int(company_id),
        title=req.title,
        body=req.body,
        channels=req.channels,
        recipient_mode=req.recipient_mode,
        user_ids=req.user_ids,
        material_id=req.material_id,
        created_by_user_id=int(admin["user_id"]),
    )
    _commit_ok(ok)
    return api_success(message=msg, data=out) if ok else api_error(msg, status_code=400)


@bp.post("/admin/batches/<int:batch_id>/resend-email")
@require_company_and_permission(doctype="Material", action="MANAGE", admin_only=True)
def resend_batch_email(company_id: int, batch_id: int):
    ok, msg, out = svc.resend_batch_emails(
        company_id=int(company_id),
        batch_id=int(batch_id),
    )
    _commit_ok(ok)
    return api_success(message=msg, data=out) if ok else api_error(msg, status_code=400)
