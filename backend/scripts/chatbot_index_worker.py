#!/usr/bin/env python3
"""Background worker that processes chatbot index jobs.

Default: long-running poll loop (systemd-compatible).
  python scripts/chatbot_index_worker.py

One-shot modes (load model, drain jobs, release RAM, exit):
  python scripts/chatbot_index_worker.py --once
  python scripts/chatbot_index_worker.py --until-empty
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def _release_index_resources() -> None:
    try:
        from cmcp.modules.chatbot.rag.embeddings import release_embedding_model
        from cmcp.modules.chatbot.rag.vector_store import release_vector_store

        release_embedding_model()
        release_vector_store()
    except Exception as exc:
        print(f"Resource release warning: {exc}")


def _process_one(app, svc) -> bool:
    """Claim and run one pending job. Returns True if a job was processed."""
    job_id = None
    with app.app_context():
        from cmcp.config.database import db
        from cmcp.modules.chatbot.models import ChatbotIndexJob

        try:
            with db.session.begin():
                job = svc.claim_next_index_job()
                if job:
                    job_id = int(job.id)
        except Exception as exc:
            db.session.rollback()
            print(f"Worker claim error: {exc}")
            return False

        if not job_id:
            return False

        try:
            svc.run_index_job(job_id)
            job = db.session.get(ChatbotIndexJob, job_id)
            if job:
                print(
                    f"Job {job.id} material={job.material_id} "
                    f"status={job.status} attempts={job.attempt_count}"
                )
        except Exception as exc:
            db.session.rollback()
            print(f"Worker index error: {exc}")
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Chatbot material index worker")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once",
        action="store_true",
        help="Process at most one pending job, release resources, and exit.",
    )
    mode.add_argument(
        "--until-empty",
        action="store_true",
        help="Process pending jobs until the queue is empty, then release and exit.",
    )
    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_root / "src"))

    from cmcp.config.settings import settings
    from cmcp import create_app
    from cmcp.modules.chatbot.service import ChatbotService

    app = create_app()
    svc = ChatbotService()
    poll_seconds = settings.CHATBOT_INDEX_WORKER_POLL_SECONDS
    idle_unload_seconds = max(0, int(getattr(settings, "CHATBOT_INDEX_WORKER_IDLE_UNLOAD_SECONDS", 60)))

    if args.once:
        print("Chatbot index worker running once")
        processed = _process_one(app, svc)
        _release_index_resources()
        print("Queue empty" if not processed else "Processed 1 job")
        return 0

    if args.until_empty:
        print("Chatbot index worker draining queue (--until-empty)")
        processed = 0
        while _process_one(app, svc):
            processed += 1
        _release_index_resources()
        print(f"Queue empty after {processed} job(s); worker exiting")
        return 0

    print(f"Chatbot index worker started (poll every {poll_seconds}s)")
    idle_seconds = 0.0
    model_loaded = False

    while True:
        processed = _process_one(app, svc)
        if processed:
            idle_seconds = 0.0
            model_loaded = True
            time.sleep(0.25)
            continue

        if model_loaded and idle_unload_seconds and idle_seconds >= idle_unload_seconds:
            print(f"Queue idle for {int(idle_seconds)}s; releasing index resources")
            _release_index_resources()
            model_loaded = False
            idle_seconds = 0.0

        time.sleep(poll_seconds)
        idle_seconds += poll_seconds


if __name__ == "__main__":
    raise SystemExit(main())
