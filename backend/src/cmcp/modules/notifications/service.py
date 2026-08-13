from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from cmcp.common.email.service import EmailService
from cmcp.common.push.fcm_client import FCMClient, FCMDeliveryError
from cmcp.modules.notifications.models import NotificationEventType
from cmcp.modules.notifications.repository import NotificationsRepo, NotifyRecipient

log = logging.getLogger(__name__)

CHANNEL_IN_APP = "in_app"
CHANNEL_EMAIL = "email"
CHANNEL_PUSH = "push"


class NotificationService:
    def __init__(self, session: Optional[Session] = None):
        from cmcp.config.database import db
        self.s = session or db.session
        self.repo = NotificationsRepo(self.s)
        self.email_svc = EmailService(
            session=self.s,
            provider=os.getenv("MAIL_PROVIDER", "smtp"),
            from_email=os.getenv("MAIL_FROM_EMAIL", ""),
            from_name=os.getenv("MAIL_FROM_NAME", "JustClick"),
        )
        self.fcm = FCMClient()

    def _app_base_url(self) -> str:
        return (os.getenv("APP_BASE_URL") or os.getenv("FRONTEND_BASE_URL") or "http://localhost:3000").rstrip("/")

    def _material_link(self, material_id: int) -> str:
        return f"{self._app_base_url()}/materials/{int(material_id)}"

    def notify_material_event(
        self,
        *,
        company_id: int,
        material_id: int,
        event: str,
        created_by_user_id: Optional[int] = None,
    ) -> None:
        """Auto-notify students when material is created or file updated."""
        if event not in ("created", "updated"):
            return

        ctx = self.repo.get_material_context(company_id=company_id, material_id=material_id)
        if not ctx:
            return

        event_type = (
            NotificationEventType.MATERIAL_CREATED.value
            if event == "created"
            else NotificationEventType.MATERIAL_UPDATED.value
        )

        if event == "created":
            title = f"New material: {ctx['title']}"
            body = (
                f"A new study material \"{ctx['title']}\" was uploaded"
                f" for {ctx['course_code']} · {ctx['course_title']}."
            )
            email_template = "material_published"
            email_subject = f"New study material — {ctx['title']}"
        else:
            title = f"Material updated: {ctx['title']}"
            body = (
                f"The material \"{ctx['title']}\" was updated"
                f" for {ctx['course_code']} · {ctx['course_title']}."
            )
            email_template = "material_updated"
            email_subject = f"Material updated — {ctx['title']}"

        channels = [CHANNEL_IN_APP, CHANNEL_EMAIL, CHANNEL_PUSH]
        material_link = self._material_link(material_id)

        recipients = self.repo.list_eligible_students(
            company_id=company_id,
            department_id=ctx.get("department_id"),
            semester_id=ctx.get("semester_id"),
        )
        if not recipients:
            recipients = self.repo.list_eligible_students(company_id=company_id)

        self._dispatch(
            company_id=company_id,
            title=title,
            body=body,
            event_type=event_type,
            channels=channels,
            recipients=recipients,
            material_id=material_id,
            created_by_user_id=created_by_user_id,
            email_template=email_template,
            email_subject=email_subject,
            email_extra={
                "material_title": ctx["title"],
                "course_code": ctx["course_code"] or "",
                "course_title": ctx["course_title"] or "",
                "department_name": ctx["department_name"] or "",
                "material_type": ctx["material_type"] or "",
                "material_link": material_link,
                "event_label": "New material" if event == "created" else "Updated material",
            },
            push_data={
                "type": event_type,
                "material_id": str(material_id),
                "link": material_link,
            },
        )

    def admin_send(
        self,
        *,
        company_id: int,
        title: str,
        body: str,
        channels: List[str],
        recipient_mode: str,
        user_ids: Optional[List[int]] = None,
        material_id: Optional[int] = None,
        created_by_user_id: Optional[int] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        title = (title or "").strip()
        body = (body or "").strip()
        if not title or not body:
            return False, "Title and message are required.", {}

        normalized_channels = self._normalize_channels(channels)
        if not normalized_channels:
            return False, "Select at least one channel (in_app, email, push).", {}

        if recipient_mode == "selected":
            if not user_ids:
                return False, "Select at least one student.", {}
            recipients = self.repo.list_eligible_students(
                company_id=company_id,
                user_ids=user_ids,
            )
        else:
            recipients = self.repo.list_eligible_students(company_id=company_id)

        if not recipients:
            return False, "No eligible students found (active, approved, verified email).", {}

        material_link = self._material_link(material_id) if material_id else self._app_base_url()

        stats = self._dispatch(
            company_id=company_id,
            title=title,
            body=body,
            event_type=NotificationEventType.ADMIN_BROADCAST.value,
            channels=normalized_channels,
            recipients=recipients,
            material_id=material_id,
            created_by_user_id=created_by_user_id,
            email_template="admin_broadcast",
            email_subject=title,
            email_extra={
                "message": body,
                "material_link": material_link,
            },
            push_data={
                "type": NotificationEventType.ADMIN_BROADCAST.value,
                "material_id": str(material_id) if material_id else "",
                "link": material_link,
            },
        )

        return True, "Notification sent.", stats

    def _normalize_channels(self, channels: List[str]) -> List[str]:
        allowed = {CHANNEL_IN_APP, CHANNEL_EMAIL, CHANNEL_PUSH}
        out = []
        for ch in channels or []:
            c = str(ch).strip().lower()
            if c in allowed and c not in out:
                out.append(c)
        return out

    def _dispatch(
        self,
        *,
        company_id: int,
        title: str,
        body: str,
        event_type: str,
        channels: List[str],
        recipients: List[NotifyRecipient],
        material_id: Optional[int],
        created_by_user_id: Optional[int],
        email_template: str,
        email_subject: str,
        email_extra: Dict[str, Any],
        push_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        batch = self.repo.create_batch(
            company_id=company_id,
            title=title,
            body=body,
            event_type=event_type,
            channels=channels,
            material_id=material_id,
            created_by_user_id=created_by_user_id,
        )

        in_app_count = 0
        email_count = 0
        push_count = 0

        for recipient in recipients:
            notif_row = None
            if CHANNEL_IN_APP in channels:
                notif_row = self.repo.create_user_notification(
                    company_id=company_id,
                    user_id=recipient.user_id,
                    batch_id=int(batch.id),
                    event_type=event_type,
                    title=title,
                    body=body,
                    data=push_data,
                    material_id=material_id,
                )
                in_app_count += 1

            if CHANNEL_EMAIL in channels and recipient.email:
                payload = {
                    "full_name": recipient.full_name,
                    "student_id": recipient.student_id,
                    **email_extra,
                }
                self.email_svc.enqueue(
                    to_email=recipient.email,
                    subject=email_subject,
                    template=email_template,
                    payload=payload,
                    ref_type="NotificationBatch",
                    ref_id=int(batch.id),
                )
                email_count += 1

            if CHANNEL_PUSH in channels:
                tokens = self.repo.list_active_device_tokens(
                    company_id=company_id,
                    user_id=recipient.user_id,
                )
                for tok in tokens:
                    self.repo.enqueue_push(
                        company_id=company_id,
                        user_id=recipient.user_id,
                        device_token=tok.token,
                        title=title,
                        body=body,
                        data=push_data,
                        notification_id=int(notif_row.id) if notif_row else None,
                        batch_id=int(batch.id),
                    )
                    push_count += 1

        batch.recipient_count = len(recipients)
        batch.in_app_count = in_app_count
        batch.email_count = email_count
        batch.push_count = push_count
        self.s.flush()

        return {
            "batch_id": int(batch.id),
            "recipients": len(recipients),
            "in_app": in_app_count,
            "email": email_count,
            "push": push_count,
        }

    def register_device(
        self,
        *,
        company_id: int,
        user_id: int,
        token: str,
        platform: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        token = (token or "").strip()
        if not token:
            return False, "Device token is required.", {}
        row = self.repo.upsert_device_token(
            company_id=company_id,
            user_id=user_id,
            token=token,
            platform=platform,
        )
        return True, "Device registered.", {"id": int(row.id), "platform": row.platform}

    def list_notifications(
        self,
        *,
        company_id: int,
        user_id: int,
        unread_only: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        rows, total = self.repo.list_user_notifications(
            company_id=company_id,
            user_id=user_id,
            unread_only=unread_only,
            page=page,
            per_page=per_page,
        )
        pages = max((total + per_page - 1) // per_page, 1)
        return True, "OK", {
            "data": [self.repo.shape_notification(r) for r in rows],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": pages,
            },
            "unread_count": self.repo.unread_count(company_id=company_id, user_id=user_id),
        }

    def get_unread_count(self, *, company_id: int, user_id: int) -> int:
        return self.repo.unread_count(company_id=company_id, user_id=user_id)

    def mark_read(self, *, company_id: int, user_id: int, notification_id: int) -> Tuple[bool, str]:
        ok = self.repo.mark_read(
            company_id=company_id,
            user_id=user_id,
            notification_id=notification_id,
        )
        return (ok, "Marked as read." if ok else "Notification not found.")

    def mark_all_read(self, *, company_id: int, user_id: int) -> Tuple[bool, str, int]:
        count = self.repo.mark_all_read(company_id=company_id, user_id=user_id)
        return True, f"Marked {count} as read.", count

    def list_batches_admin(
        self,
        *,
        company_id: int,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        rows, total = self.repo.list_batches_admin(
            company_id=company_id,
            page=page,
            per_page=per_page,
        )
        pages = max((total + per_page - 1) // per_page, 1)
        return True, "OK", {
            "data": [self.repo.shape_batch(r) for r in rows],
            "pagination": {"page": page, "per_page": per_page, "total": total, "pages": pages},
        }

    def list_recipients_admin(
        self,
        *,
        company_id: int,
        limit: int = 500,
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        rows = self.repo.list_eligible_students(company_id=company_id, limit=limit)
        return True, "OK", [
            {
                "user_id": r.user_id,
                "email": r.email,
                "full_name": r.full_name,
                "student_id": r.student_id,
            }
            for r in rows
        ]

    def resend_batch_emails(
        self,
        *,
        company_id: int,
        batch_id: int,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        batch = self.repo.get_batch(company_id=company_id, batch_id=batch_id)
        if not batch:
            return False, "Batch not found.", {}

        channels = json.loads(batch.channels_json or "[]")
        if CHANNEL_EMAIL not in channels:
            return False, "This batch did not include email.", {}

        from cmcp.modules.notifications.models import UserNotification

        user_ids = {
            int(r[0])
            for r in self.s.query(UserNotification.user_id)
            .filter(UserNotification.batch_id == int(batch_id))
            .distinct()
            .all()
        }
        if not user_ids:
            return False, "No recipients found for this batch.", {}

        recipients = self.repo.list_eligible_students(company_id=company_id)
        targeted = [r for r in recipients if r.user_id in user_ids]

        email_template = "admin_broadcast"
        if batch.event_type == NotificationEventType.MATERIAL_CREATED.value:
            email_template = "material_published"
        elif batch.event_type == NotificationEventType.MATERIAL_UPDATED.value:
            email_template = "material_updated"

        material_link = self._material_link(batch.material_id) if batch.material_id else self._app_base_url()
        count = 0
        for recipient in targeted:
            self.email_svc.enqueue(
                to_email=recipient.email,
                subject=batch.title,
                template=email_template,
                payload={
                    "full_name": recipient.full_name,
                    "student_id": recipient.student_id,
                    "material_title": batch.title,
                    "message": batch.body,
                    "material_link": material_link,
                    "event_label": "Reminder",
                },
                ref_type="NotificationBatch",
                ref_id=int(batch.id),
            )
            count += 1

        return True, f"Queued {count} emails for resend.", {"queued": count}


class PushNotificationService:
    def __init__(self, session: Optional[Session] = None):
        from cmcp.config.database import db
        self.s = session or db.session
        self.repo = NotificationsRepo(self.s)
        self.fcm = FCMClient()
        self.max_tries = int(os.getenv("PUSH_OUTBOX_MAX_TRIES", "5"))

    def process_batch(self, *, batch_size: int = 50) -> int:
        rows = self.repo.fetch_push_batch(batch_size=batch_size)
        if not rows:
            return 0

        processed = 0
        for row in rows:
            try:
                if not self.fcm.is_configured():
                    self.repo.mark_push_skipped(row, "FIREBASE_SERVICE_ACCOUNT_JSON not configured")
                    self.s.commit()
                    processed += 1
                    continue

                data = {}
                try:
                    data = json.loads(row.data_json or "{}")
                except Exception:
                    pass

                self.fcm.send(
                    token=row.device_token,
                    title=row.title,
                    body=row.body,
                    data=data,
                )
                self.repo.mark_push_sent(row)
                self.s.commit()
                processed += 1
            except FCMDeliveryError as e:
                if self._is_unregistered_token_error(e):
                    self.repo.deactivate_device_token(
                        company_id=int(row.company_id),
                        user_id=int(row.user_id),
                        token=row.device_token,
                    )
                    self.repo.mark_push_skipped(row, f"Device token is no longer registered: {e}")
                else:
                    self.repo.mark_push_failed(row, str(e), max_tries=self.max_tries)
                self.s.commit()
                processed += 1
                log.warning("push skipped outbox_id=%s fcm_error=%s", row.id, e.error_code)
            except Exception as e:
                self.repo.mark_push_failed(row, str(e), max_tries=self.max_tries)
                self.s.commit()
                processed += 1
                log.exception("push failed outbox_id=%s", row.id)

        return processed

    @staticmethod
    def _is_unregistered_token_error(error: FCMDeliveryError) -> bool:
        code = str(error.error_code or "").upper()
        message = str(error).upper()
        return (
            code in {"UNREGISTERED", "NOT_FOUND", "NOTREGISTERED"}
            or "UNREGISTERED" in message
            or "NOTREGISTERED" in message
        )