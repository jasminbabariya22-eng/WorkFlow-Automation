import os
import pytest
from pathlib import Path
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from app.core.config import Settings, load_settings
from app.core.security import encrypt_text, decrypt_text

def test_settings_fails_when_required_secrets_are_missing(monkeypatch):
    """
    Verify that application configuration fails safely when required environment
    secrets (WORKFLOW_DATABASE_URL, SECRET_KEY, FERNET_KEY) are absent, and that
    the raised error does NOT disclose any sensitive credential values.
    """
    # Isolate environment by clearing required keys
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
    missing_fields = [
        ".".join(str(part) for part in err.get("loc", []))
        for err in errors
        if "missing" in str(err.get("type", ""))
    ]

    assert "WORKFLOW_DATABASE_URL" in missing_fields
    assert "SECRET_KEY" in missing_fields
    assert "FERNET_KEY" in missing_fields

    # Verify no secret values appear in the error string
    error_text = str(exc_info.value)
    assert "Alethe" not in error_text
    assert "postgres" not in error_text


def test_settings_loads_with_explicit_variables(monkeypatch):
    """
    Verify that configuration loads successfully when valid environment variables
    are provided explicitly, matching expected types.
    """
    test_db = "postgresql+psycopg2://test_user:test_pass@127.0.0.1:5432/test_db"
    test_jwt = "test_custom_jwt_secret_key_minimum_32_characters_long_123456"
    test_fernet = "ia3rsWe2JkwStfuoRIOdDtsghWrDuFY02l5tR-XyCIc="

    monkeypatch.setenv("WORKFLOW_DATABASE_URL", test_db)
    monkeypatch.setenv("SECRET_KEY", test_jwt)
    monkeypatch.setenv("FERNET_KEY", test_fernet)
    monkeypatch.setenv("WORKFLOW_DB_SCHEMA", "custom_schema")

    class ExplicitSettings(Settings):
        model_config = SettingsConfigDict(
            env_file="non_existent_isolated_test.env",
            extra="ignore"
        )

    loaded = ExplicitSettings()
    assert loaded.WORKFLOW_DATABASE_URL == test_db
    assert loaded.SECRET_KEY == test_jwt
    assert loaded.FERNET_KEY == test_fernet
    assert loaded.WORKFLOW_DB_SCHEMA == "custom_schema"
    assert loaded.ALGORITHM == "HS256"


def test_no_hardcoded_secrets_in_config_source():
    """
    Verify that no legacy hardcoded production passwords or keys remain in
    the config.py source code.
    """
    config_file = Path(__file__).resolve().parent.parent / "app" / "core" / "config.py"
    content = config_file.read_text(encoding="utf-8")

    # Known prior insecure values
    assert "Alethe%40123" not in content
    assert "192.168.1.171" not in content
    assert "0eeedb8821a0a275fc8afb816145a44cee60bfc7f55f51b1f091cca47596cdb0" not in content


def test_no_hardcoded_secrets_in_docker_compose():
    """
    Verify that docker-compose.yml does not contain fallback credentials.
    """
    compose_file = Path(__file__).resolve().parent.parent.parent / "docker-compose.yml"
    content = compose_file.read_text(encoding="utf-8")

    assert "Alethe%40123" not in content
    assert "GF_SECURITY_ADMIN_PASSWORD=admin" not in content


def test_fernet_encryption_roundtrip():
    """
    Verify that the Fernet symmetric encryption and decryption helper functions
    remain functional and retain compatibility.
    """
    sample_text = "secure_database_password_123!"
    encrypted = encrypt_text(sample_text)
    assert encrypted != sample_text

    decrypted = decrypt_text(encrypted)
    assert decrypted == sample_text


def test_isolation_guard_rejects_non_sqlite_database_urls():
    """
    Verify that the test isolation safety guard explicitly rejects any non-sqlite,
    production-like database URL (using dummy credentials) to prevent accidental
    test execution against remote databases.
    """
    from tests.conftest import is_safe_test_db_url

    dummy_urls = [
        "postgresql+psycopg2://dummy_usr:dummy_pwd@192.168.1.99:5432/dummy_db",
        "mysql+pymysql://dummy_usr:dummy_pwd@localhost:3306/dummy_db",
        "oracle+cx_oracle://dummy_usr:dummy_pwd@10.0.0.5:1521/xe",
        "mssql+pyodbc://dummy_usr:dummy_pwd@server.internal:1433/db",
        "sqlite://remote.host.net/main_test.db",  # SQLite with remote host netloc
    ]

    for unsafe_url in dummy_urls:
        assert is_safe_test_db_url(unsafe_url) is False, f"URL should be unsafe: {unsafe_url}"


def test_isolation_guard_accepts_safe_local_sqlite():
    """
    Verify that only local file or in-memory SQLite paths pass isolation validation.
    """
    from tests.conftest import is_safe_test_db_url

    safe_urls = [
        "sqlite:///main_test.db",
        "sqlite:///:memory:",
        "sqlite:///ers_test.db",
        "sqlite:///workflow_test.db",
    ]

    for safe_url in safe_urls:
        assert is_safe_test_db_url(safe_url) is True, f"URL should be safe: {safe_url}"


def test_unsafe_pre_existing_environment_value_rejected(monkeypatch):
    """
    Verify that if an unsafe remote URL is present in the environment prior to test execution,
    the isolation check detects and rejects it rather than proceeding silently.
    """
    from tests.conftest import is_safe_test_db_url

    dummy_remote_url = "postgresql+psycopg2://dummy_usr:dummy_pwd@192.168.1.99:5432/dummy_db"
    monkeypatch.setenv("WORKFLOW_DATABASE_URL", dummy_remote_url)

    active_url = os.environ.get("WORKFLOW_DATABASE_URL")
    assert not is_safe_test_db_url(active_url)


def test_all_engines_and_sessions_bound_to_isolated_sqlite():
    """
    Verify that every engine and session factory used across backend tests
    binds strictly to an isolated SQLite engine and never connects remotely.
    """
    from tests.conftest import engine as conftest_engine, TestingSessionLocal
    from app.workflow.database import workflow_engine, WorkflowSessionLocal
    from app.core.database import client_engine, ClientSessionLocal

    engines = [conftest_engine, workflow_engine, client_engine]
    for eng in engines:
        assert eng.name == "sqlite", f"Engine {eng} dialect is not sqlite"
        assert not eng.url.host, f"Engine {eng} has a remote host configured: {eng.url.host}"
        assert not eng.url.port, f"Engine {eng} has a remote port configured: {eng.url.port}"

    # Verify session factories bind to isolated sqlite engines
    test_session = TestingSessionLocal()
    assert test_session.bind.name == "sqlite"
    test_session.close()

    wf_session = WorkflowSessionLocal()
    assert wf_session.bind.name == "sqlite"
    wf_session.close()

    client_session = ClientSessionLocal()
    assert client_session.bind.name == "sqlite"
    client_session.close()
