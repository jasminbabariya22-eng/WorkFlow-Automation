from sqlalchemy import text
from app.workflow.workflow_session import workflow_engine

def run_migrations():
    """
    Ensures json_content and other required metadata columns exist on bpmn_definition table.
    """
    with workflow_engine.connect() as connection:
        trans = connection.begin()
        try:
            print("Applying schema alterations to bpmn_definition...")
            # Detect dialect (PostgreSQL vs SQLite)
            dialect = workflow_engine.dialect.name
            if dialect == 'postgresql':
                connection.execute(text("""
                ALTER TABLE workflow.bpmn_definition 
                ADD COLUMN IF NOT EXISTS name VARCHAR(200),
                ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Draft',
                ADD COLUMN IF NOT EXISTS json_content TEXT,
                ADD COLUMN IF NOT EXISTS updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ADD COLUMN IF NOT EXISTS published_on TIMESTAMP,
                ADD COLUMN IF NOT EXISTS tags VARCHAR(500);
                """))
            else:
                # SQLite fallback
                try:
                    connection.execute(text("ALTER TABLE bpmn_definition ADD COLUMN json_content TEXT;"))
                except Exception:
                    pass  # Column already exists
            trans.commit()
            print("Migrations successfully applied!")
        except Exception as e:
            trans.rollback()
            print(f"Migration execution failed: {str(e)}")

if __name__ == "__main__":
    run_migrations()
