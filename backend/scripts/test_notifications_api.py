"""
Smoke-test notification APIs (run with backend env + DB).

Usage:
  cd backend
  CMCP_SKIP_CHATBOT_WARMUP=1 PYTHONPATH=src python3 scripts/test_notifications_api.py
"""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
    os.environ.setdefault("CMCP_SKIP_CHATBOT_WARMUP", "1")
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

    from cmcp import create_app
    from cmcp.config.database import db
    from cmcp.modules.notifications.service import NotificationService
    from cmcp.modules.notifications.repository import NotificationsRepo

    app = create_app()
    with app.app_context():
        repo = NotificationsRepo(db.session)
        svc = NotificationService(session=db.session)

        # Basic repo/service wiring
        companies = db.session.execute(db.text("SELECT id FROM companies ORDER BY id LIMIT 1")).scalar()
        if not companies:
            print("SKIP: no company in database")
            return 0

        company_id = int(companies)
        recipients = repo.list_eligible_students(company_id=company_id, limit=5)
        print(f"eligible_students={len(recipients)}")

        if not recipients:
            print("SKIP: no eligible students to test with")
            return 0

        user_id = recipients[0].user_id
        ok, msg, out = svc.list_notifications(
            company_id=company_id,
            user_id=user_id,
            page=1,
            per_page=5,
        )
        assert ok, msg
        print("list_notifications:", json.dumps(out, indent=2)[:500])

        ok, msg, reg = svc.register_device(
            company_id=company_id,
            user_id=user_id,
            token="test-fcm-token-smoke-001",
            platform="android",
        )
        assert ok, msg
        db.session.commit()
        print("register_device:", reg)

        ok, msg, stats = svc.admin_send(
            company_id=company_id,
            title="API smoke test",
            body="Notification system smoke test message.",
            channels=["in_app", "email"],
            recipient_mode="selected",
            user_ids=[user_id],
            created_by_user_id=None,
        )
        assert ok, msg
        db.session.commit()
        print("admin_send:", stats)

        unread = svc.get_unread_count(company_id=company_id, user_id=user_id)
        print(f"unread_count={unread}")
        assert unread >= 1

        print("OK: notification smoke test passed")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise
