import os
import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from app.core.config import Settings
from app.core.security import encrypt_text, decrypt_text
from tests.conftest import is_safe_test_db_url


def test_health_endpoint(client):
    """Verify health endpoint returns healthy status and 200."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_settings_fails_when_required_secrets_are_missing(monkeypatch):
    """
    Verify application configuration fails safely when required environment
    secrets are absent.
    """
    monkeypatch.delenv("WORKFLOW_DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("FERNET_KEY", raising=False)

    class IsolatedSettings(Settings):
        model_config = SettingsConfigDict(
            env_file="non_existent_isolated_test.env",
            extra="ignore"
        )

    with pytest.raises(ValidationError) as exc_info:
        IsolatedSettings()

    errors = exc_info.value.errors()
    missing_fields = [e["loc"][0] for e in errors]
    assert "WORKFLOW_DATABASE_URL" in missing_fields or "DATABASE_URL" in missing_fields


def test_fernet_encryption_roundtrip():
    """Verify Fernet encryption and decryption functions maintain data integrity."""
    secret_payload = "HighPrioritySecretCredential_2026!#"
    encrypted = encrypt_text(secret_payload)
    assert encrypted != secret_payload
    decrypted = decrypt_text(encrypted)
    assert decrypted == secret_payload


def test_database_isolation_guard():
    """Verify the database isolation guard permits safe local SQLite and blocks network DBs."""
    assert is_safe_test_db_url("sqlite:///main_test.db") is True
    assert is_safe_test_db_url("sqlite:///:memory:") is True
    assert is_safe_test_db_url("postgresql://user:pass@192.168.1.171/db") is False
    assert is_safe_test_db_url("mssql+pyodbc://sa:pass@192.168.1.192/db") is False
    assert is_safe_test_db_url("") is False
