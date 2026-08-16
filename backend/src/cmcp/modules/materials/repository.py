# # src/cmcp/modules/materials/repository.py


from __future__ import annotations
import logging
from dataclasses import dataclass, field

from dataclasses import dataclass
from typing import Optional, Any, Dict, Tuple, List, Optional, Set, Tuple
from flask import g
from sqlalchemy import exists, func, select, and_, case, literal, update, or_ as sa_or, or_
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload
from cmcp.config.database import db
from cmcp.core.base_repo import BaseRepository
from cmcp.modules.materials.models import (
    Material,
    StudentMaterialInteraction,
    MaterialFeedback,
    MaterialFeedbackReply,
    MaterialFeedbackTypeEnum,
    MaterialFeedbackStatusEnum,
)
from cmcp.modules.academic.models import (
    Course,
    CourseOffering,  # NEW
    CourseChapter,  # NEW (replaces old Chapter)
    Semester,
    AcademicYear,
    Department,
    Faculty
)
from cmcp.modules.education_people.models import StudentProfile, StaffProfile

log = logging.getLogger(__name__)


def _ilike_pattern(search: str) -> str:
    escaped = (
        (search or "")
        .strip()
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{escaped}%"


@dataclass
class MaterialListRow:
    """
    Student-facing list/detail row with full context and user interactions.
    """
    # Core
    material_id: int
    title: str
    description: Optional[str]
    material_type: str
    file_url: Optional[str]
    file_size_mb: Optional[float]
    page_count: Optional[int]
    slide_count: Optional[int]
    is_enabled: bool
    is_downloadable: bool
    created_at: Any
    updated_at: Any

    # Stats
    view_count: int
    download_count: int

    # Course context
    course_id: int
    course_title: str
    course_code: Optional[str]

    # Offering context
    course_offering_id: int
    custom_title: Optional[str]
    credit_hours: Optional[int]

    # Chapter context
    chapter_id: Optional[int]
    chapter_title: Optional[str]
    chapter_number: Optional[int]

    # Academic context
    semester_id: Optional[int]
    semester_number: Optional[int]
    semester_name: Optional[str]
    academic_year_id: Optional[int]
    academic_year_name: Optional[str]
    department_id: Optional[int]
    department_name: Optional[str]
    faculty_id: Optional[int]
    faculty_name: Optional[str]

    # User interactions
    is_favorite: bool
    user_view_count: int
    user_download_count: int
    last_viewed_at: Optional[Any]
    last_downloaded_at: Optional[Any]

    # Sort helpers
    sort_semester_number: Optional[int] = None
    sort_semester_priority: Optional[int] = None
    rating_count: int = 0
    rating_avg: float = 0.0


@dataclass
class MaterialAdminListRow:
    """
    Admin-facing row - lighter, no user interactions.
    Includes all fields needed for both list and detail views.
    """
    # Core
    material_id: int
    title: str
    material_type: str
    is_enabled: bool
    is_downloadable: bool
    view_count: int
    download_count: int
    created_at: Any
    updated_at: Any

    # File metadata
    file_url: Optional[str]
    file_size_mb: Optional[float]
    page_count: Optional[int]
    slide_count: Optional[int]

    # Chapter (with description for detail)
    chapter_id: Optional[int]
    chapter_title: Optional[str]
    chapter_number: Optional[int]
    chapter_description: Optional[str]

    # Course
    course_id: int
    course_title: str
    course_code: Optional[str]

    # Offering
    course_offering_id: int
    custom_title: Optional[str]
    credit_hours: Optional[int]

    # Academic context (for detail)
    department_id: Optional[int]
    department_name: Optional[str]
    faculty_id: Optional[int]
    faculty_name: Optional[str]
    semester_id: Optional[int]
    semester_number: Optional[int]
    semester_name: Optional[str]
    academic_year_id: Optional[int]
    academic_year_name: Optional[str]

    # Detail-only fields
    description: Optional[str] = None
    learning_objectives: Optional[List[Any]] = field(default_factory=list)


MaterialDetailRow = MaterialListRow  # Same shape for student detail

class MaterialsRepo:
    def __init__(self, session: Optional[Session] = None):
        self.s: Session = session or db.session
        self.materials = BaseRepository(Material, self.s)

    # =========================================================
    # GETTERS
    # =========================================================

    def get_material(
            self,
            material_id: int,
            *,
            company_id: int,
            eager_load: Optional[List[str]] = None,
    ) -> Optional[Material]:
        """Get single material by ID."""
        return self.materials.get(
            int(material_id),
            company_id=int(company_id),
            eager_load=eager_load,
        )

    def get_materials_by_ids(
            self,
            material_ids: List[int],
            *,
            company_id: int,
            eager_load: Optional[List[str]] = None,
    ) -> Dict[int, Material]:
        """Batch fetch materials by IDs (fixes N+1 queries)."""
        if not material_ids:
            return {}

        stmt = select(Material).where(
            Material.id.in_([int(x) for x in material_ids]),
            Material.company_id == int(company_id),
        )

        if eager_load:
            if "course_offering" in eager_load:
                stmt = stmt.options(selectinload(Material.course_offering))
            if "chapter" in eager_load:
                stmt = stmt.options(selectinload(Material.chapter))

        materials = self.s.scalars(stmt).all()
        return {int(m.id): m for m in materials}

    def get_material_ids_by_offering(
            self,
            *,
            company_id: int,
            offering_id: int,
    ) -> Set[int]:
        """Get all material IDs for an offering (lightweight)."""
        stmt = select(Material.id).where(
            Material.company_id == int(company_id),
            Material.course_offering_id == int(offering_id),
        )
        return {int(x) for x in self.s.scalars(stmt).all()}

    # ----------------------------
    # helpers
    # ----------------------------

    def _current_user_id(self) -> Optional[int]:
        ctx = getattr(g, "auth", None)
        uid = getattr(ctx, "user_id", None) if ctx else None
        try:
            return int(uid) if uid is not None else None
        except Exception:
            return None

    def course_exists(self, *, company_id: int, course_id: int) -> bool:
        """Check if a course definition exists"""
        stmt = select(exists().where(
            Course.company_id == int(company_id),
            Course.id == int(course_id),
            Course.is_enabled.is_(True)
        ))
        return bool(self.s.scalar(stmt))

    def course_offering_exists(self, *, company_id: int, offering_id: int) -> bool:
        stmt = select(exists().where(
            CourseOffering.company_id == int(company_id),
            CourseOffering.id == int(offering_id),
            CourseOffering.is_enabled.is_(True),  # ✅ PostgreSQL correct
        ))
        return bool(self.s.scalar(stmt))

    def chapter_exists(self, *, company_id: int, chapter_id: int) -> bool:
        """Check if chapter exists."""
        stmt = select(exists().where(
            CourseChapter.company_id == int(company_id),
            CourseChapter.id == int(chapter_id),
        ))
        return bool(self.s.scalar(stmt))
    def chapter_get(self, *, company_id: int, chapter_id: int) -> Optional[CourseChapter]:
        """Get a course chapter (UPDATED to use CourseChapter)"""
        return self.s.query(CourseChapter).filter(
            CourseChapter.company_id == int(company_id),
            CourseChapter.id == int(chapter_id),
        ).first()

    def title_exists_in_scope(
            self,
            *,
            company_id: int,
            course_offering_id: int,
            chapter_id: Optional[int],
            title: str,
            exclude_id: Optional[int] = None,
    ) -> bool:
        """Check if material title exists in offering scope (case-insensitive)."""
        conds = [
            Material.company_id == int(company_id),
            Material.course_offering_id == int(course_offering_id),
            func.lower(Material.title) == func.lower(title.strip()),
        ]

        if chapter_id is None:
            conds.append(Material.chapter_id.is_(None))
        else:
            conds.append(Material.chapter_id == int(chapter_id))

        if exclude_id:
            conds.append(Material.id != int(exclude_id))

        stmt = select(exists().where(*conds))
        return bool(self.s.scalar(stmt))

    def chapter_belongs_to_offering(
            self,
            *,
            company_id: int,
            chapter_id: int,
            offering_id: int,
    ) -> bool:
        """Check if chapter belongs to a specific offering."""
        stmt = select(exists().where(
            CourseChapter.company_id == int(company_id),
            CourseChapter.id == int(chapter_id),
            CourseChapter.course_offering_id == int(offering_id),
        ))
        return bool(self.s.scalar(stmt))
    def has_interactions(self, *, company_id: int, material_id: int) -> bool:
        """Check if material has student interactions."""
        stmt = select(exists().where(
            StudentMaterialInteraction.company_id == int(company_id),
            StudentMaterialInteraction.material_id == int(material_id),
        ))
        return bool(self.s.scalar(stmt))

    # -------------------------------------------------------------------------
    # QUERY BUILDING HELPERS (Shared)
    # -------------------------------------------------------------------------

    def _add_standard_joins(self, stmt, *, company_id: int):
        """Add all standard joins once, reuse everywhere."""
        cid = int(company_id)
        return (
            stmt
            .join(CourseOffering, and_(
                CourseOffering.id == Material.course_offering_id,
                CourseOffering.company_id == cid,
            ))
            .join(Course, and_(
                Course.id == CourseOffering.course_id,
                Course.company_id == cid,
            ))
            .outerjoin(CourseChapter, and_(
                CourseChapter.id == Material.chapter_id,
                CourseChapter.company_id == cid,
            ))
            .outerjoin(Semester, and_(
                Semester.id == CourseOffering.semester_id,
                Semester.company_id == cid,
            ))
            .outerjoin(AcademicYear, and_(
                AcademicYear.id == Semester.academic_year_id,
                AcademicYear.company_id == cid,
            ))
            .outerjoin(Department, and_(
                Department.id == CourseOffering.department_id,
                Department.company_id == cid,
            ))
            .outerjoin(Faculty, and_(
                Faculty.id == Department.faculty_id,
                Faculty.company_id == cid,
            ))
        )

    def _apply_common_filters(self, stmt, filters: Dict[str, Any]) -> Any:
        """Apply all common filters (shared between student and admin)."""
        # Offering filter (CRITICAL for students)
        if filters.get("course_offering_id"):
            stmt = stmt.where(CourseOffering.id == int(filters["course_offering_id"]))

        if filters.get("chapter_id"):
            stmt = stmt.where(Material.chapter_id == int(filters["chapter_id"]))

        if filters.get("material_type"):
            stmt = stmt.where(
                func.lower(func.cast(Material.material_type, db.String))
                == filters["material_type"].lower()
            )

        if filters.get("semester_id"):
            stmt = stmt.where(CourseOffering.semester_id == int(filters["semester_id"]))

        if filters.get("academic_year_id"):
            stmt = stmt.where(Semester.academic_year_id == int(filters["academic_year_id"]))

        if filters.get("course_id"):
            stmt = stmt.where(Course.id == int(filters["course_id"]))

        if filters.get("department_id"):
            stmt = stmt.where(Department.id == int(filters["department_id"]))

        if filters.get("faculty_id"):
            stmt = stmt.where(Faculty.id == int(filters["faculty_id"]))

        if filters.get("uploaded_from"):
            stmt = stmt.where(Material.created_at >= filters["uploaded_from"])

        if filters.get("uploaded_to"):
            stmt = stmt.where(Material.created_at <= filters["uploaded_to"])

        search = (filters.get("search") or "").strip()
        if search:
            pattern = _ilike_pattern(search)
            stmt = stmt.where(
                or_(
                    func.coalesce(Material.title, "").ilike(pattern, escape="\\"),
                    func.coalesce(Material.description, "").ilike(pattern, escape="\\"),
                    func.coalesce(Course.title, "").ilike(pattern, escape="\\"),
                    func.coalesce(Course.code, "").ilike(pattern, escape="\\"),
                    func.coalesce(CourseChapter.title, "").ilike(pattern, escape="\\"),
                )
            )

        return stmt

    def count_interactions_for_materials(
            self,
            *,
            company_id: int,
            material_ids: List[int],
    ) -> Dict[int, int]:
        """Batch count interactions for multiple materials."""
        if not material_ids:
            return {}

        stmt = (
            select(
                StudentMaterialInteraction.material_id,
                func.count(StudentMaterialInteraction.id),
            )
            .where(
                StudentMaterialInteraction.company_id == int(company_id),
                StudentMaterialInteraction.material_id.in_([int(x) for x in material_ids]),
            )
            .group_by(StudentMaterialInteraction.material_id)
        )

        results = self.s.execute(stmt).all()
        return {int(row[0]): int(row[1]) for row in results}

    def _current_user_scope(self, *, company_id: int) -> Dict[str, Any]:
        """
        Resolve user's academic scope.

        Priority:
        1. Student → department_id + faculty_id + semester_id + semester_number
        2. Staff with department_id → restrict to that department
        3. Staff with faculty_id only → restrict to all depts in that faculty
        4. Neither → super-admin (no restriction)
        """
        uid = self._current_user_id()
        base: Dict[str, Any] = {
            "user_id": int(uid) if uid is not None else None,
            "profile_type": None,
            "department_id": None,
            "faculty_id": None,
            "semester_id": None,
            "semester_number": None,
        }
        if uid is None:
            return base

        # Student profile
        sp = (
            self.s.query(
                StudentProfile.department_id,
                StudentProfile.faculty_id,
                StudentProfile.semester_id,
                Semester.number.label("semester_number"),
            )
            .outerjoin(
                Semester,
                and_(
                    Semester.id == StudentProfile.semester_id,
                    Semester.company_id == int(company_id),
                ),
            )
            .filter(
                StudentProfile.company_id == int(company_id),
                StudentProfile.user_id == int(uid),
                StudentProfile.is_enabled.is_(True),
            )
            .first()
        )
        if sp:
            return {
                **base,
                "profile_type": "student",
                "department_id": int(sp.department_id) if sp.department_id else None,
                "faculty_id": int(sp.faculty_id) if sp.faculty_id else None,
                "semester_id": int(sp.semester_id) if sp.semester_id else None,
                "semester_number": int(sp.semester_number) if sp.semester_number else None,
            }

        # Staff profile
        st = (
            self.s.query(StaffProfile.department_id, StaffProfile.faculty_id)
            .filter(
                StaffProfile.company_id == int(company_id),
                StaffProfile.user_id == int(uid),
                StaffProfile.is_enabled.is_(True),
            )
            .first()
        )
        if st:
            return {
                **base,
                "profile_type": "staff",
                "department_id": int(st.department_id) if st.department_id else None,
                "faculty_id": int(st.faculty_id) if st.faculty_id else None,
            }

        # Super admin
        return {**base, "profile_type": "admin"}
    def _apply_scope(self, stmt, scope: Dict[str, Any]):
        """Apply department/faculty scope to any statement with CourseOffering joined."""
        dept_id = scope.get("department_id")
        fac_id = scope.get("faculty_id")

        if dept_id:
            return stmt.where(CourseOffering.department_id == int(dept_id))
        if fac_id:
            return stmt.where(Faculty.id == int(fac_id))
        return stmt
    # =========================================================
    # WRITE OPERATIONS
    # =========================================================

    def create_material(self, data: Dict[str, Any]) -> Material:
        """Create a new material."""
        return self.materials.create(data)

    def update_material(self, material: Material, data: Dict[str, Any]) -> None:
        """Update a material in-place."""
        for key, value in data.items():
            if hasattr(material, key) and key != "id":
                setattr(material, key, value)
        self.s.flush([material])

    def delete_material_permanently(self, material: Material) -> None:
        """Hard delete - USE WITH CAUTION. Caller must verify interactions check."""
        self.s.delete(material)

    def bulk_create_materials(self, materials_data: List[Dict[str, Any]]) -> List[Material]:
        """Create multiple materials in one transaction."""
        created = []
        for data in materials_data:
            material = self.materials.create(data)
            created.append(material)
        return created

    # ----------------------------
    # list/detail query builder (UPDATED)
    # ----------------------------

    def _semester_priority_expr(self, current_semester_number: Optional[int]):
        if not current_semester_number:
            return None
        n = int(current_semester_number)
        return case(
            (Semester.number >= n, Semester.number - n),
            else_=(1000 + Semester.number - n),
        )

    def _use_semester_priority(self, *, scope: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Semester-proximity ordering only for students with no explicit filters."""
        if scope.get("profile_type") != "student":
            return False
        if not scope.get("semester_number"):
            return False
        # Don't use priority if user explicitly filtered
        if any(filters.get(k) for k in ("semester_id", "course_id", "chapter_id")):
            return False
        if self._resolve_sort_by(filters) != "recent":
            return False
        return True


    def _resolve_sort_by(self, filters: Dict[str, Any]) -> str:
        raw = (filters.get("sort_by") or "recent").strip().lower()
        allowed = {
            "recent",
            "most_viewed",
            "most_downloaded",
            "highest_rated",
            "alphabetical",
        }
        return raw if raw in allowed else "recent"

    def _apply_ordering(self, stmt, *, scope: Dict[str, Any], filters: Dict[str, Any]):
        sort_by = self._resolve_sort_by(filters)

        if sort_by == "most_viewed":
            return stmt.order_by(Material.view_count.desc(), Material.id.desc())
        if sort_by == "most_downloaded":
            return stmt.order_by(Material.download_count.desc(), Material.id.desc())
        if sort_by == "highest_rated":
            return stmt.order_by(Material.rating_avg.desc(), Material.rating_count.desc(), Material.id.desc())
        if sort_by == "alphabetical":
            return stmt.order_by(Material.title.asc(), Material.id.asc())

        if self._use_semester_priority(scope=scope, filters=filters):
            prio = self._semester_priority_expr(scope["semester_number"])
            return stmt.order_by(
                prio.asc(),
                func.coalesce(Semester.number, 0).asc(),
                Material.id.desc(),
            )
        return stmt.order_by(Material.id.desc())

    def _apply_cursor_boundary(
        self,
        stmt,
        *,
        scope: Dict[str, Any],
        filters: Dict[str, Any],
        last_id: Optional[int],
        last_priority: Optional[int],
        last_semester_number: Optional[int],
    ):
        if not last_id:
            return stmt

        if self._use_semester_priority(scope=scope, filters=filters):
            if last_priority is None or last_semester_number is None:
                return stmt
            prio = self._semester_priority_expr(scope["semester_number"])
            sem_num = func.coalesce(Semester.number, 0)
            return stmt.where(
                or_(
                    prio > int(last_priority),
                    and_(prio == int(last_priority), sem_num > int(last_semester_number)),
                    and_(
                        prio == int(last_priority),
                        sem_num == int(last_semester_number),
                        Material.id < int(last_id),
                    ),
                )
            )

        return stmt.where(Material.id < int(last_id))

    # -------------------------------------------------------------------------
    # STUDENT BASE STATEMENT (With User Interactions)
    # -------------------------------------------------------------------------

    def _user_interaction_subquery(self, *, company_id: int, uid: int):
        return (
            select(
                StudentMaterialInteraction.material_id.label("m_id"),
                func.coalesce(StudentMaterialInteraction.is_favorite, False).label("is_favorite"),
                func.coalesce(StudentMaterialInteraction.view_count, 0).label("u_view_count"),
                func.coalesce(StudentMaterialInteraction.download_count, 0).label("u_download_count"),
                StudentMaterialInteraction.last_viewed_at,
                StudentMaterialInteraction.last_downloaded_at,
            )
            .where(
                StudentMaterialInteraction.company_id == int(company_id),
                StudentMaterialInteraction.user_id == int(uid),
            )
            .subquery("ui")
        )

    def _base_stmt(
        self,
        *,
        company_id: int,
        filters: Dict[str, Any],
        is_enabled: Optional[bool],
    ):
        """Student-facing base statement - includes user interactions."""
        uid = self._current_user_id() or 0
        scope = self._current_user_scope(company_id=company_id)

        use_sem = self._use_semester_priority(scope=scope, filters=filters)
        sem_prio = self._semester_priority_expr(scope.get("semester_number")) if use_sem else None
        ui = self._user_interaction_subquery(company_id=company_id, uid=uid)

        stmt = (
            select(
                Material.id.label("material_id"),
                Material.title,
                Material.description,
                Material.material_type,
                Material.file_url,
                Material.file_size_mb,
                Material.page_count,
                Material.slide_count,
                Material.is_enabled,
                Material.is_downloadable,
                Material.created_at,
                Material.updated_at,
                func.coalesce(Material.view_count, 0).label("view_count"),
                func.coalesce(Material.download_count, 0).label("download_count"),
                func.coalesce(Material.rating_count, 0).label("rating_count"),
                func.coalesce(Material.rating_avg, 0).label("rating_avg"),
                Course.id.label("course_id"),
                Course.title.label("course_title"),
                Course.code.label("course_code"),
                CourseOffering.id.label("course_offering_id"),
                CourseOffering.custom_title,
                CourseOffering.credit_hours,
                CourseChapter.id.label("chapter_id"),
                CourseChapter.title.label("chapter_title"),
                CourseChapter.number.label("chapter_number"),
                Semester.id.label("semester_id"),
                Semester.number.label("semester_number"),
                Semester.name.label("semester_name"),
                AcademicYear.id.label("academic_year_id"),
                AcademicYear.name.label("academic_year_name"),
                Department.id.label("department_id"),
                Department.name.label("department_name"),
                Faculty.id.label("faculty_id"),
                Faculty.name.label("faculty_name"),
                func.coalesce(ui.c.is_favorite, False).label("is_favorite"),
                func.coalesce(ui.c.u_view_count, 0).label("user_view_count"),
                func.coalesce(ui.c.u_download_count, 0).label("user_download_count"),
                ui.c.last_viewed_at,
                ui.c.last_downloaded_at,
                func.coalesce(Semester.number, 0).label("sort_semester_number"),
                sem_prio.label("sort_semester_priority") if sem_prio is not None else literal(None).label("sort_semester_priority"),
            )
            .select_from(Material)
        )

        stmt = self._add_standard_joins(stmt, company_id=company_id)
        stmt = stmt.outerjoin(ui, ui.c.m_id == Material.id)
        stmt = stmt.where(Material.company_id == int(company_id))

        # is_enabled filter
        if is_enabled is True:
            stmt = stmt.where(Material.is_enabled.is_(True))
        elif is_enabled is False:
            stmt = stmt.where(Material.is_enabled.is_(False))

        # Apply user scope
        stmt = self._apply_scope(stmt, scope)

        # Apply filters
        stmt = self._apply_common_filters(stmt, filters)

        # is_favorite filter
        if filters.get("is_favorite") is True:
            stmt = stmt.where(func.coalesce(ui.c.is_favorite, False).is_(True))

        return stmt

    # -------------------------------------------------------------------------
    # ADMIN BASE STATEMENT (No User Interactions)
    # -------------------------------------------------------------------------

    def _admin_base_stmt(
        self,
        *,
        company_id: int,
        filters: Dict[str, Any],
    ):
        """
        Admin-facing base statement - lighter, no user interactions.
        Admins see ALL materials (disabled ones too) unless filtered.
        """
        scope = self._current_user_scope(company_id=company_id)

        stmt = (
            select(
                Material.id.label("material_id"),
                Material.title,
                Material.description,
                Material.material_type,
                Material.file_url,
                Material.file_size_mb,
                Material.page_count,
                Material.slide_count,
                Material.is_enabled,
                Material.is_downloadable,
                Material.created_at,
                Material.updated_at,
                func.coalesce(Material.view_count, 0).label("view_count"),
                func.coalesce(Material.download_count, 0).label("download_count"),
                CourseChapter.id.label("chapter_id"),
                CourseChapter.title.label("chapter_title"),
                CourseChapter.number.label("chapter_number"),
                CourseChapter.description.label("chapter_description"),
                Course.id.label("course_id"),
                Course.title.label("course_title"),
                Course.code.label("course_code"),
                CourseOffering.id.label("course_offering_id"),
                CourseOffering.custom_title,
                CourseOffering.credit_hours,
                Department.id.label("department_id"),
                Department.name.label("department_name"),
                Faculty.id.label("faculty_id"),
                Faculty.name.label("faculty_name"),
                Semester.id.label("semester_id"),
                Semester.number.label("semester_number"),
                Semester.name.label("semester_name"),
                AcademicYear.id.label("academic_year_id"),
                AcademicYear.name.label("academic_year_name"),
            )
            .select_from(Material)
        )

        stmt = self._add_standard_joins(stmt, company_id=company_id)
        stmt = stmt.where(Material.company_id == int(company_id))

        # Apply admin scope (if admin belongs to a specific dept/faculty)
        stmt = self._apply_scope(stmt, scope)

        # Admin filters
        if filters.get("course_offering_id"):
            stmt = stmt.where(CourseOffering.id == int(filters["course_offering_id"]))
        if filters.get("chapter_id"):
            stmt = stmt.where(Material.chapter_id == int(filters["chapter_id"]))
        if filters.get("material_type"):
            stmt = stmt.where(
                func.lower(func.cast(Material.material_type, db.String))
                == filters["material_type"].lower()
            )
        if filters.get("is_enabled") is not None:
            stmt = stmt.where(Material.is_enabled.is_(bool(filters["is_enabled"])))

        search = (filters.get("search") or "").strip()
        if search:
            pattern = _ilike_pattern(search)
            stmt = stmt.where(
                or_(
                    func.coalesce(Material.title, "").ilike(pattern, escape="\\"),
                    func.coalesce(Material.description, "").ilike(pattern, escape="\\"),
                )
            )

        return stmt

    # -------------------------------------------------------------------------
    # STUDENT LIST METHODS
    # -------------------------------------------------------------------------

    def list_materials_cursor(
        self,
        *,
        company_id: int,
        limit: int,
        last_id: Optional[int],
        filters: Dict[str, Any],
        is_enabled: Optional[bool],
        last_priority: Optional[int] = None,
        last_semester_number: Optional[int] = None,
    ) -> Tuple[List[MaterialListRow], int, bool, Optional[Dict[str, Any]]]:
        """Student cursor-based list with full context."""
        scope = self._current_user_scope(company_id=company_id)

        base = self._base_stmt(company_id=company_id, filters=filters, is_enabled=is_enabled)
        base = self._apply_cursor_boundary(
            base, scope=scope, filters=filters,
            last_id=last_id, last_priority=last_priority,
            last_semester_number=last_semester_number,
        )
        base = self._apply_ordering(base, scope=scope, filters=filters).limit(limit + 1)

        rows = list(self.s.execute(base).all())
        has_more = len(rows) > limit
        rows = rows[:limit]

        # Count total
        count_base = self._base_stmt(company_id=company_id, filters=filters, is_enabled=is_enabled)
        total = int(self.s.scalar(select(func.count()).select_from(count_base.order_by(None).subquery())) or 0)

        shaped = [MaterialListRow(**r._asdict()) for r in rows]

        next_cursor_payload = None
        if has_more and shaped:
            last = shaped[-1]
            if self._use_semester_priority(scope=scope, filters=filters):
                next_cursor_payload = {
                    "last_id": int(last.material_id),
                    "last_priority": int(last.sort_semester_priority or 0),
                    "last_semester_number": int(last.sort_semester_number or 0),
                }
            else:
                next_cursor_payload = {"last_id": int(last.material_id)}

        return shaped, total, has_more, next_cursor_payload

    def list_materials_page(
        self,
        *,
        company_id: int,
        page: int,
        per_page: int,
        filters: Dict[str, Any],
        is_enabled: Optional[bool],
    ) -> Tuple[List[MaterialListRow], int, int]:
        """Student page-based list."""
        scope = self._current_user_scope(company_id=company_id)

        base = self._base_stmt(company_id=company_id, filters=filters, is_enabled=is_enabled)
        base = self._apply_ordering(base, scope=scope, filters=filters)

        total = int(self.s.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0)
        pages = max((total + per_page - 1) // per_page, 1)
        page = min(max(page, 1), pages)
        offset = (page - 1) * per_page

        base = self._apply_ordering(base, scope=scope, filters=filters).offset(offset).limit(per_page)
        rows = list(self.s.execute(base).all())
        shaped = [MaterialListRow(**r._asdict()) for r in rows]
        return shaped, total, pages

    # -------------------------------------------------------------------------
    # STUDENT DETAIL
    # -------------------------------------------------------------------------

    def get_material_detail(
            self,
            *,
            company_id: int,
            material_id: int,
    ) -> Optional[MaterialDetailRow]:
        """Get single enabled material detail with user state and scope check."""
        base = self._base_stmt(
            company_id=company_id,
            filters={},
            is_enabled=True,
        )

        row = self.s.execute(
            base.where(Material.id == int(material_id)).limit(1)
        ).first()

        return MaterialDetailRow(**row._asdict()) if row else None
    # -------------------------------------------------------------------------
    # ADMIN LIST
    # -------------------------------------------------------------------------

    def list_materials_admin_page(
        self,
        *,
        company_id: int,
        page: int,
        per_page: int,
        filters: Dict[str, Any],
    ) -> Tuple[List[MaterialAdminListRow], int, int]:
        """Admin page-based list - minimal data for tables."""
        base = self._admin_base_stmt(company_id=company_id, filters=filters)
        base = base.order_by(Material.updated_at.desc(), Material.id.desc())

        total = int(self.s.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0)
        pages = max((total + per_page - 1) // per_page, 1)
        page = min(max(page, 1), pages)
        offset = (page - 1) * per_page

        rows = list(self.s.execute(base.offset(offset).limit(per_page)).all())
        shaped = [MaterialAdminListRow(**r._asdict()) for r in rows]
        return shaped, total, pages

    # -------------------------------------------------------------------------
    # ADMIN DETAIL
    # -------------------------------------------------------------------------

    def get_material_detail_admin(
        self,
        *,
        company_id: int,
        material_id: int,
    ) -> Optional[MaterialAdminListRow]:
        """
        Full admin detail including learning objectives.
        Respects admin's dept/faculty scope.
        """
        base = self._admin_base_stmt(company_id=company_id, filters={})
        row = self.s.execute(base.where(Material.id == material_id).limit(1)).first()
        if not row:
            return None

        r = MaterialAdminListRow(**row._asdict())

        # Load learning objectives
        mat = self.s.get(Material, material_id)
        r.learning_objectives = list(mat.learning_objectives) if mat and mat.learning_objectives else []
        return r


    # -------------------------------------------------------------------------
    # RESPONSE SHAPERS
    # -------------------------------------------------------------------------

    def _file_extension(self, file_url: Optional[str]) -> Optional[str]:
        if not file_url:
            return None
        last = file_url.rstrip("/").split("/")[-1]
        if last.endswith(".enc"):
            last = last[:-4]
        return last.rsplit(".", 1)[-1].lower() if "." in last else None

    def _material_type_value(self, material_type) -> Optional[str]:
        if material_type is None:
            return None
        return getattr(material_type, "value", str(material_type)).lower()

    def _normalize_url(self, file_url: Optional[str], external_base: str) -> Optional[str]:
        """
        Rebuild media URLs for the current environment.

        DB should store relative paths like `/api/media/file/<key>` (or legacy absolute
        hosts). We always re-emit using external_base when provided, otherwise a
        relative `/api/media/...` path so DEV→PROD does not require rewriting rows.
        """
        if not file_url:
            return None

        raw = str(file_url).strip()
        marker = "/api/media/file/"

        # External LINK materials: leave untouched.
        if raw.startswith(("http://", "https://")) and marker not in raw:
            return raw

        key = None
        if marker in raw:
            key = raw.split(marker, 1)[1]
        elif raw.startswith("materials_files/"):
            key = raw

        if not key:
            return raw

        base = (external_base or "").rstrip("/")
        if base:
            return f"{base}{marker}{key}"
        return f"{marker}{key}"

    def _download_url(self, file_url: Optional[str], external_base: str) -> Optional[str]:
        read = self._normalize_url(file_url, external_base)
        return read.replace("/api/media/file/", "/api/media/download/") if read else None

    def _can_preview(self, ext: Optional[str]) -> bool:
        return bool(ext) and ext.lower() in {
            "pdf", "png", "jpg", "jpeg", "webp", "gif", "bmp", "txt", "mp4", "webm", "mp3", "wav",
        }


    def shape_material_list_row(self, r: MaterialListRow, *, external_base: str) -> Dict[str, Any]:
        """Shape for student list/detail responses."""
        ext = self._file_extension(r.file_url)
        return {
            "id": int(r.material_id),
            "title": r.title,
            "material_type": self._material_type_value(r.material_type),
            "description": r.description,
            "file": {
                "read_url": self._normalize_url(r.file_url, external_base),
                "download_url": self._download_url(r.file_url, external_base),
                "extension": ext,
                "size_mb": float(r.file_size_mb) if r.file_size_mb is not None else None,
                "page_count": int(r.page_count) if r.page_count is not None else None,
                "slide_count": int(r.slide_count) if r.slide_count is not None else None,
                "can_preview_in_browser": self._can_preview(ext),
            },
            "flags": {
                "is_enabled": bool(r.is_enabled),
                "is_downloadable": bool(r.is_downloadable),
            },
            "stats": {
                "view_count": int(r.view_count or 0),
                "download_count": int(r.download_count or 0),
                "rating_count": int(getattr(r, "rating_count", 0) or 0),
                "rating_avg": round(float(getattr(r, "rating_avg", 0) or 0), 2),
            },
            "context": {
                "academic_year": {"id": int(r.academic_year_id), "name": r.academic_year_name} if r.academic_year_id else None,
                "semester": {"id": int(r.semester_id), "number": r.semester_number, "name": r.semester_name} if r.semester_id else None,
                "department": {"id": int(r.department_id), "name": r.department_name} if r.department_id else None,
                "faculty": {"id": int(r.faculty_id), "name": r.faculty_name} if r.faculty_id else None,
                "course": {"id": int(r.course_id), "title": r.course_title, "code": r.course_code},
                "course_offering": {
                    "id": int(r.course_offering_id),
                    "custom_title": r.custom_title,
                    "credit_hours": r.credit_hours,
                } if r.course_offering_id else None,
                "chapter": {"id": int(r.chapter_id), "number": r.chapter_number, "title": r.chapter_title} if r.chapter_id else None,
            },
            "user_state": {
                "is_favorite": bool(r.is_favorite),
                "view_count": int(r.user_view_count or 0),
                "download_count": int(r.user_download_count or 0),
                "last_viewed_at": r.last_viewed_at.isoformat() if r.last_viewed_at else None,
                "last_downloaded_at": r.last_downloaded_at.isoformat() if r.last_downloaded_at else None,
            },
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }

    def shape_material_detail_row(
        self,
        r: MaterialDetailRow,
        *,
        external_base: str,
        company_id: int,
    ) -> Dict[str, Any]:
        """Student detail - adds learning objectives."""
        out = self.shape_material_list_row(r, external_base=external_base)
        mat = self.s.get(Material, int(r.material_id))
        out["learning_objectives"] = list(mat.learning_objectives) if mat and mat.learning_objectives else []
        return out

    def shape_admin_list_row(self, r: MaterialAdminListRow) -> Dict[str, Any]:
        """Minimal shape for admin list (fast, no URL generation)."""
        return {
            "id": int(r.material_id),
            "title": r.title,
            "material_type": self._material_type_value(r.material_type),
            "flags": {
                "is_enabled": bool(r.is_enabled),
                "is_downloadable": bool(r.is_downloadable),
            },
            "chapter": {
                "id": int(r.chapter_id),
                "number": r.chapter_number,
                "title": r.chapter_title,
            } if r.chapter_id else None,
            "course": {
                "id": int(r.course_id),
                "title": r.course_title,
                "code": r.course_code,
            },
            "course_code": r.course_code,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }

    def shape_admin_detail_row(self, r: MaterialAdminListRow, *, external_base: str) -> Dict[str, Any]:
        """Full shape for admin detail (for editing)."""
        ext = self._file_extension(r.file_url)
        return {
            "id": int(r.material_id),
            "title": r.title,
            "material_type": self._material_type_value(r.material_type),
            "description": r.description,
            "learning_objectives": r.learning_objectives or [],
            "flags": {
                "is_enabled": bool(r.is_enabled),
                "is_downloadable": bool(r.is_downloadable),
            },
            "stats": {
                "view_count": int(r.view_count or 0),
                "download_count": int(r.download_count or 0),
                "rating_count": int(getattr(r, "rating_count", 0) or 0),
                "rating_avg": round(float(getattr(r, "rating_avg", 0) or 0), 2),
            },
            "file": {
                "url": r.file_url,
                "read_url": self._normalize_url(r.file_url, external_base),
                "extension": ext,
                "size_mb": float(r.file_size_mb) if r.file_size_mb is not None else None,
                "page_count": int(r.page_count) if r.page_count is not None else None,
                "slide_count": int(r.slide_count) if r.slide_count is not None else None,
            },
            "chapter": {
                "id": int(r.chapter_id),
                "number": r.chapter_number,
                "title": r.chapter_title,
                "description": r.chapter_description,
            } if r.chapter_id else None,
            "course_offering": {
                "id": int(r.course_offering_id),
                "custom_title": r.custom_title,
                "credit_hours": r.credit_hours,
            } if r.course_offering_id else None,
            "course": {
                "id": int(r.course_id),
                "code": r.course_code,
                "title": r.course_title,
            },
            "department": {"id": int(r.department_id), "name": r.department_name} if r.department_id else None,
            "semester": {"id": int(r.semester_id), "number": r.semester_number, "name": r.semester_name} if r.semester_id else None,
            "academic_year": {"id": int(r.academic_year_id), "name": r.academic_year_name} if r.academic_year_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }


    # ----------------------------
    # Filter options (UPDATED)
    # ----------------------------
    # -------------------------------------------------------------------------
    # FILTER OPTIONS
    # -------------------------------------------------------------------------

    @staticmethod
    def _clean_filter_options_filters(filters: Dict[str, Any] | None) -> Dict[str, Any]:
        """
        Remove empty values so SQL filters do not accidentally apply None.
        """
        clean: Dict[str, Any] = {}

        for k, v in dict(filters or {}).items():
            if v is None:
                continue
            if isinstance(v, str) and not v.strip():
                continue
            clean[k] = v

        return clean

    def _filters_base_stmt(
        self,
        *,
        company_id: int,
        filters: Dict[str, Any] | None,
        ignore: tuple[str, ...] = (),
        scope: Dict[str, Any] | None = None,
    ):
        """
        Lightweight base query for material filter dropdown options.

        This query respects:
        - company_id
        - enabled materials only
        - enabled courses only
        - enabled course offerings only
        - current user academic scope
        - selected filters, except filters passed in ignore
        """
        filters = self._clean_filter_options_filters(filters)

        for key in ignore:
            filters.pop(key, None)

        if scope is None:
            scope = self._current_user_scope(company_id=company_id)

        stmt = (
            select(
                Material.id.label("material_id"),

                Course.id.label("course_id"),
                Course.title.label("course_title"),
                Course.code.label("course_code"),

                CourseOffering.id.label("course_offering_id"),
                CourseOffering.custom_title.label("course_offering_custom_title"),

                CourseChapter.id.label("chapter_id"),
                CourseChapter.title.label("chapter_title"),
                CourseChapter.number.label("chapter_number"),

                Semester.id.label("semester_id"),
                Semester.name.label("semester_name"),
                Semester.number.label("semester_number"),

                AcademicYear.id.label("academic_year_id"),
                AcademicYear.name.label("academic_year_name"),

                Department.id.label("department_id"),
                Department.name.label("department_name"),

                Faculty.id.label("faculty_id"),
                Faculty.name.label("faculty_name"),
            )
            .select_from(Material)
        )

        stmt = self._add_standard_joins(stmt, company_id=company_id)

        stmt = stmt.where(
            Material.company_id == int(company_id),
            Material.is_enabled.is_(True),
            Course.is_enabled.is_(True),
            CourseOffering.is_enabled.is_(True),
        )

        stmt = self._apply_scope(stmt, scope)

        if filters.get("faculty_id"):
            stmt = stmt.where(Faculty.id == int(filters["faculty_id"]))

        if filters.get("department_id"):
            stmt = stmt.where(CourseOffering.department_id == int(filters["department_id"]))

        if filters.get("academic_year_id"):
            stmt = stmt.where(Semester.academic_year_id == int(filters["academic_year_id"]))

        if filters.get("semester_id"):
            stmt = stmt.where(CourseOffering.semester_id == int(filters["semester_id"]))

        if filters.get("course_id"):
            stmt = stmt.where(Course.id == int(filters["course_id"]))

        if filters.get("course_offering_id"):
            stmt = stmt.where(CourseOffering.id == int(filters["course_offering_id"]))

        if filters.get("chapter_id"):
            stmt = stmt.where(CourseChapter.id == int(filters["chapter_id"]))

        search = (filters.get("search") or "").strip()
        if search:
            pattern = _ilike_pattern(search)
            stmt = stmt.where(
                or_(
                    func.coalesce(Material.title, "").ilike(pattern, escape="\\"),
                    func.coalesce(Material.description, "").ilike(pattern, escape="\\"),
                    func.coalesce(Course.title, "").ilike(pattern, escape="\\"),
                    func.coalesce(Course.code, "").ilike(pattern, escape="\\"),
                    func.coalesce(CourseChapter.title, "").ilike(pattern, escape="\\"),
                    func.coalesce(Department.name, "").ilike(pattern, escape="\\"),
                    func.coalesce(Faculty.name, "").ilike(pattern, escape="\\"),
                )
            )

        return stmt

    def get_material_filter_options(
        self,
        *,
        company_id: int,
        filters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Get all material filter dropdown options.

        Returns:
        - academic_years
        - faculties
        - departments
        - semesters
        - courses
        - course_offerings
        - chapters
        """
        filters = self._clean_filter_options_filters(filters)
        scope = self._current_user_scope(company_id=company_id)

        def _sub(*, ignore: tuple[str, ...] = ()):
            return self._filters_base_stmt(
                company_id=company_id,
                filters=filters,
                ignore=ignore,
                scope=scope,
            ).subquery()

        def _selected_int(key: str) -> int | None:
            value = filters.get(key)
            return int(value) if value is not None else None

        # Academic years
        ay = _sub(ignore=("academic_year_id", "semester_id", "course_id", "course_offering_id", "chapter_id"))
        academic_year_rows = self.s.execute(
            select(
                ay.c.academic_year_id.label("id"),
                ay.c.academic_year_name.label("label"),
                func.count(func.distinct(ay.c.material_id)).label("material_count"),
            )
            .where(ay.c.academic_year_id.isnot(None))
            .group_by(ay.c.academic_year_id, ay.c.academic_year_name)
            .order_by(ay.c.academic_year_name.desc(), ay.c.academic_year_id.desc())
        ).all()

        academic_years = [
            {
                "id": int(r.id),
                "label": r.label,
                "count": int(r.material_count or 0),
            }
            for r in academic_year_rows
        ]

        # Faculties
        f = _sub(ignore=("faculty_id", "department_id", "semester_id", "course_id", "course_offering_id", "chapter_id"))
        faculty_rows = self.s.execute(
            select(
                f.c.faculty_id.label("id"),
                f.c.faculty_name.label("label"),
                func.count(func.distinct(f.c.material_id)).label("material_count"),
            )
            .where(f.c.faculty_id.isnot(None))
            .group_by(f.c.faculty_id, f.c.faculty_name)
            .order_by(f.c.faculty_name.asc(), f.c.faculty_id.asc())
        ).all()

        faculties = [
            {
                "id": int(r.id),
                "label": r.label,
                "count": int(r.material_count or 0),
            }
            for r in faculty_rows
        ]

        # Departments
        d = _sub(ignore=("department_id", "semester_id", "course_id", "course_offering_id", "chapter_id"))
        department_rows = self.s.execute(
            select(
                d.c.department_id.label("id"),
                d.c.department_name.label("label"),
                d.c.faculty_id.label("faculty_id"),
                d.c.faculty_name.label("faculty_name"),
                func.count(func.distinct(d.c.material_id)).label("material_count"),
            )
            .where(d.c.department_id.isnot(None))
            .group_by(d.c.department_id, d.c.department_name, d.c.faculty_id, d.c.faculty_name)
            .order_by(d.c.department_name.asc(), d.c.department_id.asc())
        ).all()

        departments = [
            {
                "id": int(r.id),
                "label": r.label,
                "count": int(r.material_count or 0),
                "meta": {
                    "faculty_id": int(r.faculty_id) if r.faculty_id else None,
                    "faculty_name": r.faculty_name,
                },
            }
            for r in department_rows
        ]

        # Semesters
        s = _sub(ignore=("semester_id", "course_id", "course_offering_id", "chapter_id"))
        semester_rows = self.s.execute(
            select(
                s.c.semester_id.label("id"),
                func.coalesce(
                    s.c.semester_name,
                    func.concat("Semester ", s.c.semester_number),
                ).label("label"),
                s.c.semester_number.label("number"),
                s.c.academic_year_id.label("academic_year_id"),
                s.c.academic_year_name.label("academic_year_name"),
                func.count(func.distinct(s.c.material_id)).label("material_count"),
            )
            .where(s.c.semester_id.isnot(None))
            .group_by(
                s.c.semester_id,
                s.c.semester_name,
                s.c.semester_number,
                s.c.academic_year_id,
                s.c.academic_year_name,
            )
            .order_by(s.c.semester_number.asc(), s.c.semester_id.asc())
        ).all()

        semesters = [
            {
                "id": int(r.id),
                "label": r.label,
                "count": int(r.material_count or 0),
                "meta": {
                    "number": int(r.number) if r.number is not None else None,
                    "academic_year_id": int(r.academic_year_id) if r.academic_year_id else None,
                    "academic_year_name": r.academic_year_name,
                },
            }
            for r in semester_rows
        ]

        # Courses
        c = _sub(ignore=("course_id", "course_offering_id", "chapter_id"))
        course_rows = self.s.execute(
            select(
                c.c.course_id.label("id"),
                c.c.course_title.label("label"),
                c.c.course_code.label("code"),
                func.count(func.distinct(c.c.material_id)).label("material_count"),
            )
            .where(c.c.course_id.isnot(None))
            .group_by(c.c.course_id, c.c.course_title, c.c.course_code)
            .order_by(c.c.course_title.asc(), c.c.course_id.asc())
        ).all()

        courses = [
            {
                "id": int(r.id),
                "label": r.label,
                "count": int(r.material_count or 0),
                "meta": {
                    "code": r.code,
                },
            }
            for r in course_rows
        ]

        # Course offerings
        co = _sub(ignore=("course_offering_id", "chapter_id"))
        offering_rows = self.s.execute(
            select(
                co.c.course_offering_id.label("id"),
                func.coalesce(
                    co.c.course_offering_custom_title,
                    co.c.course_title,
                ).label("label"),
                co.c.course_id.label("course_id"),
                co.c.course_title.label("course_title"),
                co.c.course_code.label("course_code"),
                co.c.department_id.label("department_id"),
                co.c.department_name.label("department_name"),
                co.c.semester_id.label("semester_id"),
                co.c.semester_name.label("semester_name"),
                co.c.semester_number.label("semester_number"),
                func.count(func.distinct(co.c.material_id)).label("material_count"),
            )
            .where(co.c.course_offering_id.isnot(None))
            .group_by(
                co.c.course_offering_id,
                co.c.course_offering_custom_title,
                co.c.course_id,
                co.c.course_title,
                co.c.course_code,
                co.c.department_id,
                co.c.department_name,
                co.c.semester_id,
                co.c.semester_name,
                co.c.semester_number,
            )
            .order_by(
                co.c.course_title.asc(),
                co.c.department_name.asc(),
                co.c.semester_number.asc(),
                co.c.course_offering_id.asc(),
            )
        ).all()

        course_offerings = []
        for r in offering_rows:
            semester_label = r.semester_name or (
                f"Semester {int(r.semester_number)}"
                if r.semester_number is not None
                else None
            )

            course_offerings.append({
                "id": int(r.id),
                "label": r.label,
                "count": int(r.material_count or 0),
                "meta": {
                    "course_id": int(r.course_id) if r.course_id else None,
                    "course_title": r.course_title,
                    "course_code": r.course_code,
                    "department_id": int(r.department_id) if r.department_id else None,
                    "department_name": r.department_name,
                    "semester_id": int(r.semester_id) if r.semester_id else None,
                    "semester_name": semester_label,
                    "semester_number": int(r.semester_number) if r.semester_number is not None else None,
                },
            })

        # Chapters
        ch = _sub(ignore=("chapter_id",))
        chapter_rows = self.s.execute(
            select(
                ch.c.chapter_id.label("id"),
                ch.c.chapter_title.label("title"),
                ch.c.chapter_number.label("number"),
                ch.c.course_id.label("course_id"),
                ch.c.course_title.label("course_title"),
                ch.c.course_offering_id.label("course_offering_id"),
                func.count(func.distinct(ch.c.material_id)).label("material_count"),
            )
            .where(ch.c.chapter_id.isnot(None))
            .group_by(
                ch.c.chapter_id,
                ch.c.chapter_title,
                ch.c.chapter_number,
                ch.c.course_id,
                ch.c.course_title,
                ch.c.course_offering_id,
            )
            .order_by(ch.c.chapter_number.asc(), ch.c.chapter_id.asc())
        ).all()

        chapters = []
        for r in chapter_rows:
            label = (
                f"Chapter {int(r.number)} — {r.title}"
                if r.number is not None
                else r.title
            )

            chapters.append({
                "id": int(r.id),
                "label": label,
                "count": int(r.material_count or 0),
                "meta": {
                    "number": int(r.number) if r.number is not None else None,
                    "title": r.title,
                    "course_id": int(r.course_id) if r.course_id else None,
                    "course_title": r.course_title,
                    "course_offering_id": int(r.course_offering_id) if r.course_offering_id else None,
                },
            })

        return {
            "selected": {
                "academic_year_id": _selected_int("academic_year_id"),
                "faculty_id": _selected_int("faculty_id"),
                "department_id": _selected_int("department_id"),
                "semester_id": _selected_int("semester_id"),
                "course_id": _selected_int("course_id"),
                "course_offering_id": _selected_int("course_offering_id"),
                "chapter_id": _selected_int("chapter_id"),
                "search": filters.get("search"),
            },
            "options": {
                "academic_years": academic_years,
                "faculties": faculties,
                "departments": departments,
                "semesters": semesters,
                "courses": courses,
                "course_offerings": course_offerings,
                "chapters": chapters,
            },
            "scope": {
                "profile_type": scope.get("profile_type"),
                "department_id": int(scope["department_id"]) if scope.get("department_id") else None,
                "faculty_id": int(scope["faculty_id"]) if scope.get("faculty_id") else None,
                "semester_id": int(scope["semester_id"]) if scope.get("semester_id") else None,
            },
        }

    # =============================================================================
    # CURSOR HELPERS (Keep in service)
    # =============================================================================

    def _encode_cursor(payload: Optional[Dict[str, Any]]) -> Optional[str]:
        if not payload:
            return None
        try:
            import base64, json
            return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        except Exception:
            return None

    def _decode_cursor(cursor: Optional[str]) -> Dict[str, Any]:
        if not cursor:
            return {}
        try:
            import base64, json
            return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        except Exception:
            return {}

    # ----------------------------
    # tracking methods (mostly unchanged, but material validation updated)
    # ----------------------------

    def _material_exists_for_event(
            self,
            *,
            company_id: int,
            material_id: int,
            require_downloadable: bool = False,
    ) -> bool:
        stmt = select(exists().where(
            Material.company_id == int(company_id),
            Material.id == int(material_id),
            Material.is_enabled.is_(True),
            *([Material.is_downloadable.is_(True)] if require_downloadable else []),
        ))
        return bool(self.s.scalar(stmt))

    def _interaction_snapshot(
            self,
            *,
            company_id: int,
            material_id: int,
            user_id: int,
    ) -> Dict[str, Any]:
        row = self.s.execute(
            select(
                Material.id.label("material_id"),
                Material.view_count.label("global_view_count"),
                Material.download_count.label("global_download_count"),
                func.coalesce(StudentMaterialInteraction.view_count, 0).label("user_view_count"),
                func.coalesce(StudentMaterialInteraction.download_count, 0).label("user_download_count"),
                StudentMaterialInteraction.last_viewed_at.label("last_viewed_at"),
                StudentMaterialInteraction.last_downloaded_at.label("last_downloaded_at"),
            )
            .select_from(Material)
            .outerjoin(
                StudentMaterialInteraction,
                and_(
                    StudentMaterialInteraction.company_id == Material.company_id,
                    StudentMaterialInteraction.material_id == Material.id,
                    StudentMaterialInteraction.user_id == int(user_id),
                ),
            )
            .where(
                Material.company_id == int(company_id),
                Material.id == int(material_id),
            )
            .limit(1)
        ).first()

        if not row:
            return {
                "material_id": int(material_id),
                "global_view_count": 0,
                "global_download_count": 0,
                "user_view_count": 0,
                "user_download_count": 0,
                "last_viewed_at": None,
                "last_downloaded_at": None,
            }

        d = row._asdict()
        return {
            "material_id": int(d["material_id"]),
            "global_view_count": int(d["global_view_count"] or 0),
            "global_download_count": int(d["global_download_count"] or 0),
            "user_view_count": int(d["user_view_count"] or 0),
            "user_download_count": int(d["user_download_count"] or 0),
            "last_viewed_at": d["last_viewed_at"].isoformat() if d["last_viewed_at"] else None,
            "last_downloaded_at": d["last_downloaded_at"].isoformat() if d["last_downloaded_at"] else None,
        }

    def increment_view(
            self,
            *,
            company_id: int,
            material_id: int,
            user_id: int,
            cooldown_seconds: int = 3600,
    ) -> Dict[str, Any]:
        if not self._material_exists_for_event(
                company_id=company_id,
                material_id=material_id,
                require_downloadable=False,
        ):
            return {
                "counted": False,
                "reason": "Material not found or disabled.",
                **self._interaction_snapshot(
                    company_id=company_id,
                    material_id=material_id,
                    user_id=user_id,
                ),
            }

        cutoff_dt = datetime.now(timezone.utc) - timedelta(seconds=int(cooldown_seconds))

        stmt_user = pg_insert(StudentMaterialInteraction).values(
            company_id=int(company_id),
            user_id=int(user_id),
            material_id=int(material_id),
            is_favorite=False,
            view_count=1,
            download_count=0,
            last_viewed_at=func.now(),
        )

        stmt_user = stmt_user.on_conflict_do_update(
            index_elements=["company_id", "user_id", "material_id"],
            set_={
                "view_count": StudentMaterialInteraction.view_count + 1,
                "last_viewed_at": func.now(),
            },
            where=sa_or(
                StudentMaterialInteraction.last_viewed_at.is_(None),
                StudentMaterialInteraction.last_viewed_at < cutoff_dt,
            ),
        ).returning(StudentMaterialInteraction.material_id)

        user_row = self.s.execute(stmt_user).first()

        if not user_row:
            return {
                "counted": False,
                "reason": "Cooldown active.",
                **self._interaction_snapshot(
                    company_id=company_id,
                    material_id=material_id,
                    user_id=user_id,
                ),
            }

        stmt_global = (
            update(Material)
            .where(
                Material.company_id == int(company_id),
                Material.id == int(material_id),
                Material.is_enabled.is_(True),
            )
            .values(view_count=Material.view_count + 1)
        )
        self.s.execute(stmt_global)
        self.s.flush()

        return {
            "counted": True,
            "reason": None,
            **self._interaction_snapshot(
                company_id=company_id,
                material_id=material_id,
                user_id=user_id,
            ),
        }

    def increment_download(
            self,
            *,
            company_id: int,
            material_id: int,
            user_id: int,
    ) -> Dict[str, Any]:
        if not self._material_exists_for_event(
                company_id=company_id,
                material_id=material_id,
                require_downloadable=True,
        ):
            return {
                "counted": False,
                "reason": "Material not found, disabled, or not downloadable.",
                **self._interaction_snapshot(
                    company_id=company_id,
                    material_id=material_id,
                    user_id=user_id,
                ),
            }

        stmt_user = pg_insert(StudentMaterialInteraction).values(
            company_id=int(company_id),
            user_id=int(user_id),
            material_id=int(material_id),
            is_favorite=False,
            view_count=0,
            download_count=1,
            last_downloaded_at=func.now(),
        )

        stmt_user = stmt_user.on_conflict_do_update(
            index_elements=["company_id", "user_id", "material_id"],
            set_={
                "download_count": StudentMaterialInteraction.download_count + 1,
                "last_downloaded_at": func.now(),
            },
        ).returning(StudentMaterialInteraction.material_id)

        self.s.execute(stmt_user)

        stmt_global = (
            update(Material)
            .where(
                Material.company_id == int(company_id),
                Material.id == int(material_id),
                Material.is_enabled.is_(True),
                Material.is_downloadable.is_(True),
            )
            .values(download_count=Material.download_count + 1)
        )
        self.s.execute(stmt_global)
        self.s.flush()

        return {
            "counted": True,
            "reason": None,
            **self._interaction_snapshot(
                company_id=company_id,
                material_id=material_id,
                user_id=user_id,
            ),
        }

    def set_favorite(
            self,
            *,
            company_id: int,
            material_id: int,
            user_id: int,
            is_favorite: bool,
    ) -> Dict[str, Any]:
        if not self._material_exists_for_event(
                company_id=company_id,
                material_id=material_id,
                require_downloadable=False,
        ):
            return {
                "counted": False,
                "reason": "Material not found or disabled.",
                **self._interaction_snapshot(
                    company_id=company_id,
                    material_id=material_id,
                    user_id=user_id,
                ),
            }

        stmt_user = pg_insert(StudentMaterialInteraction).values(
            company_id=int(company_id),
            user_id=int(user_id),
            material_id=int(material_id),
            is_favorite=bool(is_favorite),
            view_count=0,
            download_count=0,
            last_viewed_at=None,
            last_downloaded_at=None,
        )

        stmt_user = stmt_user.on_conflict_do_update(
            index_elements=["company_id", "user_id", "material_id"],
            set_={
                "is_favorite": bool(is_favorite),
            },
        ).returning(StudentMaterialInteraction.material_id)

        self.s.execute(stmt_user)
        self.s.flush()

        snap = self._interaction_snapshot(
            company_id=company_id,
            material_id=material_id,
            user_id=user_id,
        )

        return {
            "counted": True,
            "reason": None,
            "is_favorite": bool(is_favorite),
            **snap,
        }

    def list_favorite_materials_page(
            self,
            *,
            company_id: int,
            user_id: int,
            page: int,
            per_page: int,
            external_base: str,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        page = max(int(page or 1), 1)
        allowed = {10, 20, 50, 500}
        per_page = per_page if int(per_page or 20) in allowed else 20

        base = (
            select(Material.id)
            .select_from(StudentMaterialInteraction)
            .join(
                Material,
                and_(
                    Material.id == StudentMaterialInteraction.material_id,
                    Material.company_id == int(company_id),
                ),
            )
            .where(
                StudentMaterialInteraction.company_id == int(company_id),
                StudentMaterialInteraction.user_id == int(user_id),
                StudentMaterialInteraction.is_favorite.is_(True),
                Material.is_enabled.is_(True),
            )
            .order_by(StudentMaterialInteraction.updated_at.desc(), Material.id.desc())
        )

        count_stmt = select(func.count()).select_from(base.order_by(None).subquery())
        total = int(self.s.scalar(count_stmt) or 0)
        pages = max((total + per_page - 1) // per_page, 1)
        page = min(page, pages)
        offset = (page - 1) * per_page

        material_ids = list(self.s.scalars(base.offset(offset).limit(per_page)).all())

        rows: List[Dict[str, Any]] = []
        for mid in material_ids:
            detail_row = self.get_material_detail(company_id=company_id, material_id=int(mid))
            if detail_row:
                rows.append(self.shape_material_list_row(detail_row, external_base=external_base))

        return rows, total, pages

    def current_user_scope_for_debug(self, *, company_id: int) -> Dict[str, Any]:
        """
        Safe wrapper for service cache/debug use.
        """
        return self._current_user_scope(company_id=company_id)

    def get_student_materials_empty_message(
            self,
            *,
            company_id: int,
            filters: Dict[str, Any],
    ) -> str:
        """
        ERP-style empty-state message for student material list.
        Keeps scope strict, but explains the empty result cleanly.
        """
        scope = self._current_user_scope(company_id=company_id)

        if scope.get("profile_type") != "student":
            return "No materials are available."

        if not scope.get("department_id"):
            return "Your student profile is not linked to a department. Please contact the academic office."

        if filters.get("course_offering_id"):
            offering_id = int(filters["course_offering_id"])

            offering = (
                self.s.query(
                    CourseOffering.id.label("offering_id"),
                    CourseOffering.department_id.label("department_id"),
                    CourseOffering.semester_id.label("semester_id"),
                    Department.name.label("department_name"),
                    Faculty.id.label("faculty_id"),
                    Faculty.name.label("faculty_name"),
                    Course.title.label("course_title"),
                )
                .join(Department, Department.id == CourseOffering.department_id)
                .join(Faculty, Faculty.id == Department.faculty_id)
                .join(Course, Course.id == CourseOffering.course_id)
                .filter(
                    CourseOffering.company_id == int(company_id),
                    CourseOffering.id == offering_id,
                )
                .first()
            )

            if not offering:
                return "The selected course offering was not found."

            if scope.get("department_id") and int(scope["department_id"]) != int(offering.department_id):
                return "This course belongs to another department. Materials are only available for your department."

            if scope.get("faculty_id") and int(scope["faculty_id"]) != int(offering.faculty_id):
                return "This course belongs to another faculty. Materials are only available for your faculty."

            return "No materials have been published for this course yet."

        if filters.get("search"):
            return "No materials matched your search within your department."

        if filters.get("semester_id"):
            return "No materials are available for the selected semester in your department."

        return "No materials have been published for your department yet."

    def get_student_material_access_message(
            self,
            *,
            company_id: int,
            material_id: int,
    ) -> str:
        """
        ERP-style message for student detail when row is hidden by scope or unavailable.
        """
        scope = self._current_user_scope(company_id=company_id)

        if scope.get("profile_type") != "student":
            return "Material not found."

        if not scope.get("department_id"):
            return "Your student profile is not linked to a department. Please contact the academic office."

        mat = (
            self.s.query(
                Material.id.label("material_id"),
                Material.title.label("material_title"),
                Material.is_enabled.label("material_enabled"),
                CourseOffering.id.label("offering_id"),
                CourseOffering.department_id.label("offering_department_id"),
                CourseOffering.semester_id.label("offering_semester_id"),
                Department.name.label("department_name"),
                Faculty.id.label("offering_faculty_id"),
                Faculty.name.label("faculty_name"),
                Course.title.label("course_title"),
            )
            .join(CourseOffering, CourseOffering.id == Material.course_offering_id)
            .join(Department, Department.id == CourseOffering.department_id)
            .join(Faculty, Faculty.id == Department.faculty_id)
            .join(Course, Course.id == CourseOffering.course_id)
            .filter(
                Material.company_id == int(company_id),
                Material.id == int(material_id),
            )
            .first()
        )

        if not mat:
            return "Material not found."

        if not mat.material_enabled:
            return "This material is currently unavailable."

        if scope.get("department_id") and int(scope["department_id"]) != int(mat.offering_department_id):
            return "This material belongs to another department. You can only access materials assigned to your department."

        if scope.get("faculty_id") and int(scope["faculty_id"]) != int(mat.offering_faculty_id):
            return "This material belongs to another faculty. You can only access materials assigned to your faculty."

        return "This material is not available for your academic profile."

    # -------------------------------------------------------------------------
    # FEEDBACK
    # -------------------------------------------------------------------------

    def material_exists_in_scope(self, *, company_id: int, material_id: int) -> bool:
        row = self.get_material_detail(company_id=company_id, material_id=material_id)
        return row is not None

    def get_user_rating(self, *, company_id: int, material_id: int, user_id: int) -> Optional[MaterialFeedback]:
        return (
            self.s.query(MaterialFeedback)
            .filter(
                MaterialFeedback.company_id == int(company_id),
                MaterialFeedback.material_id == int(material_id),
                MaterialFeedback.user_id == int(user_id),
                MaterialFeedback.feedback_type == MaterialFeedbackTypeEnum.RATING,
            )
            .first()
        )

    def upsert_rating(
        self,
        *,
        company_id: int,
        material_id: int,
        user_id: int,
        rating: int,
    ) -> MaterialFeedback:
        existing = self.get_user_rating(
            company_id=company_id,
            material_id=material_id,
            user_id=user_id,
        )
        old_rating = int(existing.rating) if existing else None

        if existing:
            existing.rating = int(rating)
            row = existing
        else:
            row = MaterialFeedback(
                company_id=int(company_id),
                material_id=int(material_id),
                user_id=int(user_id),
                feedback_type=MaterialFeedbackTypeEnum.RATING,
                rating=int(rating),
            )
            self.s.add(row)

        self.s.flush()
        self._refresh_material_rating_stats(
            company_id=company_id,
            material_id=material_id,
            old_rating=old_rating,
            new_rating=int(rating),
            is_new=existing is None,
        )
        return row

    def _refresh_material_rating_stats(
        self,
        *,
        company_id: int,
        material_id: int,
        old_rating: Optional[int],
        new_rating: int,
        is_new: bool,
    ) -> None:
        mat = (
            self.s.query(Material)
            .filter(
                Material.company_id == int(company_id),
                Material.id == int(material_id),
            )
            .with_for_update()
            .first()
        )
        if not mat:
            return

        total = int(mat.rating_count or 0)
        avg = float(mat.rating_avg or 0.0)
        total_score = avg * total

        if is_new:
            total += 1
            total_score += int(new_rating)
        elif old_rating is not None:
            total_score += int(new_rating) - int(old_rating)

        mat.rating_count = total
        mat.rating_avg = round(total_score / total, 2) if total > 0 else 0.0

    def create_feedback(
        self,
        *,
        company_id: int,
        material_id: int,
        user_id: int,
        feedback_type: str,
        rating: Optional[int] = None,
        message: Optional[str] = None,
    ) -> MaterialFeedback:
        ftype = MaterialFeedbackTypeEnum(feedback_type)
        status = None
        if ftype in {MaterialFeedbackTypeEnum.BROKEN_FILE, MaterialFeedbackTypeEnum.CLARIFICATION}:
            status = MaterialFeedbackStatusEnum.OPEN

        row = MaterialFeedback(
            company_id=int(company_id),
            material_id=int(material_id),
            user_id=int(user_id),
            feedback_type=ftype,
            rating=int(rating) if rating is not None else None,
            message=message,
            status=status,
        )
        self.s.add(row)
        self.s.flush()
        return row

    def list_material_feedback(
        self,
        *,
        company_id: int,
        material_id: int,
        viewer_user_id: Optional[int] = None,
        include_ratings: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        from cmcp.modules.auth.models import User
        from cmcp.modules.education_people.models import StudentProfile

        public_types = [
            MaterialFeedbackTypeEnum.COMMENT,
            MaterialFeedbackTypeEnum.CLARIFICATION,
        ]

        visibility = MaterialFeedback.feedback_type.in_(public_types)
        if viewer_user_id:
            visibility = sa_or(
                visibility,
                and_(
                    MaterialFeedback.feedback_type == MaterialFeedbackTypeEnum.BROKEN_FILE,
                    MaterialFeedback.user_id == int(viewer_user_id),
                ),
            )

        q = (
            self.s.query(
                MaterialFeedback,
                User.username,
                StudentProfile.full_name,
            )
            .join(User, User.id == MaterialFeedback.user_id)
            .outerjoin(
                StudentProfile,
                and_(
                    StudentProfile.user_id == MaterialFeedback.user_id,
                    StudentProfile.company_id == MaterialFeedback.company_id,
                ),
            )
            .filter(
                MaterialFeedback.company_id == int(company_id),
                MaterialFeedback.material_id == int(material_id),
                visibility,
            )
        )

        if not include_ratings:
            q = q.filter(
                MaterialFeedback.feedback_type != MaterialFeedbackTypeEnum.RATING
            )

        rows = (
            q.order_by(MaterialFeedback.created_at.desc())
            .limit(max(1, min(int(limit), 200)))
            .all()
        )
        shaped = [self._shape_feedback_row(row[0], row[1], row[2]) for row in rows]
        return self._attach_feedback_replies(company_id=company_id, items=shaped)

    def get_feedback_admin_summary(self, *, company_id: int) -> Dict[str, Any]:
        base = self.s.query(MaterialFeedback).filter(
            MaterialFeedback.company_id == int(company_id),
        )

        open_issues = int(
            base.filter(MaterialFeedback.status == MaterialFeedbackStatusEnum.OPEN).count()
        )
        broken_open = int(
            base.filter(
                MaterialFeedback.feedback_type == MaterialFeedbackTypeEnum.BROKEN_FILE,
                MaterialFeedback.status == MaterialFeedbackStatusEnum.OPEN,
            ).count()
        )
        clarification_open = int(
            base.filter(
                MaterialFeedback.feedback_type == MaterialFeedbackTypeEnum.CLARIFICATION,
                MaterialFeedback.status == MaterialFeedbackStatusEnum.OPEN,
            ).count()
        )
        comments_total = int(
            base.filter(
                MaterialFeedback.feedback_type == MaterialFeedbackTypeEnum.COMMENT,
            ).count()
        )
        awaiting_reply = int(
            base.filter(
                MaterialFeedback.feedback_type.in_(
                    [
                        MaterialFeedbackTypeEnum.COMMENT,
                        MaterialFeedbackTypeEnum.CLARIFICATION,
                        MaterialFeedbackTypeEnum.BROKEN_FILE,
                    ]
                ),
                MaterialFeedback.admin_reply.is_(None),
                MaterialFeedback.message.isnot(None),
            ).count()
        )

        return {
            "open_issues": open_issues,
            "broken_file_open": broken_open,
            "clarification_open": clarification_open,
            "comments_total": comments_total,
            "awaiting_admin_reply": awaiting_reply,
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
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        from cmcp.modules.auth.models import User
        from cmcp.modules.education_people.models import StudentProfile

        base = (
            self.s.query(MaterialFeedback)
            .filter(MaterialFeedback.company_id == int(company_id))
        )

        if status:
            base = base.filter(MaterialFeedback.status == MaterialFeedbackStatusEnum(status))
        if feedback_type:
            base = base.filter(MaterialFeedback.feedback_type == MaterialFeedbackTypeEnum(feedback_type))
        if material_id:
            base = base.filter(MaterialFeedback.material_id == int(material_id))

        total = int(base.count())
        pages = max((total + per_page - 1) // per_page, 1)
        page = min(max(page, 1), pages)
        offset = (page - 1) * per_page

        rows = (
            base.order_by(MaterialFeedback.created_at.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        out = []
        for fb in rows:
            user = self.s.get(User, int(fb.user_id))
            full_name = self._resolve_user_display_name(
                company_id=company_id,
                user_id=int(fb.user_id),
            )
            item = self._shape_feedback_row(fb, user.username if user else None, full_name)
            mat = self.s.get(Material, int(fb.material_id))
            item["material"] = {"id": int(fb.material_id), "title": mat.title if mat else None}
            out.append(item)

        out = self._attach_feedback_replies(company_id=company_id, items=out)
        return out, total, pages

    def get_feedback_by_id(
        self,
        *,
        company_id: int,
        feedback_id: int,
    ) -> Optional[MaterialFeedback]:
        return (
            self.s.query(MaterialFeedback)
            .filter(
                MaterialFeedback.company_id == int(company_id),
                MaterialFeedback.id == int(feedback_id),
            )
            .first()
        )

    def add_feedback_reply(
        self,
        *,
        company_id: int,
        feedback_id: int,
        user_id: int,
        message: str,
        set_admin_reply: bool = False,
    ) -> Optional[MaterialFeedbackReply]:
        feedback = self.get_feedback_by_id(company_id=company_id, feedback_id=feedback_id)
        if not feedback:
            return None

        text = (message or "").strip()
        if not text:
            return None

        reply = MaterialFeedbackReply(
            company_id=int(company_id),
            feedback_id=int(feedback_id),
            user_id=int(user_id),
            message=text,
        )
        self.s.add(reply)

        if set_admin_reply:
            feedback.admin_reply = text

        self.s.flush()
        return reply

    def reply_to_feedback(
        self,
        *,
        company_id: int,
        feedback_id: int,
        admin_user_id: int,
        admin_reply: str,
    ) -> Optional[MaterialFeedback]:
        row = self.get_feedback_by_id(company_id=company_id, feedback_id=feedback_id)
        if not row:
            return None
        text = admin_reply.strip()
        row.admin_reply = text
        self.add_feedback_reply(
            company_id=company_id,
            feedback_id=feedback_id,
            user_id=int(admin_user_id),
            message=text,
            set_admin_reply=False,
        )
        self.s.flush()
        return row

    def resolve_feedback(
        self,
        *,
        company_id: int,
        feedback_id: int,
        admin_user_id: int,
        admin_reply: Optional[str] = None,
    ) -> Optional[MaterialFeedback]:
        row = self.get_feedback_by_id(company_id=company_id, feedback_id=feedback_id)
        if not row:
            return None
        if admin_reply:
            text = admin_reply.strip()
            row.admin_reply = text
            self.add_feedback_reply(
                company_id=company_id,
                feedback_id=feedback_id,
                user_id=int(admin_user_id),
                message=text,
                set_admin_reply=False,
            )
        row.status = MaterialFeedbackStatusEnum.RESOLVED
        row.resolved_at = datetime.now(timezone.utc)
        row.resolved_by_user_id = int(admin_user_id)
        self.s.flush()
        return row

    def _resolve_user_display_name(self, *, company_id: int, user_id: int) -> Optional[str]:
        student = (
            self.s.query(StudentProfile.full_name)
            .filter(
                StudentProfile.company_id == int(company_id),
                StudentProfile.user_id == int(user_id),
            )
            .first()
        )
        if student and student[0]:
            return student[0]

        staff = (
            self.s.query(StaffProfile.full_name)
            .filter(
                StaffProfile.company_id == int(company_id),
                StaffProfile.user_id == int(user_id),
            )
            .first()
        )
        if staff and staff[0]:
            return staff[0]
        return None

    def _shape_reply_row(
        self,
        reply: MaterialFeedbackReply,
        username: Optional[str],
        full_name: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "id": int(reply.id),
            "feedback_id": int(reply.feedback_id),
            "user_id": int(reply.user_id),
            "user": {
                "username": username,
                "full_name": full_name,
            },
            "message": reply.message,
            "created_at": reply.created_at.isoformat() if reply.created_at else None,
            "updated_at": reply.updated_at.isoformat() if reply.updated_at else None,
        }

    def _attach_feedback_replies(
        self,
        *,
        company_id: int,
        items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not items:
            return items

        from cmcp.modules.auth.models import User

        feedback_ids = [int(item["id"]) for item in items]
        reply_rows = (
            self.s.query(
                MaterialFeedbackReply,
                User.username,
                StudentProfile.full_name,
                StaffProfile.full_name,
            )
            .join(User, User.id == MaterialFeedbackReply.user_id)
            .outerjoin(
                StudentProfile,
                and_(
                    StudentProfile.user_id == MaterialFeedbackReply.user_id,
                    StudentProfile.company_id == MaterialFeedbackReply.company_id,
                ),
            )
            .outerjoin(
                StaffProfile,
                and_(
                    StaffProfile.user_id == MaterialFeedbackReply.user_id,
                    StaffProfile.company_id == MaterialFeedbackReply.company_id,
                ),
            )
            .filter(
                MaterialFeedbackReply.company_id == int(company_id),
                MaterialFeedbackReply.feedback_id.in_(feedback_ids),
            )
            .order_by(MaterialFeedbackReply.created_at.asc(), MaterialFeedbackReply.id.asc())
            .all()
        )

        by_feedback: Dict[int, List[Dict[str, Any]]] = {fid: [] for fid in feedback_ids}
        for reply, username, student_name, staff_name in reply_rows:
            by_feedback.setdefault(int(reply.feedback_id), []).append(
                self._shape_reply_row(reply, username, student_name or staff_name)
            )

        for item in items:
            item["replies"] = by_feedback.get(int(item["id"]), [])
        return items

    def _shape_feedback_row(
        self,
        row: MaterialFeedback,
        username: Optional[str],
        full_name: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "id": int(row.id),
            "material_id": int(row.material_id),
            "user_id": int(row.user_id),
            "user": {
                "username": username,
                "full_name": full_name,
            },
            "feedback_type": row.feedback_type.value,
            "rating": int(row.rating) if row.rating is not None else None,
            "message": row.message,
            "status": row.status.value if row.status else None,
            "admin_reply": row.admin_reply,
            "replies": [],
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    # -------------------------------------------------------------------------
    # ACCESS REPORTS
    # -------------------------------------------------------------------------

    def _admin_materials_scope_stmt(self, *, company_id: int):
        scope = self._current_user_scope(company_id=company_id)
        stmt = (
            select(
                Material.id.label("material_id"),
                Material.title,
                Material.view_count,
                Material.download_count,
                Material.rating_avg,
                Material.rating_count,
                Material.created_at,
                Course.id.label("course_id"),
                Course.title.label("course_title"),
                Course.code.label("course_code"),
                Department.id.label("department_id"),
                Department.name.label("department_name"),
            )
            .select_from(Material)
        )
        stmt = self._add_standard_joins(stmt, company_id=company_id)
        stmt = stmt.where(Material.company_id == int(company_id), Material.is_enabled.is_(True))
        stmt = self._apply_scope(stmt, scope)
        return stmt

    def get_access_reports(self, *, company_id: int, limit: int = 10) -> Dict[str, Any]:
        limit = max(1, min(int(limit), 50))
        base_sq = self._admin_materials_scope_stmt(company_id=company_id).subquery()

        totals = self.s.execute(
            select(
                func.coalesce(func.sum(base_sq.c.view_count), 0),
                func.coalesce(func.sum(base_sq.c.download_count), 0),
                func.count(base_sq.c.material_id),
            ).select_from(base_sq)
        ).first()

        total_views = int(totals[0] or 0)
        total_downloads = int(totals[1] or 0)
        material_count = int(totals[2] or 0)

        zero_access = int(
            self.s.scalar(
                select(func.count()).select_from(base_sq).where(
                    base_sq.c.view_count == 0,
                    base_sq.c.download_count == 0,
                )
            )
            or 0
        )

        engaged_students = int(
            self.s.scalar(
                select(func.count(func.distinct(StudentMaterialInteraction.user_id))).where(
                    StudentMaterialInteraction.company_id == int(company_id),
                    or_(
                        StudentMaterialInteraction.view_count > 0,
                        StudentMaterialInteraction.download_count > 0,
                    ),
                )
            )
            or 0
        )

        top_viewed = self.s.execute(
            select(base_sq)
            .where(base_sq.c.view_count > 0)
            .order_by(base_sq.c.view_count.desc(), base_sq.c.material_id.desc())
            .limit(limit)
        ).all()

        top_downloaded = self.s.execute(
            select(base_sq)
            .where(base_sq.c.download_count > 0)
            .order_by(base_sq.c.download_count.desc(), base_sq.c.material_id.desc())
            .limit(limit)
        ).all()

        least_limit = min(limit, 5)
        least_accessed = self.s.execute(
            select(base_sq)
            .order_by(
                (base_sq.c.view_count + base_sq.c.download_count).asc(),
                base_sq.c.material_id.asc(),
            )
            .limit(least_limit)
        ).all()

        course_views = func.coalesce(func.sum(base_sq.c.view_count), 0)
        course_downloads = func.coalesce(func.sum(base_sq.c.download_count), 0)
        engagement_score = course_views + course_downloads

        top_courses = self.s.execute(
            select(
                base_sq.c.course_id,
                base_sq.c.course_title,
                base_sq.c.course_code,
                course_views.label("views"),
                course_downloads.label("downloads"),
                engagement_score.label("engagement_score"),
                func.count(base_sq.c.material_id).label("material_count"),
            )
            .group_by(base_sq.c.course_id, base_sq.c.course_title, base_sq.c.course_code)
            .having(engagement_score > 0)
            .order_by(engagement_score.desc())
            .limit(limit)
        ).all()

        def _row_dict(r):
            return {
                "material_id": int(r.material_id),
                "title": r.title,
                "view_count": int(r.view_count or 0),
                "download_count": int(r.download_count or 0),
                "rating_avg": round(float(r.rating_avg or 0), 2),
                "rating_count": int(r.rating_count or 0),
                "course": {
                    "id": int(r.course_id),
                    "title": r.course_title,
                    "code": r.course_code,
                },
                "department": {
                    "id": int(r.department_id) if r.department_id else None,
                    "name": r.department_name,
                },
            }

        return {
            "summary": {
                "total_materials": material_count,
                "total_views": total_views,
                "total_downloads": total_downloads,
                "materials_without_access": zero_access,
                "engaged_students": engaged_students,
            },
            "top_viewed_materials": [_row_dict(r) for r in top_viewed],
            "top_downloaded_materials": [_row_dict(r) for r in top_downloaded],
            "least_accessed_materials": [_row_dict(r) for r in least_accessed],
            "most_accessed_courses": [
                {
                    "course_id": int(r.course_id),
                    "title": r.course_title,
                    "code": r.course_code,
                    "view_count": int(r.views or 0),
                    "download_count": int(r.downloads or 0),
                    "engagement_score": int(r.engagement_score or 0),
                    "material_count": int(r.material_count or 0),
                }
                for r in top_courses
            ],
        }