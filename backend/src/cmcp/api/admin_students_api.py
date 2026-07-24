import json
from flask import Blueprint, request
from typing import Dict, Any

from cmcp.common.api_response import api_success, api_error
from cmcp.security.rbac_guards import require_company_and_permission
from cmcp.modules.admin_students.service import AdminStudentsService
from cmcp.core.exceptions import NotFoundError, BusinessValidationError

bp = Blueprint("admin_students", __name__, url_prefix="/api/admin/students")
svc = AdminStudentsService()

def _parse_bool(v) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).lower()
    if s in ["true", "1", "yes"]:
        return True
    if s in ["false", "0", "no"]:
        return False
    return None

def _handle_error(e: Exception):
    if isinstance(e, NotFoundError):
        return api_error(str(e), status_code=404)
    if isinstance(e, BusinessValidationError):
        return api_error(str(e), status_code=400)
    return api_error(str(e), status_code=400)

@bp.get("/list")
@require_company_and_permission(doctype="StudentProfile", action="READ")
def list_students(company_id: int):
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        
        filters = {
            "search": request.args.get("search", ""),
            "faculty_id": request.args.get("faculty_id", type=int),
            "department_id": request.args.get("department_id", type=int),
            "semester_id": request.args.get("semester_id", type=int),
            "classroom_id": request.args.get("classroom_id", type=int),
            "status": request.args.get("status"),
            "is_enabled": _parse_bool(request.args.get("is_enabled"))
        }

        ok, msg, data = svc.list_students(company_id, page, limit, filters)
        return api_success(message=msg, data=data, status_code=200) if ok else api_error(msg, status_code=400)
    except Exception as e:
        return _handle_error(e)

@bp.get("/<int:student_profile_id>")
@require_company_and_permission(doctype="StudentProfile", action="READ")
def get_student(company_id: int, student_profile_id: int):
    try:
        ok, msg, data = svc.get_student(company_id, student_profile_id)
        return api_success(message=msg, data=data, status_code=200) if ok else api_error(msg, status_code=400)
    except Exception as e:
        return _handle_error(e)

@bp.put("/<int:student_profile_id>")
@require_company_and_permission(doctype="StudentProfile", action="WRITE")
def update_student(company_id: int, student_profile_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        ok, msg, data = svc.update_student(company_id, student_profile_id, payload)
        if ok:
            from cmcp.config.database import db
            db.session.commit()
        else:
            from cmcp.config.database import db
            db.session.rollback()
        return api_success(message=msg, data=data, status_code=200) if ok else api_error(msg, status_code=400)
    except Exception as e:
        from cmcp.config.database import db
        db.session.rollback()
        return _handle_error(e)


@bp.post("/<int:student_profile_id>/reset-password")
@require_company_and_permission(doctype="StudentProfile", action="WRITE")
def reset_student_password(company_id: int, student_profile_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        mode = str(payload.get("mode") or "email").strip().lower()
        ok, msg, data = svc.reset_student_password(
            company_id=company_id,
            student_profile_id=student_profile_id,
            mode=mode,
            new_password=payload.get("new_password"),
        )
        if ok:
            from cmcp.config.database import db
            db.session.commit()
        else:
            from cmcp.config.database import db
            db.session.rollback()
        return api_success(message=msg, data=data, status_code=200) if ok else api_error(msg, status_code=400)
    except Exception as e:
        from cmcp.config.database import db
        db.session.rollback()
        return _handle_error(e)
