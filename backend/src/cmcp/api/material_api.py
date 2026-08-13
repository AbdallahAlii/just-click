from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from flask import Blueprint, request
from pydantic import field_validator
from pydantic import ValidationError


from cmcp.common.api_response import api_success, api_error
from cmcp.common.cache import bump_detail, bump_list
from cmcp.config.database import db
from cmcp.core.exceptions import BusinessValidationError, NotFoundError
from cmcp.modules.materials.constants import MAX_MATERIALS_PER_REQUEST
from cmcp.modules.materials.schemas import MaterialCreateIn, MaterialUpdateIn, MaterialFavoriteIn, _BaseIn
from cmcp.modules.materials.feedback_schemas import (
    MaterialFeedbackCreateIn,
    MaterialFeedbackReplyIn,
    MaterialFeedbackDiscussionReplyIn,
    MaterialFeedbackResolveIn,
)
from cmcp.modules.materials.service import MaterialsService
from cmcp.security.rbac_guards import require_company_and_permission


bp = Blueprint("materials", __name__, url_prefix="/api/materials")
svc = MaterialsService()

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
    return api_error(str(e), status_code=400)

def _external_base() -> str:
    """
    Base used only when shaping response URLs.

    Prefer PUBLIC_API_BASE_URL when absolute API URLs are required.
    Default empty string → relative `/api/media/...` paths so DEV→PROD
    does not depend on request.host_url (localhost) or DB rewrites.
    """
    import os

    explicit = (os.getenv("PUBLIC_API_BASE_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    return ""


class MaterialDeleteIn(_BaseIn):
    """Delete a material."""
    permanent: bool = False


class MaterialBulkDeleteIn(_BaseIn):
    """Bulk delete materials."""
    material_ids: List[int]
    permanent: bool = False

    @field_validator("material_ids")
    @classmethod
    def validate_ids(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("material_ids is required")
        if len(v) > MAX_MATERIALS_PER_REQUEST:
            raise ValueError(f"Cannot delete more than {MAX_MATERIALS_PER_REQUEST} materials at once.")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate material IDs are not allowed.")
        return v

def _json_body() -> Dict[str, Any]:
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        raise BusinessValidationError("Request body must be a JSON object.")
    return payload


def _parse_optional_datetime(value: Optional[str]):
    if not value:
        return None
    from datetime import datetime

    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_student_list_filters(q) -> Dict[str, Any]:
    return {
        "course_offering_id": q.get("course_offering_id", type=int),
        "chapter_id": q.get("chapter_id", type=int),
        "semester_id": q.get("semester_id", type=int),
        "academic_year_id": q.get("academic_year_id", type=int),
        "course_id": q.get("course_id", type=int),
        "department_id": q.get("department_id", type=int),
        "faculty_id": q.get("faculty_id", type=int),
        "material_type": (q.get("material_type") or "").strip() or None,
        "search": (q.get("search") or "").strip() or None,
        "is_favorite": q.get("is_favorite", type=bool),
        "sort_by": (q.get("sort_by") or "").strip() or None,
        "uploaded_from": _parse_optional_datetime(q.get("uploaded_from")),
        "uploaded_to": _parse_optional_datetime(q.get("uploaded_to")),
    }
def _clean_pydantic_error(e: ValidationError) -> str:
    errors = e.errors() or []
    if not errors:
        return "Invalid request data."

    first = errors[0]
    loc = first.get("loc") or []
    field = str(loc[-1]) if loc else "field"
    err_type = first.get("type", "")
    msg = first.get("msg", "Invalid value.")

    labels = {
        "course_offering_id": "Course offering",
        "chapter_id": "Chapter",
        "title": "Title",
        "material_type": "Material type",
        "file_url": "File URL",
        "page_count": "Page count",
        "slide_count": "Slide count",
        "file_size_mb": "File size",
        "learning_objectives": "Learning objectives",
        "description": "Description",
        "is_downloadable": "Download permission",
        "is_enabled": "Status",
    }

    label = labels.get(field, field.replace("_", " ").title())

    if err_type == "missing":
        return f"{label} is required."

    if err_type in {"int_parsing", "int_type"}:
        return f"{label} must be a valid number."

    if err_type in {"float_parsing", "float_type"}:
        return f"{label} must be a valid decimal number."

    if err_type in {"bool_parsing", "bool_type"}:
        return f"{label} must be true or false."

    if err_type in {"list_type"}:
        return f"{label} must be a list."

    return f"{label}: {msg}"

class MaterialBulkUpdateIn(_BaseIn):
    """Frappe-style full-state sync for materials in an offering."""
    offering_id: int
    materials: List[Dict[str, Any]]
    missing_action: str = "disable"
    permanent: bool = False

    @field_validator("materials")
    @classmethod
    def validate_materials_length(cls, v: List) -> List:
        if len(v) > MAX_MATERIALS_PER_REQUEST:
            raise ValueError(f"Cannot process more than {MAX_MATERIALS_PER_REQUEST} materials at once.")
        return v

    @field_validator("missing_action")
    @classmethod
    def validate_missing_action(cls, v: str) -> str:
        if v not in {"disable", "delete", "keep"}:
            raise ValueError("missing_action must be 'disable', 'delete', or 'keep'")
        return v

@bp.post("/create")
@require_company_and_permission(doctype="Material", action="CREATE")
def create_material(company_id: int):
    """
    Create a single material.

    Supports:
    - JSON: application/json
    - Multipart: multipart/form-data (payload + file)
    """
    try:
        file_storage = None

        if request.content_type and "multipart/form-data" in request.content_type:
            payload_raw = request.form.get("payload")
            if not payload_raw:
                return api_error("Missing 'payload' JSON in form-data.", status_code=422)

            try:
                payload_data = json.loads(payload_raw)
            except Exception:
                return api_error("Invalid payload JSON.", status_code=400)

            try:
                payload = MaterialCreateIn.model_validate(payload_data)
            except ValidationError as e:
                return api_error(_clean_pydantic_error(e), status_code=400)

            file_storage = request.files.get("file")

        else:
            try:
                payload = MaterialCreateIn.model_validate(request.get_json(silent=True) or {})
            except ValidationError as e:
                return api_error(_clean_pydantic_error(e), status_code=400)

        ok, msg, out = svc.create_material(
            company_id=company_id,
            data=payload.model_dump(),
            file_storage=file_storage,
            external_base=_external_base(),
        )

        _commit_ok(ok)

        # ✅ keep cache invalidation
        if ok:
            bump_list("materials:list", company_id)
            bump_list("materials:admin:list", company_id, scope="admin")

            mid = (
                (out or {}).get("data", {}).get("material_id")
                or (out or {}).get("data", {}).get("material", {}).get("id")
                or (out or {}).get("material_id")
                or (out or {}).get("material", {}).get("id")
            )

            if mid:
                bump_detail("materials:detail", company_id, int(mid))
                bump_detail("materials:admin:detail", company_id, int(mid))

        return api_success(message=msg, data=out, status_code=201) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)

@bp.put("/<int:material_id>/update")
@require_company_and_permission(doctype="Material", action="UPDATE")
def update_material(company_id: int, material_id: int):
    """
    Update a single material.

    Supports:
    - JSON: application/json
    - Multipart: multipart/form-data
      - payload JSON optional when only replacing file
      - file optional when only updating fields
    """
    try:
        file_storage = None

        if request.content_type and "multipart/form-data" in request.content_type:
            file_storage = request.files.get("file")
            payload_raw = request.form.get("payload")

            if payload_raw:
                try:
                    payload_data = json.loads(payload_raw)
                except Exception:
                    return api_error("Invalid payload JSON.", status_code=400)
            else:
                payload_data = {
                    k: v
                    for k, v in request.form.items()
                    if k != "payload"
                }

            if not payload_data and not file_storage:
                return api_error("Nothing to update.", status_code=422)

            try:
                payload = MaterialUpdateIn.model_validate(payload_data)
            except ValidationError as e:
                return api_error(_clean_pydantic_error(e), status_code=400)

        else:
            payload_data = request.get_json(silent=True) or {}

            if not payload_data:
                return api_error("Nothing to update.", status_code=422)

            try:
                payload = MaterialUpdateIn.model_validate(payload_data)
            except ValidationError as e:
                return api_error(_clean_pydantic_error(e), status_code=400)

        ok, msg, out = svc.update_material(
            company_id=company_id,
            material_id=material_id,
            data=payload.model_dump(exclude_unset=True),
            file_storage=file_storage,
            external_base=_external_base(),
        )

        _commit_ok(ok)

        # ✅ keep cache invalidation
        if ok:
            bump_detail("materials:detail", company_id, int(material_id))
            bump_detail("materials:admin:detail", company_id, int(material_id))
            bump_list("materials:list", company_id)
            bump_list("materials:admin:list", company_id, scope="admin")

        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)

@bp.put("/bulk-update")
@require_company_and_permission(doctype="Material", action="UPDATE")
def bulk_update_materials(company_id: int):
    """
    Frappe-style full-state sync for materials in an offering.

    This is the PREFERRED way to manage all materials for a specific offering.
    Send the COMPLETE desired state of materials.

    Example:
    {
        "offering_id": 205,
        "materials": [
            {"id": 501, "title": "Updated Syllabus"},
            {"title": "New Material", "material_type": "pdf", "page_count": 10}
        ],
        "missing_action": "disable"
    }
    """
    try:
        payload = MaterialBulkUpdateIn.model_validate(_json_body())

        ok, msg, out = svc.bulk_update_materials(
            company_id=company_id,
            offering_id=payload.offering_id,
            materials_data=payload.materials,
            missing_action=payload.missing_action,
            permanent=payload.permanent,
        )
        _commit_ok(ok)

        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)

