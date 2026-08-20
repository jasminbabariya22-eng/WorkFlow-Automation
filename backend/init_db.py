from sqlalchemy import text
from app.workflow.workflow_base import WorkflowBase
from app.workflow.workflow_session import workflow_engine
from app.core.database import Base, engine as main_engine
import app.models.workflow_visibility

# Import models to register them on SQLAlchemy metadata
import app.workflow.persistence.models
import app.workflow_definition.models


def main():
    print("Connecting to database...")
    try:
        # Create schema in PostgreSQL if not exists
        with workflow_engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS workflow;"))
            conn.commit()
        print("Verified schema 'workflow' exists.")

        # Create all tables on WorkflowBase
        print("Creating workflow engine tables...")
        WorkflowBase.metadata.create_all(bind=workflow_engine)
        
        # Create all tables on Base (main ERM database, e.g. visibility table)
        print("Creating ERM database tables...")
        Base.metadata.create_all(bind=main_engine)

        # Run schema migrations to add missing columns (e.g. json_content)
        from app.workflow_management.migrations import run_migrations
        run_migrations()
        
        print("All tables initialized successfully!")
    except Exception as e:
        print(f"Database initialization failed: {e}")

if __name__ == "__main__":
    main()
