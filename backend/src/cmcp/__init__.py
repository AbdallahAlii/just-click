
from __future__ import annotations

import importlib
import logging
from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from flask_session import Session
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError

from cmcp.config.settings import settings
from cmcp.config.database import db, migrate
from cmcp.common.api_response import api_error

from cmcp.core.middleware.request_id import before_request_request_id, after_request_request_id
from cmcp.core.middleware.security_headers import after_request_security_headers
from cmcp.core.middleware.session_auth import before_request_session_auth
from cmcp.core.auth import require_login_globally
from cmcp.api import register_blueprints
from cmcp.modules.media.utils import ensure_local_media_folders

# ✅ Redis optional clients (for cache/rate-limit/etc)
from cmcp.common.cache.redis_client import redis_raw

log = logging.getLogger(__name__)


def create_app() -> Flask:
    import os

    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    os.environ.setdefault("CHROMA_TELEMETRY", "FALSE")

    app = Flask(__name__)
    # --- ADD THESE TWO LINES ---

    from cmcp.cli.seed_command import seed_cli
    from cmcp.cli.demo_reset import demo_reset_cli
    app.cli.add_command(seed_cli)
    app.cli.add_command(demo_reset_cli)
    # ---------------------------
    # ------------------------------------------------------------------
    # Core config
    # ------------------------------------------------------------------
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # ✅ cookie session settings (these apply even without Flask-Session)
    app.config.update(
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=settings.SESSION_COOKIE_MAX_AGE),
        SESSION_COOKIE_NAME=settings.SESSION_COOKIE_NAME,
        SESSION_COOKIE_HTTPONLY=settings.SESSION_COOKIE_HTTPONLY,
        SESSION_COOKIE_SECURE=settings.cookie_secure_effective,
        SESSION_COOKIE_SAMESITE=settings.cookie_samesite_effective,
        SESSION_COOKIE_DOMAIN=settings.SESSION_COOKIE_DOMAIN,
    )

    # ------------------------------------------------------------------
    # Sessions Backend (FAIL-SAFE DEFAULT)
    # ------------------------------------------------------------------
    # ✅ default: cookie sessions -> DO NOT init Flask-Session
    if settings.SESSION_BACKEND == "filesystem":
        app.config.update(
            SESSION_TYPE="filesystem",
            SESSION_FILE_DIR=settings.SESSION_FILESYSTEM_DIR,
            SESSION_PERMANENT=True,
            SESSION_USE_SIGNER=True,
            SESSION_KEY_PREFIX="cmcp_session:",
        )
        Session(app)

    elif settings.SESSION_BACKEND == "redis":
        # ✅ only enable if Redis is reachable at startup
        if redis_raw.ping():
            app.config.update(
                SESSION_TYPE="redis",
                SESSION_REDIS=redis_raw.raw_client(),  # underlying redis-py client or None
                SESSION_PERMANENT=True,
                SESSION_USE_SIGNER=True,
                SESSION_KEY_PREFIX="cmcp_session:",
            )
            Session(app)
        else:
            # fall back to cookie sessions automatically
            log.warning("SESSION_BACKEND=redis but Redis is down -> using cookie sessions fallback")

    # ------------------------------------------------------------------
    # DB + migrations
    # ------------------------------------------------------------------
    db.init_app(app)
    importlib.import_module("cmcp.models")  # auto-import models
    migrate.init_app(app, db)

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS(
        app,
        supports_credentials=True,
        origins=settings.CORS_ALLOWED_ORIGINS,
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Cookie",
            "X-Company-Id",
        ],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    # ------------------------------------------------------------------
    # Middleware hooks
    # ------------------------------------------------------------------
    app.before_request(before_request_request_id)
    app.before_request(before_request_session_auth)
    app.after_request(after_request_request_id)
    app.after_request(after_request_security_headers)

    # ------------------------------------------------------------------
    # Global exception handlers
    # ------------------------------------------------------------------
    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        return api_error(getattr(e, "description", None) or e.name, status_code=e.code)

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e: IntegrityError):
        db.session.rollback()
        return api_error("Database conflict.", status_code=409)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e: Exception):
        app.logger.exception("Unhandled error", exc_info=True)
        return api_error("Internal server error.", status_code=500)

    # ------------------------------------------------------------------
    # Ensure local media folders exist
    # ------------------------------------------------------------------
    try:
        ensure_local_media_folders()
    except Exception:
        app.logger.exception("ensure_local_media_folders failed")

    # ------------------------------------------------------------------
    # Register blueprints
    # ------------------------------------------------------------------
    register_blueprints(app)

    # ------------------------------------------------------------------
    # Require login by default
    # ------------------------------------------------------------------
    require_login_globally(app)

    try:
        from cmcp.modules.chatbot.rag.warmup import schedule_chatbot_rag_warmup

        if not os.getenv("CMCP_SKIP_CHATBOT_WARMUP"):
            schedule_chatbot_rag_warmup(app)
    except Exception:
        app.logger.exception("Chatbot RAG warmup scheduling failed")

    return app