from typing import Optional, Dict, Any, List
from sqlalchemy import or_, desc, asc, select, func
from cmcp.config.database import db
from cmcp.modules.auth.models import User, UserAffiliation, UserStatusEnum
from cmcp.modules.education_people.models import StudentProfile, Classroom
from cmcp.modules.academic.models import Faculty, Department, Semester
from cmcp.common.email.outbox_model import EmailOutbox
from cmcp.core.base_repo import BaseRepository

class AdminStudentsRepository:
    def __init__(self, session=None):
        self.s = session or db.session
        self.profiles = BaseRepository(StudentProfile, self.s)

    def _build_query(self, company_id: int, filters: Dict[str, Any]):
        q = (
            select(StudentProfile, User, Faculty, Department, Semester, Classroom)
            .join(User, User.id == StudentProfile.user_id)
            .outerjoin(Faculty, Faculty.id == StudentProfile.faculty_id)
            .outerjoin(Department, Department.id == StudentProfile.department_id)
            .outerjoin(Semester, Semester.id == StudentProfile.semester_id)
            .outerjoin(Classroom, Classroom.id == StudentProfile.classroom_id)
            .where(StudentProfile.company_id == company_id)
        )

        search = filters.get("search")
        if search:
            q = q.where(
                or_(
                    StudentProfile.full_name.ilike(f"%{search}%"),
                    StudentProfile.student_id.ilike(f"%{search}%"),
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )

        if filters.get("faculty_id"):
            q = q.where(StudentProfile.faculty_id == filters["faculty_id"])
        
        if filters.get("department_id"):
            q = q.where(StudentProfile.department_id == filters["department_id"])

        if filters.get("semester_id"):
            q = q.where(StudentProfile.semester_id == filters["semester_id"])

        if filters.get("classroom_id"):
            q = q.where(StudentProfile.classroom_id == filters["classroom_id"])
            
        is_enabled = filters.get("is_enabled")
        if is_enabled is not None:
            q = q.where(StudentProfile.is_enabled.is_(is_enabled))

        return q

    def list_students(self, company_id: int, limit: int, offset: int, filters: Dict[str, Any]):
        q = self._build_query(company_id, filters)
        
        count_stmt = select(func.count()).select_from(q.subquery())
        total = self.s.scalar(count_stmt) or 0
        
        q = q.order_by(StudentProfile.id.desc()).offset(offset).limit(limit)
        rows = self.s.execute(q).all()
        
        results = []
        for row in rows:
            prof, usr, fac, dept, sem, cls = row
            user_status = getattr(usr.status, "value", str(usr.status))
            status_label = self._status_label(usr)

            results.append({
                "id": prof.id,
                "user": {
                    "id": usr.id,
                    "username": usr.username,
                    "email": usr.email,
                    "status": user_status,
                    "is_enabled": bool(usr.is_enabled),
                    "email_verified_at": usr.email_verified_at.isoformat() if usr.email_verified_at else None,
                    "approved_at": usr.approved_at.isoformat() if usr.approved_at else None,
                },
                "profile": {
                    "id": prof.id,
                    "full_name": prof.full_name,
                    "student_id": prof.student_id,
                    "is_enabled": prof.is_enabled,
                },
                "context": {
                    "faculty": {"id": fac.id, "name": fac.name} if fac else None,
                    "department": {"id": dept.id, "name": dept.name} if dept else None,
                    "semester": {"id": sem.id, "name": sem.name, "number": getattr(sem, "number", None)} if sem else None,
                    "classroom": {"id": cls.id, "name": cls.name} if cls else None,
                },
                "flags": {
                    "profile_enabled": bool(prof.is_enabled),
                    "account_enabled": bool(usr.is_enabled),
                    "is_enabled": bool(prof.is_enabled and usr.is_enabled),
                    "status_label": status_label,
                    "approval_status": user_status,
                },
                "created_at": prof.created_at.isoformat() if prof.created_at else None,
            })
            
        return results, total

    def get_student(self, company_id: int, student_profile_id: int):
        q = self._build_query(company_id, {})
        q = q.where(StudentProfile.id == int(student_profile_id))
        
        row = self.s.execute(q).first()

        if not row:
            return None

        prof, usr, fac, dept, sem, cls = row
        user_status = getattr(usr.status, "value", str(usr.status))
        email_outboxes = self._latest_email_outboxes(user_id=int(usr.id))

        return {
            "id": prof.id,
            "user": {
                "id": usr.id,
                "username": usr.username,
                "email": usr.email,
                "status": user_status,
                "is_enabled": bool(usr.is_enabled),
                "email_verified_at": usr.email_verified_at.isoformat() if usr.email_verified_at else None,
                "approved_at": usr.approved_at.isoformat() if usr.approved_at else None,
                "must_change_password": bool(usr.must_change_password),
            },
            "profile": {
                "id": prof.id,
                "full_name": prof.full_name,
                "student_id": prof.student_id,
                "is_enabled": prof.is_enabled,
            },
            "context": {
                "faculty": {"id": fac.id, "name": fac.name} if fac else None,
                "department": {"id": dept.id, "name": dept.name} if dept else None,
                "semester": {"id": sem.id, "name": sem.name, "number": getattr(sem, "number", None)} if sem else None,
                "classroom": {"id": cls.id, "name": cls.name, "room_number": getattr(cls, "room_number", None)} if cls else None,
            },
            "flags": {
                "profile_enabled": bool(prof.is_enabled),
                "account_enabled": bool(usr.is_enabled),
                "is_enabled": bool(prof.is_enabled and usr.is_enabled),
                "status_label": self._status_label(usr),
                "approval_status": user_status,
                "email_verified": usr.email_verified_at is not None,
                "approved": user_status == UserStatusEnum.ACTIVE.value,
            },
            "email_outboxes": email_outboxes,
            "email_verification_outbox": email_outboxes.get("verify_email"),
            "verification_email_outbox": email_outboxes.get("verify_email"),
            "approval_email_outbox": email_outboxes.get("approved"),
            "audit": {
                "created_at": prof.created_at.isoformat() if prof.created_at else None,
                "updated_at": prof.updated_at.isoformat() if prof.updated_at else None,
            }
        }

    def _status_label(self, user: User) -> str:
        status = getattr(user.status, "value", str(user.status))
        if not user.is_enabled:
            return "Blocked"
        if status == UserStatusEnum.ACTIVE.value:
            return "Active"
        if status == UserStatusEnum.PENDING_APPROVAL.value:
            return "Pending approval"
        if status == UserStatusEnum.PENDING_EMAIL.value:
            return "Pending email"
        if status == UserStatusEnum.REJECTED.value:
            return "Rejected"
        return status.replace("_", " ").title()

    def _latest_email_outboxes(self, *, user_id: int) -> Dict[str, Any]:
        rows = (
            self.s.query(EmailOutbox)
            .filter(
                EmailOutbox.ref_type == "User",
                EmailOutbox.ref_id == int(user_id),
            )
            .order_by(EmailOutbox.created_at.desc())
            .limit(20)
            .all()
        )
        out: Dict[str, Any] = {}
        for row in rows:
            key = str(row.template or "")
            if key and key not in out:
                out[key] = {
                    "id": int(row.id),
                    "status": row.status,
                    "template": row.template,
                    "to_email": row.to_email,
                    "last_error": row.last_error,
                    "sent_at": row.sent_at.isoformat() if row.sent_at else None,
                }
        return out

    def department_belongs_to_faculty(self, *, company_id: int, department_id: int, faculty_id: int) -> bool:
        row = self.s.execute(
            select(Department.id).where(
                Department.id == int(department_id),
                Department.company_id == int(company_id),
                Department.faculty_id == int(faculty_id),
            )
        ).first()
        return bool(row)
