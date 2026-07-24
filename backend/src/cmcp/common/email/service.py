from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from cmcp.config.database import db
from cmcp.common.email.client import SMTPEmailClient
from cmcp.common.email.outbox_model import EmailOutbox, EmailOutboxStatus
from cmcp.common.email.renderer import build_renderer, render_template

log = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EmailService:
    """
    Best practice rules:
    - enqueue/mark_* NEVER commit (caller controls transaction)
    - send_outbox_row_now(): render + SMTP send immediately (no commit)
    - fetch_batch_for_sending(): worker locks rows (commit is OK in worker)
    """

    _renderer_env = None  # cached Jinja env

    def __init__(
        self,
        *,
        session: Optional[Session] = None,
        provider: str,
        from_email: str,
        from_name: Optional[str] = None,
        max_tries: int = 5,
        templates_dir: Optional[str] = None,
    ):
        self.s: Session = session or db.session
        self.provider = (provider or "smtp").strip().lower()
        self.from_email = (from_email or "").strip()
        self.from_name = (from_name or "").strip() if from_name else None
        self.max_tries = int(max_tries)

        if templates_dir:
            self.templates_dir = templates_dir
        else:
            self.templates_dir = str(Path(__file__).resolve().parent / "templates")

        if EmailService._renderer_env is None:
            EmailService._renderer_env = build_renderer(templates_dir=self.templates_dir)
            log.info("Email renderer initialized templates_dir=%s", self.templates_dir)

    # ----------------------------
    # SMTP client
    # ----------------------------
    def _smtp_client(self) -> SMTPEmailClient:
        host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        port = int(os.getenv("SMTP_PORT", "587") or 587)
        username = os.getenv("SMTP_USERNAME", "")
        password = os.getenv("SMTP_PASSWORD", "")
        use_tls = str(os.getenv("SMTP_USE_TLS", "true")).strip().lower() in ("1", "true", "yes", "y", "on")

        if not username or not password:
            raise RuntimeError("SMTP_USERNAME/SMTP_PASSWORD are required.")

        return SMTPEmailClient(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
        )

    # ----------------------------
    # Outbox primitives (NO COMMIT)
    # ----------------------------
    def enqueue(
        self,
        *,
        to_email: str,
        subject: str,
        template: str,
        payload: Dict[str, Any],
        ref_type: Optional[str] = None,
        ref_id: Optional[int] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        status: Optional[str] = None,
        last_error: Optional[str] = None,
    ) -> EmailOutbox:
        row = EmailOutbox(
            to_email=(to_email or "").strip(),
            subject=(subject or "").strip(),
            template=(template or "").strip(),
            payload_json=json.dumps(payload or {}, ensure_ascii=False),
            from_email=(from_email or self.from_email or None),
            from_name=(from_name or self.from_name or None),
            status=status or EmailOutboxStatus.PENDING,
            tries=0,
            last_error=(last_error or None),
            locked_at=None,
            sent_at=None,
            ref_type=ref_type,
            ref_id=ref_id,
        )
        self.s.add(row)
        self.s.flush([row])  # get row.id without commit
        return row

    def mark_sent(self, row: EmailOutbox) -> None:
        row.status = EmailOutboxStatus.SENT
        row.sent_at = _utcnow()
        row.last_error = None

    def mark_failed(self, row: EmailOutbox, err: str) -> None:
        row.tries = int(row.tries or 0) + 1
        row.last_error = (err or "")[:800]
        if row.tries >= self.max_tries:
            row.status = EmailOutboxStatus.FAILED
        else:
            row.status = EmailOutboxStatus.PENDING
            row.locked_at = None

    # ----------------------------
    # Sync send (Option B)
    # ----------------------------
    def send_outbox_row_now(self, row: EmailOutbox) -> None:
        if self.provider != "smtp":
            raise RuntimeError(f"Only SMTP is supported right now (provider={self.provider}).")

        payload = json.loads(row.payload_json or "{}")
        html = render_template(EmailService._renderer_env, f"{row.template}.html", payload)

        from_email = row.from_email or self.from_email
        from_name = row.from_name or self.from_name
        if not from_email:
            raise RuntimeError("MAIL_FROM_EMAIL is required.")

        # status visibility
        row.status = EmailOutboxStatus.SENDING
        row.locked_at = _utcnow()
        self.s.flush([row])

        log.info("SMTP send start outbox_id=%s to=%s template=%s", row.id, row.to_email, row.template)

        try:
            smtp = self._smtp_client()
            smtp.send_html(
                from_email=from_email,
                from_name=from_name,
                to_email=row.to_email,
                subject=row.subject,
                html_body=html,
                text_body=None,
            )
            self.mark_sent(row)
            self.s.flush([row])
            log.info("SMTP send OK outbox_id=%s to=%s", row.id, row.to_email)
        except Exception as e:
            err = str(e)
            self.mark_failed(row, err)
            self.s.flush([row])
            if "WebLoginRequired" in err or "5.7.9" in err:
                log.error(
                    "SMTP auth blocked by Gmail for outbox_id=%s. Use a Google App Password "
                    "(https://myaccount.google.com/apppasswords) in SMTP_PASSWORD, not your normal Gmail password.",
                    row.id,
                )
            else:
                log.exception("SMTP send FAILED outbox_id=%s to=%s", row.id, row.to_email)
            raise

    # ----------------------------
    # Worker lock step (COMMIT OK)
    # ----------------------------
    def fetch_batch_for_sending(self, *, batch_size: int = 50) -> List[EmailOutbox]:
        rows = (
            self.s.query(EmailOutbox)
            .filter(EmailOutbox.status == EmailOutboxStatus.PENDING)
            .order_by(EmailOutbox.created_at.asc())
            .limit(int(batch_size))
            .all()
        )
        if not rows:
            return []

        now = _utcnow()
        for r in rows:
            r.status = EmailOutboxStatus.SENDING
            r.locked_at = now

        self.s.commit()  # worker lock
        return rows