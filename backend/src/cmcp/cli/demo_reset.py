from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from flask.cli import with_appcontext
from sqlalchemy import delete, func, select, update

from cmcp.config.database import db
from cmcp.modules.University.models import Company
from cmcp.modules.academic.models import Course, CourseChapter, CourseOffering
from cmcp.modules.chatbot.models import (
    ChatbotIndexJob,
    ChatbotMaterialIndex,
    ChatMessage,
    ChatSession,
)
from cmcp.modules.materials.models import (
    Material,
    MaterialFeedback,
    MaterialFeedbackReply,
    StudentMaterialInteraction,
)
from cmcp.modules.notifications.models import NotificationBatch, PushOutbox, UserNotification

logger = logging.getLogger(__name__)

DEMO_COMPANY_CODE = "JC"


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _media_root() -> Path:
    from cmcp.config.media_config import settings

    root = Path(settings.LOCAL_MEDIA_ROOT)
    if not root.is_absolute():
        root = _backend_root() / root
    return root


def _preview_demo_reset(*, company_code: str) -> Optional[Dict[str, Any]]:
    company = db.session.scalar(select(Company).where(Company.code == company_code))
    if not company:
        return None

    cid = int(company.id)
    material_ids = list(db.session.scalars(select(Material.id).where(Material.company_id == cid)))
    return {
        "company_id": cid,
        "company_code": company.code,
        "company_name": company.name,
        "materials": len(material_ids),
        "material_ids": material_ids,
        "chapters": int(
            db.session.scalar(select(func.count(CourseChapter.id)).where(CourseChapter.company_id == cid)) or 0
        ),
        "offerings": int(
            db.session.scalar(select(func.count(CourseOffering.id)).where(CourseOffering.company_id == cid)) or 0
        ),
        "courses": int(
            db.session.scalar(select(func.count(Course.id)).where(Course.company_id == cid)) or 0
        ),
        "index_jobs": int(
            db.session.scalar(select(func.count(ChatbotIndexJob.id)).where(ChatbotIndexJob.company_id == cid)) or 0
        ),
        "material_indexes": int(
            db.session.scalar(
                select(func.count(ChatbotMaterialIndex.id)).where(ChatbotMaterialIndex.company_id == cid)
            )
            or 0
        ),
        "chat_sessions": int(
            db.session.scalar(select(func.count(ChatSession.id)).where(ChatSession.company_id == cid)) or 0
        ),
    }


def _delete_material_files(material_ids: List[int]) -> int:
    root = _media_root() / "materials_files"
    removed = 0
    for material_id in material_ids:
        folder = root / str(int(material_id))
        if folder.exists() and folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)
            removed += 1
    return removed


def _delete_company_chroma(company_id: int) -> int:
    try:
        from cmcp.modules.chatbot.rag.vector_store import delete_company_chunks

        return int(delete_company_chunks(int(company_id)) or 0)
    except Exception:
        logger.warning("Chroma cleanup skipped or failed for company_id=%s", company_id, exc_info=True)
        return 0


