from __future__ import annotations

import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import Session

from cmcp.common.security.passwords import hash_password
from cmcp.modules.University.models import Company
from cmcp.modules.academic.models import (
    AcademicYear,
    Course,
    CourseChapter,
    CourseOffering,
    Department,
    Faculty,
    Semester,
)
from cmcp.modules.auth.models import (
    LinkedEntityTypeEnum,
    User,
    UserAffiliation,
    UserStatusEnum,
    UserTypeEnum,
)
from cmcp.modules.education_people.models import Classroom, StaffProfile, StudentProfile
from cmcp.modules.media.encrypted_files import file_url_from_key
from cmcp.modules.media.service import save_file_for
from cmcp.modules.media.utils import MediaFolder
from cmcp.modules.materials.models import Material, MaterialTypeEnum
from cmcp.modules.rbac.models import Role, UserRole
from cmcp.seed_data.university.data import UNIVERSITIES

logger = logging.getLogger(__name__)


def _get_or_create(
    db: Session,
    model,
    *,
    defaults: Optional[dict] = None,
    **filters,
) -> Tuple[object, bool]:
    obj = db.scalar(select(model).filter_by(**filters))
    if obj:
        return obj, False

    obj = model(**{**filters, **(defaults or {})})
    db.add(obj)
    db.flush([obj])
    return obj, True


def _sync_attrs(db: Session, obj: object, attrs: Dict[str, Any]) -> bool:
    changed = False
    for field, value in attrs.items():
        if not hasattr(obj, field):
            continue
        if getattr(obj, field) != value:
            setattr(obj, field, value)
            changed = True
    if changed:
        db.flush([obj])
    return changed


def _model_columns(model) -> set[str]:
    return {c.key for c in sa_inspect(model).columns}


def _only_model_columns(model, attrs: Dict[str, Any]) -> Dict[str, Any]:
    cols = _model_columns(model)
    return {k: v for k, v in attrs.items() if k in cols}


def _safe_hash(plain: str) -> str:
    return hash_password(plain)


def _user_type_from_str(value: str) -> UserTypeEnum:
    normalized = (value or "").strip().lower()
    if normalized == "admin":
        return UserTypeEnum.ADMIN
    if normalized == "staff":
        return UserTypeEnum.STAFF
    if normalized == "teacher":
        return UserTypeEnum.TEACHER
    return UserTypeEnum.STUDENT


def _material_type_from_str(value: str) -> MaterialTypeEnum:
    normalized = (value or "").strip().lower()
    for item in MaterialTypeEnum:
        if item.value == normalized:
            return item
    return MaterialTypeEnum.SLIDES


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _mock_files_dir(material_spec: Dict[str, Any]) -> Path:
    configured = Path(str(material_spec.get("mock_files_dir") or "mock_files"))
    if configured.is_absolute():
        return configured

    candidates = [
        _backend_root() / configured,
        Path.cwd() / configured,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _pick_mock_file(material_spec: Dict[str, Any], *, file_group: str, seed: str) -> Path:
    names = [str(x) for x in material_spec.get(file_group, []) if str(x).strip()]
    if not names:
        raise RuntimeError(f"No seed mock files configured for '{file_group}'.")

    base_dir = _mock_files_dir(material_spec)
    start = sum(ord(ch) for ch in seed) % len(names)
    ordered = names[start:] + names[:start]

    for name in ordered:
        candidate = base_dir / name
        if candidate.exists() and candidate.is_file():
            return candidate

    raise RuntimeError(f"None of the configured seed files for '{file_group}' exist in {base_dir}.")


def _extract_media_file_key(file_url: Optional[str]) -> Optional[str]:
    if not file_url:
        return None
    marker = "/api/media/file/"
    if marker not in file_url:
        return None
    return file_url.split(marker, 1)[1]


def _file_size_mb(path: Path) -> float:
    return round(path.stat().st_size / (1024 * 1024), 4)


def _ensure_role(db: Session, name: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == name))
    if not role:
        raise RuntimeError(f"Role '{name}' not found. Run RBAC seeding before university seeding.")
    return role


