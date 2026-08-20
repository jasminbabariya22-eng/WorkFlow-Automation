from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings

workflow_engine = create_engine(
    settings.WORKFLOW_DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

WorkflowSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=workflow_engine
)

WorkflowBase = declarative_base()


# Dependency for FastAPI
def get_workflow_db():
    db = WorkflowSessionLocal()
    try:
        yield db
    finally:
        db.close()