def run_demo_reset(*, company_code: str) -> Dict[str, Any]:
    preview = _preview_demo_reset(company_code=company_code)
    if not preview:
        raise RuntimeError(f"Demo company with code '{company_code}' was not found.")

    cid = int(preview["company_id"])
    material_ids = [int(x) for x in preview["material_ids"]]

    files_removed = _delete_material_files(material_ids)
    chroma_removed = _delete_company_chroma(cid)

    db.session.execute(delete(ChatbotIndexJob).where(ChatbotIndexJob.company_id == cid))
    db.session.execute(delete(ChatbotMaterialIndex).where(ChatbotMaterialIndex.company_id == cid))
    db.session.execute(delete(ChatMessage).where(ChatMessage.company_id == cid))
    db.session.execute(delete(ChatSession).where(ChatSession.company_id == cid))

    if material_ids:
        db.session.execute(
            delete(PushOutbox).where(
                PushOutbox.company_id == cid,
                PushOutbox.notification_id.in_(
                    select(UserNotification.id).where(
                        UserNotification.company_id == cid,
                        UserNotification.material_id.in_(material_ids),
                    )
                ),
            )
        )
        db.session.execute(
            delete(UserNotification).where(
                UserNotification.company_id == cid,
                UserNotification.material_id.in_(material_ids),
            )
        )
        db.session.execute(
            update(NotificationBatch)
            .where(
                NotificationBatch.company_id == cid,
                NotificationBatch.material_id.in_(material_ids),
            )
            .values(material_id=None)
        )
        db.session.execute(
            delete(MaterialFeedbackReply).where(
                MaterialFeedbackReply.feedback_id.in_(
                    select(MaterialFeedback.id).where(
                        MaterialFeedback.company_id == cid,
                        MaterialFeedback.material_id.in_(material_ids),
                    )
                )
            )
        )
        db.session.execute(
            delete(MaterialFeedback).where(
                MaterialFeedback.company_id == cid,
                MaterialFeedback.material_id.in_(material_ids),
            )
        )
        db.session.execute(
            delete(StudentMaterialInteraction).where(
                StudentMaterialInteraction.company_id == cid,
                StudentMaterialInteraction.material_id.in_(material_ids),
            )
        )

    db.session.execute(delete(Material).where(Material.company_id == cid))
    db.session.execute(delete(CourseChapter).where(CourseChapter.company_id == cid))
    db.session.execute(delete(CourseOffering).where(CourseOffering.company_id == cid))
    db.session.execute(delete(Course).where(Course.company_id == cid))
    db.session.commit()

    preview["files_removed"] = files_removed
    preview["chroma_removed"] = chroma_removed
    return preview


def _print_scope(preview: Dict[str, Any]) -> None:
    click.echo("")
    click.echo("Demo reset scope (Jamhuriya demo tenant only):")
    click.echo(f"  company: {preview['company_name']} (code={preview['company_code']}, id={preview['company_id']})")
    click.echo("  tables / rows:")
    click.echo(f"    chatbot_index_jobs          ({preview['index_jobs']} rows)")
    click.echo(f"    chatbot_material_indexes    ({preview['material_indexes']} rows)")
    click.echo(f"    chatbot_messages            (sessions={preview['chat_sessions']})")
    click.echo("    chatbot_sessions")
    click.echo("    push_outbox                 (material-linked only)")
    click.echo("    user_notifications          (material-linked only)")
    click.echo("    notification_batches        (material_id set NULL)")
    click.echo("    edu_material_feedback_replies")
    click.echo("    edu_material_feedback")
    click.echo("    edu_material_interactions")
    click.echo(f"    edu_materials               ({preview['materials']} rows)")
    click.echo(f"    edu_course_chapters         ({preview['chapters']} rows)")
    click.echo(f"    edu_course_offerings        ({preview['offerings']} rows)")
    click.echo(f"    edu_courses                 ({preview['courses']} rows)")
    click.echo("  directories:")
    click.echo("    LOCAL_MEDIA_ROOT/materials_files/<material_id>/")
    click.echo("    Chroma vectors for this company_id (not embedding model cache)")
    click.echo("  not deleted: users, roles, faculty/dept/semesters/classrooms, email_outbox, other companies")
    click.echo("")


@click.command("demo-reset")
@click.option("--yes", "confirm", is_flag=True, help="Confirm this destructive reset.")
@click.option("--company-code", default=DEMO_COMPANY_CODE, show_default=True)
@with_appcontext
def demo_reset_cli(confirm: bool, company_code: str) -> None:
    """Remove demo-seeded materials and related data so seed all can recreate a small dataset.

    Never runs during deploy. Requires --yes.
    """
    try:
        preview = _preview_demo_reset(company_code=company_code)
        if not preview:
            click.secho(f"No company with code '{company_code}' found. Nothing to reset.", fg="yellow")
            return

        _print_scope(preview)

        if not confirm:
            click.secho("Refusing to run. Re-run with --yes after reviewing the scope.", fg="yellow")
            raise SystemExit(2)

        click.echo("Running demo reset...")
        result = run_demo_reset(company_code=company_code)
        click.secho(
            "Demo reset complete. "
            f"Removed {result['materials']} materials, "
            f"{result['files_removed']} media folders, "
            f"{result['chroma_removed']} chroma ids. "
            "Next: flask --app cmcp seed all",
            fg="green",
        )
    except SystemExit:
        raise
    except Exception as exc:
        db.session.rollback()
        logger.error("Demo reset failed", exc_info=True)
        click.secho(f"Demo reset failed: {exc}", fg="red")
        raise SystemExit(1)
