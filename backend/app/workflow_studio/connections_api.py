import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.security import encrypt_text, decrypt_text
from app.core.database import DynamicEnginePool, ClientDatabaseAdapter
from app.workflow.persistence.models import DatabaseConnection

router = APIRouter(prefix="/workflow-studio/connections", tags=["Workflow Studio Database Connections"])


# -------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------
class ConnectionCreate(BaseModel):
    connection_name: str = Field(..., min_length=2, max_length=100)
    db_type: str = Field("postgresql", description="postgresql, mysql, mssql, oracle, sqlite")
    host: Optional[str] = "localhost"
    port: Optional[int] = 5432
    database_name: str = Field(..., min_length=1, max_length=100)
    default_schema: Optional[str] = "ers"
    username: Optional[str] = "postgres"
    password: Optional[str] = ""
    ssl_mode: Optional[str] = "disable"
    pool_size: Optional[int] = 10
    is_default: Optional[bool] = False
    is_active: Optional[bool] = True


class ConnectionUpdate(BaseModel):
    connection_name: Optional[str] = None
    db_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    default_schema: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_mode: Optional[str] = None
    pool_size: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class ConnectionTestRequest(BaseModel):
    db_type: str = "postgresql"
    host: str = "localhost"
    port: int = 5432
    database_name: str
    username: Optional[str] = "postgres"
    password: Optional[str] = ""
    default_schema: Optional[str] = "ers"
    ssl_mode: Optional[str] = "disable"


class ConnectionResponse(BaseModel):
    connection_id: int
    connection_name: str
    db_type: str
    host: Optional[str]
    port: Optional[int]
    database_name: Optional[str]
    default_schema: Optional[str]
    username: Optional[str]
    ssl_mode: Optional[str]
    pool_size: int
    is_default: bool
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------
@router.get("", response_model=List[ConnectionResponse])
def list_connections(
    db: Session = Depends(get_workflow_db)
):
    """
    Lists all saved Client Database connection profiles.
    """
    rows = db.query(DatabaseConnection).order_by(DatabaseConnection.is_default.desc(), DatabaseConnection.connection_id.asc()).all()
    return [
        ConnectionResponse(
            connection_id=r.connection_id,
            connection_name=r.connection_name,
            db_type=r.db_type,
            host=r.host,
            port=r.port,
            database_name=r.database_name,
            default_schema=r.default_schema,
            username=r.username,
            ssl_mode=r.ssl_mode,
            pool_size=r.pool_size or 10,
            is_default=r.is_default,
            is_active=r.is_active,
            created_at=r.created_at.isoformat() if r.created_at else None,
            updated_at=r.updated_at.isoformat() if r.updated_at else None
        )
        for r in rows
    ]


@router.post("/test", response_model=Dict[str, Any])
def test_connection_endpoint(payload: ConnectionTestRequest):
    """
    Live tests database credentials and network reachability before saving.
    """
    return DynamicEnginePool.test_connection_params(
        db_type=payload.db_type,
        host=payload.host,
        port=payload.port,
        database_name=payload.database_name,
        username=payload.username or "",
        password=payload.password or "",
        default_schema=payload.default_schema,
        ssl_mode=payload.ssl_mode or "disable"
    )