def _ensure_user_role(db: Session, *, company_id: int, user_id: int, role_name: str) -> None:
    role = _ensure_role(db, role_name)
    user_role, _ = _get_or_create(
        db,
        UserRole,
        company_id=int(company_id),
        user_id=int(user_id),
        role_id=int(role.id),
        defaults={"is_enabled": True},
    )
    _sync_attrs(db, user_role, {"is_enabled": True})


def _user_email(username: str, spec: Dict[str, Any], domain: str = "jamhuriya.edu") -> str:
    return str(spec.get("email") or f"{username}@{domain}").strip().lower()


def _active_user_attrs(now: datetime, *, approved_by: Optional[int] = None) -> Dict[str, Any]:
    attrs: Dict[str, Any] = {
        "status": UserStatusEnum.ACTIVE,
        "is_enabled": True,
        "email_verified_at": now,
        "approved_at": now,
        "must_change_password": False,
        "email_verify_token_hash": None,
        "email_verify_expires_at": None,
        "temp_password_expires_at": None,
        "rejected_at": None,
        "rejected_by": None,
        "rejection_reason": None,
    }
    if approved_by is not None:
        attrs["approved_by"] = int(approved_by)
    return attrs


def _ensure_user(
    db: Session,
    *,
    spec: Dict[str, Any],
    fallback_domain: str,
    now: datetime,
    approved_by: Optional[int] = None,
) -> User:
    username = str(spec["username"]).strip()
    desired_type = _user_type_from_str(spec.get("user_type", "STUDENT"))

    defaults = _only_model_columns(
        User,
        {
            "email": _user_email(username, spec, fallback_domain),
            "password_hash": _safe_hash(str(spec["password"])),
            "user_type": desired_type,
            "is_system_owner": False,
            **_active_user_attrs(now, approved_by=approved_by),
        },
    )

    user, created = _get_or_create(db, User, username=username, defaults=defaults)
    _sync_attrs(
        db,
        user,
        _only_model_columns(
            User,
            {
                "email": _user_email(username, spec, fallback_domain),
                "user_type": desired_type,
                "is_system_owner": False,
                **_active_user_attrs(now, approved_by=approved_by),
            },
        ),
    )
    logger.info("%s user: %s", "Created" if created else "Ensured", username)
    return user


def _ensure_affiliation(
    db: Session,
    *,
    user_id: int,
    company_id: int,
    is_company_owner: bool,
    linked_entity_type: Optional[LinkedEntityTypeEnum] = None,
    linked_entity_id: Optional[int] = None,
) -> UserAffiliation:
    aff, created = _get_or_create(
        db,
        UserAffiliation,
        user_id=int(user_id),
        company_id=int(company_id),
        defaults={
            "is_primary": True,
            "is_enabled": True,
            "is_company_owner": bool(is_company_owner),
            "linked_entity_type": linked_entity_type,
            "linked_entity_id": int(linked_entity_id) if linked_entity_id is not None else None,
        },
    )
    _sync_attrs(
        db,
        aff,
        {
            "is_primary": True,
            "is_enabled": True,
            "is_company_owner": bool(is_company_owner),
            "linked_entity_type": linked_entity_type,
            "linked_entity_id": int(linked_entity_id) if linked_entity_id is not None else None,
        },
    )
    logger.info("%s affiliation user=%s company=%s", "Created" if created else "Ensured", user_id, company_id)
    return aff


def _ensure_company(db: Session, spec: Dict[str, Any]) -> Company:
    code = (spec.get("code") or "").strip() or None
    stmt = select(Company).where(Company.code == code) if code else select(Company).where(Company.name == spec["name"].strip())
    company = db.scalar(stmt)

    attrs = {
        "name": spec["name"].strip(),
        "code": code,
        "contact_email": spec.get("contact_email"),
        "contact_phone": spec.get("contact_phone"),
        "country": spec.get("country"),
        "city": spec.get("city"),
        "timezone": spec.get("timezone"),
        "is_enabled": bool(spec.get("is_enabled", True)),
    }

    if not company:
        company = Company(**attrs)
        db.add(company)
        db.flush([company])
        logger.info("Created company: %s (%s)", company.name, company.code)
    else:
        _sync_attrs(db, company, attrs)
        logger.info("Ensured company: %s (%s)", company.name, company.code)

    return company


