# modules/materials/models.py
from __future__ import annotations

from typing import Optional
import enum

from sqlalchemy import UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from cmcp.config.database import db
from cmcp.common.models.base import BaseModel, TenantMixin


class MaterialTypeEnum(str, enum.Enum):
    SLIDES = "slides"
    PDF = "pdf"
    DOC = "doc"
    VIDEO = "video"
    LINK = "link"
    OTHER = "other"


def _enum_values(enum_cls):
    return [item.value for item in enum_cls]


class Material(BaseModel, TenantMixin):
    """
    A learning material (PDF, slides, video, etc.) uploaded by a lecturer.

    Scoping logic:
      - course_offering_id (required): which specific offering this belongs to.
        e.g. "Math 101 — Computer Apps dept — Semester 1 / 2025-2026"

      - chapter_id (optional): if the material belongs to a specific chapter
        inside that offering, set this. If the material is general for the
        whole offering (not chapter-specific), leave it NULL.

    Examples:
      - A course syllabus PDF   → chapter_id = NULL  (belongs to whole offering)
      - Chapter 3 lecture slides → chapter_id = <id of Chapter 3>
      - A reference video        → chapter_id = NULL  (general resource)
    """
    __tablename__ = "edu_materials"

    # Required: which offering this material belongs to
    course_offering_id: Mapped[int] = mapped_column(
        db.BigInteger,
        db.ForeignKey("edu_course_offerings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Optional: narrows the material down to a specific chapter of that offering
    chapter_id: Mapped[Optional[int]] = mapped_column(
        db.BigInteger,
        db.ForeignKey("edu_course_chapters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(db.String(200), nullable=False, index=True)

    material_type: Mapped[MaterialTypeEnum] = mapped_column(
        db.Enum(MaterialTypeEnum, name="edu_material_type_enum"),
        nullable=False,
        index=True,
    )

    # Where the file is stored (S3/MinIO/local path, etc.)
    file_url: Mapped[Optional[str]] = mapped_column(db.String(512), nullable=True)

    # Metadata about the file
    page_count: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        nullable=True,
        comment="For PDF/DOC materials",
    )
    slide_count: Mapped[Optional[int]] = mapped_column(
        db.Integer,
        nullable=True,
        comment="For SLIDES/PPT materials",
    )
    file_size_mb: Mapped[Optional[float]] = mapped_column(
        db.Float,
        nullable=True,
        comment="File size in megabytes",
    )

    learning_objectives: Mapped[Optional[list[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment='e.g. ["Understand loops", "Apply recursion"]',
    )

    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)

    # Permissions
    is_downloadable: Mapped[bool] = mapped_column(
        db.Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="If False, students can view but not download",
    )
    is_enabled: Mapped[bool] = mapped_column(db.Boolean, default=True, nullable=False, index=True)

    # Global counters — incremented every time a student views or downloads
    view_count: Mapped[int] = mapped_column(db.Integer, default=0, nullable=False)
    download_count: Mapped[int] = mapped_column(db.Integer, default=0, nullable=False)

    # Aggregate student ratings (updated when ratings are submitted)
    rating_count: Mapped[int] = mapped_column(db.Integer, default=0, nullable=False)
    rating_avg: Mapped[float] = mapped_column(db.Float, default=0.0, nullable=False)

    # --- Relationships ---

    course_offering: Mapped["CourseOffering"] = db.relationship(
        "CourseOffering",
        back_populates="materials",
        lazy="select",
    )

    chapter: Mapped[Optional["CourseChapter"]] = db.relationship(
        "CourseChapter",
        back_populates="materials",
        lazy="select",
    )

    interactions: Mapped[list["StudentMaterialInteraction"]] = db.relationship(
        "StudentMaterialInteraction",
        back_populates="material",
        cascade="all, delete-orphan",
        lazy="select",
    )

    feedback_entries: Mapped[list["MaterialFeedback"]] = db.relationship(
        "MaterialFeedback",
        back_populates="material",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        # FIXED: Using partial indexes for PostgreSQL NULL chapter_id issue
        Index(
            "uq_edu_materials_offering_no_chapter_title",
            "company_id", "course_offering_id", "title",
            unique=True,
            postgresql_where=text("chapter_id IS NULL"),
        ),
        Index(
            "uq_edu_materials_offering_chapter_title",
            "company_id", "course_offering_id", "chapter_id", "title",
            unique=True,
            postgresql_where=text("chapter_id IS NOT NULL"),
        ),
        CheckConstraint(
            "(page_count IS NULL) OR (page_count >= 1)",
            name="ck_edu_material_page_min",
        ),
        CheckConstraint(
            "(slide_count IS NULL) OR (slide_count >= 1)",
            name="ck_edu_material_slide_min",
        ),
        CheckConstraint(
            "(file_size_mb IS NULL) OR (file_size_mb >= 0)",
            name="ck_edu_material_size_min",
        ),
        Index("ix_edu_materials_company_offering", "company_id", "course_offering_id"),
        Index("ix_edu_materials_company_chapter", "company_id", "chapter_id"),
    )

class StudentMaterialInteraction(BaseModel, TenantMixin):
    """
    One row per (user, material) to keep it simple:
      - favorite
      - per-user view/download counts
      - last seen / last downloaded timestamps
    """
    __tablename__ = "edu_material_interactions"

    user_id: Mapped[int] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    material_id: Mapped[int] = mapped_column(
        db.BigInteger,
        db.ForeignKey("edu_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_favorite: Mapped[bool] = mapped_column(db.Boolean, default=False, nullable=False, index=True)

    view_count: Mapped[int] = mapped_column(db.Integer, default=0, nullable=False)
    download_count: Mapped[int] = mapped_column(db.Integer, default=0, nullable=False)

    last_viewed_at: Mapped[Optional[db.DateTime]] = mapped_column(db.DateTime(timezone=True), nullable=True)
    last_downloaded_at: Mapped[Optional[db.DateTime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    material: Mapped["Material"] = db.relationship("Material", back_populates="interactions", lazy="select")

    __table_args__ = (
        UniqueConstraint("company_id", "user_id", "material_id", name="uq_user_material_interaction"),
        Index("ix_interactions_company_user", "company_id", "user_id"),
        Index("ix_interactions_company_material", "company_id", "material_id"),
    )


class MaterialFeedbackTypeEnum(str, enum.Enum):
    RATING = "rating"
    COMMENT = "comment"
    BROKEN_FILE = "broken_file"
    CLARIFICATION = "clarification"


class MaterialFeedbackStatusEnum(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"


class MaterialFeedback(BaseModel, TenantMixin):
    """Student feedback on a material: ratings, comments, issue reports."""
    __tablename__ = "edu_material_feedback"

    material_id: Mapped[int] = mapped_column(
        db.BigInteger,
        db.ForeignKey("edu_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    feedback_type: Mapped[MaterialFeedbackTypeEnum] = mapped_column(
        db.Enum(
            MaterialFeedbackTypeEnum,
            name="edu_material_feedback_type_enum",
            values_callable=_enum_values,
        ),
        nullable=False,
        index=True,
    )

    rating: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)

    status: Mapped[Optional[MaterialFeedbackStatusEnum]] = mapped_column(
        db.Enum(
            MaterialFeedbackStatusEnum,
            name="edu_material_feedback_status_enum",
            values_callable=_enum_values,
        ),
        nullable=True,
        index=True,
    )

    admin_reply: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    resolved_at: Mapped[Optional[db.DateTime]] = mapped_column(db.DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[Optional[int]] = mapped_column(
        db.BigInteger,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    material: Mapped["Material"] = db.relationship("Material", back_populates="feedback_entries", lazy="select")

    __table_args__ = (
        CheckConstraint(
            "(rating IS NULL) OR (rating >= 1 AND rating <= 5)",
            name="ck_material_feedback_rating_range",
        ),
        Index(
            "uq_material_feedback_one_rating",
            "company_id",
            "material_id",
            "user_id",
            unique=True,
            postgresql_where=text("feedback_type = 'rating'"),
        ),
        Index("ix_material_feedback_company_material", "company_id", "material_id"),
        Index("ix_material_feedback_company_status", "company_id", "status"),
    )