@router.post("", response_model=ConnectionResponse)
def create_connection(
    payload: ConnectionCreate,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Creates a new Client Database connection profile.
    """
    # Check duplicate name
    existing = db.query(DatabaseConnection).filter(DatabaseConnection.connection_name == payload.connection_name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Connection with name '{payload.connection_name}' already exists.")

    if payload.is_default:
        db.query(DatabaseConnection).update({DatabaseConnection.is_default: False})

    enc_pwd = encrypt_text(payload.password) if payload.password else ""

    record = DatabaseConnection(
        connection_name=payload.connection_name,
        db_type=payload.db_type.lower(),
        host=payload.host,
        port=payload.port,
        database_name=payload.database_name,
        default_schema=payload.default_schema or "ers",
        username=payload.username,
        password_encrypted=enc_pwd,
        ssl_mode=payload.ssl_mode or "disable",
        pool_size=payload.pool_size or 10,
        is_default=payload.is_default or False,
        is_active=payload.is_active if payload.is_active is not None else True
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return ConnectionResponse(
        connection_id=record.connection_id,
        connection_name=record.connection_name,
        db_type=record.db_type,
        host=record.host,
        port=record.port,
        database_name=record.database_name,
        default_schema=record.default_schema,
        username=record.username,
        ssl_mode=record.ssl_mode,
        pool_size=record.pool_size,
        is_default=record.is_default,
        is_active=record.is_active,
        created_at=record.created_at.isoformat() if record.created_at else None,
        updated_at=record.updated_at.isoformat() if record.updated_at else None
    )


@router.put("/{connection_id}", response_model=ConnectionResponse)
def update_connection(
    connection_id: int,
    payload: ConnectionUpdate,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Updates an existing Client Database connection profile.
    """
    record = db.query(DatabaseConnection).filter(DatabaseConnection.connection_id == connection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Connection ID {connection_id} not found.")

    if payload.is_default:
        db.query(DatabaseConnection).filter(DatabaseConnection.connection_id != connection_id).update({DatabaseConnection.is_default: False})

    if payload.connection_name is not None:
        record.connection_name = payload.connection_name
    if payload.db_type is not None:
        record.db_type = payload.db_type.lower()
    if payload.host is not None:
        record.host = payload.host
    if payload.port is not None:
        record.port = payload.port
    if payload.database_name is not None:
        record.database_name = payload.database_name
    if payload.default_schema is not None:
        record.default_schema = payload.default_schema
    if payload.username is not None:
        record.username = payload.username
    if payload.password is not None and payload.password != "":
        record.password_encrypted = encrypt_text(payload.password)
    if payload.ssl_mode is not None:
        record.ssl_mode = payload.ssl_mode
    if payload.pool_size is not None:
        record.pool_size = payload.pool_size
    if payload.is_default is not None:
        record.is_default = payload.is_default
    if payload.is_active is not None:
        record.is_active = payload.is_active

    db.commit()
    db.refresh(record)

    # Invalidate cache
    DynamicEnginePool.invalidate_engine(connection_id)

    return ConnectionResponse(
        connection_id=record.connection_id,
        connection_name=record.connection_name,
        db_type=record.db_type,
        host=record.host,
        port=record.port,
        database_name=record.database_name,
        default_schema=record.default_schema,
        username=record.username,
        ssl_mode=record.ssl_mode,
        pool_size=record.pool_size,
        is_default=record.is_default,
        is_active=record.is_active,
        created_at=record.created_at.isoformat() if record.created_at else None,
        updated_at=record.updated_at.isoformat() if record.updated_at else None
    )


@router.delete("/{connection_id}")
def delete_connection(
    connection_id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes a Client Database connection profile.
    """
    record = db.query(DatabaseConnection).filter(DatabaseConnection.connection_id == connection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Connection ID {connection_id} not found.")

    if record.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete the default active connection. Set another connection as default first.")

    db.delete(record)
    db.commit()
    DynamicEnginePool.invalidate_engine(connection_id)
    return {"message": f"Connection '{record.connection_name}' deleted successfully."}


@router.post("/{connection_id}/set-default")
def set_default_connection(
    connection_id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Sets a connection profile as the active default Client Database.
    """
    record = db.query(DatabaseConnection).filter(DatabaseConnection.connection_id == connection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Connection ID {connection_id} not found.")

    # Unset all others
    db.query(DatabaseConnection).update({DatabaseConnection.is_default: False})
    record.is_default = True
    record.is_active = True
    db.commit()

    # Invalidate cache to switch engines immediately
    DynamicEnginePool.invalidate_engine(connection_id)

    return {"message": f"Connection '{record.connection_name}' is now the default Client Database."}


@router.get("/{connection_id}/tables")
def get_connection_tables(
    connection_id: int,
    schema: Optional[str] = None,
    db: Session = Depends(get_workflow_db)
):
    """
    Introspects and returns all tables available in the selected database connection.
    """
    record = db.query(DatabaseConnection).filter(DatabaseConnection.connection_id == connection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Connection ID {connection_id} not found.")

    target_schema = schema or record.default_schema or "ers"
    eng = DynamicEnginePool.get_engine(connection_id)
    try:
        with eng.connect() as conn:
            query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            rows = conn.execute(query, {"schema": target_schema}).scalars().all()
            return {"schema": target_schema, "tables": list(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading tables from connection: {str(e)}")