def _ensure_faculty(db: Session, *, company_id: int, spec: Dict[str, Any]) -> Faculty:
    code = (spec.get("code") or "").strip() or None
    faculty = None
    if code:
        faculty = db.scalar(select(Faculty).where(Faculty.company_id == company_id, Faculty.code == code))
    if not faculty:
        faculty = db.scalar(select(Faculty).where(Faculty.company_id == company_id, Faculty.name == spec["name"].strip()))

    attrs = {"name": spec["name"].strip(), "code": code, "is_enabled": bool(spec.get("is_enabled", True))}
    if not faculty:
        faculty = Faculty(company_id=company_id, **attrs)
        db.add(faculty)
        db.flush([faculty])
        logger.info("Created faculty: %s", faculty.name)
    else:
        _sync_attrs(db, faculty, attrs)
        logger.info("Ensured faculty: %s", faculty.name)
    return faculty


def _ensure_departments(
    db: Session,
    *,
    company_id: int,
    faculty: Faculty,
    specs: Iterable[Dict[str, Any]],
) -> Dict[str, Department]:
    by_code: Dict[str, Department] = {}
    for spec in specs:
        code = (spec.get("code") or "").strip() or None
        dept = None
        if code:
            dept = db.scalar(select(Department).where(Department.company_id == company_id, Department.code == code))
        if not dept:
            dept = db.scalar(
                select(Department).where(
                    Department.company_id == company_id,
                    Department.faculty_id == int(faculty.id),
                    Department.name == spec["name"].strip(),
                )
            )

        attrs = {
            "faculty_id": int(faculty.id),
            "name": spec["name"].strip(),
            "code": code,
            "is_enabled": bool(spec.get("is_enabled", True)),
        }
        if not dept:
            dept = Department(company_id=company_id, **attrs)
            db.add(dept)
            db.flush([dept])
            logger.info("Created department: %s (%s)", dept.name, dept.code)
        else:
            _sync_attrs(db, dept, attrs)
            logger.info("Ensured department: %s (%s)", dept.name, dept.code)
        if code:
            by_code[code] = dept
    return by_code


def _ensure_academic_year(db: Session, *, company_id: int, spec: Dict[str, Any]) -> AcademicYear:
    year, created = _get_or_create(
        db,
        AcademicYear,
        company_id=company_id,
        name=spec["name"].strip(),
        defaults={"is_enabled": bool(spec.get("is_enabled", True))},
    )
    _sync_attrs(db, year, {"is_enabled": bool(spec.get("is_enabled", True))})
    logger.info("%s academic year: %s", "Created" if created else "Ensured", year.name)
    return year


def _ensure_semesters(
    db: Session,
    *,
    company_id: int,
    academic_year: AcademicYear,
    specs: Iterable[Dict[str, Any]],
) -> Dict[int, Semester]:
    by_number: Dict[int, Semester] = {}
    for spec in specs:
        number = int(spec["number"])
        semester, created = _get_or_create(
            db,
            Semester,
            company_id=company_id,
            academic_year_id=int(academic_year.id),
            number=number,
            defaults={
                "name": (spec.get("name") or f"Semester {number}").strip(),
                "is_enabled": bool(spec.get("is_enabled", True)),
            },
        )
        _sync_attrs(
            db,
            semester,
            {
                "name": (spec.get("name") or f"Semester {number}").strip(),
                "is_enabled": bool(spec.get("is_enabled", True)),
            },
        )
        by_number[number] = semester
        logger.info("%s semester: %s", "Created" if created else "Ensured", semester.name)
    return by_number