@bp.delete("/<int:material_id>/delete")
@require_company_and_permission(doctype="Material", action="DELETE")
def delete_material(company_id: int, material_id: int):
    """
    Delete a single material.

    Default:
        Soft delete by setting is_enabled=False.

    Hard delete:
        Send {"permanent": true}.
        Permanent deletion may be blocked when the material has interactions.
    """
    try:
        payload = MaterialDeleteIn.model_validate(_json_body())

        ok, msg, out = svc.delete_material(
            company_id=company_id,
            material_id=material_id,
            permanent=payload.permanent,
        )

        _commit_ok(ok)

        if ok:
            bump_list("materials:list", company_id)
            bump_list(
                "materials:admin:list",
                company_id,
                scope="admin",
            )

            bump_detail(
                "materials:detail",
                company_id,
                int(material_id),
            )
            bump_detail(
                "materials:admin:detail",
                company_id,
                int(material_id),
            )

        if ok:
            return api_success(
                message=msg,
                data=out,
                status_code=200,
            )

        return api_error(
            msg,
            status_code=400,
        )

    except ValidationError as e:
        db.session.rollback()
        return api_error(
            _clean_pydantic_error(e),
            status_code=400,
        )

    except Exception as e:
        return _handle_error(e)


@bp.delete("/bulk-delete")
@require_company_and_permission(doctype="Material", action="DELETE")
def bulk_delete_materials(company_id: int):
    """
    Bulk delete materials.

    Request body:
    {
        "material_ids": [1, 2, 3],
        "permanent": false
    }
    """
    try:
        payload = MaterialBulkDeleteIn.model_validate(_json_body())

        ok, msg, out = svc.bulk_delete_materials(
            company_id=company_id,
            material_ids=payload.material_ids,
            permanent=payload.permanent,
        )

        _commit_ok(ok)

        if ok:
            bump_list("materials:list", company_id)
            bump_list(
                "materials:admin:list",
                company_id,
                scope="admin",
            )

            for material_id in payload.material_ids:
                bump_detail(
                    "materials:detail",
                    company_id,
                    int(material_id),
                )
                bump_detail(
                    "materials:admin:detail",
                    company_id,
                    int(material_id),
                )

            return api_success(
                message=msg,
                data=out,
                status_code=200,
            )

        return api_error(
            msg,
            status_code=400,
        )

    except ValidationError as e:
        db.session.rollback()
        return api_error(
            _clean_pydantic_error(e),
            status_code=400,
        )

    except Exception as e:
        return _handle_error(e)

