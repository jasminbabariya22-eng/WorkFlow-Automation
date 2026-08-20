from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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
