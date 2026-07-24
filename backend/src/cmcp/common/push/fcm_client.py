from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import requests

log = logging.getLogger(__name__)


class FCMClient:
    """Firebase Cloud Messaging legacy HTTP API."""

    def __init__(self, *, server_key: Optional[str] = None):
        self.server_key = (server_key or os.getenv("FIREBASE_SERVER_KEY") or "").strip()

    def is_configured(self) -> bool:
        return bool(self.server_key)

    def send(
        self,
        *,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.is_configured():
            raise RuntimeError("FIREBASE_SERVER_KEY is not configured.")

        payload = {
            "to": token,
            "notification": {
                "title": title,
                "body": body,
            },
            "data": {k: str(v) for k, v in (data or {}).items()},
            "priority": "high",
        }

        resp = requests.post(
            "https://fcm.googleapis.com/fcm/send",
            headers={
                "Authorization": f"key={self.server_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )

        if resp.status_code >= 400:
            raise RuntimeError(f"FCM HTTP {resp.status_code}: {resp.text[:300]}")

        out = resp.json()
        if out.get("failure", 0) > 0:
            raise RuntimeError(f"FCM delivery failed: {json.dumps(out)[:300]}")
