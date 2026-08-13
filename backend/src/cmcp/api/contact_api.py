from __future__ import annotations

from flask import Blueprint, request, session
from pydantic import ValidationError

from cmcp.common.api_response import api_error, api_success
from cmcp.common.decorators import rate_limit
from cmcp.common.validation.pydantic_errors import clean_pydantic_error
from cmcp.config.database import db
from cmcp.core.auth import public
from cmcp.modules.auth.deps import get_current_user
from cmcp.modules.contact.schemas import ContactCreateIn, ContactHandleIn
from cmcp.modules.contact.service import ContactService
from cmcp.security.rbac_guards import require_company_and_permission

bp = Blueprint("contact", __name__, url_prefix="/api/contact")
svc = ContactService()


def _commit_ok(ok: bool):
    if ok:
        db.session.commit()
    else:
        db.session.rollback()


@bp.post("/submit")
@public
@rate_limit(key_prefix="contact_submit", limit=5, window=300)
def submit_contact():
    payload = request.get_json(silent=True) or {}
    try:
        req = ContactCreateIn(**payload)
    except ValidationError as e:
        return api_error(clean_pydantic_error(e), status_code=400)

    user_id = session.get("user_id")
    company_id = session.get("company_id")

    ok, msg, out = svc.submit(
        name=req.name,
        email=str(req.email),
        subject=req.subject,
        message=req.message,
        user_id=int(user_id) if user_id else None,
        company_id=int(company_id) if company_id else None,
    )
    _commit_ok(ok)
    return api_success(message=msg, data=out, status_code=201) if ok else api_error(msg, status_code=400)


@bp.get("/admin/list")
@require_company_and_permission(doctype="Material", action="READ", admin_only=True)
def list_contact_admin(company_id: int):
    _ = company_id
    status = (request.args.get("status") or "").strip() or None
    page = request.args.get("page", type=int) or 1
    per_page = request.args.get("per_page", type=int) or 20
    ok, msg, out = svc.list_admin(status=status, page=page, per_page=per_page)
    return api_success(message=msg, data=out) if ok else api_error(msg, status_code=400)


@bp.get("/admin/<int:contact_id>")
@require_company_and_permission(doctype="Material", action="READ", admin_only=True)
def get_contact_admin(company_id: int, contact_id: int):
    _ = company_id
    ok, msg, out = svc.get_admin(contact_id=contact_id)
    return api_success(message=msg, data=out) if ok else api_error(msg, status_code=404)


@bp.post("/admin/<int:contact_id>/handle")
@require_company_and_permission(doctype="Material", action="UPDATE", admin_only=True)
def handle_contact_admin(company_id: int, contact_id: int):
    _ = company_id
    admin = get_current_user()
    payload = request.get_json(silent=True) or {}
    try:
        req = ContactHandleIn(**payload)
    except ValidationError as e:
        return api_error(clean_pydantic_error(e), status_code=400)

    ok, msg, out = svc.handle(
        contact_id=contact_id,
        admin_user_id=int(admin["user_id"]),
        status=req.status,
        admin_notes=req.admin_notes,
        admin_reply=req.admin_reply,
        send_reply_email=bool(req.send_reply_email),
    )
    _commit_ok(ok)
    return api_success(message=msg, data=out) if ok else api_error(msg, status_code=404)
