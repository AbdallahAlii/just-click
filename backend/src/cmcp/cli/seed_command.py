from __future__ import annotations

import logging

import click
from flask.cli import with_appcontext

from cmcp.config.database import db
from cmcp.seed_data.rbac.seeder import seed_rbac

logger = logging.getLogger(__name__)


@click.group(name="seed")
def seed_cli() -> None:
    """Database seeding commands."""
    pass


def _seed_jamhuriya_stack() -> None:
    """Seed the full demo stack in dependency order."""
    click.echo("🌱 Seeding CORE...")
    from cmcp.seed_data.core.seeder import seed_core
    seed_core(db.session)

    click.echo("🔐 Seeding RBAC...")
    seed_rbac(db.session)

    click.echo("🏫 Seeding JAMHURIYA UNIVERSITY demo...")
    from cmcp.seed_data.university.seeder import seed_university
    seed_university(db.session)


def _run_jamhuriya_command(*, start_message: str, success_message: str) -> None:
    try:
        click.echo(start_message)
        _seed_jamhuriya_stack()
        db.session.commit()
        click.secho(success_message, fg="green")

    except Exception as e:
        db.session.rollback()
        logger.error("Jamhuriya demo seeding failed", exc_info=True)
        click.secho(f"❌ Jamhuriya demo seeding failed: {e}", fg="red")
        raise SystemExit(1)


@seed_cli.command("all")
@with_appcontext
def seed_all() -> None:
    """Seed core, RBAC, and the full Jamhuriya University demo data."""
    try:
        click.echo("🚀 Starting full database seeding...")

        _seed_jamhuriya_stack()

        db.session.commit()
        click.secho("✅ All data seeded successfully!", fg="green")
        from sqlalchemy import func, select
        from cmcp.modules.materials.models import Material
        total = int(db.session.scalar(select(func.count()).select_from(Material)) or 0)
        click.echo(f"edu_materials count: {total}")

    except Exception as e:
        db.session.rollback()
        logger.error("Seeding failed", exc_info=True)
        click.secho(f"❌ Seeding failed: {e}", fg="red")
        raise SystemExit(1)


@seed_cli.command("rbac")
@with_appcontext
def seed_rbac_only() -> None:
    """Seed RBAC (DocTypes, Actions, Permissions, Roles, RolePermissions)."""
    try:

        click.echo("🔐 Seeding RBAC...")
        seed_rbac(db.session)
        db.session.commit()
        click.secho("✅ RBAC seeded successfully!", fg="green")

    except Exception as e:
        db.session.rollback()
        logger.error("RBAC seeding failed", exc_info=True)
        click.secho(f"❌ RBAC seeding failed: {e}", fg="red")
        raise SystemExit(1)


@seed_cli.command("core")
@with_appcontext
def seed_core_only() -> None:
    """Seed CORE system data (system owner users)."""
    try:
        click.echo("🌱 Seeding core system data...")

        from cmcp.seed_data.core.seeder import seed_core
        seed_core(db.session)

        db.session.commit()
        click.secho("✅ Core data seeded successfully!", fg="green")

    except Exception as e:
        db.session.rollback()
        logger.error("Core seeding failed", exc_info=True)
        click.secho(f"❌ Error seeding core data: {e}", fg="red")
        raise SystemExit(1)


@seed_cli.command("university")
@with_appcontext
def seed_university_only() -> None:
    """Seed the full Jamhuriya University demo stack."""
    _run_jamhuriya_command(
        start_message="🏫 Seeding Jamhuriya University demo data...",
        success_message="✅ Jamhuriya University demo seeded successfully!",
    )


@seed_cli.command("jamhuriya")
@with_appcontext
def seed_jamhuriya_only() -> None:
    """Alias for seed university."""
    _run_jamhuriya_command(
        start_message="🏫 Seeding Jamhuriya University demo data...",
        success_message="✅ Jamhuriya University demo seeded successfully!",
    )


@seed_cli.command("academic")
@with_appcontext
def seed_academic_demo_only() -> None:
    """Alias for the academic demo inside the Jamhuriya University stack."""
    _run_jamhuriya_command(
        start_message="📚 Seeding Jamhuriya academic demo data...",
        success_message="✅ Jamhuriya academic demo seeded successfully!",
    )


# education_people
@seed_cli.command("education_people")
@with_appcontext
def seed_people_only() -> None:
    """Legacy people-only seeder. Prefer `flask seed all` for the full demo."""
    try:
        click.echo("👥 Seeding PEOPLE...")
        from cmcp.seed_data.people.seeder import seed_people
        seed_people(db.session)

        db.session.commit()
        click.secho("✅ People seeded successfully!", fg="green")

    except Exception as e:
        db.session.rollback()
        logger.error("People seeding failed", exc_info=True)
        click.secho(f"❌ People seeding failed: {e}", fg="red")
        raise SystemExit(1)
