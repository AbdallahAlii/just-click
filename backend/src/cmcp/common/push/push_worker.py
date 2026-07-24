from __future__ import annotations

import logging
import os
import time

from cmcp.config.database import db
from cmcp.modules.notifications.service import PushNotificationService

log = logging.getLogger(__name__)


def _load_create_app():
    try:
        from cmcp import create_app  # type: ignore
        return create_app
    except Exception:
        pass

    try:
        from cmcp.wsgi import app  # type: ignore
        return lambda: app
    except Exception:
        pass

    raise RuntimeError("Could not import Flask app for notification worker.")


def run_push_worker_forever() -> None:
    create_app = _load_create_app()
    app = create_app()

    batch_size = int(os.getenv("PUSH_OUTBOX_BATCH_SIZE", "50"))
    sleep_seconds = float(os.getenv("PUSH_OUTBOX_POLL_SECONDS", "2"))

    with app.app_context():
        svc = PushNotificationService(session=db.session)
        log.info("Push notification worker started batch_size=%s", batch_size)

        idle_logged = False
        while True:
            try:
                processed = svc.process_batch(batch_size=batch_size)
                if processed == 0:
                    if not idle_logged:
                        configured = PushNotificationService(session=db.session).fcm.is_configured()
                        if configured:
                            log.info("Push worker idle — no pending push notifications.")
                        else:
                            log.warning(
                                "Push worker idle — FIREBASE_SERVER_KEY is not set. "
                                "Push rows will be marked skipped when processed."
                            )
                        idle_logged = True
                    time.sleep(sleep_seconds)
                else:
                    idle_logged = False
                    log.info("Push worker processed %s notification(s)", processed)
            except Exception:
                log.exception("Push worker loop crashed; sleeping 3 seconds")
                try:
                    db.session.rollback()
                except Exception:
                    pass
                time.sleep(3)
