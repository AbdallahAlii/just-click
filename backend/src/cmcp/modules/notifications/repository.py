from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from cmcp.modules.auth.models import User, UserAffiliation, UserStatusEnum, UserTypeEnum, LinkedEntityTypeEnum
from cmcp.modules.education_people.models import StudentProfile
from cmcp.modules.materials.models import Material
from cmcp.modules.academic.models import CourseOffering, Course, Department
from cmcp.modules.notifications.models import (
    NotificationBatch,
    UserNotification,
    UserDeviceToken,
    PushOutbox,
    PushOutboxStatus,
)
from cmcp.common.email.outbox_model import EmailOutbox


@dataclass
class NotifyRecipient:
    user_id: int
    email: str
    full_name: str
    student_id: str


class NotificationsRepo:
    def __init__(self, session: Session):
        self.s = session

    def list_eligible_students(
        self,
        *,
        company_id: int,
        user_ids: Optional[List[int]] = None,
        department_id: Optional[int] = None,
        semester_id: Optional[int] = None,
        limit: int = 5000,
    ) -> List[NotifyRecipient]:
        stmt = (
            self.s.query(
                User.id,
                User.email,
                StudentProfile.full_name,
                StudentProfile.student_id,
            )
            .join(StudentProfile, StudentProfile.user_id == User.id)
            .join(
                UserAffiliation,
                and_(
                    UserAffiliation.user_id == User.id,
                    UserAffiliation.company_id == int(company_id),
                    UserAffiliation.is_enabled.is_(True),
                    UserAffiliation.linked_entity_type == LinkedEntityTypeEnum.STUDENT_PROFILE,
                    UserAffiliation.linked_entity_id == StudentProfile.id,
                ),
            )
            .filter(
                StudentProfile.company_id == int(company_id),
                StudentProfile.is_enabled.is_(True),
                User.user_type == UserTypeEnum.STUDENT,
                User.status == UserStatusEnum.ACTIVE,
                User.is_enabled.is_(True),
                User.email_verified_at.isnot(None),
            )
        )

        if user_ids:
            stmt = stmt.filter(User.id.in_([int(x) for x in user_ids]))
        if department_id:
            stmt = stmt.filter(StudentProfile.department_id == int(department_id))
        if semester_id:
            stmt = stmt.filter(StudentProfile.semester_id == int(semester_id))

        rows = stmt.limit(max(1, min(int(limit), 10000))).all()

        return [
            NotifyRecipient(
                user_id=int(r[0]),
                email=str(r[1] or "").strip(),
                full_name=str(r[2] or "").strip() or "Student",
                student_id=str(r[3] or "").strip(),
            )
            for r in rows
            if r[1]
        ]

    def get_material_context(
        self,
        *,
        company_id: int,
        material_id: int,
    ) -> Optional[Dict[str, Any]]:
        row = (
            self.s.query(
                Material.id,
                Material.title,
                Material.material_type,
                Material.course_offering_id,
                Course.title.label("course_title"),
                Course.code.label("course_code"),
                Department.name.label("department_name"),
                CourseOffering.department_id,
                CourseOffering.semester_id,
            )
            .join(CourseOffering, CourseOffering.id == Material.course_offering_id)
            .join(Course, Course.id == CourseOffering.course_id)
            .outerjoin(Department, Department.id == CourseOffering.department_id)
            .filter(
                Material.company_id == int(company_id),
                Material.id == int(material_id),
            )
            .first()
        )
        if not row:
            return None
        mtype = getattr(row.material_type, "value", str(row.material_type))
        return {
            "material_id": int(row.id),
            "title": row.title,
            "material_type": mtype,
            "course_offering_id": int(row.course_offering_id),
            "course_title": row.course_title,
            "course_code": row.course_code,
            "department_name": row.department_name,
            "department_id": int(row.department_id) if row.department_id else None,
            "semester_id": int(row.semester_id) if row.semester_id else None,
        }

    def create_batch(
        self,
        *,
        company_id: int,
        title: str,
        body: str,
        event_type: str,
        channels: List[str],
        material_id: Optional[int] = None,
        created_by_user_id: Optional[int] = None,
    ) -> NotificationBatch:
        row = NotificationBatch(
            company_id=int(company_id),
            title=title.strip(),
            body=body.strip(),
            event_type=event_type,
            channels_json=json.dumps(channels),
            material_id=int(material_id) if material_id else None,
            created_by_user_id=created_by_user_id,
        )
        self.s.add(row)
        self.s.flush()
        return row

    def create_user_notification(
        self,
        *,
        company_id: int,
        user_id: int,
        batch_id: Optional[int],
        event_type: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        material_id: Optional[int] = None,
    ) -> UserNotification:
        row = UserNotification(
            company_id=int(company_id),
            user_id=int(user_id),
            batch_id=batch_id,
            event_type=event_type,
            title=title.strip(),
            body=body.strip(),
            data_json=json.dumps(data or {}, ensure_ascii=False),
            material_id=int(material_id) if material_id else None,
        )
        self.s.add(row)
        self.s.flush()
        return row

    def list_active_device_tokens(self, *, company_id: int, user_id: int) -> List[UserDeviceToken]:
        return (
            self.s.query(UserDeviceToken)
            .filter(
                UserDeviceToken.company_id == int(company_id),
                UserDeviceToken.user_id == int(user_id),
                UserDeviceToken.is_active.is_(True),
            )
            .all()
        )

    def upsert_device_token(
        self,
        *,
        company_id: int,
        user_id: int,
        token: str,
        platform: str,
    ) -> UserDeviceToken:
        token = (token or "").strip()
        platform = (platform or "android").strip().lower()
        now = datetime.now(timezone.utc)

        row = (
            self.s.query(UserDeviceToken)
            .filter(
                UserDeviceToken.company_id == int(company_id),
                UserDeviceToken.user_id == int(user_id),
                UserDeviceToken.token == token,
            )
            .first()
        )
        if row:
            row.is_active = True
            row.platform = platform
            row.last_seen_at = now
        else:
            row = UserDeviceToken(
                company_id=int(company_id),
                user_id=int(user_id),
                token=token,
                platform=platform,
                is_active=True,
                last_seen_at=now,
            )
            self.s.add(row)
        self.s.flush()
        return row

    def enqueue_push(
        self,
        *,
        company_id: int,
        user_id: int,
        device_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        notification_id: Optional[int] = None,
        batch_id: Optional[int] = None,
    ) -> PushOutbox:
        row = PushOutbox(
            company_id=int(company_id),
            user_id=int(user_id),
            device_token=device_token.strip(),
            title=title.strip(),
            body=body.strip(),
            data_json=json.dumps(data or {}, ensure_ascii=False),
            status=PushOutboxStatus.PENDING,
            notification_id=notification_id,
            batch_id=batch_id,
        )
        self.s.add(row)
        self.s.flush()
        return row

    def list_user_notifications(
        self,
        *,
        company_id: int,
        user_id: int,
        unread_only: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[UserNotification], int]:
        base = self.s.query(UserNotification).filter(
            UserNotification.company_id == int(company_id),
            UserNotification.user_id == int(user_id),
        )
        if unread_only:
            base = base.filter(UserNotification.read_at.is_(None))

        total = int(base.count())
        page = max(1, page)
        per_page = max(1, min(int(per_page), 100))
        offset = (page - 1) * per_page

        rows = (
            base.order_by(UserNotification.created_at.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )
        return rows, total

    def unread_count(self, *, company_id: int, user_id: int) -> int:
        return int(
            self.s.query(func.count(UserNotification.id))
            .filter(
                UserNotification.company_id == int(company_id),
                UserNotification.user_id == int(user_id),
                UserNotification.read_at.is_(None),
            )
            .scalar()
            or 0
        )

    def mark_read(self, *, company_id: int, user_id: int, notification_id: int) -> bool:
        row = (
            self.s.query(UserNotification)
            .filter(
                UserNotification.company_id == int(company_id),
                UserNotification.user_id == int(user_id),
                UserNotification.id == int(notification_id),
            )
            .first()
        )
        if not row:
            return False
        if not row.read_at:
            row.read_at = datetime.now(timezone.utc)
        return True

    def mark_all_read(self, *, company_id: int, user_id: int) -> int:
        now = datetime.now(timezone.utc)
        q = (
            self.s.query(UserNotification)
            .filter(
                UserNotification.company_id == int(company_id),
                UserNotification.user_id == int(user_id),
                UserNotification.read_at.is_(None),
            )
        )
        count = 0
        for row in q.all():
            row.read_at = now
            count += 1
        return count

    def list_batches_admin(
        self,
        *,
        company_id: int,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[NotificationBatch], int]:
        base = self.s.query(NotificationBatch).filter(
            NotificationBatch.company_id == int(company_id),
        )
        total = int(base.count())
        page = max(1, page)
        per_page = max(1, min(int(per_page), 100))
        offset = (page - 1) * per_page
        rows = (
            base.order_by(NotificationBatch.created_at.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )
        return rows, total

    def get_batch(self, *, company_id: int, batch_id: int) -> Optional[NotificationBatch]:
        return (
            self.s.query(NotificationBatch)
            .filter(
                NotificationBatch.company_id == int(company_id),
                NotificationBatch.id == int(batch_id),
            )
            .first()
        )

    def shape_notification(self, row: UserNotification) -> Dict[str, Any]:
        data = {}
        try:
            data = json.loads(row.data_json or "{}")
        except Exception:
            pass
        return {
            "id": int(row.id),
            "event_type": row.event_type,
            "title": row.title,
            "body": row.body,
            "data": data,
            "material_id": int(row.material_id) if row.material_id else None,
            "read_at": row.read_at.isoformat() if row.read_at else None,
            "is_read": row.read_at is not None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    def shape_batch(self, row: NotificationBatch) -> Dict[str, Any]:
        try:
            channels = json.loads(row.channels_json or "[]")
        except Exception:
            channels = []
        delivery = self.get_batch_delivery_stats([int(row.id)]).get(int(row.id), {})
        return {
            "id": int(row.id),
            "title": row.title,
            "body": row.body,
            "event_type": row.event_type,
            "channels": channels,
            "material_id": int(row.material_id) if row.material_id else None,
            "recipient_count": int(row.recipient_count or 0),
            "in_app_count": int(row.in_app_count or 0),
            "email_count": int(row.email_count or 0),
            "push_count": int(row.push_count or 0),
            "delivery": delivery,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    def get_batch_delivery_stats(self, batch_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        if not batch_ids:
            return {}

        ids = [int(x) for x in batch_ids if int(x or 0) > 0]
        if not ids:
            return {}

        email_rows = (
            self.s.query(EmailOutbox.ref_id, EmailOutbox.status, func.count(EmailOutbox.id))
            .filter(
                EmailOutbox.ref_type == "NotificationBatch",
                EmailOutbox.ref_id.in_(ids),
            )
            .group_by(EmailOutbox.ref_id, EmailOutbox.status)
            .all()
        )

        email_by_batch: Dict[int, Dict[str, int]] = {}
        for ref_id, status, count in email_rows:
            bid = int(ref_id)
            bucket = email_by_batch.setdefault(bid, {})
            bucket[str(status or "unknown")] = int(count or 0)

        push_rows = (
            self.s.query(PushOutbox.batch_id, PushOutbox.status, func.count(PushOutbox.id))
            .filter(PushOutbox.batch_id.in_(ids))
            .group_by(PushOutbox.batch_id, PushOutbox.status)
            .all()
        )
        push_by_batch: Dict[int, Dict[str, int]] = {}
        for batch_id, status, count in push_rows:
            bid = int(batch_id)
            bucket = push_by_batch.setdefault(bid, {})
            bucket[str(status or "unknown")] = int(count or 0)

        out: Dict[int, Dict[str, Any]] = {}
        for bid in ids:
            email_stats = email_by_batch.get(bid, {})
            push_stats = push_by_batch.get(bid, {})
            email_sent = int(email_stats.get("sent", 0))
            email_pending = int(email_stats.get("pending", 0)) + int(email_stats.get("sending", 0))
            email_failed = int(email_stats.get("failed", 0))
            push_sent = int(push_stats.get("sent", 0))
            push_pending = int(push_stats.get("pending", 0)) + int(push_stats.get("sending", 0))
            push_failed = int(push_stats.get("failed", 0))
            push_skipped = int(push_stats.get("skipped", 0))
            in_app_count = int(
                self.s.query(func.count(UserNotification.id))
                .filter(UserNotification.batch_id == bid)
                .scalar()
                or 0
            )

            if email_failed > 0 or push_failed > 0:
                overall = "failed"
            elif email_pending > 0 or push_pending > 0:
                overall = "pending"
            elif email_sent > 0 or push_sent > 0 or in_app_count > 0:
                overall = "sent"
            else:
                overall = "queued"

            out[bid] = {
                "overall_status": overall,
                "email": email_stats,
                "push": push_stats,
                "push_skipped": push_skipped,
                "in_app_count": in_app_count,
                "email_last_error": self._latest_email_error(bid) if email_failed > 0 else None,
            }
        return out

    def _latest_email_error(self, batch_id: int) -> Optional[str]:
        row = (
            self.s.query(EmailOutbox.last_error)
            .filter(
                EmailOutbox.ref_type == "NotificationBatch",
                EmailOutbox.ref_id == int(batch_id),
                EmailOutbox.last_error.isnot(None),
            )
            .order_by(EmailOutbox.updated_at.desc())
            .first()
        )
        return str(row[0])[:200] if row and row[0] else None

    def fetch_push_batch(self, *, batch_size: int = 50) -> List[PushOutbox]:
        rows = (
            self.s.query(PushOutbox)
            .filter(PushOutbox.status == PushOutboxStatus.PENDING)
            .order_by(PushOutbox.created_at.asc())
            .limit(int(batch_size))
            .all()
        )
        if not rows:
            return []
        now = datetime.now(timezone.utc)
        for r in rows:
            r.status = PushOutboxStatus.SENDING
            r.locked_at = now
        self.s.commit()
        return rows

    def mark_push_sent(self, row: PushOutbox) -> None:
        row.status = PushOutboxStatus.SENT
        row.sent_at = datetime.now(timezone.utc)
        row.last_error = None

    def mark_push_failed(self, row: PushOutbox, err: str, *, max_tries: int = 5) -> None:
        row.tries = int(row.tries or 0) + 1
        row.last_error = (err or "")[:800]
        if row.tries >= max_tries:
            row.status = PushOutboxStatus.FAILED
        else:
            row.status = PushOutboxStatus.PENDING
            row.locked_at = None

    def mark_push_skipped(self, row: PushOutbox, reason: str) -> None:
        row.status = PushOutboxStatus.SKIPPED
        row.last_error = (reason or "")[:800]
        row.sent_at = datetime.now(timezone.utc)
