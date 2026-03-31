from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core import security


def test_settings_allow_missing_encryption_keys_in_development() -> None:
    settings = Settings(
        app_env="development",
        connector_token_encryption_key="",
        session_encryption_key="",
    )

    assert settings.app_env == "development"


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_settings_require_explicit_encryption_keys_outside_development(app_env: str) -> None:
    with pytest.raises(ValidationError, match="CONNECTOR_TOKEN_ENCRYPTION_KEY, SESSION_ENCRYPTION_KEY"):
        Settings(
            app_env=app_env,
            connector_token_encryption_key="",
            session_encryption_key="",
        )


def test_security_uses_development_fallback_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: SimpleNamespace(
            connector_token_encryption_key="",
            session_encryption_key="",
        ),
    )

    encrypted = security.encrypt_secret("s3cr3t")

    assert encrypted is not None
    assert security.decrypt_secret(encrypted) == "s3cr3t"
    assert security.session_token_hash("token") == security.session_token_hash("token")
