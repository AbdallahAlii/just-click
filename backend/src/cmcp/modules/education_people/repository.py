from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Set, List, Dict, Any, Tuple

from sqlalchemy import exists, func, select, and_
from sqlalchemy.orm import Session

from cmcp.config.database import db
from cmcp.core.base_repo import BaseRepository
import calendar as py_calendar
from cmcp.modules.auth.models import User, UserAffiliation, UserStatusEnum, UserTypeEnum
from cmcp.modules.education_people.models import StudentProfile, Classroom, StaffProfile
from cmcp.modules.academic.models import Faculty, Department, CourseOffering
from cmcp.modules.materials.models import StudentMaterialInteraction, Material


@dataclass
class StudentListRow:
    id: int
    full_name: str
    student_id: str
    department_name: Optional[str]
    is_enabled: bool
class EducationPeopleRepo:
    def __init__(self, session: Optional[Session] = None):
        self.s: Session = session or db.session

        # same as AcademicRepo
        self.classrooms = BaseRepository(Classroom, self.s)
        self.students = BaseRepository(StudentProfile, self.s)
        self.staff = BaseRepository(StaffProfile, self.s)

    # -------------------------
    # Classroom uniqueness
    # -------------------------
    def classroom_name_exists(self, *, company_id: int, name: str, exclude_id: Optional[int] = None) -> bool:
        conds = [
            Classroom.company_id == int(company_id),
            func.lower(Classroom.name) == func.lower(name.strip()),
        ]
        if exclude_id:
            conds.append(Classroom.id != int(exclude_id))
        return bool(self.s.scalar(select(exists().where(*conds))))

    # -------------------------
    # Registration duplicate checks
    # -------------------------
    def user_by_username(self, *, student_id: str) -> Optional[User]:
        return self.s.query(User).filter(User.username == student_id.strip()).first()

    def user_by_email(self, *, email: str) -> Optional[User]:
        return self.s.query(User).filter(func.lower(User.email) == func.lower(email.strip())).first()

    def student_profile_by_student_id(self, *, company_id: int, student_id: str) -> Optional[StudentProfile]:
        return self.s.query(StudentProfile).filter(
            StudentProfile.company_id == int(company_id),
            StudentProfile.student_id == student_id.strip(),
        ).first()

    # -------------------------
    # Foreign-key existence checks
    # -------------------------
    def faculty_exists(self, *, company_id: int, faculty_id: int) -> bool:
        return bool(
            self.s.scalar(
                select(exists().where(
                    Faculty.company_id == int(company_id),
                    Faculty.id == int(faculty_id),
                ))
            )
        )

    def department_exists(self, *, company_id: int, department_id: int, faculty_id: int) -> bool:
        return bool(
            self.s.scalar(
                select(exists().where(
                    Department.company_id == int(company_id),
                    Department.id == int(department_id),
                    Department.faculty_id == int(faculty_id),
                ))
            )
        )

    def semester_exists(self, *, company_id: int, semester_id: int) -> bool:
        from cmcp.modules.academic.models import Semester

        return bool(
            self.s.scalar(
                select(exists().where(
                    Semester.company_id == int(company_id),
                    Semester.id == int(semester_id),
                    Semester.is_enabled.is_(True),
                ))
            )
        )

    def classroom_exists(self, *, company_id: int, classroom_id: int) -> bool:
        return bool(
            self.s.scalar(
                select(exists().where(
                    Classroom.company_id == int(company_id),
                    Classroom.id == int(classroom_id),
                ))
            )
        )

    # -------------------------
    # Pending approvals (for admin dashboard)
    # -------------------------
    def pending_approval_user_ids(self, *, company_id: int) -> List[int]:
        # optional helper if you need it later
        # NOTE: User is not tenant-aware in your schema, so we join through profiles/affiliations when needed.
        stmt = select(StudentProfile.user_id).where(StudentProfile.company_id == int(company_id)).distinct()
        return list(self.s.scalars(stmt).all())

        # =========================================================
        # BASE STMT
        # =========================================================

    def _base_stmt(
            self,
            *,
            company_id: int,
            filters: Dict[str, Any],
            is_enabled: Optional[bool],
    ):
        stmt = (
            select(
                StudentProfile.id.label("id"),
                StudentProfile.full_name.label("full_name"),
                StudentProfile.student_id.label("student_id"),
                Department.name.label("department_name"),
                StudentProfile.is_enabled.label("is_enabled"),
            )
            .select_from(StudentProfile)
            .outerjoin(
                Department,
                and_(
                    Department.id == StudentProfile.department_id,
                    Department.company_id == int(company_id),
                ),
            )
            .where(StudentProfile.company_id == int(company_id))
        )

        # enabled filter
        if is_enabled is True:
            stmt = stmt.where(StudentProfile.is_enabled.is_(True))
        elif is_enabled is False:
            stmt = stmt.where(StudentProfile.is_enabled.is_(False))

        # filters
        if filters.get("department_id"):
            stmt = stmt.where(StudentProfile.department_id == int(filters["department_id"]))

        # search
        search = (filters.get("search") or "").strip()
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(
                func.lower(func.coalesce(StudentProfile.full_name, "")).like(like)
                | func.lower(func.coalesce(StudentProfile.student_id, "")).like(like)
            )

        return stmt

        # =========================================================
        # LIST cursor (descending id)
        # =========================================================

    def list_students_cursor(
            self,
            *,
            company_id: int,
            limit: int,
            last_id: Optional[int],
            filters: Dict[str, Any],
            is_enabled: Optional[bool],
    ) -> Tuple[List[StudentListRow], int, bool]:
        base = self._base_stmt(company_id=company_id, filters=filters, is_enabled=is_enabled)

        if last_id:
            base = base.where(StudentProfile.id < int(last_id))

        base = base.order_by(StudentProfile.id.desc()).limit(int(limit) + 1)

        rows = list(self.s.execute(base).all())
        has_more = len(rows) > limit
        rows = rows[:limit]

        # total count aligned with filters
        count_stmt = select(func.count()).select_from(StudentProfile).where(
            StudentProfile.company_id == int(company_id))

        if is_enabled is True:
            count_stmt = count_stmt.where(StudentProfile.is_enabled.is_(True))
        elif is_enabled is False:
            count_stmt = count_stmt.where(StudentProfile.is_enabled.is_(False))

        if filters.get("department_id"):
            count_stmt = count_stmt.where(StudentProfile.department_id == int(filters["department_id"]))

        search = (filters.get("search") or "").strip()
        if search:
            like = f"%{search.lower()}%"
            count_stmt = count_stmt.where(
                func.lower(func.coalesce(StudentProfile.full_name, "")).like(like)
                | func.lower(func.coalesce(StudentProfile.student_id, "")).like(like)
            )

        total = int(self.s.scalar(count_stmt) or 0)

        shaped = [StudentListRow(**r._asdict()) for r in rows]
        return shaped, total, has_more

        # =========================================================
        # LIST page
        # =========================================================

    def list_students_page(
            self,
            *,
            company_id: int,
            page: int,
            per_page: int,
            filters: Dict[str, Any],
            is_enabled: Optional[bool],
    ) -> Tuple[List[StudentListRow], int, int]:
        base = self._base_stmt(company_id=company_id, filters=filters, is_enabled=is_enabled)

        # count (subquery)
        count_stmt = select(func.count()).select_from(base.order_by(None).subquery())
        total = int(self.s.scalar(count_stmt) or 0)
        pages = max((total + per_page - 1) // per_page, 1)
        page = min(max(page, 1), pages)
        offset = (page - 1) * per_page

        base = base.order_by(StudentProfile.id.desc()).offset(offset).limit(per_page)
        rows = list(self.s.execute(base).all())
        shaped = [StudentListRow(**r._asdict()) for r in rows]
        return shaped, total, pages

        # optional: if you want to add external_base later (like materials)

    def shape_student_list_row(self, r: StudentListRow, *, external_base: str) -> Dict[str, Any]:
        return {
            "id": int(r.id),
            "full_name": r.full_name,
            "student_id": r.student_id,
            "department_name": r.department_name,
            "is_enabled": bool(r.is_enabled),
        }


    # =========================================================
    # DASHBOARD - USERS
    # =========================================================
    def dashboard_user_type_counts(self, *, company_id: int) -> Dict[str, int]:
        rows = self.s.execute(
            select(
                User.user_type.label("user_type"),
                func.count(User.id).label("total"),
            )
            .select_from(UserAffiliation)
            .join(User, User.id == UserAffiliation.user_id)
            .where(UserAffiliation.company_id == int(company_id))
            .group_by(User.user_type)
        ).all()

        out = {
            "students": 0,
            "lecturers": 0,   # maps from teacher
            "staff": 0,
            "admins": 0,
        }

        for r in rows:
            utype = getattr(r.user_type, "value", str(r.user_type))
            total = int(r.total or 0)

            if utype == UserTypeEnum.STUDENT.value:
                out["students"] = total
            elif utype == UserTypeEnum.TEACHER.value:
                out["lecturers"] = total
            elif utype == UserTypeEnum.STAFF.value:
                out["staff"] = total
            elif utype == UserTypeEnum.ADMIN.value:
                out["admins"] = total

        return out

    def dashboard_total_users(self, *, company_id: int) -> int:
        stmt = (
            select(func.count(User.id))
            .select_from(UserAffiliation)
            .join(User, User.id == UserAffiliation.user_id)
            .where(UserAffiliation.company_id == int(company_id))
        )
        return int(self.s.scalar(stmt) or 0)

    def dashboard_new_user_counts_between(
        self,
        *,
        company_id: int,
        start_dt: datetime,
        end_dt: datetime,
    ) -> Dict[str, int]:
        rows = self.s.execute(
            select(
                User.user_type.label("user_type"),
                func.count(User.id).label("total"),
            )
            .select_from(UserAffiliation)
            .join(User, User.id == UserAffiliation.user_id)
            .where(
                UserAffiliation.company_id == int(company_id),
                User.created_at >= start_dt,
                User.created_at < end_dt,
            )
            .group_by(User.user_type)
        ).all()

        out = {
            "students": 0,
            "lecturers": 0,
            "staff": 0,
            "admins": 0,
            "total": 0,
        }

        for r in rows:
            utype = getattr(r.user_type, "value", str(r.user_type))
            total = int(r.total or 0)
            out["total"] += total

            if utype == UserTypeEnum.STUDENT.value:
                out["students"] = total
            elif utype == UserTypeEnum.TEACHER.value:
                out["lecturers"] = total
            elif utype == UserTypeEnum.STAFF.value:
                out["staff"] = total
            elif utype == UserTypeEnum.ADMIN.value:
                out["admins"] = total

        return out

    def dashboard_pending_approval_counts(self, *, company_id: int) -> Dict[str, Any]:
        rows = self.s.execute(
            select(
                User.user_type.label("user_type"),
                User.status.label("status"),
                func.count(User.id).label("total"),
            )
            .select_from(UserAffiliation)
            .join(User, User.id == UserAffiliation.user_id)
            .where(
                UserAffiliation.company_id == int(company_id),
                User.status.in_([
                    UserStatusEnum.PENDING_EMAIL,
                    UserStatusEnum.PENDING_APPROVAL,
                ]),
            )
            .group_by(User.user_type, User.status)
        ).all()

        out = {
            "value": 0,
            "students": 0,
            "lecturers": 0,
            "staff": 0,
            "admins": 0,
            "approval_stages": {
                "pending_email_verification": 0,
                "pending_admin_approval": 0,
            },
        }

        for r in rows:
            utype = getattr(r.user_type, "value", str(r.user_type))
            status = getattr(r.status, "value", str(r.status))
            total = int(r.total or 0)

            out["value"] += total

            if utype == UserTypeEnum.STUDENT.value:
                out["students"] += total
            elif utype == UserTypeEnum.TEACHER.value:
                out["lecturers"] += total
            elif utype == UserTypeEnum.STAFF.value:
                out["staff"] += total
            elif utype == UserTypeEnum.ADMIN.value:
                out["admins"] += total

            if status == UserStatusEnum.PENDING_EMAIL.value:
                out["approval_stages"]["pending_email_verification"] += total
            elif status == UserStatusEnum.PENDING_APPROVAL.value:
                out["approval_stages"]["pending_admin_approval"] += total

        return out

    def dashboard_pending_new_between(
        self,
        *,
        company_id: int,
        start_dt: datetime,
        end_dt: datetime,
    ) -> int:
        stmt = (
            select(func.count(User.id))
            .select_from(UserAffiliation)
            .join(User, User.id == UserAffiliation.user_id)
            .where(
                UserAffiliation.company_id == int(company_id),
                User.created_at >= start_dt,
                User.created_at < end_dt,
                User.status.in_([
                    UserStatusEnum.PENDING_EMAIL,
                    UserStatusEnum.PENDING_APPROVAL,
                ]),
            )
        )
        return int(self.s.scalar(stmt) or 0)

    def dashboard_user_growth_monthly(
        self,
        *,
        company_id: int,
        start_dt: datetime,
        end_dt: datetime,
    ) -> List[Dict[str, Any]]:
        rows = self.s.execute(
            select(
                func.date_trunc("month", User.created_at).label("month_start"),
                User.user_type.label("user_type"),
                func.count(User.id).label("total"),
            )
            .select_from(UserAffiliation)
            .join(User, User.id == UserAffiliation.user_id)
            .where(
                UserAffiliation.company_id == int(company_id),
                User.created_at >= start_dt,
                User.created_at < end_dt,
            )
            .group_by(func.date_trunc("month", User.created_at), User.user_type)
            .order_by(func.date_trunc("month", User.created_at).asc())
        ).all()

        return [
            {
                "month_start": r.month_start,
                "user_type": getattr(r.user_type, "value", str(r.user_type)),
                "total": int(r.total or 0),
            }
            for r in rows
        ]

    # =========================================================
    # DASHBOARD - MATERIALS
    # =========================================================
    def dashboard_material_type_counts(self, *, company_id: int) -> Dict[str, int]:
        rows = self.s.execute(
            select(
                Material.material_type.label("material_type"),
                func.count(Material.id).label("total"),
            )
            .where(Material.company_id == int(company_id))
            .group_by(Material.material_type)
        ).all()

        out = {
            "slides": 0,
            "pdf": 0,
            "doc": 0,
            "video": 0,
            "link": 0,
            "other": 0,
        }

        for r in rows:
            mtype = getattr(r.material_type, "value", str(r.material_type)).lower()
            if mtype in out:
                out[mtype] = int(r.total or 0)

        return out

    def dashboard_total_materials(self, *, company_id: int) -> int:
        stmt = select(func.count(Material.id)).where(Material.company_id == int(company_id))
        return int(self.s.scalar(stmt) or 0)

    def dashboard_new_materials_between(
        self,
        *,
        company_id: int,
        start_dt: datetime,
        end_dt: datetime,
    ) -> int:
        stmt = (
            select(func.count(Material.id))
            .where(
                Material.company_id == int(company_id),
                Material.created_at >= start_dt,
                Material.created_at < end_dt,
            )
        )
        return int(self.s.scalar(stmt) or 0)

    def dashboard_global_material_analytics(self, *, company_id: int) -> Dict[str, int]:
        row = self.s.execute(
            select(
                func.coalesce(func.sum(Material.view_count), 0).label("total_views"),
                func.coalesce(func.sum(Material.download_count), 0).label("total_downloads"),
            )
            .where(Material.company_id == int(company_id))
        ).first()

        return {
            "total_views": int(getattr(row, "total_views", 0) or 0),
            "total_downloads": int(getattr(row, "total_downloads", 0) or 0),
        }

    def dashboard_recent_material_activity_proxy_between(
        self,
        *,
        company_id: int,
        start_dt: datetime,
        end_dt: datetime,
    ) -> int:
        """
        Best-effort proxy trend only.
        Accurate per-period analytics needs an event log table.
        """
        view_hits = int(self.s.scalar(
            select(func.count(StudentMaterialInteraction.id)).where(
                StudentMaterialInteraction.company_id == int(company_id),
                StudentMaterialInteraction.last_viewed_at.isnot(None),
                StudentMaterialInteraction.last_viewed_at >= start_dt,
                StudentMaterialInteraction.last_viewed_at < end_dt,
            )
        ) or 0)

        download_hits = int(self.s.scalar(
            select(func.count(StudentMaterialInteraction.id)).where(
                StudentMaterialInteraction.company_id == int(company_id),
                StudentMaterialInteraction.last_downloaded_at.isnot(None),
                StudentMaterialInteraction.last_downloaded_at >= start_dt,
                StudentMaterialInteraction.last_downloaded_at < end_dt,
            )
        ) or 0)

        return view_hits + download_hits

    def dashboard_total_students(self, *, company_id: int) -> int:
        stmt = (
            select(func.count(StudentProfile.id))
            .where(StudentProfile.company_id == int(company_id))
        )
        return int(self.s.scalar(stmt) or 0)

    def dashboard_students_by_department(self, *, company_id: int) -> List[Dict[str, Any]]:
        rows = self.s.execute(
            select(
                Department.id.label("department_id"),
                Department.name.label("department_name"),
                Department.code.label("department_code"),
                func.count(StudentProfile.id).label("total"),
            )
            .select_from(Department)
            .outerjoin(
                StudentProfile,
                and_(
                    StudentProfile.department_id == Department.id,
                    StudentProfile.company_id == int(company_id),
                ),
            )
            .where(Department.company_id == int(company_id))
            .group_by(Department.id, Department.name, Department.code)
            .order_by(Department.name.asc())
        ).all()

        return [
            {
                "department_id": int(r.department_id),
                "department_name": r.department_name,
                "department_code": r.department_code,
                "count": int(r.total or 0),
            }
            for r in rows
        ]

    def dashboard_materials_by_department(self, *, company_id: int) -> List[Dict[str, Any]]:
        rows = self.s.execute(
            select(
                Department.id.label("department_id"),
                Department.name.label("department_name"),
                Department.code.label("department_code"),
                func.count(Material.id).label("total"),
            )
            .select_from(Department)
            .outerjoin(
                CourseOffering,
                and_(
                    CourseOffering.department_id == Department.id,
                    CourseOffering.company_id == int(company_id),
                ),
            )
            .outerjoin(
                Material,
                and_(
                    Material.course_offering_id == CourseOffering.id,
                    Material.company_id == int(company_id),
                ),
            )
            .where(Department.company_id == int(company_id))
            .group_by(Department.id, Department.name, Department.code)
            .order_by(Department.name.asc())
        ).all()

        return [
            {
                "department_id": int(r.department_id),
                "department_name": r.department_name,
                "department_code": r.department_code,
                "count": int(r.total or 0),
            }
            for r in rows
        ]
