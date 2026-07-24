# # src/cmcp/modules/materials/service.py

from __future__ import annotations

import base64
import json
import logging
import os
from urllib.parse import unquote
from sqlite3 import IntegrityError
from typing import Any, Dict, Optional, Tuple, List, Set

from flask import g
from werkzeug.datastructures import FileStorage

from sqlalchemy.orm import Session

from cmcp.core.base_service import BaseService
from cmcp.core.exceptions import BusinessValidationError, NotFoundError

from cmcp.modules.materials.models import Material, MaterialTypeEnum
from cmcp.modules.media.service import save_file_for
from cmcp.modules.media.utils import MediaFolder
from cmcp.modules.media.encrypted_files import file_url_from_key

from .repository import MaterialsRepo
from .validation import (
    require_title,
    require_material_type,
    validate_learning_objectives,
    validate_file_size_mb,
    validate_counts,
    validate_link_url_if_needed,
)
from .constants import (
    ERR_COURSE_NOT_FOUND,
    ERR_CHAPTER_NOT_FOUND,
    ERR_CHAPTER_NOT_IN_COURSE,
    ERR_MATERIAL_TITLE_EXISTS,
    ERR_CANNOT_CHANGE_COURSE,
    ERR_CANNOT_CHANGE_CHAPTER,
    ERR_CANNOT_CHANGE_TYPE,
    ERR_MATERIAL_NOT_FOUND,
    ERR_FILE_TYPE_NOT_ALLOWED,
    ERR_FILE_REQUIRED_FOR_TYPE,
    ERR_COURSE_OFFERING_NOT_FOUND,  # NEW
    ALLOWED_EXTENSIONS_BY_TYPE, ERR_LEARNING_OBJECTIVES_INVALID, ERR_LINK_INVALID_URL, ERR_INVALID_MISSING_ACTION,
    ERR_FILE_SIZE_TOO_LARGE, ERR_FILE_SIZE_NEGATIVE, MAX_FILE_SIZE_MB, ERR_MATERIAL_COUNTS_CONFLICT,
    ERR_SLIDE_COUNT_MIN, ERR_PAGE_COUNT_MIN, ERR_MATERIAL_TYPE_INVALID, MAX_TITLE_LENGTH, MAX_MATERIALS_PER_REQUEST,
    ERR_TOO_MANY_MATERIALS, ERR_DUPLICATE_IDS, ERR_MATERIAL_HAS_INTERACTIONS, ERR_CHAPTER_NOT_IN_OFFERING,
    ERR_CANNOT_CHANGE_OFFERING,
)

from cmcp.common.cache import cached_list, cached_detail

log = logging.getLogger(__name__)


def _calc_size_mb(b: bytes) -> float:
    return round(len(b) / (1024 * 1024), 4)


def _file_ext(filename: str) -> str:
    if not filename:
        return ""
    _, ext = os.path.splitext(filename.strip())
    return ext.lower()