# =============================================================================
# STUDENT LIST ENDPOINTS
# =============================================================================

@bp.get("/list")
@require_company_and_permission(doctype="Material", action="READ")
def list_materials(company_id: int):
    """
    Student-facing material list with department/faculty scope filtering.

    Query params:
    - mode: "cursor" (default) or "page"
    - limit: items per page (default 20, max 100)
    - cursor: pagination cursor
    - page: page number (for page mode)
    - course_offering_id: Filter by offering (REQUIRED for students)
    - chapter_id: Filter by specific chapter
    - semester_id: Filter by semester
    - academic_year_id: Filter by academic year
    - material_type: slides, pdf, doc, video, link, other
    - is_favorite: true/false - show only favorites
    - search: Search in title/description/course/chapter
    - is_enabled: true/false/all (default: true)
    """
    try:
        q = request.args
        mode = (q.get("mode") or "cursor").strip().lower()
        external_base = _external_base()

        filters: Dict[str, Any] = _parse_student_list_filters(q)

        # Parse is_enabled
        is_enabled_raw = q.get("is_enabled", "true")
        is_enabled: Optional[bool] = True
        s = str(is_enabled_raw).strip().lower()
        if s in {"1", "true", "yes"}:
            is_enabled = True
        elif s in {"0", "false", "no"}:
            is_enabled = False
        elif s in {"all", "any"}:
            is_enabled = None

        if mode == "page":
            page = q.get("page", type=int) or 1
            per_page = q.get("limit", type=int) or 20

            ok, msg, out = svc.list_materials_page(
                company_id=company_id,
                page=page,
                per_page=per_page,
                filters=filters,
                is_enabled=is_enabled,
                external_base=external_base,
            )
            return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

        # Cursor mode (default)
        limit = q.get("limit", type=int) or 20
        cursor = (q.get("cursor") or "").strip() or None

        ok, msg, out = svc.list_materials_cursor(
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


# =============================================================================
# ADMIN LIST ENDPOINT
# =============================================================================

@bp.get("/list/admin")
@require_company_and_permission(doctype="Material", action="READ", admin_only=True)
def list_materials_admin(company_id: int):
    """
    Admin-facing material list (minimal data for tables).

    Query params:
    - page: Page number (default 1)
    - limit: Items per page (default 20)
    - course_offering_id: Filter by offering
    - chapter_id: Filter by chapter
    - material_type: slides, pdf, doc, video, link, other
    - is_enabled: true/false
    - search: Search in title
    """
    try:
        q = request.args
        external_base = _external_base()

        filters: Dict[str, Any] = {
            "course_offering_id": q.get("course_offering_id", type=int),
            "chapter_id": q.get("chapter_id", type=int),
            "material_type": (q.get("material_type") or "").strip() or None,
            "search": (q.get("search") or "").strip() or None,
        }

        # Parse is_enabled
        is_enabled_raw = q.get("is_enabled")
        if is_enabled_raw is not None:
            s = str(is_enabled_raw).strip().lower()
            if s in {"1", "true", "yes"}:
                filters["is_enabled"] = True
            elif s in {"0", "false", "no"}:
                filters["is_enabled"] = False

        page = q.get("page", type=int) or 1
        per_page = q.get("limit", type=int) or 20

        ok, msg, out = svc.list_materials_admin_page(
            company_id=company_id,
            page=page,
            per_page=per_page,
            filters=filters,
            external_base=external_base,
        )
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)


