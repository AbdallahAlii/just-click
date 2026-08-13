
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time
from http import HTTPStatus
from urllib.parse import quote

from flask import Blueprint, Response, abort, request, send_from_directory

from cmcp.common.api_response import api_success
from cmcp.config.media_config import settings
from cmcp.config.settings import settings as app_settings
from cmcp.modules.media.encrypted_files import download_and_decrypt_file
from cmcp.modules.media.encrypted_media import download_and_decrypt, image_url_from_key
from cmcp.security.rbac_guards import require_permission

media_bp = Blueprint("media_stream", __name__, url_prefix="/api/media")

# -------------------------------------------------------------------
# Key safety: only allow characters we generate for keys. Block "../".
# -------------------------------------------------------------------
_SAFE_KEY = re.compile(r"^[A-Za-z0-9._/\-]+$")


def _assert_safe_key(k: str) -> None:
    if not _SAFE_KEY.fullmatch(k) or ".." in k or k.startswith("/"):
        abort(HTTPStatus.BAD_REQUEST)


# -------------------------------------------------------------------
# Token-signed URLs
# -------------------------------------------------------------------
# Signing must use the real app SECRET_KEY. Never silently fall back in production.
_raw_signing_secret = getattr(app_settings, "SECRET_KEY", None)
if not _raw_signing_secret:
    if str(getattr(app_settings, "ENV", "development")).lower() in {"production", "prod"}:
        raise RuntimeError("SECRET_KEY is required for media URL signing in production.")
    _raw_signing_secret = "dev-secret"
_SIGNING_SECRET = str(_raw_signing_secret).encode("utf-8")


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("utf-8")


def _make_token(key: str, exp_ts: int) -> str:
    data = f"{key}|{exp_ts}".encode("utf-8")
    mac = hmac.new(_SIGNING_SECRET, data, hashlib.sha256).digest()
    return f"{_b64u(mac)}.{exp_ts}"


def _verify_token(key: str, token: str) -> bool:
    try:
        sig_b64, exp_s = token.split(".", 1)
        exp_ts = int(exp_s)
    except Exception:
        return False

    if exp_ts < int(time.time()):
        return False

    data = f"{key}|{exp_ts}".encode("utf-8")
    mac = hmac.new(_SIGNING_SECRET, data, hashlib.sha256).digest()
    return hmac.compare_digest(_b64u(mac), sig_b64)


def _ttl_from_request(default: int = 300) -> int:
    try:
        ttl = int(request.args.get("ttl", default))
    except Exception:
        ttl = default

    return max(30, min(ttl, 3600))


def _filename_from_file_key(file_key: str) -> str:
    """
    Convert:
      materials_files/5/file.ppt.enc
    into:
      material.ppt
    """
    filename = "material"

    if "/file" in file_key:
        part = file_key.split("/file", 1)[-1]

        if part.endswith(".enc"):
            part = part[:-4]

        if part.startswith("."):
            filename = "material" + part

    return filename


# -------------------------------------------------------------------
# Images
# -------------------------------------------------------------------

