import pytest
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.workflow.workflow_base import WorkflowBase
from app.main import app
from app.core.dependencies import get_current_user

# Setup isolated file-backed test databases
for f in ["ers_test.db", "workflow_test.db", "main_test.db"]:
    if os.path.exists(f):
        try:
            os.remove(f)
        except Exception:
            pass

TEST_DB_URL = "sqlite:///main_test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Attach mock schemas on SQLite connection event using files
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("ATTACH DATABASE 'ers_test.db' AS ers")
    cursor.execute("ATTACH DATABASE 'workflow_test.db' AS workflow")
    cursor.close()

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Create all tables on both declarative bases
    Base.metadata.create_all(bind=engine)
    WorkflowBase.metadata.create_all(bind=engine)
    yield
    WorkflowBase.metadata.drop_all(bind=engine)
    Base.metadata.drop_all(bind=engine)
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

# Mock auth dependency
def mock_get_current_user():
    return {"id": 1, "username": "admin", "role_code": "admin"}

def mock_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def client():
    from app.workflow.database import get_workflow_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_workflow_db] = mock_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