# =============================================================================
# STUDENT DETAIL
# =============================================================================

@bp.get("/get/<int:material_id>")
@require_company_and_permission(doctype="Material", action="READ")
def get_material_detail(company_id: int, material_id: int):
    """Student-facing material detail with user_state."""
    try:
        ok, msg, out = svc.get_material_detail(
            company_id=company_id,
            material_id=material_id,
            external_base=_external_base(),
        )
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=404)

    except Exception as e:
        return _handle_error(e)


# =============================================================================
# ADMIN DETAIL
# =============================================================================

@bp.get("/get/<int:material_id>/admin")
@require_company_and_permission(doctype="Material", action="READ", admin_only=True)
def get_material_detail_admin(company_id: int, material_id: int):
    """Admin-facing material detail (full data for editing)."""
    try:
        ok, msg, out = svc.get_material_detail_admin(
            company_id=company_id,
            material_id=material_id,
            external_base=_external_base(),
        )
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=404)

    except Exception as e:
        return _handle_error(e)


# =============================================================================
# FILTER OPTIONS
# =============================================================================

@bp.get("/filter-options")
@require_company_and_permission(doctype="Material", action="READ")
def get_material_filter_options(company_id: int):
    """
    Get filter options (semesters, courses, chapters) based on current selection.

    Query params:
    - academic_year_id: Filter by academic year
    - semester_id: Filter by semester
    - course_id: Filter by course
    - department_id: Filter by department
    - faculty_id: Filter by faculty
    - search: Search text
    """
    try:
        q = request.args

        filters: Dict[str, Any] = {
            "academic_year_id": q.get("academic_year_id", type=int),
            "semester_id": q.get("semester_id", type=int),
            "course_id": q.get("course_id", type=int),
            "course_offering_id": q.get("course_offering_id", type=int),
            "chapter_id": q.get("chapter_id", type=int),
            "department_id": q.get("department_id", type=int),
            "faculty_id": q.get("faculty_id", type=int),
            "search": (q.get("search") or "").strip() or None,
        }

        ok, msg, out = svc.get_material_filter_options(
            company_id=company_id,
            filters=filters,
        )

        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)


