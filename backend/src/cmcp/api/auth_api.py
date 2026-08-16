from __future__ import annotations

from typing import Optional

from flask import Blueprint, request, session, make_response, current_app, g
from werkzeug.exceptions import HTTPException
from pydantic import ValidationError

from cmcp.common.validation.pydantic_errors import clean_pydantic_error

from cmcp.common.api_response import api_error, api_success
from cmcp.common.decorators import rate_limit
from cmcp.core.auth import public

from cmcp.modules.auth.deps import get_current_user
from cmcp.modules.auth.schemas import (
    LoginRequest,
    ChangeMyPasswordRequest,
    ResetPasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordWithTokenRequest,
    UserProfilePageOut,
    UpdateMyProfilePageRequest,
)
from cmcp.modules.auth.service.auth_service import AuthService
from cmcp.modules.auth.service.user_profile_page import UserProfilePageService
from cmcp.modules.auth.service.user_service import UserService
from cmcp.modules.education_people.service import EducationPeopleService
from cmcp.security.rbac_guards import require_permission, require_company_and_permission

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
auth_svc = AuthService()
user_svc = UserService()
edu_svc = EducationPeopleService()
profile_page_svc = UserProfilePageService()


def _resolve_company_id_for_profile(user: dict) -> Optional[int]:
    raw = request.args.get("company_id")

    if raw is None:
        raw = request.headers.get("X-Company-ID")

    if raw is None:
        raw = session.get("company_id")

    if raw is None:
        raw = user.get("active_company_id")

    try:
        return int(raw) if raw is not None and raw != "" else None
    except Exception:
        return None
def _delete_session_cookie(resp):
    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session")
    cookie_domain = current_app.config.get("SESSION_COOKIE_DOMAIN", None)
    cookie_path = current_app.config.get("SESSION_COOKIE_PATH", "/")
    resp.delete_cookie(
        cookie_name,
        domain=cookie_domain,
        path=cookie_path,
        secure=bool(current_app.config.get("SESSION_COOKIE_SECURE")),
        httponly=bool(current_app.config.get("SESSION_COOKIE_HTTPONLY", True)),
        samesite=current_app.config.get("SESSION_COOKIE_SAMESITE") or "lax",
    )
    return resp
@bp.post("/login")
@public
@rate_limit(key_prefix="login", limit=5, window=60, include_username=True)
def login():
    payload = request.get_json(silent=True) or {}
    try:
        req = LoginRequest(**payload)
    except ValidationError as e:
        return api_error(clean_pydantic_error(e), status_code=400)

    ok, msg, profile = auth_svc.login(username=req.username, password=req.password, company_id=req.company_id)
    if not ok:
        return api_error(msg, status_code=401)

    # store chosen company in session for next requests
    session["company_id"] = req.company_id

    return api_success(message=msg, data={"user": profile})


@bp.post("/logout")
@public
@rate_limit(key_prefix="logout", limit=10, window=60)
def logout():
    ok, message = auth_svc.logout()

    session.clear()
    session.permanent = False

    resp = make_response(
        api_success(message=message, data={}) if ok else api_error(message=message, status_code=500)
    )

    return _delete_session_cookie(resp)


@bp.get("/me")
def me():
    user_profile = get_current_user()
    return api_success(data={"user": user_profile})


@bp.patch("/me/password/change")
@rate_limit(key_prefix="change_my_password", limit=5, window=60)
def change_my_password():
    user = get_current_user()
    payload = request.get_json(silent=True) or {}
    try:
        req = ChangeMyPasswordRequest(**payload)
        msg = user_svc.change_my_password(
            user_id=int(user["user_id"]),
            old_password=req.old_password,
            new_password=req.new_password,
        )
        return api_success(message=msg, data={})
    except HTTPException as e:
        return api_error(e.description or str(e), status_code=e.code or 400)
    except Exception as e:
        return api_error(f"Unexpected error: {e}", status_code=500)


