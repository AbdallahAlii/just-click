from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from cmcp.common.email.service import EmailService
from cmcp.config.database import db
from cmcp.modules.contact.models import ContactMessage, ContactMessageStatusEnum

log = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _contact_notify_email() -> str:
    return (
        os.getenv("CONTACT_NOTIFY_EMAIL")
        or os.getenv("MAIL_FROM_EMAIL")
        or "justclick.cmc@gmail.com"
    ).strip()


class ContactService:
    def __init__(self, session: Optional[Session] = None):
        self.s: Session = session or db.session
        self.email_svc = EmailService(
            session=self.s,
            provider=os.getenv("MAIL_PROVIDER", "smtp"),
            from_email=os.getenv("MAIL_FROM_EMAIL", ""),
            from_name=os.getenv("MAIL_FROM_NAME", "JustClick"),
            max_tries=int(os.getenv("EMAIL_OUTBOX_MAX_TRIES", "5")),
        )

    def _shape(self, row: ContactMessage) -> Dict[str, Any]:
        return {
            "id": int(row.id),
            "name": row.name,
            "email": row.email,
            "subject": row.subject,
            "message": row.message,
            "status": row.status.value if row.status else None,
            "user_id": int(row.user_id) if row.user_id else None,
            "company_id": int(row.company_id) if row.company_id else None,
            "admin_notes": row.admin_notes,
            "admin_reply": row.admin_reply,
            "handled_by_user_id": int(row.handled_by_user_id) if row.handled_by_user_id else None,
            "handled_at": row.handled_at.isoformat() if row.handled_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def submit(
        self,
        *,
        name: str,
        email: str,
        subject: str,
        message: str,
        user_id: Optional[int] = None,
        company_id: Optional[int] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        row = ContactMessage(
            name=name.strip(),
            email=str(email).strip().lower(),
            subject=subject.strip(),
            message=message.strip(),
            status=ContactMessageStatusEnum.OPEN,
            user_id=int(user_id) if user_id else None,
            company_id=int(company_id) if company_id else None,
        )
        self.s.add(row)
        self.s.flush([row])

        notify_to = _contact_notify_email()
        self.email_svc.enqueue(
            to_email=notify_to,
            subject=f"[JustClick Contact] {row.subject}",
            template="contact_message",
            payload={
                "name": row.name,
                "email": row.email,
                "subject": row.subject,
                "message": row.message,
                "contact_id": int(row.id),
                "created_at": row.created_at.isoformat() if row.created_at else "",
            },
            ref_type="ContactMessage",
            ref_id=int(row.id),
        )

        return True, "Thanks — your message has been sent.", {"contact": self._shape(row)}

    def list_admin(
        self,
        *,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        q = self.s.query(ContactMessage)
        if status:
            q = q.filter(ContactMessage.status == ContactMessageStatusEnum(status))

        total = int(q.count())
        pages = max((total + per_page - 1) // per_page, 1)
        page = min(max(page, 1), pages)
        rows = (
            q.order_by(ContactMessage.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return True, "OK", {
            "items": [self._shape(r) for r in rows],
            "pagination": {"page": page, "per_page": per_page, "total": total, "pages": pages},
        }

    def get_admin(self, *, contact_id: int) -> Tuple[bool, str, Dict[str, Any]]:
        row = self.s.get(ContactMessage, int(contact_id))
        if not row:
            return False, "Contact message not found.", {}
        return True, "OK", {"contact": self._shape(row)}

    def handle(
        self,
        *,
        contact_id: int,
        admin_user_id: int,
        status: Optional[str] = None,
        admin_notes: Optional[str] = None,
        admin_reply: Optional[str] = None,
        send_reply_email: bool = False,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        row = self.s.get(ContactMessage, int(contact_id))
        if not row:
            return False, "Contact message not found.", {}

        if status:
            row.status = ContactMessageStatusEnum(status)
        if admin_notes is not None:
            row.admin_notes = admin_notes
        if admin_reply is not None:
            row.admin_reply = admin_reply

        row.handled_by_user_id = int(admin_user_id)
        row.handled_at = _utcnow()

        if send_reply_email and admin_reply:
            self.email_svc.enqueue(
                to_email=row.email,
                subject=f"Re: {row.subject}",
                template="contact_reply",
                payload={
                    "name": row.name,
                    "subject": row.subject,
                    "admin_reply": admin_reply,
                },
                ref_type="ContactMessage",
                ref_id=int(row.id),
            )
            if row.status == ContactMessageStatusEnum.OPEN:
                row.status = ContactMessageStatusEnum.RESOLVED

        self.s.flush([row])
        return True, "Contact message updated.", {"contact": self._shape(row)}