# =============================================================================
# TRACK VIEW
# =============================================================================

@bp.post("/<int:material_id>/view")
@require_company_and_permission(doctype="Material", action="READ")
def track_material_view(company_id: int, material_id: int):
    """Track when a student views a material (with cooldown)."""
    try:
        cooldown_seconds = request.args.get("cooldown_seconds", type=int) or 3600

        ok, msg, out = svc.track_view(
            company_id=company_id,
            material_id=material_id,
            cooldown_seconds=cooldown_seconds,
        )
        _commit_ok(ok)

        if ok and (out or {}).get("tracking", {}).get("counted"):
            bump_list("materials:list", company_id)
            bump_list("materials:admin:list", company_id, scope="admin")
            bump_detail("materials:detail", company_id, int(material_id))
            bump_detail("materials:admin:detail", company_id, int(material_id))

        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)


# =============================================================================
# TRACK DOWNLOAD
# =============================================================================

@bp.post("/<int:material_id>/download")
@require_company_and_permission(doctype="Material", action="DOWNLOAD")
def track_material_download(company_id: int, material_id: int):
    """Track when a student downloads a material."""
    try:
        ok, msg, out = svc.track_download(
            company_id=company_id,
            material_id=material_id,
        )
        _commit_ok(ok)

        if ok and (out or {}).get("tracking", {}).get("counted"):
            bump_list("materials:list", company_id)
            bump_list("materials:admin:list", company_id, scope="admin")
            bump_detail("materials:detail", company_id, int(material_id))
            bump_detail("materials:admin:detail", company_id, int(material_id))

        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)


# =============================================================================
# FAVORITE TOGGLE
# =============================================================================

@bp.post("/<int:material_id>/favorite")
@require_company_and_permission(doctype="Material", action="READ")
def set_material_favorite(company_id: int, material_id: int):
    """Add or remove material from student's favorites."""
    try:
        payload = MaterialFavoriteIn.model_validate(_json_body())

        ok, msg, out = svc.set_favorite(
            company_id=company_id,
            material_id=material_id,
            is_favorite=payload.is_favorite,
        )
        _commit_ok(ok)

        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)


# =============================================================================
# MY FAVORITES LIST
# =============================================================================

@bp.get("/favorites")
@require_company_and_permission(doctype="Material", action="READ")
def list_my_favorites(company_id: int):
    """List student's favorite materials."""
    try:
        q = request.args
        page = q.get("page", type=int) or 1
        per_page = q.get("limit", type=int) or 20

        ok, msg, out = svc.list_my_favorites_page(
            company_id=company_id,
            page=page,
            per_page=per_page,
            external_base=_external_base(),
        )
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=400)

    except Exception as e:
        return _handle_error(e)


# =============================================================================
# FEEDBACK
# =============================================================================

@bp.post("/<int:material_id>/feedback")
@require_company_and_permission(doctype="Material", action="READ")
def submit_material_feedback(company_id: int, material_id: int):
    try:
        payload = MaterialFeedbackCreateIn.model_validate(_json_body())
        ok, msg, out = svc.submit_feedback(
            company_id=company_id,
            material_id=material_id,
            feedback_type=payload.feedback_type,
            rating=payload.rating,
            message=payload.message,
        )
        _commit_ok(ok)
        status = 201 if ok else 400
        return api_success(message=msg, data=out, status_code=status) if ok else api_error(msg, status_code=status)
    except ValidationError as e:
        return api_error(_clean_pydantic_error(e), status_code=400)
    except Exception as e:
        return _handle_error(e)


