from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def future_utc(*, seconds: int) -> datetime:
    return utcnow() + timedelta(seconds=seconds)


def generate_state_token() -> str:
    return secrets.token_urlsafe(32)


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def create_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def _normalize_fernet_key(raw: str) -> bytes:
    candidate = raw.strip().encode("utf-8")
    try:
        decoded = base64.urlsafe_b64decode(candidate)
        if len(decoded) == 32:
            return candidate
    except Exception:  # noqa: BLE001
        pass
    digest = hashlib.sha256(candidate).digest()
    return base64.urlsafe_b64encode(digest)


def _token_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(_normalize_fernet_key(settings.connector_token_encryption_key or "connector-dev-key"))


def encrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    return _token_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    return _token_fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def session_token_hash(token: str) -> str:
    settings = get_settings()
    secret = (settings.session_encryption_key or "session-dev-key").encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()