@media_bp.get("/img/<path:img_key>")
@require_permission("Material", "READ")
def stream_image(img_key: str):
    _assert_safe_key(img_key)

    try:
        raw_bytes, mime_type = download_and_decrypt(img_key)
    except FileNotFoundError:
        abort(HTTPStatus.NOT_FOUND)
    except Exception:
        abort(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = Response(raw_bytes, mimetype=mime_type)
    resp.headers["Content-Disposition"] = "inline"
    resp.headers["Cache-Control"] = "private, max-age=300"
    return resp


@media_bp.get("/url/<path:img_key>")
@require_permission("Material", "READ")
def get_image_url(img_key: str):
    _assert_safe_key(img_key)

    url = image_url_from_key(img_key)

    return api_success(data={"url": url})


@media_bp.get("/presign/<path:img_key>")
@require_permission("Material", "READ")
def presign_image(img_key: str):
    _assert_safe_key(img_key)

    ttl = _ttl_from_request(300)
    exp = int(time.time()) + ttl
    token = _make_token(img_key, exp)

    signed_url = f"/api/media/img-signed/{img_key}?t={token}"

    return api_success(
        data={
            "url": signed_url,
            "expires_at": exp,
        }
    )


@media_bp.get("/img-signed/<path:img_key>")
def stream_image_signed(img_key: str):
    _assert_safe_key(img_key)

    token = request.args.get("t")
    if not token or not _verify_token(img_key, token):
        abort(HTTPStatus.FORBIDDEN)

    try:
        raw_bytes, mime_type = download_and_decrypt(img_key)
    except FileNotFoundError:
        abort(HTTPStatus.NOT_FOUND)
    except Exception:
        abort(HTTPStatus.INTERNAL_SERVER_ERROR)

    resp = Response(raw_bytes, mimetype=mime_type)
    resp.headers["Content-Disposition"] = "inline"
    resp.headers["Cache-Control"] = "private, max-age=300"
    return resp


# -------------------------------------------------------------------
# Files
# Important:
# Student material pages require Material READ.
# Do NOT use File Read here unless all students have File Read permission.
# -------------------------------------------------------------------

@media_bp.get("/file/<path:file_key>")
@require_permission("Material", "READ")
def stream_file(file_key: str):
    _assert_safe_key(file_key)

    try:
        raw, mime = download_and_decrypt_file(file_key)
    except FileNotFoundError:
        abort(HTTPStatus.NOT_FOUND)
    except Exception:
        abort(HTTPStatus.INTERNAL_SERVER_ERROR)

    filename = _filename_from_file_key(file_key)

    resp = Response(raw, mimetype=mime)
    resp.headers["Content-Disposition"] = (
        f"inline; filename*=UTF-8''{quote(filename)}"
    )
    resp.headers["Cache-Control"] = "private, max-age=300"
    return resp


@media_bp.get("/presign-file/<path:file_key>")
@require_permission("Material", "READ")
def presign_file(file_key: str):
    _assert_safe_key(file_key)

    ttl = _ttl_from_request(300)
    exp = int(time.time()) + ttl
    token = _make_token(file_key, exp)

    signed_url = f"/api/media/file-signed/{file_key}?t={token}"

    return api_success(
        data={
            "url": signed_url,
            "expires_at": exp,
        }
    )


@media_bp.get("/file-signed/<path:file_key>")
def stream_file_signed(file_key: str):
    _assert_safe_key(file_key)

    token = request.args.get("t")
    if not token or not _verify_token(file_key, token):
        abort(HTTPStatus.FORBIDDEN)

    try:
        raw, mime = download_and_decrypt_file(file_key)
    except FileNotFoundError:
        abort(HTTPStatus.NOT_FOUND)
    except Exception:
        abort(HTTPStatus.INTERNAL_SERVER_ERROR)

    filename = _filename_from_file_key(file_key)

    resp = Response(raw, mimetype=mime)
    resp.headers["Content-Disposition"] = (
        f"inline; filename*=UTF-8''{quote(filename)}"
    )
    resp.headers["Cache-Control"] = "private, max-age=300"
    return resp


@media_bp.get("/download/<path:file_key>")
@require_permission("Material", "READ")
def download_file(file_key: str):
    _assert_safe_key(file_key)

    try:
        raw, mime = download_and_decrypt_file(file_key)
    except FileNotFoundError:
        abort(HTTPStatus.NOT_FOUND)
    except Exception:
        abort(HTTPStatus.INTERNAL_SERVER_ERROR)

    filename = _filename_from_file_key(file_key)

    resp = Response(raw, mimetype=mime)
    resp.headers["Content-Disposition"] = (
        f"attachment; filename*=UTF-8''{quote(filename)}"
    )
    resp.headers["Cache-Control"] = "private, max-age=300"
    return resp


# -------------------------------------------------------------------
# DEV ONLY: serve encrypted ciphertext from disk.
# Never register in production even when MEDIA_BACKEND=local.
# -------------------------------------------------------------------
_env = str(getattr(app_settings, "ENV", "development") or "development").lower()
if settings.MEDIA_BACKEND.lower() == "local" and _env not in {"production", "prod"}:

    @media_bp.get("/_debug/raw/<path:filename>")
    def serve_media_local(filename: str):
        _assert_safe_key(filename)
        return send_from_directory(settings.LOCAL_MEDIA_ROOT, filename)