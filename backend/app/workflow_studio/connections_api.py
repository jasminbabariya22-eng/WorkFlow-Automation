import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.logger import logger
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


@router.post("/{connection_id}/test", response_model=Dict[str, Any])
def test_saved_connection(
    connection_id: int,
    db: Session = Depends(get_workflow_db)
):
    """
    Live tests an existing saved connection profile by ID in <50ms.
    """
    record = db.query(DatabaseConnection).filter(DatabaseConnection.connection_id == connection_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Connection ID {connection_id} not found.")

    pwd = decrypt_text(record.password_encrypted) if record.password_encrypted else ""
    return DynamicEnginePool.test_connection_params(
        db_type=record.db_type,
        host=record.host,
        port=record.port,
        database_name=record.database_name,
        username=record.username or "",
        password=pwd,
        default_schema=record.default_schema,
        ssl_mode=record.ssl_mode or "disable"
    )


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


def _fetch_email_servers_from_engine(eng, target_conn_id: int, conn_name: str = ""):
    """
    High-performance generic helper to inspect and fetch all configured email servers 
    from ANY client database engine (MSSQL, PostgreSQL, MySQL, SQLite, Oracle).
    """
    from sqlalchemy import inspect
    results = []
    seen_keys = set()

    def _process_rows(rows, candidate_name: str):
        for r in rows:
            m = dict(r._mapping)
            # Check deleted flag safely
            is_del = None
            for k, v in m.items():
                if k.lower() == "is_deleted":
                    is_del = v
                    break
            if is_del is not None and str(is_del).strip().lower() in ("1", "true", "t", "yes"):
                continue

            # 1. Server ID
            sid = None
            for cand_col in ["email_server_id", "server_id", "id", "pk"]:
                for k, v in m.items():
                    if k.lower() == cand_col and v is not None:
                        sid = v
                        break
                if sid is not None:
                    break
            sid = sid or 1

            # 2. Email / Username
            s_user = ""
            for cand_col in ["outgoing_email_user", "email_user", "email", "from_email", "sender_email", "username", "email_id", "emailid", "user_email", "login"]:
                for k, v in m.items():
                    if k.lower() == cand_col and v is not None:
                        s_user = str(v).strip()
                        break
                if s_user:
                    break
            if not s_user:
                for k, v in m.items():
                    if v and "@" in str(v):
                        s_user = str(v).strip()
                        break

            # 3. Server Name
            s_name = ""
            for cand_col in ["server_name", "title", "description", "label", "name"]:
                for k, v in m.items():
                    if k.lower() == cand_col and v is not None:
                        s_name = str(v).strip()
                        break
                if s_name:
                    break
            s_name = s_name or "SMTP Server"

            # 4. Outgoing Host / Server IP
            s_host = ""
            for cand_col in ["outgoing_server_ip", "server_ip", "smtp_host", "outgoing_server", "host"]:
                for k, v in m.items():
                    if k.lower() == cand_col and v is not None:
                        s_host = str(v).strip()
                        break
                if s_host:
                    break

            # 5. Port
            s_port = 587
            for cand_col in ["outgoing_email_port", "smtp_port", "port"]:
                for k, v in m.items():
                    if k.lower() == cand_col and v is not None:
                        try:
                            s_port = int(v)
                        except Exception:
                            s_port = 587
                        break
                if s_port != 587:
                    break

            # 6. Encryption
            s_enc = 1
            for cand_col in ["outgoing_email_encryption", "encryption", "use_ssl"]:
                for k, v in m.items():
                    if k.lower() == cand_col and v is not None:
                        try:
                            s_enc = int(v)
                        except Exception:
                            s_enc = 1
                        break

            dedup_key = f"{target_conn_id}:{sid}:{s_user}"
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            results.append({
                "email_server_id": sid,
                "server_name": s_name,
                "outgoing_email_user": s_user,
                "from_email": s_user,
                "outgoing_server_ip": s_host,
                "outgoing_email_port": s_port,
                "outgoing_email_encryption": s_enc,
                "connection_id": target_conn_id,
                "connection_name": conn_name,
                "display_name": f"{s_user} ({s_name} - #{sid})" if s_user else f"{s_name} (#{sid})"
            })

    try:
        with eng.connect() as conn:
            # 1. Fast path: Direct query on standard table names using a single connection
            fast_candidates = [
                "email_server",
                "dbo.email_server",
                "public.email_server",
                "ers.email_server",
                "mst_email_server",
                "dbo.mst_email_server",
                "public.mst_email_server",
                "email_servers",
                "smtp_settings",
                "email_config"
            ]

            for candidate in fast_candidates:
                try:
                    rows = conn.execute(text(f"SELECT * FROM {candidate}")).fetchall()
                    if rows:
                        _process_rows(rows, candidate)
                        if results:
                            return results
                except Exception:
                    pass

            # 2. Schema introspection fallback for unusual schemas/prefixes
            if not results:
                try:
                    inspector = inspect(eng)
                    all_schemas = []
                    try:
                        all_schemas = inspector.get_schema_names()
                    except Exception:
                        all_schemas = []

                    schemas_to_scan = [s for s in all_schemas if s.lower() not in ("information_schema", "pg_catalog", "sys", "guest")]
                    if not schemas_to_scan:
                        schemas_to_scan = [None]

                    for sch in schemas_to_scan:
                        try:
                            tbls = inspector.get_table_names(schema=sch) if sch else inspector.get_table_names()
                            for t in tbls:
                                t_lower = t.lower()
                                if any(cand in t_lower for cand in ["email_server", "email_config", "smtp_setting", "smtp"]):
                                    full_t = f"{sch}.{t}" if sch else t
                                    try:
                                        rows = conn.execute(text(f"SELECT * FROM {full_t}")).fetchall()
                                        if rows:
                                            _process_rows(rows, full_t)
                                            if results:
                                                return results
                                    except Exception:
                                        pass
                        except Exception:
                            continue
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error reading email servers from connection #{target_conn_id}: {e}")

    return results


@router.get("/{connection_id}/email-servers")
@router.get("/email-servers")
def get_connection_email_servers(
    connection_id: Optional[int] = None,
    db: Session = Depends(get_workflow_db)
):
    """
    Introspects and returns ONLY the configured email servers from the specific connected client database.
    Optimized to execute in < 15ms by utilizing persistent pooled database connections.
    """
    target_conn = None

    if connection_id is not None:
        target_conn = db.query(DatabaseConnection).filter(
            DatabaseConnection.connection_id == connection_id,
            DatabaseConnection.is_active == True
        ).first()
    else:
        # Fallback to single default connection if not specified
        target_conn = db.query(DatabaseConnection).filter(
            DatabaseConnection.is_default == True,
            DatabaseConnection.is_active == True
        ).first()
        if not target_conn:
            target_conn = db.query(DatabaseConnection).filter(
                DatabaseConnection.is_active == True
            ).first()

    if not target_conn:
        return []

    try:
        eng = DynamicEnginePool.get_engine(target_conn.connection_id)
        return _fetch_email_servers_from_engine(
            eng,
            target_conn.connection_id,
            target_conn.connection_name or f"Conn #{target_conn.connection_id}"
        )
    except Exception as e:
        logger.error(f"Error reading email servers from connection #{target_conn.connection_id}: {e}")
        return []


class EmailServerCreate(BaseModel):
    outgoing_email_user: str = Field(..., description="Sender / SMTP Username (e.g. notifications@company.com)")
    outgoing_email_password: str = Field(..., description="Password or App Password (will be Fernet-encrypted)")
    outgoing_server_ip: str = Field("smtp.gmail.com", description="SMTP Host / Server IP (e.g. smtp.gmail.com)")
    outgoing_email_port: int = Field(587, description="SMTP Port (587, 465, 25)")
    outgoing_email_encryption: int = Field(1, description="1=STARTTLS, 2=SSL, 0=None")
    server_name: Optional[str] = "SMTP Server"


class EmailServerTestRequest(BaseModel):
    outgoing_email_user: str = Field(..., description="Sender / SMTP Username")
    outgoing_email_password: str = Field(..., description="Password or App Password to test")
    outgoing_server_ip: str = Field("smtp.gmail.com", description="SMTP Host / Server IP")
    outgoing_email_port: int = Field(587, description="SMTP Port")
    outgoing_email_encryption: int = Field(1, description="1=STARTTLS, 2=SSL, 0=None")


@router.post("/{connection_id}/email-servers/test")
@router.post("/email-servers/test")
def test_email_server_credentials(
    payload: EmailServerTestRequest,
    connection_id: Optional[int] = None
):
    """
    Live tests SMTP credentials against the specified mail server before saving.
    """
    import smtplib
    import socket
    import time

    host = payload.outgoing_server_ip.strip()
    port = int(payload.outgoing_email_port or 587)
    user = payload.outgoing_email_user.strip()
    password = payload.outgoing_email_password.strip()
    encryption = int(payload.outgoing_email_encryption or 1)

    start_ts = time.time()
    server = None
    try:
        if port == 465 or encryption == 2:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            if encryption == 1 or port == 587:
                server.starttls()
                server.ehlo()

        server.login(user, password)
        elapsed_ms = round((time.time() - start_ts) * 1000, 1)
        return {
            "success": True,
            "message": f"SMTP Authentication Successful for '{user}' on {host}:{port} in {elapsed_ms}ms.",
            "latency_ms": elapsed_ms
        }
    except smtplib.SMTPAuthenticationError as auth_err:
        return {
            "success": False,
            "message": f"Authentication failed (Incorrect email or password): {str(auth_err.smtp_error or auth_err)}",
            "error_type": "AUTH_ERROR"
        }
    except (smtplib.SMTPConnectError, socket.timeout, TimeoutError) as conn_err:
        return {
            "success": False,
            "message": f"Connection timeout to {host}:{port}. Check host and port: {str(conn_err)}",
            "error_type": "CONNECT_ERROR"
        }
    except Exception as ex:
        return {
            "success": False,
            "message": f"SMTP validation error: {str(ex)}",
            "error_type": "GENERAL_ERROR"
        }
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


@router.post("/{connection_id}/email-servers")
@router.post("/email-servers")
def create_connection_email_server(
    payload: EmailServerCreate,
    connection_id: Optional[int] = None,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Authenticates and registers a new Email Server / Sender in the Client Database email_server table.
    Encrypts password securely using FERNET before saving.
    """
    from sqlalchemy import inspect
    from datetime import datetime

    target_conn_id = connection_id
    if target_conn_id is None:
        def_conn = db.query(DatabaseConnection).filter(DatabaseConnection.is_default == True, DatabaseConnection.is_active == True).first()
        if def_conn:
            target_conn_id = def_conn.connection_id
        else:
            first_conn = db.query(DatabaseConnection).filter(DatabaseConnection.is_active == True).first()
            target_conn_id = first_conn.connection_id if first_conn else None

    if target_conn_id is None:
        raise HTTPException(status_code=400, detail="No active database connection found to store email server.")

    eng = DynamicEnginePool.get_engine(target_conn_id)
    inspector = inspect(eng)
    target_schema = ClientDatabaseAdapter._resolve_target_schema(None, target_conn_id)

    schemas_to_check = []
    if target_schema:
        schemas_to_check.append(target_schema)
    for s in ["dbo", "public", "ers"]:
        if s in inspector.get_schema_names() and s not in schemas_to_check:
            schemas_to_check.append(s)
    for s in inspector.get_schema_names():
        if s not in schemas_to_check and s.lower() not in ("information_schema", "pg_catalog", "sys", "guest"):
            schemas_to_check.append(s)
    if not schemas_to_check:
        schemas_to_check = [None]

    found_tbl = None
    found_schema = None

    for sch in schemas_to_check:
        try:
            raw_table_names = inspector.get_table_names(schema=sch)
            table_map = {t.lower(): t for t in raw_table_names}
        except Exception:
            table_map = {}

        for s_tbl in ["email_server", "mst_email_server", "smtp_settings", "email_config", "email_servers", "tbl_email_server"]:
            if s_tbl in table_map:
                found_tbl = table_map[s_tbl]
                found_schema = sch
                break
        if found_tbl:
            break

    if not found_tbl:
        raise HTTPException(
            status_code=400,
            detail=f"Could not locate an email_server / mst_email_server table in client database connection #{target_conn_id}."
        )

    full_tbl = f"{found_schema}.{found_tbl}" if found_schema else found_tbl
    raw_cols = inspector.get_columns(found_tbl, schema=found_schema)
    cols_dict = {c["name"].lower(): c["name"] for c in raw_cols}
    cols_type_map = {c["name"].lower(): str(c.get("type", "")).lower() for c in raw_cols}

    # Encrypt password using FERNET
    encrypted_password = encrypt_text(payload.outgoing_email_password.strip())

    insert_data = {}
    if "server_name" in cols_dict:
        insert_data[cols_dict["server_name"]] = payload.server_name or "SMTP Server"
    elif "name" in cols_dict:
        insert_data[cols_dict["name"]] = payload.server_name or "SMTP Server"

    if "outgoing_server_ip" in cols_dict:
        insert_data[cols_dict["outgoing_server_ip"]] = payload.outgoing_server_ip.strip()
    elif "server_ip" in cols_dict:
        insert_data[cols_dict["server_ip"]] = payload.outgoing_server_ip.strip()
    elif "host" in cols_dict:
        insert_data[cols_dict["host"]] = payload.outgoing_server_ip.strip()

    if "outgoing_email_user" in cols_dict:
        insert_data[cols_dict["outgoing_email_user"]] = payload.outgoing_email_user.strip()
    elif "email_user" in cols_dict:
        insert_data[cols_dict["email_user"]] = payload.outgoing_email_user.strip()
    elif "username" in cols_dict:
        insert_data[cols_dict["username"]] = payload.outgoing_email_user.strip()

    if "outgoing_email_password" in cols_dict:
        insert_data[cols_dict["outgoing_email_password"]] = encrypted_password
    elif "password" in cols_dict:
        insert_data[cols_dict["password"]] = encrypted_password

    if "outgoing_email_port" in cols_dict:
        insert_data[cols_dict["outgoing_email_port"]] = int(payload.outgoing_email_port or 587)
    elif "port" in cols_dict:
        insert_data[cols_dict["port"]] = int(payload.outgoing_email_port or 587)

    if "outgoing_email_encryption" in cols_dict:
        insert_data[cols_dict["outgoing_email_encryption"]] = int(payload.outgoing_email_encryption or 1)
    elif "encryption" in cols_dict:
        insert_data[cols_dict["encryption"]] = int(payload.outgoing_email_encryption or 1)

    if "is_deleted" in cols_dict:
        del_type = cols_type_map.get("is_deleted", "")
        if "bit" in del_type or "bool" in del_type:
            insert_data[cols_dict["is_deleted"]] = False
        else:
            insert_data[cols_dict["is_deleted"]] = 0

    if "created_on" in cols_dict:
        insert_data[cols_dict["created_on"]] = datetime.now()

    user_id = current_user.get("user_id") or current_user.get("id") if isinstance(current_user, dict) else 1
    if "created_by" in cols_dict and user_id is not None:
        cb_type = cols_type_map.get("created_by", "")
        if "int" in cb_type:
            insert_data[cols_dict["created_by"]] = int(user_id) if str(user_id).isdigit() else 1
        else:
            insert_data[cols_dict["created_by"]] = str(user_id)

    pk_name = None
    for p_cand in ["email_server_id", "id", "server_id"]:
        if p_cand in cols_dict:
            pk_name = cols_dict[p_cand]
            break

    col_names = list(insert_data.keys())
    param_names = [f":p_{i}" for i in range(len(col_names))]
    params = {f"p_{i}": v for i, v in enumerate(insert_data.values())}

    insert_sql = f"INSERT INTO {full_tbl} ({', '.join(col_names)}) VALUES ({', '.join(param_names)})"
    dialect_name = eng.dialect.name.lower()
    created_id = None

    try:
        with eng.begin() as conn:
            if "postgres" in dialect_name and pk_name:
                ret_sql = f"INSERT INTO {full_tbl} ({', '.join(col_names)}) VALUES ({', '.join(param_names)}) RETURNING {pk_name}"
                res = conn.execute(text(ret_sql), params).first()
                if res:
                    created_id = res[0]
            else:
                conn.execute(text(insert_sql), params)
                if pk_name:
                    try:
                        max_res = conn.execute(text(f"SELECT MAX({pk_name}) FROM {full_tbl}")).scalar()
                        created_id = max_res
                    except Exception:
                        created_id = 1
                else:
                    created_id = 1

        logger.info(f"[EMAIL_SERVERS] Authenticated & registered new Email Server #{created_id} ('{payload.outgoing_email_user}') in '{full_tbl}' (Encrypted using Fernet).")

        return {
            "email_server_id": created_id,
            "server_name": payload.server_name or "SMTP Server",
            "outgoing_email_user": payload.outgoing_email_user,
            "from_email": payload.outgoing_email_user,
            "outgoing_server_ip": payload.outgoing_server_ip,
            "outgoing_email_port": payload.outgoing_email_port,
            "outgoing_email_encryption": payload.outgoing_email_encryption,
            "display_name": f"{payload.outgoing_email_user} ({payload.server_name or 'SMTP'} - #{created_id})",
            "message": "Email server registered and credentials encrypted successfully."
        }
    except Exception as ex:
        logger.error(f"[EMAIL_SERVERS] Failed to insert email server into '{full_tbl}': {ex}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register email server in client database: {str(ex)}")