# -----------------------------
# Cursor helpers (simple, stable)
# -----------------------------
def _encode_cursor(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _decode_cursor(cursor: str) -> Dict[str, Any]:
    if not cursor:
        return {}
    pad = "=" * ((4 - len(cursor) % 4) % 4)
    raw = base64.urlsafe_b64decode((cursor + pad).encode("utf-8"))
    obj = json.loads(raw.decode("utf-8"))
    return obj if isinstance(obj, dict) else {}


# =========================================================
# VALIDATION HELPERS (Centralized for reusability)
# =========================================================

def _require_text(value: Any, field_label: str, max_length: int = MAX_TITLE_LENGTH) -> str:
    value = (str(value) if value is not None else "").strip()
    if not value:
        raise BusinessValidationError(f"{field_label} is required.")
    if len(value) > max_length:
        raise BusinessValidationError(f"{field_label} is too long (max {max_length} characters).")
    return value


def _safe_text(value: Any) -> Optional[str]:
    value = (str(value) if value is not None else "").strip()
    return value or None


def _as_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    return bool(value)


def _parse_material_type(raw: Any) -> MaterialTypeEnum:
    s = (str(raw) if raw is not None else "").strip().lower()
    try:
        return MaterialTypeEnum(s)
    except ValueError:
        raise BusinessValidationError(ERR_MATERIAL_TYPE_INVALID)

def _validate_counts_relaxed(
    material_type: str,
    page_count: Any,
    slide_count: Any,
) -> Tuple[Optional[int], Optional[int]]:
    """
    Relaxed counts for setup-first workflow.

    Rules:
    - counts are optional
    - page_count and slide_count cannot both be set
    - slides can only use slide_count
    - pdf/doc can only use page_count
    - video/link/other should not use counts
    """
    t = (material_type or "other").strip().lower()

    def _to_int_or_none(value: Any, label: str) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            n = int(value)
        except Exception:
            raise BusinessValidationError(f"{label} must be a valid number.")
        if n < 1:
            raise BusinessValidationError(f"{label} must be at least 1.")
        return n

    page = _to_int_or_none(page_count, "Page count")
    slide = _to_int_or_none(slide_count, "Slide count")

    if page is not None and slide is not None:
        raise BusinessValidationError("Use either page count or slide count, not both.")

    if t == "slides":
        if page is not None:
            raise BusinessValidationError("Slides materials use slide count, not page count.")
        return None, slide

    if t in {"pdf", "doc"}:
        if slide is not None:
            raise BusinessValidationError("PDF/DOC materials use page count, not slide count.")
        return page, None

    if t in {"video", "link", "other"}:
        if page is not None or slide is not None:
            raise BusinessValidationError("This material type does not use page count or slide count.")
        return None, None

    return None, None
def _validate_file_against_type(material_type: str, file_storage: Optional[FileStorage]) -> None:
    """
    File is optional.

    Admin may create the material record first, then upload the file later.
    If a file is provided, validate extension against material_type.
    """
    t = (material_type or "other").strip().lower()

    if not file_storage:
        return

    if t == "link":
        return

    ext = os.path.splitext(file_storage.filename or "")[1].lower()
    allowed = ALLOWED_EXTENSIONS_BY_TYPE.get(t, set())

    if allowed and ext not in allowed:
        raise BusinessValidationError(
            f"{ERR_FILE_TYPE_NOT_ALLOWED} Allowed: {', '.join(sorted(allowed))}"
        )


def _validate_counts(
        material_type: str,
        page_count: Any,
        slide_count: Any,
) -> Tuple[Optional[int], Optional[int]]:
    """Validate and return page_count, slide_count based on material type."""
    t = material_type.lower()

    if t == "pdf" or t == "doc":
        if slide_count is not None:
            raise BusinessValidationError(ERR_MATERIAL_COUNTS_CONFLICT)
        if page_count is not None:
            pc = int(page_count)
            if pc < 1:
                raise BusinessValidationError(ERR_PAGE_COUNT_MIN)
            return pc, None
        return None, None

    if t == "slides":
        if page_count is not None:
            raise BusinessValidationError(ERR_MATERIAL_COUNTS_CONFLICT)
        if slide_count is not None:
            sc = int(slide_count)
            if sc < 1:
                raise BusinessValidationError(ERR_SLIDE_COUNT_MIN)
            return None, sc
        return None, None

    # For video, link, other - no counts allowed
    if page_count is not None or slide_count is not None:
        raise BusinessValidationError(ERR_MATERIAL_COUNTS_CONFLICT)

    return None, None


def _validate_file_size_mb(value: Any) -> Optional[float]:
    if value is None:
        return None

    size = float(value)
    if size < 0:
        raise BusinessValidationError(ERR_FILE_SIZE_NEGATIVE)
    if size > MAX_FILE_SIZE_MB:
        raise BusinessValidationError(ERR_FILE_SIZE_TOO_LARGE)
    return size


def _validate_link_url(url: Optional[str]) -> Optional[str]:
    if url is None:
        return None

    url = url.strip()
    if not url:
        return None

    if not url.startswith(("http://", "https://")):
        raise BusinessValidationError(ERR_LINK_INVALID_URL)

    return url


def _validate_learning_objectives(value: Any) -> Optional[List[str]]:
    if value is None:
        return None

    if not isinstance(value, list):
        raise BusinessValidationError(ERR_LEARNING_OBJECTIVES_INVALID)

    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return cleaned if cleaned else None


def _normalize_missing_action(action: str) -> str:
    action = (action or "disable").strip().lower()
    if action not in {"disable", "delete", "keep"}:
        raise BusinessValidationError(ERR_INVALID_MISSING_ACTION)
    return action

class MaterialsService:
    def __init__(self, repo: Optional[MaterialsRepo] = None, session: Optional[Session] = None):
        self.repo = repo or MaterialsRepo(session=session)
        self.s: Session = self.repo.s

        # important: external tx (blueprint commits)
        self.material_svc = BaseService(Material, session=self.s, tx_mode="external")

    def _parse_enum_type(self, raw: str) -> MaterialTypeEnum:
        s = (raw or "").strip().lower()
        try:
            return MaterialTypeEnum(s)
        except Exception:
            raise BusinessValidationError("Invalid material_type.")



    def _clean_material_out(self, material: Material) -> Dict[str, Any]:
        return {
            "id": int(material.id),
            "title": (material.title or "").strip(),
        }

    def _material_summary_out(self, material: Material) -> Dict[str, Any]:
        """Small create/update response."""
        return {
            "material_id": int(material.id),
            "title": material.title,
        }

    # =========================================================
    # CREATE
    # =========================================================

    def create_material(
            self,
            *,
            company_id: int,
            data: Dict[str, Any],
            file_storage: Optional[FileStorage] = None,
            external_base: str = "",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a single material.

        Setup-first workflow:
        - course_offering_id is required
        - title is required
        - material_type is optional; defaults to "other"
        - file upload is optional for all material types
        - counts are optional, but must match material_type if provided
        """
        try:
            # -----------------------------
            # Validate course offering
            # -----------------------------
            course_offering_id = int(data.get("course_offering_id") or 0)
            if not course_offering_id:
                raise BusinessValidationError("Course offering is required.")

            if not self.repo.course_offering_exists(
                    company_id=company_id,
                    offering_id=course_offering_id,
            ):
                raise NotFoundError(ERR_COURSE_OFFERING_NOT_FOUND)

            # -----------------------------
            # Validate chapter if provided
            # -----------------------------
            chapter_id = data.get("chapter_id")
            chapter_id = int(chapter_id) if chapter_id else None

            if chapter_id:
                if not self.repo.chapter_exists(
                        company_id=company_id,
                        chapter_id=chapter_id,
                ):
                    raise NotFoundError(ERR_CHAPTER_NOT_FOUND)

                if not self.repo.chapter_belongs_to_offering(
                        company_id=company_id,
                        chapter_id=chapter_id,
                        offering_id=course_offering_id,
                ):
                    raise BusinessValidationError(ERR_CHAPTER_NOT_IN_OFFERING)

            # -----------------------------
            # Validate title
            # -----------------------------
            title = _require_text(data.get("title"), "Title")

            if self.repo.title_exists_in_scope(
                    company_id=company_id,
                    course_offering_id=course_offering_id,
                    chapter_id=chapter_id,
                    title=title,
            ):
                raise BusinessValidationError(ERR_MATERIAL_TITLE_EXISTS)

            # -----------------------------
            # Material type: optional on create
            # DB requires material_type, so default to "other"
            # -----------------------------
            material_type = _parse_material_type(data.get("material_type") or "other")

            # -----------------------------
            # File is optional. Validate only if uploaded.
            # -----------------------------
            _validate_file_against_type(material_type.value, file_storage)

            # -----------------------------
            # Counts are optional, but must match type if provided.
            # -----------------------------
            page_count, slide_count = _validate_counts_relaxed(
                material_type.value,
                data.get("page_count"),
                data.get("slide_count"),
            )

            # -----------------------------
            # Other optional fields
            # -----------------------------
            file_size_mb = _validate_file_size_mb(data.get("file_size_mb"))
            learning_objectives = _validate_learning_objectives(data.get("learning_objectives"))

            # Link URL is optional during setup.
            # If provided, validate URL format.
            file_url = _validate_link_url(data.get("file_url")) if data.get("file_url") else None

            with self.s.begin_nested():
                payload = {
                    "company_id": int(company_id),
                    "course_offering_id": course_offering_id,
                    "chapter_id": chapter_id,
                    "title": title,
                    "material_type": material_type,
                    "file_url": file_url,
                    "page_count": page_count,
                    "slide_count": slide_count,
                    "file_size_mb": file_size_mb,
                    "learning_objectives": learning_objectives,
                    "description": _safe_text(data.get("description")),
                    "is_downloadable": _as_bool(data.get("is_downloadable"), default=True),
                    "is_enabled": _as_bool(data.get("is_enabled"), default=True),
                }

                material = self.repo.create_material(payload)
                self.s.flush()

                # Upload file only if provided.
                # For link type, file_url comes from data["file_url"], not file upload.
                if file_storage and material_type.value != "link":
                    self._upload_material_file(material, file_storage, external_base)

                self.s.flush()

                from cmcp.modules.chatbot.jobs import schedule_index_for_material
                schedule_index_for_material(material, trigger_type="material_created")

                if material.is_enabled:
                    try:
                        from cmcp.modules.notifications.service import NotificationService
                        NotificationService(session=self.s).notify_material_event(
                            company_id=int(company_id),
                            material_id=int(material.id),
                            event="created",
                        )
                    except Exception:
                        log.exception("material create notification failed material_id=%s", material.id)

                return True, "Material created successfully.", {
                    "material": self._material_summary_out(material)
                }
        except (BusinessValidationError, NotFoundError) as e:
            return False, str(e), None
        except IntegrityError:
            return False, "Database constraint error. Please check duplicate material title or invalid references.", None
        except Exception as e:
            return False, f"Unexpected error: {e}", None

    def update_material(
            self,
            *,
            company_id: int,
            material_id: int,
            data: Dict[str, Any],
            file_storage: Optional[FileStorage] = None,
            external_base: str = "",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Update a single material.

        Setup-first workflow:
        - file upload is optional
        - material_type can be changed later
        - counts are optional, but must match the final material_type
        - course_offering_id and chapter_id remain protected unless you intentionally allow moving
        """
        try:
            material = self.repo.get_material(material_id, company_id=company_id)
            if not material:
                raise NotFoundError(ERR_MATERIAL_NOT_FOUND)

            patch: Dict[str, Any] = {}

            # -----------------------------
            # Prevent moving offering unless you explicitly want to allow it.
            # Safer for final project: do not move material between offerings here.
            # -----------------------------
            if "course_offering_id" in data and data["course_offering_id"] is not None:
                incoming_offering_id = int(data["course_offering_id"])
                if incoming_offering_id != int(material.course_offering_id):
                    raise BusinessValidationError(ERR_CANNOT_CHANGE_OFFERING)

            # -----------------------------
            # Prevent changing chapter unless you intentionally allow it.
            # -----------------------------
            if "chapter_id" in data:
                incoming_chapter_id = int(data["chapter_id"]) if data["chapter_id"] else None
                current_chapter_id = int(material.chapter_id) if material.chapter_id else None

                if incoming_chapter_id != current_chapter_id:
                    raise BusinessValidationError(ERR_CANNOT_CHANGE_CHAPTER)

            # -----------------------------
            # Material type can be changed later
            # -----------------------------
            current_type = getattr(material.material_type, "value", str(material.material_type)).lower()
            new_type = current_type
            material_type_enum = material.material_type

            if "material_type" in data and data["material_type"]:
                new_type = str(data["material_type"]).strip().lower()
                material_type_enum = _parse_material_type(new_type)

            # -----------------------------
            # File is optional. Validate only if uploaded.
            # -----------------------------
            if file_storage:
                _validate_file_against_type(new_type, file_storage)

            # -----------------------------
            # Validate counts using final material type.
            #
            # If material type changes, old counts are cleared unless new counts are sent.
            # Example: other -> slides clears old page_count and accepts slide_count if provided.
            # -----------------------------
            page_count = material.page_count
            slide_count = material.slide_count

            type_changed = new_type != current_type
            count_fields_sent = "page_count" in data or "slide_count" in data

            if type_changed or count_fields_sent:
                page_count, slide_count = _validate_counts_relaxed(
                    new_type,
                    data.get("page_count", None if type_changed else material.page_count),
                    data.get("slide_count", None if type_changed else material.slide_count),
                )

                patch["page_count"] = page_count
                patch["slide_count"] = slide_count

            if type_changed:
                patch["material_type"] = material_type_enum

            # -----------------------------
            # Title
            # -----------------------------
            if "title" in data and data["title"] is not None:
                new_title = _require_text(data["title"], "Title")

                current_title_norm = (material.title or "").strip().casefold()
                new_title_norm = new_title.strip().casefold()

                if new_title_norm != current_title_norm:
                    if self.repo.title_exists_in_scope(
                            company_id=company_id,
                            course_offering_id=int(material.course_offering_id),
                            chapter_id=int(material.chapter_id) if material.chapter_id else None,
                            title=new_title,
                            exclude_id=int(material.id),
                    ):
                        raise BusinessValidationError(ERR_MATERIAL_TITLE_EXISTS)

                    patch["title"] = new_title

            # -----------------------------
            # Normal editable fields
            # -----------------------------
            if "description" in data:
                patch["description"] = _safe_text(data["description"])

            if "learning_objectives" in data:
                patch["learning_objectives"] = _validate_learning_objectives(data["learning_objectives"])

            if "is_downloadable" in data:
                patch["is_downloadable"] = _as_bool(data["is_downloadable"])

            if "is_enabled" in data:
                patch["is_enabled"] = _as_bool(data["is_enabled"])

            if "file_size_mb" in data:
                patch["file_size_mb"] = _validate_file_size_mb(data["file_size_mb"])

            # -----------------------------
            # Link URL:
            # - optional
            # - if sent empty, clear it
            # - if sent non-empty, validate URL
            # -----------------------------
            if "file_url" in data:
                patch["file_url"] = _validate_link_url(data["file_url"]) if data["file_url"] else None

            was_disabled = not bool(material.is_enabled)

            with self.s.begin_nested():
                if patch:
                    self.repo.update_material(material, patch)

                # Replace/upload physical file only if provided.
                # Use new_type because admin may change type and upload in the same request.
                if file_storage and new_type != "link":
                    self._upload_material_file(material, file_storage, external_base)

                self.s.flush()

                from cmcp.modules.chatbot.jobs import schedule_index_for_material
                file_changed = bool(file_storage) or "file_url" in patch
                re_enabled = patch.get("is_enabled") is True and was_disabled
                is_enabled_now = patch.get("is_enabled", material.is_enabled)
                if file_changed:
                    schedule_index_for_material(material, trigger_type="material_updated")

                if (file_changed or re_enabled) and is_enabled_now:
                    try:
                        from cmcp.modules.notifications.service import NotificationService
                        NotificationService(session=self.s).notify_material_event(
                            company_id=int(company_id),
                            material_id=int(material.id),
                            event="updated",
                        )
                    except Exception:
                        log.exception("material update notification failed material_id=%s", material.id)

                return True, "Material updated successfully.", {
                    "material": self._material_summary_out(material)
                }

        except (BusinessValidationError, NotFoundError) as e:
            return False, str(e), None
        except IntegrityError:
            return False, "Database constraint error. Please check duplicate material title or invalid references.", None
        except Exception as e:
            return False, f"Unexpected error: {e}", None

    # =========================================================
    # DELETE (Single & Bulk)
    # =========================================================

    def delete_material(
            self,
            *,
            company_id: int,
            material_id: int,
            permanent: bool = False,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Delete a material. Soft delete by default."""
        try:
            material = self.repo.get_material(material_id, company_id=company_id)
            if not material:
                raise NotFoundError(ERR_MATERIAL_NOT_FOUND)

            with self.s.begin_nested():
                if permanent:
                    if self.repo.has_interactions(company_id=company_id, material_id=material_id):
                        raise BusinessValidationError(ERR_MATERIAL_HAS_INTERACTIONS)


                    self.repo.delete_material_permanently(material)
                else:
                    material.is_enabled = False
                    self.s.flush([material])

            action = "permanently deleted" if permanent else "disabled"
            return True, f"Material {action} successfully", {
                "material": self._material_record(material)
            }

        except (BusinessValidationError, NotFoundError) as e:
            return False, str(e), None
        except Exception as e:

            return False, f"Unexpected error: {e}", None

    def bulk_delete_materials(
            self,
            *,
            company_id: int,
            material_ids: List[int],
            permanent: bool = False,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Bulk delete materials with detailed results."""
        try:
            if not material_ids:
                raise BusinessValidationError("material_ids is required.")

            if len(material_ids) > MAX_MATERIALS_PER_REQUEST:
                raise BusinessValidationError(ERR_TOO_MANY_MATERIALS)

            material_ids = [int(x) for x in material_ids]
            if len(set(material_ids)) != len(material_ids):
                raise BusinessValidationError(ERR_DUPLICATE_IDS)

            # Batch fetch all materials (ONE query)
            materials = self.repo.get_materials_by_ids(material_ids, company_id=company_id)

            # Batch check interactions for permanent delete (ONE query)
            interaction_counts = {}
            if permanent:
                interaction_counts = self.repo.count_interactions_for_materials(
                    company_id=company_id,
                    material_ids=material_ids,
                )

            deleted: List[int] = []
            failed: List[Dict[str, Any]] = []

            with self.s.begin_nested():
                for material_id in material_ids:
                    material = materials.get(int(material_id))

                    if not material:
                        failed.append({"id": material_id, "message": ERR_MATERIAL_NOT_FOUND})
                        continue

                    if permanent:
                        count = interaction_counts.get(int(material_id), 0)
                        if count > 0:
                            failed.append({
                                "id": material_id,
                                "message": f"Cannot delete: has {count} student interaction(s).",
                            })
                            continue


                        self.repo.delete_material_permanently(material)
                    else:
                        material.is_enabled = False
                        self.s.flush([material])

                    deleted.append(material_id)

            return True, "Bulk delete completed", {
                "deleted": deleted,
                "failed": failed,
                "deleted_count": len(deleted),
                "failed_count": len(failed),
                "permanent": permanent,
            }

        except BusinessValidationError as e:
            return False, str(e), None
        except Exception as e:

            return False, f"Unexpected error: {e}", None

        # =========================================================
        # FRAPPE-STYLE BULK UPDATE (Full-State Sync)
        # =========================================================

    def bulk_update_materials(
            self,
            *,
            company_id: int,
            offering_id: int,
            materials_data: List[Dict[str, Any]],
            missing_action: str = "disable",
            permanent: bool = False,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Frappe-style full-state sync for materials in an offering.

        This is the PREFERRED way to manage materials for a specific offering.

        Rules:
        - ID in request → UPDATE existing material
        - No ID → CREATE new material
        - Existing ID not in request → DISABLE (or DELETE if permanent=true & missing_action=delete)
        """
        try:
            # Validate offering
            if not offering_id:
                raise BusinessValidationError("offering_id is required.")

            if not self.repo.course_offering_exists(company_id=company_id, offering_id=offering_id):
                raise NotFoundError(ERR_COURSE_OFFERING_NOT_FOUND)

            # Validate request size
            if len(materials_data) > MAX_MATERIALS_PER_REQUEST:
                raise BusinessValidationError(ERR_TOO_MANY_MATERIALS)

            # Normalize missing action
            action = _normalize_missing_action(missing_action)

            # Fetch existing materials for this offering (ONE query with eager loading)
            existing_ids = self.repo.get_material_ids_by_offering(
                company_id=company_id,
                offering_id=offering_id,
            )

            existing_materials = self.repo.get_materials_by_ids(
                list(existing_ids),
                company_id=company_id,
                eager_load=["course_offering", "chapter"],
            )
            existing_map = {int(m.id): m for m in existing_materials.values()}

            # Process all materials
            incoming_ids: Set[int] = set()
            created: List[Material] = []
            updated: List[Material] = []

            with self.s.begin_nested():
                for raw in materials_data:
                    row = dict(raw or {})
                    material_id = row.get("id")

                    if material_id:
                        # UPDATE existing material
                        material_id = int(material_id)
                        incoming_ids.add(material_id)

                        if material_id not in existing_map:
                            raise BusinessValidationError(
                                f"Material {material_id} does not exist or does not belong to offering {offering_id}."
                            )

                        material = existing_map[material_id]

                        # Prevent changing offering via bulk update
                        if "course_offering_id" in row and int(row["course_offering_id"]) != offering_id:
                            raise BusinessValidationError(
                                f"Cannot move material {material_id} to different offering via bulk update."
                            )

                        # Remove immutable fields
                        row.pop("course_offering_id", None)
                        row.pop("material_type", None)

                        # Apply update
                        success, msg, _ = self.update_material(
                            company_id=company_id,
                            material_id=material_id,
                            data=row,
                        )
                        if not success:
                            raise BusinessValidationError(f"Error updating material {material_id}: {msg}")

                        material = self.repo.get_material(material_id, company_id=company_id)
                        updated.append(material)
                    else:
                        # CREATE new material
                        row["course_offering_id"] = offering_id

                        success, msg, out = self.create_material(
                            company_id=company_id,
                            data=row,
                        )
                        if not success or not out:
                            raise BusinessValidationError(f"Error creating material: {msg}")

                        material_id = out["material"]["id"]
                        material = self.repo.get_material(material_id, company_id=company_id)
                        created.append(material)
                        incoming_ids.add(material_id)

                # Handle missing materials (Frappe pattern)
                if action != "keep":
                    missing_ids = set(existing_map.keys()) - incoming_ids

                    for material_id in missing_ids:
                        material = existing_map[material_id]

                        if action == "disable":
                            material.is_enabled = False
                            self.s.flush([material])
                        elif action == "delete":
                            if not permanent:
                                raise BusinessValidationError(
                                    f"Cannot delete material {material_id} without permanent=true."
                                )

                            if self.repo.has_interactions(company_id=company_id, material_id=material_id):
                                raise BusinessValidationError(
                                    f"Cannot delete material {material_id}: has student interactions."
                                )


                            self.repo.delete_material_permanently(material)

            return True, "Materials updated successfully", {
                "created": [self._material_record(m) for m in created],
                "updated": [self._material_record(m) for m in updated],
                "deleted": list(missing_ids) if action == "delete" else [],
                "disabled": list(missing_ids) if action == "disable" else [],
                "created_count": len(created),
                "updated_count": len(updated),
                "deleted_count": len(missing_ids) if action == "delete" else 0,
                "disabled_count": len(missing_ids) if action == "disable" else 0,
            }

        except (BusinessValidationError, NotFoundError) as e:
            return False, str(e), None
        except Exception as e:

            return False, f"Unexpected error: {e}", None

    # =========================================================
    # FILE HANDLING
    # =========================================================

    def _upload_material_file(
            self,
            material: Material,
            file_storage: FileStorage,
            external_base: str,
    ) -> None:
        """Upload file to storage and update material file_url."""
        try:
            # Read file for size calculation
            raw = file_storage.read()
            file_storage.stream.seek(0)

            # Update file size if not set
            if material.file_size_mb is None:
                size_mb = round(len(raw) / (1024 * 1024), 4)
                material.file_size_mb = size_mb

            old_key = None
            marker = "/api/media/file/"
            if material.file_url and marker in material.file_url:
                old_key = unquote(material.file_url.split(marker, 1)[1])

            new_key = save_file_for(
                folder=MediaFolder.MATERIALS,
                item_id=material.id,
                file=file_storage,
                old_file_key=old_key,
            )
            if not new_key:
                raise BusinessValidationError("File upload failed: missing file content.")

            material.file_url = file_url_from_key(new_key, external_base=external_base)
            self.s.flush([material])

        except Exception as e:

            raise BusinessValidationError(f"File upload failed: {e}")

        # =========================================================
        # RECORD FORMATTERS
        # =========================================================

    @staticmethod
    def _material_record(material: Material) -> Dict[str, Any]:
        """Format material for API response (consistent shape)."""
        return {
            "id": int(material.id),
            "title": material.title,
            "material_type": material.material_type.value,
            "course_offering_id": int(material.course_offering_id),
            "chapter_id": int(material.chapter_id) if material.chapter_id else None,
            "file_url": material.file_url,
            "file_size_mb": float(material.file_size_mb) if material.file_size_mb is not None else None,
            "page_count": material.page_count,
            "slide_count": material.slide_count,
            "learning_objectives": material.learning_objectives,
            "description": material.description,
            "is_downloadable": bool(material.is_downloadable),
            "is_enabled": bool(material.is_enabled),
            "view_count": int(material.view_count),
            "download_count": int(material.download_count),
            "created_at": material.created_at.isoformat() if material.created_at else None,
            "updated_at": material.updated_at.isoformat() if material.updated_at else None,
        }

    # =========================================================
    # LIST (CURSOR)
    # =========================================================
    def list_materials_cursor(
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
        cur = _decode_cursor(cursor)

        def _safe_int(val):
            try:
                return int(val) if val is not None else None
            except Exception:
                return None

        last_id = _safe_int(cur.get("last_id"))
        last_priority = _safe_int(cur.get("last_priority"))
        last_semester_number = _safe_int(cur.get("last_semester_number"))

        uid = getattr(getattr(g, "auth", None), "user_id", None)

        params = {
            "mode": "cursor",
            "limit": limit,
            "last_id": last_id,
            "last_priority": last_priority,
            "last_semester_number": last_semester_number,
            "filters": filters,
            "is_enabled": is_enabled,
            "external_base": external_base,
            "user_id": int(uid) if uid is not None else None,
        }

        def builder():
            rows, total, has_more, next_cursor_payload = self.repo.list_materials_cursor(
                company_id=company_id,
                limit=limit,
                last_id=last_id,
                last_priority=last_priority,
                last_semester_number=last_semester_number,
                filters=filters,
                is_enabled=is_enabled,
            )

            data = [
                self.repo.shape_material_list_row(r, external_base=external_base)
                for r in rows
            ]

            empty_message = None
            if not data:
                empty_message = self.repo.get_student_materials_empty_message(
                    company_id=company_id,
                    filters=filters,
                )

            return {
                "data": data,
                "message": empty_message,
                "pagination": {
                    "limit": limit,
                    "next_cursor": _encode_cursor(next_cursor_payload),
                    "has_more": bool(has_more),
                },
                "meta": {
                    "total_count": int(total),
                },
            }

        out = cached_list(
            entity="materials:list",
            company_id=company_id,
            params=params,
            scope="default",
            ttl=20,
            builder=builder,
        )

        msg = out.get("message") or "OK"
        return True, msg, out
    # -------------------------------------------------------------------------
    # STUDENT LIST (Page)
    # -------------------------------------------------------------------------

    def list_materials_page(
            self,
            *,
            company_id: int,
            page: int,
            per_page: int,
            filters: Dict[str, Any],
            is_enabled: Optional[bool],
            external_base: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        allowed = {10, 20, 50, 100}
        per_page = per_page if int(per_page or 20) in allowed else 20
        page = max(int(page or 1), 1)

        uid = getattr(getattr(g, "auth", None), "user_id", None)

        params = {
            "mode": "page",
            "page": page,
            "per_page": per_page,
            "filters": filters,
            "is_enabled": is_enabled,
            "external_base": external_base,
            "user_id": int(uid) if uid is not None else None,
        }

        def builder():
            rows, total, pages = self.repo.list_materials_page(
                company_id=company_id,
                page=page,
                per_page=per_page,
                filters=filters,
                is_enabled=is_enabled,
            )

            data = [
                self.repo.shape_material_list_row(r, external_base=external_base)
                for r in rows
            ]

            empty_message = None
            if not data:
                empty_message = self.repo.get_student_materials_empty_message(
                    company_id=company_id,
                    filters=filters,
                )

            return {
                "data": data,
                "message": empty_message,
                "pagination": {
                    "page": page,
                    "limit": per_page,
                    "total": int(total),
                    "has_more": page < pages,
                },
            }

        out = cached_list(
            entity="materials:list",
            company_id=company_id,
            params=params,
            scope="default",
            ttl=20,
            builder=builder,
        )

        msg = out.get("message") or "OK"
        return True, msg, out

    # -------------------------------------------------------------------------
    # STUDENT DETAIL
    # -------------------------------------------------------------------------

    def get_material_detail(
            self,
            *,
            company_id: int,
            material_id: int,
            external_base: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Student-facing material detail.

        Rules:
        - Student can only see enabled materials inside their company.
        - Student can only see materials for their own department/faculty scope.
        - Cache must be user-aware because response includes user_state.
        """

        uid = getattr(getattr(g, "auth", None), "user_id", None)
        uid_int = int(uid) if uid is not None else None

        scope = self.repo.current_user_scope_for_debug(company_id=company_id)

        params = {
            "user_id": uid_int,
            "material_id": int(material_id),
            "external_base": external_base,
            "profile_type": scope.get("profile_type"),
            "department_id": scope.get("department_id"),
            "faculty_id": scope.get("faculty_id"),
            "semester_id": scope.get("semester_id"),
        }

        def builder():
            row = self.repo.get_material_detail(
                company_id=company_id,
                material_id=material_id,
            )

            if not row:
                return None

            return self.repo.shape_material_detail_row(
                row,
                external_base=external_base,
                company_id=company_id,
            )

        # ✅ Keep TTL cache, but make student detail user/scope aware.
        data = cached_list(
            entity="materials:student:detail",
            company_id=company_id,
            params=params,
            scope="student",
            ttl=20,
            builder=builder,
        )

        if data is None:
            reason = self.repo.get_student_material_access_message(
                company_id=company_id,
                material_id=material_id,
            )
            return False, reason, {}

        return True, "OK", {"data": data}
    # -------------------------------------------------------------------------
    # ADMIN LIST (Page)
    # -------------------------------------------------------------------------

    def list_materials_admin_page(
        self,
        *,
        company_id: int,
        page: int,
        per_page: int,
        filters: Dict[str, Any],
        external_base: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        allowed = {10, 20, 50, 100}
        per_page = per_page if int(per_page or 20) in allowed else 20
        page = max(int(page or 1), 1)

        uid = getattr(getattr(g, "auth", None), "user_id", None)

        params = {
            "mode": "admin:page",
            "page": page,
            "per_page": per_page,
            "filters": filters,
            "user_id": int(uid) if uid is not None else None,
        }

        def builder():
            rows, total, pages = self.repo.list_materials_admin_page(
                company_id=company_id,
                page=page,
                per_page=per_page,
                filters=filters,
            )
            data = [self.repo.shape_admin_list_row(r) for r in rows]
            return {
                "data": data,
                "pagination": {
                    "page": page,
                    "limit": per_page,
                    "total": int(total),
                    "has_more": page < pages,
                },
            }

        out = cached_list(
            entity="materials:admin:list",
            company_id=company_id,
            params=params,
            scope="admin",
            ttl=5,
            builder=builder,
        )
        return True, "OK", out

    # -------------------------------------------------------------------------
    # ADMIN DETAIL
    # -------------------------------------------------------------------------

    def get_material_detail_admin(
        self,
        *,
        company_id: int,
        material_id: int,
        external_base: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        row = self.repo.get_material_detail_admin(
            company_id=company_id, material_id=material_id
        )
        if not row:
            return False, "Material not found.", {}

        data = self.repo.shape_admin_detail_row(row, external_base=external_base)
        return True, "OK", {"data": data}

    # -------------------------------------------------------------------------
    # FILTER OPTIONS
    # -------------------------------------------------------------------------

    def get_material_filter_options(
        self,
        *,
        company_id: int,
        filters: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        uid = getattr(getattr(g, "auth", None), "user_id", None)

        params = {
            "mode": "filter-options",
            "filters": filters,
            "user_id": int(uid) if uid is not None else None,
        }

        def builder():
            return self.repo.get_material_filter_options(
                company_id=company_id, filters=filters
            )

        out = cached_list(
            entity="materials:filter-options",
            company_id=company_id,
            params=params,
            scope="default",
            ttl=20,
            builder=builder,
        )
        return True, "OK", out

    # -------------------------------------------------------------------------
    # TRACK VIEW
    # -------------------------------------------------------------------------

    def track_view(
        self,
        *,
        company_id: int,
        material_id: int,
        cooldown_seconds: int = 3600,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        uid = self.repo._current_user_id()
        if not uid:
            return False, "Authentication required.", {}

        try:
            with self.s.begin_nested():
                result = self.repo.increment_view(
                    company_id=company_id,
                    material_id=material_id,
                    user_id=int(uid),
                    cooldown_seconds=int(cooldown_seconds),
                )
            message = (
                "View tracked successfully."
                if result["counted"]
                else (result.get("reason") or "View not counted.")
            )
            return True, message, {
                "tracking": {
                    "material_id": int(result["material_id"]),
                    "user_id": int(uid),
                    "event": "view",
                    "counted": bool(result["counted"]),
                    "reason": result.get("reason"),
                    "global_view_count": int(result["global_view_count"]),
                    "global_download_count": int(result["global_download_count"]),
                    "user_view_count": int(result["user_view_count"]),
                    "user_download_count": int(result["user_download_count"]),
                    "last_viewed_at": result.get("last_viewed_at"),
                    "last_downloaded_at": result.get("last_downloaded_at"),
                }
            }
        except Exception as exc:
            log.exception("[materials.track_view] material_id=%s", material_id)
            return False, f"Failed to track view: {exc}", {}

    # -------------------------------------------------------------------------
    # TRACK DOWNLOAD
    # -------------------------------------------------------------------------

    def track_download(
        self,
        *,
        company_id: int,
        material_id: int,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        uid = self.repo._current_user_id()
        if not uid:
            return False, "Authentication required.", {}

        try:
            with self.s.begin_nested():
                result = self.repo.increment_download(
                    company_id=company_id,
                    material_id=material_id,
                    user_id=int(uid),
                )
            if not result["counted"]:
                return False, result.get("reason") or "Download not counted.", {}

            return True, "Download tracked successfully.", {
                "tracking": {
                    "material_id": int(result["material_id"]),
                    "user_id": int(uid),
                    "event": "download",
                    "counted": bool(result["counted"]),
                    "reason": result.get("reason"),
                    "global_view_count": int(result["global_view_count"]),
                    "global_download_count": int(result["global_download_count"]),
                    "user_view_count": int(result["user_view_count"]),
                    "user_download_count": int(result["user_download_count"]),
                    "last_viewed_at": result.get("last_viewed_at"),
                    "last_downloaded_at": result.get("last_downloaded_at"),
                }
            }
        except Exception as exc:
            log.exception("[materials.track_download] material_id=%s", material_id)
            return False, f"Failed to track download: {exc}", {}

    # -------------------------------------------------------------------------
    # SET FAVORITE
    # -------------------------------------------------------------------------

    def set_favorite(
        self,
        *,
        company_id: int,
        material_id: int,
        is_favorite: bool,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        uid = self.repo._current_user_id()
        if not uid:
            return False, "Authentication required.", {}

        try:
            with self.s.begin_nested():
                result = self.repo.set_favorite(
                    company_id=company_id,
                    material_id=material_id,
                    user_id=int(uid),
                    is_favorite=bool(is_favorite),
                )
            if not result["counted"]:
                return False, result.get("reason") or "Favorite not updated.", {}

            return True, "Favorite updated successfully.", {
                "favorite": {
                    "material_id": int(result["material_id"]),
                    "user_id": int(uid),
                    "is_favorite": bool(result["is_favorite"]),
                    "user_view_count": int(result["user_view_count"]),
                    "user_download_count": int(result["user_download_count"]),
                    "last_viewed_at": result.get("last_viewed_at"),
                    "last_downloaded_at": result.get("last_downloaded_at"),
                }
            }
        except Exception as exc:
            log.exception("[materials.set_favorite] material_id=%s", material_id)
            return False, f"Failed to update favorite: {exc}", {}

    # -------------------------------------------------------------------------
    # LIST FAVORITES
    # -------------------------------------------------------------------------

    def list_my_favorites_page(
        self,
        *,
        company_id: int,
        page: int,
        per_page: int,
        external_base: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        uid = self.repo._current_user_id()
        if not uid:
            return False, "Authentication required.", {}

        allowed = {10, 20, 50, 100}
        per_page = per_page if int(per_page or 20) in allowed else 20
        page = max(int(page or 1), 1)

        try:
            rows, total, pages = self.repo.list_favorite_materials_page(
                company_id=company_id,
                user_id=int(uid),
                page=page,
                per_page=per_page,
                external_base=external_base,
            )
            return True, "OK", {
                "data": rows,
                "pagination": {
                    "page": int(page),
                    "limit": int(per_page),
                    "total": int(total),
                    "has_more": page < pages,
                },
            }
        except Exception as exc:
            log.exception("[materials.list_favorites]")
            return False, f"Failed to load favorites: {exc}", {}

    # -------------------------------------------------------------------------
    # FEEDBACK
    # -------------------------------------------------------------------------

    def submit_feedback(
        self,
        *,
        company_id: int,
        material_id: int,
        feedback_type: str,
        rating: Optional[int] = None,
        message: Optional[str] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        uid = self.repo._current_user_id()
        if not uid:
            return False, "Authentication required.", {}

        if not self.repo.material_exists_in_scope(
            company_id=company_id,
            material_id=material_id,
        ):
            return False, "Material not found.", {}

        try:
            with self.s.begin_nested():
                if feedback_type == "rating":
                    row = self.repo.upsert_rating(
                        company_id=company_id,
                        material_id=material_id,
                        user_id=int(uid),
                        rating=int(rating or 0),
                    )
                else:
                    row = self.repo.create_feedback(
                        company_id=company_id,
                        material_id=material_id,
                        user_id=int(uid),
                        feedback_type=feedback_type,
                        rating=rating,
                        message=message,
                    )

            mat = self.s.get(Material, int(material_id))
            return True, "Feedback submitted.", {
                "feedback": self.repo._shape_feedback_row(row, None, None),
                "material_stats": {
                    "rating_count": int(mat.rating_count or 0) if mat else 0,
                    "rating_avg": round(float(mat.rating_avg or 0), 2) if mat else 0.0,
                },
            }
        except Exception as exc:
            log.exception("[materials.submit_feedback] material_id=%s", material_id)
            return False, "Failed to submit feedback.", {}

    def list_material_feedback(
        self,
        *,
        company_id: int,
        material_id: int,
        limit: int = 50,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        if not self.repo.material_exists_in_scope(
            company_id=company_id,
            material_id=material_id,
        ):
            return False, "Material not found.", {}

        uid = self.repo._current_user_id()
        rows = self.repo.list_material_feedback(
            company_id=company_id,
            material_id=material_id,
            viewer_user_id=int(uid) if uid else None,
            include_ratings=False,
            limit=limit,
        )

        user_rating = None
        if uid:
            rating_row = self.repo.get_user_rating(
                company_id=company_id,
                material_id=material_id,
                user_id=int(uid),
            )
            if rating_row:
                user_rating = int(rating_row.rating)

        return True, "OK", {
            "items": rows,
            "user_rating": user_rating,
        }

    def list_feedback_admin(
        self,
        *,
        company_id: int,
        status: Optional[str] = None,
        feedback_type: Optional[str] = None,
        material_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        rows, total, pages = self.repo.list_feedback_admin(
            company_id=company_id,
            status=status,
            feedback_type=feedback_type,
            material_id=material_id,
            page=page,
            per_page=per_page,
        )
        return True, "OK", {
            "data": rows,
            "pagination": {
                "page": int(page),
                "limit": int(per_page),
                "total": int(total),
                "pages": int(pages),
            },
        }

    def reply_feedback(
        self,
        *,
        company_id: int,
        feedback_id: int,
        admin_user_id: int,
        admin_reply: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        row = self.repo.reply_to_feedback(
            company_id=company_id,
            feedback_id=feedback_id,
            admin_user_id=admin_user_id,
            admin_reply=admin_reply,
        )
        if not row:
            return False, "Feedback not found.", {}
        return True, "Reply saved.", {
            "feedback": self.repo._shape_feedback_row(row, None, None),
        }

    def resolve_feedback(
        self,
        *,
        company_id: int,
        feedback_id: int,
        admin_user_id: int,
        admin_reply: Optional[str] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        row = self.repo.resolve_feedback(
            company_id=company_id,
            feedback_id=feedback_id,
            admin_user_id=admin_user_id,
            admin_reply=admin_reply,
        )
        if not row:
            return False, "Feedback not found.", {}
        return True, "Feedback resolved.", {
            "feedback": self.repo._shape_feedback_row(row, None, None),
        }

    def get_access_reports(
        self,
        *,
        company_id: int,
        limit: int = 10,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        return True, "OK", self.repo.get_access_reports(company_id=company_id, limit=limit)

    def get_feedback_admin_summary(
        self,
        *,
        company_id: int,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        return True, "OK", self.repo.get_feedback_admin_summary(company_id=company_id)