@bp.get("/<int:material_id>/feedback")
@require_company_and_permission(doctype="Material", action="READ")
def list_material_feedback(company_id: int, material_id: int):
    try:
        limit = request.args.get("limit", type=int) or 50
        ok, msg, out = svc.list_material_feedback(
            company_id=company_id,
            material_id=material_id,
            limit=limit,
        )
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=404)
    except Exception as e:
        return _handle_error(e)


@bp.get("/feedback/admin")
@require_company_and_permission(doctype="Material", action="READ", admin_only=True)
def list_material_feedback_admin(company_id: int):
    try:
        q = request.args
        ok, msg, out = svc.list_feedback_admin(
            company_id=company_id,
            status=(q.get("status") or "").strip() or None,
            feedback_type=(q.get("feedback_type") or "").strip() or None,
            material_id=q.get("material_id", type=int),
            page=q.get("page", type=int) or 1,
            per_page=q.get("limit", type=int) or 20,
        )
        return api_success(message=msg, data=out, status_code=200)
    except Exception as e:
        return _handle_error(e)


@bp.post("/feedback/<int:feedback_id>/reply")
@require_company_and_permission(doctype="Material", action="UPDATE", admin_only=True)
def reply_material_feedback(company_id: int, feedback_id: int):
    try:
        from cmcp.modules.auth.deps import get_current_user

        admin = get_current_user()
        payload = MaterialFeedbackReplyIn.model_validate(_json_body())
        ok, msg, out = svc.reply_feedback(
            company_id=company_id,
            feedback_id=feedback_id,
            admin_user_id=int(admin["user_id"]),
            admin_reply=payload.admin_reply,
        )
        _commit_ok(ok)
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=404)
    except ValidationError as e:
        return api_error(_clean_pydantic_error(e), status_code=400)
    except Exception as e:
        return _handle_error(e)


@bp.post("/feedback/<int:feedback_id>/replies")
@require_company_and_permission(doctype="Material", action="READ")
def post_material_feedback_discussion_reply(company_id: int, feedback_id: int):
    """Authorized material users (students/staff/admins) reply on public discussions."""
    try:
        payload = MaterialFeedbackDiscussionReplyIn.model_validate(_json_body())
        ok, msg, out = svc.add_discussion_reply(
            company_id=company_id,
            feedback_id=feedback_id,
            message=payload.message,
        )
        _commit_ok(ok)
        status = 200 if ok else 404
        if not ok and "cannot reply" in (msg or "").lower():
            status = 403
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=status)
    except ValidationError as e:
        return api_error(_clean_pydantic_error(e), status_code=400)
    except Exception as e:
        return _handle_error(e)


@bp.post("/feedback/<int:feedback_id>/resolve")
@require_company_and_permission(doctype="Material", action="UPDATE", admin_only=True)
def resolve_material_feedback(company_id: int, feedback_id: int):
    try:
        from cmcp.modules.auth.deps import get_current_user

        admin = get_current_user()
        payload = MaterialFeedbackResolveIn.model_validate(_json_body() or {})
        ok, msg, out = svc.resolve_feedback(
            company_id=company_id,
            feedback_id=feedback_id,
            admin_user_id=int(admin["user_id"]),
            admin_reply=payload.admin_reply,
        )
        _commit_ok(ok)
        return api_success(message=msg, data=out, status_code=200) if ok else api_error(msg, status_code=404)
    except ValidationError as e:
        return api_error(_clean_pydantic_error(e), status_code=400)
    except Exception as e:
        return _handle_error(e)


# =============================================================================
# ACCESS REPORTS
# =============================================================================

@bp.get("/feedback/admin/summary")
@require_company_and_permission(doctype="Material", action="READ", admin_only=True)
def material_feedback_admin_summary(company_id: int):
    try:
        ok, msg, out = svc.get_feedback_admin_summary(company_id=company_id)
        return api_success(message=msg, data=out, status_code=200)
    except Exception as e:
        return _handle_error(e)


@bp.get("/reports/access")
@require_company_and_permission(doctype="Material", action="READ", admin_only=True)
def material_access_reports(company_id: int):
    try:
        limit = request.args.get("limit", type=int) or 10
        ok, msg, out = svc.get_access_reports(company_id=company_id, limit=limit)
        return api_success(message=msg, data=out, status_code=200)
    except Exception as e:
        return _handle_error(e)