# Admin: reset user password (permission only; scope is validated inside service)
@bp.patch("/users/<int:user_id>/password/reset")
@require_permission("User", "MANAGE_PASSWORD")
def reset_user_password(user_id: int):
    _ = get_current_user()
    payload = request.get_json(silent=True) or {}
    try:
        req = ResetPasswordRequest(**payload)
        msg = user_svc.reset_user_password(
            target_user_id=int(user_id),
            new_password=req.new_password,
            ctx=g.auth,
        )
        return api_success(message=msg, data={})
    except HTTPException as e:
        return api_error(e.description or str(e), status_code=e.code or 400)
    except Exception as e:
        return api_error(f"Unexpected error: {e}", status_code=500)


@bp.get("/verify-email")
@public
@rate_limit(key_prefix="verify_email", limit=20, window=60)  # optional
def verify_email():
    username = (request.args.get("username") or "").strip()
    token = (request.args.get("token") or "").strip()

    ok, msg = edu_svc.verify_email(username=username, token=token)
    if ok:
        return api_success(message=msg, data={"username": username}, status_code=200)
    return api_error(message=msg, status_code=400)


@bp.post("/forgot-password")
@public
@rate_limit(key_prefix="forgot_password", limit=5, window=60)
def forgot_password():
    payload = request.get_json(silent=True) or {}
    try:
        req = ForgotPasswordRequest(**payload)
    except ValidationError as e:
        return api_error(clean_pydantic_error(e), status_code=400)

    ok, msg = auth_svc.request_password_reset(email=str(req.email))
    return api_success(message=msg, data={}) if ok else api_error(msg, status_code=400)


@bp.post("/reset-password")
@public
@rate_limit(key_prefix="reset_password", limit=5, window=60)
def reset_password_with_token():
    payload = request.get_json(silent=True) or {}
    try:
        req = ResetPasswordWithTokenRequest(**payload)
    except ValidationError as e:
        return api_error(clean_pydantic_error(e), status_code=400)

    ok, msg = auth_svc.reset_password_with_token(
        token=req.token,
        new_password=req.new_password,
        confirm_password=req.confirm_password,
    )
    if ok:
        return api_success(message=msg, data={})
    return api_error(message=msg, status_code=400)

@bp.get("/me/profile-page")
def my_profile_page():
    user = get_current_user()
    company_id = _resolve_company_id_for_profile(user)

    try:
        data = profile_page_svc.get_my_profile_page(
            user_id=int(user["user_id"]),
            active_company_id=company_id,
            roles=user.get("roles") or [],
        )

        out = UserProfilePageOut(**data)

        return api_success(
            message="OK",
            data={"profile": out.model_dump()},
            status_code=200,
        )

    except HTTPException as e:
        return api_error(e.description or str(e), status_code=e.code or 400)
    except Exception as e:
        return api_error(f"Unexpected error: {e}", status_code=500)


@bp.patch("/me/profile-page/update")
def update_my_profile_page():
    user = get_current_user()
    company_id = _resolve_company_id_for_profile(user)
    payload = request.get_json(silent=True) or {}

    try:
        req = UpdateMyProfilePageRequest(**payload)

        data = profile_page_svc.update_my_profile_page(
            user_id=int(user["user_id"]),
            active_company_id=company_id,
            data=req.model_dump(exclude_unset=True),
            roles=user.get("roles") or [],
        )

        logout_current_session = bool(data.pop("_logout_current_session", False))

        out = UserProfilePageOut(**data)

        resp = make_response(
            api_success(
                message=(
                    "Profile updated successfully. Please log in again."
                    if logout_current_session
                    else "Profile updated successfully."
                ),
                data={
                    "profile": out.model_dump(),
                    "logged_out": logout_current_session,
                },
                status_code=200,
            )
        )

        if logout_current_session:
            session.clear()
            session.permanent = False
            _delete_session_cookie(resp)

        return resp

    except ValidationError as e:
        return api_error(clean_pydantic_error(e), status_code=400)
    except HTTPException as e:
        return api_error(e.description or str(e), status_code=e.code or 400)
    except Exception as e:
        return api_error(f"Unexpected error: {e}", status_code=500)