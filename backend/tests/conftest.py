from urllib.parse import urlparse
import pytest
import os

# ------------------------------------------------------------------------------
# Test Environment Safety & Isolation Guard
# ------------------------------------------------------------------------------
def is_safe_test_db_url(url: str) -> bool:
    """
    Strict validator ensuring tests run only against a local SQLite database.
    Rejects any network host, remote driver, or production database dialect.
    """
    if not url:
        return False
    url_str = str(url).strip()
    parsed = urlparse(url_str)
    if parsed.scheme.lower() != "sqlite":
        return False
    if parsed.netloc:
        return False
    return True

# Validate existing environment variables before test bootstrap
existing_wf_url = os.environ.get("WORKFLOW_DATABASE_URL")
if existing_wf_url and not is_safe_test_db_url(existing_wf_url):
    raise RuntimeError(
        "CRITICAL TEST ISOLATION FAILURE: Unsafe database URL detected in WORKFLOW_DATABASE_URL environment variable."
    )

existing_main_url = os.environ.get("DATABASE_URL")
if existing_main_url and not is_safe_test_db_url(existing_main_url):
    raise RuntimeError(
        "CRITICAL TEST ISOLATION FAILURE: Unsafe database URL detected in DATABASE_URL environment variable."
    )

TEST_DB_URL = "sqlite:///main_test.db"

os.environ["WORKFLOW_DATABASE_URL"] = TEST_DB_URL
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["SECRET_KEY"] = "test_mock_jwt_secret_key_only_for_unit_tests_1234567890"
os.environ["FERNET_KEY"] = "ia3rsWe2JkwStfuoRIOdDtsghWrDuFY02l5tR-XyCIc="
os.environ["WORKFLOW_DB_SCHEMA"] = "workflow"

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.workflow.workflow_base import WorkflowBase
from app.main import app as fastapi_app
from app.core.dependencies import get_current_user

# Register all workflow and studio persistence models to populate Base / WorkflowBase metadata
import app.workflow.persistence.models
import app.workflow_definition.models
import app.workflow_studio.bindings
import app.workflow.models.history

# Setup isolated file-backed test databases
for f in ["ers_test.db", "workflow_test.db", "main_test.db"]:
    if os.path.exists(f):
        try:
            os.remove(f)
        except Exception:
            pass

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Attach mock schemas on SQLite connection event across all engines (Engine class listener)
@event.listens_for(Engine, "connect")
def attach_sqlite_schemas(dbapi_connection, connection_record):
    if hasattr(dbapi_connection, "cursor"):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("ATTACH DATABASE 'ers_test.db' AS ers")
            cursor.execute("ATTACH DATABASE 'workflow_test.db' AS workflow")
        except Exception:
            pass
        finally:
            cursor.close()

@pytest.fixture(scope="session", autouse=True)
def verify_test_db_isolation():
    """
    Safety guard verifying the active database is an isolated local SQLite test database.
    """
    from app.core.config import settings
    active_url = str(settings.WORKFLOW_DATABASE_URL).strip()
    if not is_safe_test_db_url(active_url):
        raise RuntimeError(
            "CRITICAL TEST ISOLATION FAILURE: Refusing to execute tests against a non-sqlite/production database."
        )

def mock_get_current_user():
    return {
        "id": 1,
        "user_id": 1,
        "username": "admin",
        "role": "admin",
        "role_code": "admin",
        "role_id": 1,
        "dept_id": 1
    }

def mock_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session", autouse=True)
def setup_db(verify_test_db_isolation):
    # Establish session-wide dependency overrides so direct TestClient(fastapi_app) calls are safe
    from app.workflow.database import get_workflow_db
    fastapi_app.dependency_overrides[get_current_user] = mock_get_current_user
    fastapi_app.dependency_overrides[get_db] = mock_get_db
    fastapi_app.dependency_overrides[get_workflow_db] = mock_get_db

    # Create all tables on both declarative bases
    Base.metadata.create_all(bind=engine)
    WorkflowBase.metadata.create_all(bind=engine)
    yield
    WorkflowBase.metadata.drop_all(bind=engine)
    Base.metadata.drop_all(bind=engine)
    fastapi_app.dependency_overrides.clear()
    # Clean up test files
    for f in ["ers_test.db", "workflow_test.db", "main_test.db"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="module")
def client():
    with TestClient(fastapi_app) as test_client:
        yield test_client
