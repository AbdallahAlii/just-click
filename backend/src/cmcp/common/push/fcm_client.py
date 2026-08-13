from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

log = logging.getLogger(__name__)


class FCMDeliveryError(RuntimeError):
    def __init__(self, message: str, *, status_code: int, error_code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class FCMClient:
    """Firebase Cloud Messaging HTTP v1 API.

    Expects a Firebase service-account JSON string in FIREBASE_SERVICE_ACCOUNT_JSON.
    """

    TOKEN_URL = "https://oauth2.googleapis.com/token"
    SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

    def __init__(self, *, service_account_json: Optional[str] = None):
        raw = (service_account_json or os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip()
        self.service_account = self._parse_service_account(raw)
        self._access_token: Optional[str] = None
        self._access_token_expires_at = 0.0

    def is_configured(self) -> bool:
        return bool(self.service_account)

    def send(
        self,
        *,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.is_configured():
            raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not configured.")

        service_account = self.service_account or {}
        project_id = str(service_account.get("project_id") or "").strip()
        if not project_id:
            raise RuntimeError("Firebase service account is missing project_id.")

        payload = {
            "message": {
                "token": token,
                "notification": {
                    "title": title,
                    "body": body,
                },
                "data": {k: str(v) for k, v in (data or {}).items()},
                "android": {
                    "priority": "HIGH",
                    "notification": {
                        "channel_id": "default",
                    },
                },
            }
        }

        resp = requests.post(
            f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
            headers={
                "Authorization": f"Bearer {self._get_access_token()}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )

        if resp.status_code >= 400:
            error_code = self._extract_fcm_error_code(resp)
            raise FCMDeliveryError(
                f"FCM HTTP {resp.status_code}: {resp.text[:300]}",
                status_code=resp.status_code,
                error_code=error_code,
            )

        out = resp.json()
        if not out.get("name"):
            raise RuntimeError(f"FCM delivery response missing message name: {json.dumps(out)[:300]}")

    def _get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._access_token_expires_at - 60:
            return self._access_token

        assertion = self._build_jwt_assertion()
        resp = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=15,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"FCM auth HTTP {resp.status_code}: {resp.text[:300]}")

        out = resp.json()
        token = str(out.get("access_token") or "").strip()
        expires_in = int(out.get("expires_in") or 3600)
        if not token:
            raise RuntimeError(f"FCM auth response missing access_token: {json.dumps(out)[:300]}")

        self._access_token = token
        self._access_token_expires_at = now + expires_in
        return token

    def _build_jwt_assertion(self) -> str:
        service_account = self.service_account or {}
        client_email = str(service_account.get("client_email") or "").strip()
        private_key = str(service_account.get("private_key") or "").strip()
        private_key_id = str(service_account.get("private_key_id") or "").strip()
        if not client_email or not private_key:
            raise RuntimeError("Firebase service account is missing client_email or private_key.")

        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT"}
        if private_key_id:
            header["kid"] = private_key_id

        claims = {
            "iss": client_email,
            "scope": self.SCOPE,
            "aud": self.TOKEN_URL,
            "iat": now,
            "exp": now + 3600,
        }

        signing_input = (
            self._base64url_json(header)
            + "."
            + self._base64url_json(claims)
        )
        key = serialization.load_pem_private_key(private_key.encode("utf-8"), password=None)
        signature = key.sign(
            signing_input.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return signing_input + "." + self._base64url(signature)

    @staticmethod
    def _parse_service_account(raw: str) -> Optional[Dict[str, Any]]:
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                "FIREBASE_SERVICE_ACCOUNT_JSON must be a valid single-line JSON string."
            ) from e
        if not isinstance(payload, dict):
            raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON must contain a JSON object.")
        return payload

    @staticmethod
    def _extract_fcm_error_code(resp: requests.Response) -> Optional[str]:
        try:
            payload = resp.json()
        except Exception:
            return None

        error = payload.get("error") if isinstance(payload, dict) else None
        if not isinstance(error, dict):
            return None

        details = error.get("details")
        if isinstance(details, list):
            for item in details:
                if isinstance(item, dict) and item.get("errorCode"):
                    return str(item["errorCode"])

        if error.get("status"):
            return str(error["status"])
        if error.get("message"):
            return str(error["message"])
        return None

    @staticmethod
    def _base64url_json(payload: Dict[str, Any]) -> str:
        return FCMClient._base64url(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )

    @staticmethod
    def _base64url(payload: bytes) -> str:
        return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")