def _ensure_classrooms(
    db: Session,
    *,
    company_id: int,
    specs: Iterable[Dict[str, Any]],
) -> Dict[str, Classroom]:
    by_name: Dict[str, Classroom] = {}
    for spec in specs:
        name = str(spec["name"]).strip()
        classroom, created = _get_or_create(
            db,
            Classroom,
            company_id=company_id,
            name=name,
            defaults={
                "room_number": spec.get("room_number"),
                "is_enabled": bool(spec.get("is_enabled", True)),
            },
        )
        _sync_attrs(
            db,
            classroom,
            {
                "room_number": spec.get("room_number"),
                "is_enabled": bool(spec.get("is_enabled", True)),
            },
        )
        by_name[name] = classroom
        logger.info("%s classroom: %s", "Created" if created else "Ensured", name)
    return by_name


def _ensure_course(db: Session, *, company_id: int, spec: Dict[str, Any]) -> Course:
    code = (spec.get("code") or "").strip() or None
    course = None
    if code:
        course = db.scalar(select(Course).where(Course.company_id == company_id, Course.code == code))
    if not course:
        course = db.scalar(select(Course).where(Course.company_id == company_id, Course.title == spec["title"].strip()))

    attrs = {
        "title": spec["title"].strip(),
        "code": code,
        "description": (spec.get("description") or "").strip() or None,
        "is_enabled": bool(spec.get("is_enabled", True)),
    }
    if not course:
        course = Course(company_id=company_id, **attrs)
        db.add(course)
        db.flush([course])
        logger.info("Created course: %s (%s)", course.title, course.code)
    else:
        _sync_attrs(db, course, attrs)
        logger.info("Ensured course: %s (%s)", course.title, course.code)
    return course


def _ensure_offering(
    db: Session,
    *,
    company_id: int,
    course: Course,
    department: Department,
    semester: Semester,
    spec: Dict[str, Any],
) -> CourseOffering:
    offering, created = _get_or_create(
        db,
        CourseOffering,
        company_id=company_id,
        course_id=int(course.id),
        department_id=int(department.id),
        semester_id=int(semester.id),
        defaults={
            "custom_title": spec.get("custom_title"),
            "credit_hours": int(spec.get("credit_hours", 3)),
            "is_enabled": bool(spec.get("is_enabled", True)),
        },
    )
    _sync_attrs(
        db,
        offering,
        {
            "custom_title": spec.get("custom_title"),
            "credit_hours": int(spec.get("credit_hours", 3)),
            "is_enabled": bool(spec.get("is_enabled", True)),
        },
    )
    logger.info("%s offering: %s / %s", "Created" if created else "Ensured", course.code, semester.name)
    return offering


def _ensure_chapters(
    db: Session,
    *,
    company_id: int,
    offering: CourseOffering,
    course: Course,
    chapters: Iterable[Dict[str, Any]],
) -> Dict[int, CourseChapter]:
    by_number: Dict[int, CourseChapter] = {}
    for idx, spec in enumerate(chapters, start=1):
        number = int(spec.get("number") or idx)
        chapter, created = _get_or_create(
            db,
            CourseChapter,
            company_id=company_id,
            course_offering_id=int(offering.id),
            number=number,
            defaults={
                "title": str(spec["title"]).strip(),
                "description": spec.get("description"),
                "is_enabled": bool(spec.get("is_enabled", True)),
            },
        )
        _sync_attrs(
            db,
            chapter,
            {
                "title": str(spec["title"]).strip(),
                "description": spec.get("description"),
                "is_enabled": bool(spec.get("is_enabled", True)),
            },
        )
        by_number[number] = chapter
        logger.info("%s chapter %s for %s", "Created" if created else "Ensured", number, course.code)
    return by_number


