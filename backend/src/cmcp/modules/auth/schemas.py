from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str
    password: str
    company_id: Optional[int] = None


class ChangeMyPasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordWithTokenRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)


class AffiliationOut(BaseModel):
    id: int
    company_id: int
    is_primary: bool
    is_enabled: bool
    is_company_owner: bool
    linked_entity_type: Optional[str] = None
    linked_entity_id: Optional[int] = None


class UserProfileOut(BaseModel):
    user_id: int
    username: str
    user_type: str
    is_system_owner: bool
    last_login: Optional[str] = None

    affiliations: List[AffiliationOut]

    active_company_id: Optional[int] = None
    roles: List[str] = []
    permissions: List[str] = []
    is_company_admin: bool = False


class ProfileFacultyOut(BaseModel):
    id: int
    name: str


class ProfileDepartmentOut(BaseModel):
    id: int
    name: str


class ProfileClassroomOut(BaseModel):
    id: int
    name: str
    room_number: Optional[str] = None


class ProfileSemesterOut(BaseModel):
    id: int
    name: str
    number: Optional[int] = None


class UserProfilePageOut(BaseModel):
    id: Optional[int] = None
    user_id: int

    username: str
    email: str
    status: str

    user_is_enabled: bool
    profile_is_enabled: Optional[bool] = None

    profile_type: Optional[str] = None

    full_name: Optional[str] = None
    student_id: Optional[str] = None
    staff_id: Optional[str] = None

    faculty: Optional[ProfileFacultyOut] = None
    department: Optional[ProfileDepartmentOut] = None
    classroom: Optional[ProfileClassroomOut] = None
    semester: Optional[ProfileSemesterOut] = None

    roles: List[str] = []

    can_edit: List[str] = []
    security: dict = Field(default_factory=dict)


class UpdateMyProfilePageRequest(BaseModel):
    # Account fields
    email: Optional[EmailStr] = None

    # Profile fields
    full_name: Optional[str] = None

    # Staff/admin editable profile fields
    staff_id: Optional[str] = None
    faculty_id: Optional[int] = None
    department_id: Optional[int] = None

    # Admin-only account/profile switches
    status: Optional[str] = None
    user_is_enabled: Optional[bool] = None
    profile_is_enabled: Optional[bool] = None

    # Password section, Frappe-style
    set_new_password: Optional[bool] = False
    new_password: Optional[str] = None
    logout_from_all_devices: Optional[bool] = False

    # Student protected fields.
    # We keep them in schema so frontend mistakes return a clean error from service.
    student_id: Optional[str] = None
    classroom_id: Optional[int] = None
    semester_id: Optional[int] = None