def _ensure_material(
    db: Session,
    *,
    company_id: int,
    offering: CourseOffering,
    title: str,
    material_type: MaterialTypeEnum,
    source_file: Optional[Path] = None,
    file_url: Optional[str] = None,
    chapter: Optional[CourseChapter] = None,
    description: Optional[str] = None,
    learning_objectives: Optional[list[str]] = None,
    page_count: Optional[int] = None,
    slide_count: Optional[int] = None,
    file_size_mb: Optional[float] = None,
    is_downloadable: bool = True,
) -> Material:
    if material_type == MaterialTypeEnum.PDF and page_count is None:
        page_count = 12
    if material_type == MaterialTypeEnum.DOC and page_count is None:
        page_count = 8
    if material_type == MaterialTypeEnum.SLIDES and slide_count is None:
        slide_count = 24
    if source_file is not None and file_size_mb is None:
        file_size_mb = _file_size_mb(source_file)
    if material_type == MaterialTypeEnum.LINK:
        page_count = None
        slide_count = None
        file_size_mb = None
        is_downloadable = False

    material, created = _get_or_create(
        db,
        Material,
        company_id=company_id,
        course_offering_id=int(offering.id),
        chapter_id=int(chapter.id) if chapter else None,
        title=title,
        defaults={
            "material_type": material_type,
            "file_url": file_url,
            "page_count": page_count,
            "slide_count": slide_count,
            "file_size_mb": file_size_mb,
            "learning_objectives": learning_objectives,
            "description": description,
            "is_downloadable": is_downloadable,
            "is_enabled": True,
            "view_count": 0,
            "download_count": 0,
        },
    )
    _sync_attrs(
        db,
        material,
        {
            "material_type": material_type,
            "page_count": page_count,
            "slide_count": slide_count,
            "file_size_mb": file_size_mb,
            "learning_objectives": learning_objectives,
            "description": description,
            "is_downloadable": is_downloadable,
            "is_enabled": True,
        },
    )

    if material_type == MaterialTypeEnum.LINK:
        if not file_url:
            raise RuntimeError(f"LINK material requires file_url: {title}")
        _sync_attrs(db, material, {"file_url": file_url})
        logger.info("%s material: %s", "Created" if created else "Ensured", title)
        return material

    if source_file is None:
        raise RuntimeError(f"File-backed material requires source_file: {title}")

    # Idempotent re-seed: skip re-upload when the material already has a stored file.
    if not created and material.file_url:
        logger.info("Ensured material (file kept): %s", title)
        return material

    content_type, _ = mimetypes.guess_type(str(source_file))
    new_key = save_file_for(
        folder=MediaFolder.MATERIALS,
        item_id=int(material.id),
        bytes_=source_file.read_bytes(),
        filename=source_file.name,
        content_type=content_type or "application/octet-stream",
        old_file_key=_extract_media_file_key(material.file_url),
    )
    if not new_key:
        raise RuntimeError(f"Failed to store mock material file: {source_file}")

    desired_file_url = file_url_from_key(new_key)
    _sync_attrs(db, material, {"file_url": desired_file_url})

    logger.info("%s material: %s", "Created" if created else "Ensured", title)
    return material


def _chapter_material_plan(material_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Deterministic ~15 materials/chapter mix:
    slides, pdf, doc, video, link (no IMAGE/AUDIO/ZIP).
    """
    target = int(material_spec.get("materials_per_chapter") or 15)
    links = list(material_spec.get("link_resources") or [])
    # First slides title matches legacy seed ("Chapter N Slides") for idempotency.
    plan: List[Dict[str, Any]] = [
        {"kind": "slides", "title": "Slides", "slot": 0, "legacy_title": True},
        {"kind": "pdf", "title": "Reading Notes (PDF)", "slot": 0},
        {"kind": "doc", "title": "Study Guide", "slot": 0},
        {"kind": "video", "title": "Lecture Recording", "slot": 0},
        {"kind": "link", "title": None, "slot": 0},
        {"kind": "slides", "title": "Worked Examples Slides", "slot": 1},
        {"kind": "pdf", "title": "Supplementary Notes", "slot": 1},
        {"kind": "doc", "title": "Practice Worksheet", "slot": 1},
        {"kind": "video", "title": "Lab Walkthrough Video", "slot": 1},
        {"kind": "link", "title": None, "slot": 1},
        {"kind": "slides", "title": "Review Slides", "slot": 2},
        {"kind": "pdf", "title": "Reference Handout", "slot": 2},
        {"kind": "doc", "title": "Quiz Prep Document", "slot": 2},
        {"kind": "link", "title": None, "slot": 2},
        {"kind": "slides", "title": "Summary Slides", "slot": 3},
    ]
    # Ensure link slots map to configured resources
    link_i = 0
    for item in plan:
        if item["kind"] == "link":
            resource = links[link_i % len(links)] if links else None
            item["link"] = resource
            link_i += 1
    return plan[: max(1, target)]


def _seed_materials_for_course(
    db: Session,
    *,
    company_id: int,
    offering: CourseOffering,
    course: Course,
    chapters: Dict[int, CourseChapter],
    material_spec: Dict[str, Any],
) -> None:
    course_code = str(course.code or course.id).lower()

    if material_spec.get("include_course_syllabus", True):
        pdf_file = _pick_mock_file(
            material_spec,
            file_group="pdf_files",
            seed=f"{course_code}-syllabus",
        )
        _ensure_material(
            db,
            company_id=company_id,
            offering=offering,
            title="Course Syllabus",
            material_type=MaterialTypeEnum.PDF,
            source_file=pdf_file,
            description=f"Syllabus, weekly plan, grading policy, and references for {course.title}.",
            learning_objectives=["Understand course expectations", "Plan weekly study work"],
        )

    if not material_spec.get("include_chapter_slides", True):
        return

    plan = _chapter_material_plan(material_spec)
    file_group_by_kind = {
        "slides": "slide_files",
        "pdf": "pdf_files",
        "doc": "doc_files",
        "video": "video_files",
    }
    type_by_kind = {
        "slides": MaterialTypeEnum.SLIDES,
        "pdf": MaterialTypeEnum.PDF,
        "doc": MaterialTypeEnum.DOC,
        "video": MaterialTypeEnum.VIDEO,
        "link": MaterialTypeEnum.LINK,
    }

    for number, chapter in sorted(chapters.items()):
        for item in plan:
            kind = item["kind"]
            slot = int(item.get("slot") or 0)
            seed = f"{course_code}-chapter-{number}-{kind}-{slot}-{item.get('title') or 'link'}"

            if kind == "link":
                link = item.get("link") or {}
                if not link:
                    continue
                suffix = str(link.get("title_suffix") or "External Resource")
                title = f"Chapter {number} — {suffix}"
                _ensure_material(
                    db,
                    company_id=company_id,
                    offering=offering,
                    chapter=chapter,
                    title=title,
                    material_type=MaterialTypeEnum.LINK,
                    file_url=str(link["url"]),
                    description=str(
                        link.get("description")
                        or f"External learning resource for {chapter.title}."
                    ),
                    learning_objectives=[
                        f"Explore external references for {chapter.title.lower()}",
                        "Connect course concepts to reputable documentation",
                    ],
                    is_downloadable=False,
                )
                continue

            source = _pick_mock_file(
                material_spec,
                file_group=file_group_by_kind[kind],
                seed=seed,
            )
            if item.get("legacy_title"):
                title = f"Chapter {number} Slides"
            else:
                title = f"Chapter {number} — {item['title']}"
            _ensure_material(
                db,
                company_id=company_id,
                offering=offering,
                chapter=chapter,
                title=title,
                material_type=type_by_kind[kind],
                source_file=source,
                description=f"{chapter.title}: {item['title']} for {course.title}.",
                learning_objectives=[
                    f"Explain {chapter.title.lower()}",
                    "Apply the concept in practical exercises",
                ],
            )


def _resolve_faculty(profile: Dict[str, Any], faculty_by_code: Dict[str, Faculty]) -> Faculty:
    code = str(profile.get("faculty_code") or "").strip()
    faculty = faculty_by_code.get(code)
    if not faculty:
        raise RuntimeError(f"Faculty code '{code}' was not seeded.")
    return faculty


def _resolve_department(profile: Dict[str, Any], dept_by_code: Dict[str, Department]) -> Department:
    code = str(profile.get("department_code") or "").strip()
    dept = dept_by_code.get(code)
    if not dept:
        raise RuntimeError(f"Department code '{code}' was not seeded.")
    return dept


def _resolve_semester(profile: Dict[str, Any], sem_by_number: Dict[int, Semester]) -> Optional[Semester]:
    if profile.get("semester_number") is None:
        return None
    number = int(profile["semester_number"])
    semester = sem_by_number.get(number)
    if not semester:
        raise RuntimeError(f"Semester number '{number}' was not seeded.")
    return semester


def _resolve_classroom(
    profile: Dict[str, Any],
    classroom_by_name: Dict[str, Classroom],
) -> Optional[Classroom]:
    name = profile.get("classroom_name")
    if not name:
        return None
    classroom = classroom_by_name.get(str(name).strip())
    if not classroom:
        raise RuntimeError(f"Classroom '{name}' was not seeded.")
    return classroom


def _ensure_admin_profile(
    db: Session,
    *,
    company_id: int,
    user: User,
    spec: Dict[str, Any],
    faculty_by_code: Dict[str, Faculty],
    dept_by_code: Dict[str, Department],
) -> StaffProfile:
    profile_spec = spec.get("profile") or {}
    faculty = _resolve_faculty(profile_spec, faculty_by_code)
    department = _resolve_department(profile_spec, dept_by_code)
    profile, created = _get_or_create(
        db,
        StaffProfile,
        company_id=company_id,
        user_id=int(user.id),
        defaults={
            "full_name": str(profile_spec.get("full_name") or spec["username"]).strip(),
            "staff_id": profile_spec.get("staff_id"),
            "faculty_id": int(faculty.id),
            "department_id": int(department.id),
            "is_enabled": bool(profile_spec.get("is_enabled", True)),
        },
    )
    _sync_attrs(
        db,
        profile,
        {
            "full_name": str(profile_spec.get("full_name") or spec["username"]).strip(),
            "staff_id": profile_spec.get("staff_id"),
            "faculty_id": int(faculty.id),
            "department_id": int(department.id),
            "is_enabled": bool(profile_spec.get("is_enabled", True)),
        },
    )
    logger.info("%s admin staff profile: %s", "Created" if created else "Ensured", profile.full_name)
    return profile


def _ensure_student_profile(
    db: Session,
    *,
    company_id: int,
    user: User,
    spec: Dict[str, Any],
    faculty_by_code: Dict[str, Faculty],
    dept_by_code: Dict[str, Department],
    sem_by_number: Dict[int, Semester],
    classroom_by_name: Dict[str, Classroom],
) -> StudentProfile:
    profile_spec = spec.get("profile") or {}
    faculty = _resolve_faculty(profile_spec, faculty_by_code)
    department = _resolve_department(profile_spec, dept_by_code)
    semester = _resolve_semester(profile_spec, sem_by_number)
    classroom = _resolve_classroom(profile_spec, classroom_by_name)

    profile, created = _get_or_create(
        db,
        StudentProfile,
        company_id=company_id,
        user_id=int(user.id),
        defaults={
            "full_name": str(profile_spec["full_name"]).strip(),
            "student_id": str(profile_spec["student_id"]).strip(),
            "faculty_id": int(faculty.id),
            "department_id": int(department.id),
            "classroom_id": int(classroom.id) if classroom else profile_spec.get("classroom_id"),
            "semester_id": int(semester.id) if semester else None,
            "is_enabled": bool(profile_spec.get("is_enabled", True)),
        },
    )
    _sync_attrs(
        db,
        profile,
        {
            "full_name": str(profile_spec["full_name"]).strip(),
            "student_id": str(profile_spec["student_id"]).strip(),
            "faculty_id": int(faculty.id),
            "department_id": int(department.id),
            "classroom_id": int(classroom.id) if classroom else profile_spec.get("classroom_id"),
            "semester_id": int(semester.id) if semester else None,
            "is_enabled": bool(profile_spec.get("is_enabled", True)),
        },
    )
    logger.info("%s student profile: %s", "Created" if created else "Ensured", profile.student_id)
    return profile


def _student_specs(spec: Dict[str, Any]) -> list[Dict[str, Any]]:
    students: list[Dict[str, Any]] = []
    if spec.get("student_user"):
        students.append(spec["student_user"])
    students.extend(spec.get("student_users") or [])
    return students


def _seed_one_university(db: Session, spec: Dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    company = _ensure_company(db, spec["company"])
    company_id = int(company.id)
    domain = "jamhuriya.edu"

    academic = spec["academic"]
    faculty = _ensure_faculty(db, company_id=company_id, spec=academic["faculty"])
    faculty_by_code = {str(faculty.code): faculty}
    dept_by_code = _ensure_departments(
        db,
        company_id=company_id,
        faculty=faculty,
        specs=academic.get("departments", []),
    )
    year = _ensure_academic_year(db, company_id=company_id, spec=academic["academic_year"])
    sem_by_number = _ensure_semesters(
        db,
        company_id=company_id,
        academic_year=year,
        specs=academic.get("semesters", []),
    )
    classroom_by_name = _ensure_classrooms(
        db,
        company_id=company_id,
        specs=academic.get("classrooms", []),
    )

    admin_user = _ensure_user(
        db,
        spec=spec["super_admin_user"],
        fallback_domain=domain,
        now=now,
    )
    _sync_attrs(db, admin_user, _only_model_columns(User, {"approved_by": int(admin_user.id)}))
    admin_profile = _ensure_admin_profile(
        db,
        company_id=company_id,
        user=admin_user,
        spec=spec["super_admin_user"],
        faculty_by_code=faculty_by_code,
        dept_by_code=dept_by_code,
    )
    _ensure_affiliation(
        db,
        user_id=int(admin_user.id),
        company_id=company_id,
        is_company_owner=True,
        linked_entity_type=LinkedEntityTypeEnum.STAFF_PROFILE,
        linked_entity_id=int(admin_profile.id),
    )
    _ensure_user_role(db, company_id=company_id, user_id=int(admin_user.id), role_name="Super Admin")

    chapters_template = academic.get("chapters_per_course", [])
    material_spec = academic.get("materials", {})
    for course_spec in academic.get("courses", []):
        semester = sem_by_number.get(int(course_spec["semester_number"]))
        if not semester:
            raise RuntimeError(f"Semester {course_spec['semester_number']} was not seeded.")

        dept_code = str(course_spec["department_code"]).strip()
        department = dept_by_code.get(dept_code)
        if not department:
            raise RuntimeError(f"Department code '{dept_code}' was not seeded.")

        course = _ensure_course(db, company_id=company_id, spec=course_spec)
        offering = _ensure_offering(
            db,
            company_id=company_id,
            course=course,
            department=department,
            semester=semester,
            spec=course_spec,
        )
        chapters = _ensure_chapters(
            db,
            company_id=company_id,
            offering=offering,
            course=course,
            chapters=course_spec.get("chapters") or chapters_template,
        )
        _seed_materials_for_course(
            db,
            company_id=company_id,
            offering=offering,
            course=course,
            chapters=chapters,
            material_spec=material_spec,
        )

    for student_spec in _student_specs(spec):
        student_user = _ensure_user(
            db,
            spec=student_spec,
            fallback_domain=domain,
            now=now,
            approved_by=int(admin_user.id),
        )
        student_profile = _ensure_student_profile(
            db,
            company_id=company_id,
            user=student_user,
            spec=student_spec,
            faculty_by_code=faculty_by_code,
            dept_by_code=dept_by_code,
            sem_by_number=sem_by_number,
            classroom_by_name=classroom_by_name,
        )
        _ensure_affiliation(
            db,
            user_id=int(student_user.id),
            company_id=company_id,
            is_company_owner=False,
            linked_entity_type=LinkedEntityTypeEnum.STUDENT_PROFILE,
            linked_entity_id=int(student_profile.id),
        )
        _ensure_user_role(db, company_id=company_id, user_id=int(student_user.id), role_name="Student")

    logger.info("University demo data ensured for company=%s", company_id)


def seed_university(db: Session) -> None:
    logger.info("Seeding UNIVERSITY demo data...")
    for spec in UNIVERSITIES:
        _seed_one_university(db, spec)
    logger.info("University demo seeding complete.")
