import threading
import time
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.logger import logger

# Client / External Domain Database Engine
# This engine connects to the client's business database configured via settings.DATABASE_URL
client_engine = create_engine(
    settings.DATABASE_URL or settings.WORKFLOW_DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

ClientSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=client_engine
)

ClientBase = declarative_base()

# Alias for backward compatibility
engine = client_engine
SessionLocal = ClientSessionLocal
Base = ClientBase


class DynamicEnginePool:
    """
    Thread-safe dynamic connection pool manager for Client Database connections.
    Supports caching, live connection testing, and runtime database switching driven from the UI.
    """
    _lock = threading.Lock()
    _cached_engines: Dict[int, Engine] = {}

    @classmethod
    def build_connection_url(
        cls,
        db_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        ssl_mode: str = "disable"
    ) -> str:
        db_type = (db_type or "postgresql").lower().strip()
        encoded_pwd = quote_plus(password) if password else ""
        encoded_user = quote_plus(username) if username else ""
        
        if db_type in ("postgresql", "postgres"):
            url = f"postgresql+psycopg2://{encoded_user}:{encoded_pwd}@{host}:{port}/{database_name}"
            if ssl_mode and ssl_mode != "disable":
                url += f"?sslmode={ssl_mode}"
            return url
        elif db_type in ("mysql", "mariadb"):
            return f"mysql+pymysql://{encoded_user}:{encoded_pwd}@{host}:{port}/{database_name}"
        elif db_type in ("mssql", "sqlserver"):
            return f"mssql+pymssql://{encoded_user}:{encoded_pwd}@{host}:{port}/{database_name}"
        elif db_type in ("sqlite",):
            return f"sqlite:///{database_name}"
        else:
            return f"{db_type}://{encoded_user}:{encoded_pwd}@{host}:{port}/{database_name}"

    @classmethod
    def parse_connection_error(
        cls,
        err: Exception,
        db_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        ssl_mode: str = "disable"
    ) -> str:
        import re
        err_str = str(err)
        err_lower = err_str.lower()

        # 1. Password or Login Authentication Failure
        if any(k in err_lower for k in [
            "password authentication failed", "access denied for user", 
            "login failed for user", "fe_sendauth", "1045", "18456"
        ]):
            return f"Authentication failed: Incorrect password or invalid user '{username}'."

        # 2. User / Role does not exist
        if ("role" in err_lower and "does not exist" in err_lower) or ("unknown user" in err_lower):
            return f"User not found: Username/Role '{username}' does not exist on this database server."

        # 3. Database does not exist
        if (("database" in err_lower and "does not exist" in err_lower) or 
            "unknown database" in err_lower or "cannot open database" in err_lower or "1049" in err_lower):
            return f"Database not found: Database '{database_name}' does not exist on server '{host}:{port}'."

        # 4. Host unreachable / Connection Refused / Wrong Port
        if any(k in err_lower for k in [
            "connection refused", "10061", "could not connect to server", 
            "is the server running", "getaddrinfo failed", "name or service not known",
            "cant connect to mysql", "can't connect to", "adaptive server is unavailable"
        ]):
            return f"Server unreachable: Could not connect to host '{host}' on port {port}. Please verify the host IP/name and check if the database server is running."

        # 5. Connection Timeout
        if "timed out" in err_lower or "timeout" in err_lower:
            return f"Connection timed out: Server at '{host}:{port}' took too long to respond. Check network/firewall settings."

        # 6. SSL Error
        if "ssl" in err_lower or "certificate" in err_lower or "handshake failure" in err_lower:
            return f"SSL error: SSL negotiation failed with mode '{ssl_mode}'. Please verify SSL settings."

        # 7. Clean fallback
        clean = re.sub(r"\(Background on this error at:.*?\)", "", err_str, flags=re.DOTALL).strip()
        clean = re.sub(r"\(psycopg2\.[a-zA-Z]+\)", "", clean).strip()
        return clean or f"Connection failed: {err_str}"

    @classmethod
    def test_connection_params(
        cls,
        db_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        default_schema: Optional[str] = None,
        ssl_mode: str = "disable"
    ) -> Dict[str, Any]:
        url = cls.build_connection_url(db_type, host, port, database_name, username, password, ssl_mode)
        start_time = time.time()
        temp_engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        try:
            with temp_engine.connect() as conn:
                res = conn.execute(text("SELECT version()")).scalar()
                elapsed_ms = round((time.time() - start_time) * 1000, 2)
                return {
                    "success": True,
                    "latency_ms": elapsed_ms,
                    "version": str(res)[:120],
                    "message": f"Successfully connected to {db_type.upper()} in {elapsed_ms}ms"
                }
        except Exception as e:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            friendly_msg = cls.parse_connection_error(e, db_type, host, port, database_name, username, ssl_mode)
            return {
                "success": False,
                "latency_ms": elapsed_ms,
                "error": friendly_msg,
                "message": friendly_msg
            }
        finally:
            temp_engine.dispose()

    @classmethod
    def get_engine(cls, connection_id: Optional[int] = None) -> Engine:
        """
        Returns an active SQLAlchemy engine for the given connection_id or default active connection.
        """
        with cls._lock:
            if connection_id and connection_id in cls._cached_engines:
                return cls._cached_engines[connection_id]

            from app.core.security import decrypt_text
            from app.workflow.database import WorkflowSessionLocal
            from app.workflow.persistence.models import DatabaseConnection

            db = WorkflowSessionLocal()
            try:
                conn_rec = None
                if connection_id:
                    conn_rec = db.query(DatabaseConnection).filter(
                        DatabaseConnection.connection_id == connection_id,
                        DatabaseConnection.is_active == True
                    ).first()

                if not conn_rec:
                    conn_rec = db.query(DatabaseConnection).filter(
                        DatabaseConnection.is_default == True,
                        DatabaseConnection.is_active == True
                    ).first()

                if not conn_rec:
                    return client_engine

                pwd = decrypt_text(conn_rec.password_encrypted) if conn_rec.password_encrypted else ""
                url = cls.build_connection_url(
                    db_type=conn_rec.db_type,
                    host=conn_rec.host or "localhost",
                    port=conn_rec.port or 5432,
                    database_name=conn_rec.database_name or "postgres",
                    username=conn_rec.username or "postgres",
                    password=pwd,
                    ssl_mode=conn_rec.ssl_mode or "disable"
                )
                new_engine = create_engine(
                    url,
                    pool_size=conn_rec.pool_size or 10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
                cls._cached_engines[conn_rec.connection_id] = new_engine
                return new_engine
            except Exception as ex:
                logger.warning(f"DynamicEnginePool: Error resolving connection {connection_id}: {ex}. Falling back to default client_engine.")
                return client_engine
            finally:
                db.close()

    @classmethod
    def invalidate_engine(cls, connection_id: int):
        with cls._lock:
            engine = cls._cached_engines.pop(connection_id, None)
            if engine:
                try:
                    engine.dispose()
                except Exception:
                    pass


def get_client_db(connection_id: Optional[int] = None):
    """FastAPI dependency yielding a session to the Client / Domain Database."""
    eng = DynamicEnginePool.get_engine(connection_id)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


# Alias for dependency injection
get_db = get_client_db


class ClientDatabaseAdapter:
    """
    Generic Data Access Adapter for communicating with any client database dynamically.
    Enables workflow actions (Service Tasks, Gateway condition evaluators, entity status synchronizers)
    to query and update client records without coupling the workflow engine to specific client schemas.
    """

    @staticmethod
    def get_entity_record(table_name: str, primary_key_col: str, entity_id: Any, schema: Optional[str] = None, connection_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Fetches a record dynamically from any client table."""
        target_schema = ClientDatabaseAdapter._resolve_target_schema(schema, connection_id)
        full_table = f"{target_schema}.{table_name}" if target_schema else table_name
        query = text(f"SELECT * FROM {full_table} WHERE {primary_key_col} = :entity_id LIMIT 1")
        try:
            eng = DynamicEnginePool.get_engine(connection_id)
            with eng.connect() as conn:
                result = conn.execute(query, {"entity_id": entity_id}).mappings().first()
                return dict(result) if result else None
        except Exception as e:
            logger.warning(f"ClientDatabaseAdapter: Error fetching {full_table} ID={entity_id}: {e}")
            return None

    @staticmethod
    def update_entity_record(table_name: str, primary_key_col: str, entity_id: Any, updates: Dict[str, Any], schema: Optional[str] = None, connection_id: Optional[int] = None) -> bool:
        """Updates fields dynamically in any client table."""
        if not updates:
            return False
        target_schema = ClientDatabaseAdapter._resolve_target_schema(schema, connection_id)
        full_table = f"{target_schema}.{table_name}" if target_schema else table_name

        set_clauses = [f"{col} = :{col}" for col in updates.keys()]
        query_str = f"UPDATE {full_table} SET {', '.join(set_clauses)} WHERE {primary_key_col} = :_pk"

        params = dict(updates)
        params["_pk"] = entity_id

        try:
            eng = DynamicEnginePool.get_engine(connection_id)
            with eng.begin() as conn:
                conn.execute(text(query_str), params)
                logger.info(f"ClientDatabaseAdapter: Successfully updated {full_table} ID={entity_id} with {list(updates.keys())}")
                return True
        except Exception as e:
            logger.warning(f"ClientDatabaseAdapter: Error updating {full_table} ID={entity_id}: {e}")
            return False

    @staticmethod
    def execute_statement(sql_query: str, params: Optional[Dict[str, Any]] = None, connection_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Executes a parameterized read/write query against the client database."""
        eng = DynamicEnginePool.get_engine(connection_id)
        with eng.connect() as conn:
            res = conn.execute(text(sql_query), params or {})
            if res.returns_rows:
                return [dict(row) for row in res.mappings().all()]
            return []

    @staticmethod
    def _resolve_target_schema(schema: Optional[str], connection_id: Optional[int]) -> Optional[str]:
        if schema:
            return schema
        if connection_id:
            from app.workflow.database import WorkflowSessionLocal
            from app.workflow.persistence.models import DatabaseConnection
            db = WorkflowSessionLocal()
            try:
                conn_rec = db.query(DatabaseConnection).filter(DatabaseConnection.connection_id == connection_id).first()
                if conn_rec and conn_rec.default_schema:
                    return conn_rec.default_schema
            finally:
                db.close()
        return settings.DB_SCHEMA or "public"

    @staticmethod
    def _build_active_filter(col_meta_dict: dict) -> str:
        if "is_deleted" in col_meta_dict:
            dtype = str(col_meta_dict["is_deleted"].get("type", "")).lower()
            if "bool" in dtype:
                return "WHERE is_deleted IS FALSE"
            return "WHERE is_deleted = 0"
        if "is_active" in col_meta_dict:
            dtype = str(col_meta_dict["is_active"].get("type", "")).lower()
            if "bool" in dtype:
                return "WHERE is_active IS TRUE"
            return "WHERE is_active = 1"
        return ""

    @staticmethod
    def get_roles(schema: Optional[str] = None, connection_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves user roles from the Client Database dynamically. Auto-adapts to column naming conventions."""
        from sqlalchemy import inspect
        try:
            eng = DynamicEnginePool.get_engine(connection_id)
            inspector = inspect(eng)
            target_schema = ClientDatabaseAdapter._resolve_target_schema(schema, connection_id)

            schema_tables = set(inspector.get_table_names(schema=target_schema)) if target_schema else set()
            all_tables = set(inspector.get_table_names())

            role_candidates = ["mst_user_role", "user_role", "roles", "user_roles", "tbl_roles", "mst_roles", "role"]
            found_table = None
            active_schema = None

            for candidate in role_candidates:
                if candidate in schema_tables:
                    found_table = candidate
                    active_schema = target_schema
                    break
                elif candidate in all_tables:
                    found_table = candidate
                    active_schema = None
                    break

            if not found_table:
                return []

            cols_meta = inspector.get_columns(found_table, schema=active_schema)
            col_meta_dict = {c["name"].lower(): c for c in cols_meta}
            col_names = list(col_meta_dict.keys())

            id_col = next((c for c in ["role_id", "user_role_id", "id", "role_code", "code"] if c in col_names), col_names[0])
            name_col = next((c for c in ["role_name", "user_role_name", "name", "role_code", "title", "description"] if c in col_names), id_col)

            filter_clause = ClientDatabaseAdapter._build_active_filter(col_meta_dict)
            table_ref = f"{active_schema}.{found_table}" if active_schema else found_table
            query = f"SELECT {id_col} AS id, {name_col} AS name FROM {table_ref} {filter_clause} ORDER BY {id_col}"

            with eng.connect() as conn:
                rows = conn.execute(text(query)).mappings().all()
                return [{"id": str(r["id"]), "name": str(r["name"])} for r in rows]
        except Exception as ex:
            logger.info(f"ClientDatabaseAdapter: Note: No role tables in connection {connection_id}: {ex}")
            return []

    @staticmethod
    def get_users(schema: Optional[str] = None, connection_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves users from the Client Database dynamically. Auto-adapts to column naming conventions."""
        from sqlalchemy import inspect
        try:
            eng = DynamicEnginePool.get_engine(connection_id)
            inspector = inspect(eng)
            target_schema = ClientDatabaseAdapter._resolve_target_schema(schema, connection_id)

            schema_tables = set(inspector.get_table_names(schema=target_schema)) if target_schema else set()
            all_tables = set(inspector.get_table_names())

            user_candidates = ["mst_users", "users", "tbl_users", "user_master", "user", "app_users", "employees", "mst_employees"]
            found_table = None
            active_schema = None

            for candidate in user_candidates:
                if candidate in schema_tables:
                    found_table = candidate
                    active_schema = target_schema
                    break
                elif candidate in all_tables:
                    found_table = candidate
                    active_schema = None
                    break

            if not found_table:
                return []

            cols_meta = inspector.get_columns(found_table, schema=active_schema)
            col_meta_dict = {c["name"].lower(): c for c in cols_meta}
            col_names = list(col_meta_dict.keys())

            id_col = next((c for c in ["user_id", "id", "employee_id", "emp_id", "code"] if c in col_names), col_names[0])
            email_col = next((c for c in ["email", "email_id", "mail"] if c in col_names), None)

            has_first_last = "first_name" in col_names and "last_name" in col_names
            name_col = next((c for c in ["full_name", "user_name", "username", "name", "employee_name"] if c in col_names), None)

            role_id_col = next((c for c in ["role_id", "user_role_id", "role"] if c in col_names), None)
            dept_id_col = next((c for c in ["dept_id", "department_id", "department"] if c in col_names), None)

            filter_clause = ClientDatabaseAdapter._build_active_filter(col_meta_dict)
            table_ref = f"{active_schema}.{found_table}" if active_schema else found_table

            select_fields = [f"{id_col} AS id"]
            if has_first_last:
                select_fields.append("first_name")
                select_fields.append("last_name")
            elif name_col:
                select_fields.append(f"{name_col} AS name")
            else:
                select_fields.append(f"{id_col} AS name")

            if email_col:
                select_fields.append(f"{email_col} AS email")
            if role_id_col:
                select_fields.append(f"{role_id_col} AS role_id")
            if dept_id_col:
                select_fields.append(f"{dept_id_col} AS dept_id")

            query = f"SELECT {', '.join(select_fields)} FROM {table_ref} {filter_clause} ORDER BY {id_col} LIMIT 100"

            with eng.connect() as conn:
                rows = conn.execute(text(query)).mappings().all()
                result = []
                for u in rows:
                    if has_first_last:
                        display_name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or str(u["id"])
                    else:
                        display_name = str(u.get("name") or u["id"])
                    result.append({
                        "id": str(u["id"]),
                        "name": display_name,
                        "email": u.get("email"),
                        "role_id": str(u.get("role_id")) if u.get("role_id") is not None else None,
                        "dept_id": str(u.get("dept_id")) if u.get("dept_id") is not None else None
                    })
                return result
        except Exception as ex:
            logger.info(f"ClientDatabaseAdapter: Note: No user tables in connection {connection_id}: {ex}")
            return []

    @staticmethod
    def get_departments(schema: Optional[str] = None, connection_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves departments from the Client Database dynamically. Auto-adapts to column naming conventions."""
        from sqlalchemy import inspect
        try:
            eng = DynamicEnginePool.get_engine(connection_id)
            inspector = inspect(eng)
            target_schema = ClientDatabaseAdapter._resolve_target_schema(schema, connection_id)

            schema_tables = set(inspector.get_table_names(schema=target_schema)) if target_schema else set()
            all_tables = set(inspector.get_table_names())

            dept_candidates = ["mst_department", "department", "departments", "tbl_department", "dept"]
            found_table = None
            active_schema = None

            for candidate in dept_candidates:
                if candidate in schema_tables:
                    found_table = candidate
                    active_schema = target_schema
                    break
                elif candidate in all_tables:
                    found_table = candidate
                    active_schema = None
                    break

            if not found_table:
                return []

            cols_meta = inspector.get_columns(found_table, schema=active_schema)
            col_meta_dict = {c["name"].lower(): c for c in cols_meta}
            col_names = list(col_meta_dict.keys())

            id_col = next((c for c in ["dept_id", "department_id", "id", "code"] if c in col_names), col_names[0])
            name_col = next((c for c in ["dept_name", "department_name", "name", "title"] if c in col_names), id_col)
            short_name_col = next((c for c in ["dept_short_name", "short_name", "code"] if c in col_names), None)

            filter_clause = ClientDatabaseAdapter._build_active_filter(col_meta_dict)
            table_ref = f"{active_schema}.{found_table}" if active_schema else found_table

            select_fields = [f"{id_col} AS id", f"{name_col} AS name"]
            if short_name_col:
                select_fields.append(f"{short_name_col} AS short_name")

            query = f"SELECT {', '.join(select_fields)} FROM {table_ref} {filter_clause} ORDER BY {id_col}"

            with eng.connect() as conn:
                rows = conn.execute(text(query)).mappings().all()
                return [
                    {
                        "id": str(d["id"]),
                        "name": str(d.get("name") or d["id"]),
                        "short_name": d.get("short_name")
                    }
                    for d in rows
                ]
        except Exception as ex:
            logger.info(f"ClientDatabaseAdapter: Note: No department tables in connection {connection_id}: {ex}")
            return []

    @staticmethod
    def get_tables(schema: Optional[str] = None, connection_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Introspects all available tables in the Client Database dynamically."""
        from sqlalchemy import inspect
        target_schema = schema or settings.DB_SCHEMA or "ers"
        try:
            eng = DynamicEnginePool.get_engine(connection_id)
            inspector = inspect(eng)
            tables = inspector.get_table_names(schema=target_schema)
            if not tables:
                tables = inspector.get_table_names()
            return [{"table_name": t, "name": t} for t in sorted(tables)]
        except Exception as e:
            logger.warning(f"ClientDatabaseAdapter: Error introspecting tables in schema '{target_schema}': {e}")
            raise

    @staticmethod
    def get_table_columns(table_name: str, schema: Optional[str] = None, connection_id: Optional[int] = None) -> Dict[str, Any]:
        """Introspects columns, data types, primary keys, and foreign keys for a Client DB table."""
        from sqlalchemy import inspect
        target_schema = schema or settings.DB_SCHEMA or "ers"
        clean_table = table_name
        if "." in table_name:
            parts = table_name.split(".", 1)
            target_schema = parts[0]
            clean_table = parts[1]

        try:
            target_eng = DynamicEnginePool.get_engine(connection_id)
            inspector = inspect(target_eng)
            
            all_tables = inspector.get_table_names(schema=target_schema)
            schema_to_use = target_schema
            if clean_table not in all_tables:
                all_tables_default = inspector.get_table_names()
                if clean_table in all_tables_default:
                    schema_to_use = None
                else:
                    raise ValueError(f"Table '{table_name}' does not exist in Client Database.")

            cols = inspector.get_columns(clean_table, schema=schema_to_use)
            if not cols:
                raise ValueError(f"Table '{clean_table}' has no columns or does not exist.")

            pk_constraint = inspector.get_pk_constraint(table_name, schema=schema_to_use) or {}
            pk_cols = set(pk_constraint.get("constrained_columns") or [])

            fk_list = inspector.get_foreign_keys(table_name, schema=schema_to_use) or []
            fk_map = {}
            for fk in fk_list:
                constrained_cols = fk.get("constrained_columns") or []
                referred_table = fk.get("referred_table")
                referred_cols = fk.get("referred_columns") or []
                for idx, ccol in enumerate(constrained_cols):
                    ref_col = referred_cols[idx] if idx < len(referred_cols) else None
                    fk_map[ccol] = {
                        "referred_table": referred_table,
                        "referred_column": ref_col
                    }

            column_details = []
            for c in cols:
                c_name = c["name"]
                column_details.append({
                    "name": c_name,
                    "data_type": str(c["type"]).lower(),
                    "type": str(c["type"]).lower(),
                    "nullable": bool(c.get("nullable", True)),
                    "primary_key": c_name in pk_cols,
                    "foreign_key": fk_map.get(c_name)
                })

            return {
                "table_name": table_name,
                "columns": column_details,
                "primary_keys": list(pk_cols)
            }
        except Exception as e:
            logger.warning(f"ClientDatabaseAdapter: Error introspecting columns for '{table_name}': {e}")
            raise

    @classmethod
    def read_entity_record(
        cls,
        table_name: str,
        fields: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        variables: Optional[Dict[str, Any]] = None,
        result_mapping: Optional[Dict[str, str]] = None,
        schema: Optional[str] = None,
        connection_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes a secure, parameterized generic SELECT against the Client Database
        based on structured configuration without raw SQL strings.
        Maps result fields to workflow variables.
        """
        target_schema = schema or settings.DB_SCHEMA or "ers"
        clean_table = table_name
        if "." in table_name:
            parts = table_name.split(".", 1)
            target_schema = parts[0]
            clean_table = parts[1]

        context_vars = variables or {}

        # 1. Validate table & inspect columns
        table_info = cls.get_table_columns(clean_table, schema=target_schema, connection_id=connection_id)
        valid_cols = {c["name"]: c for c in table_info["columns"]}
        pk_cols = table_info.get("primary_keys") or []
        primary_key = pk_cols[0] if pk_cols else "id"

        # 2. Validate requested fields
        selected_fields = fields or list(valid_cols.keys())
        for f in selected_fields:
            if f not in valid_cols:
                raise ValueError(f"Field '{f}' does not exist on Client DB table '{table_name}'. Valid fields: {list(valid_cols.keys())}")

        # 3. Build parameterized query
        allowed_operators = {
            "=": "=",
            "==": "=",
            "equals": "=",
            "!=": "!=",
            "<>": "!=",
            "not_equals": "!=",
            ">": ">",
            "greater_than": ">",
            "<": "<",
            "less_than": "<",
            ">=": ">=",
            "greater_than_or_equals": ">=",
            "<=": "<=",
            "less_than_or_equals": "<=",
            "like": "LIKE",
            "ilike": "ILIKE"
        }

        where_clauses = []
        bind_params = {}
        filter_list = filters or []

        for idx, flt in enumerate(filter_list):
            flt_field = flt.get("field")
            if flt_field == "id" and "id" not in valid_cols:
                flt_field = primary_key

            if not flt_field or flt_field not in valid_cols:
                raise ValueError(f"Filter references invalid field '{flt_field}' for table '{table_name}'.")

            op_raw = str(flt.get("operator", "=")).strip().lower()
            if op_raw in ("is null", "null", "is_null"):
                where_clauses.append(f"{flt_field} IS NULL")
                continue
            if op_raw in ("is not null", "not null", "is_not_null"):
                where_clauses.append(f"{flt_field} IS NOT NULL")
                continue

            if op_raw not in allowed_operators:
                raise ValueError(f"Unsupported filter operator '{flt.get('operator')}'. Allowed: {list(allowed_operators.keys())}")

            sql_op = allowed_operators[op_raw]

            # Resolve template placeholders in value
            raw_val = flt.get("value")
            resolved_val = cls._resolve_template_value(raw_val, context_vars)

            param_name = f"param_{idx}_{flt_field}"
            where_clauses.append(f"{flt_field} {sql_op} :{param_name}")
            bind_params[param_name] = resolved_val

        # Construct safe SELECT statement
        escaped_fields = ", ".join(selected_fields)
        schema_prefix = f"{target_schema}." if target_schema else ""
        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query_str = f"SELECT {escaped_fields} FROM {schema_prefix}{clean_table}{where_sql} LIMIT 1"

        try:
            target_eng = DynamicEnginePool.get_engine(connection_id)
            with target_eng.connect() as conn:
                result_row = conn.execute(text(query_str), bind_params).mappings().first()
        except Exception as e:
            # If type mismatch / invalid input syntax occurs (e.g. string passed to integer parameter), treat safely as no match or raise sanitized error
            err_str = str(e).lower()
            if "invalid input syntax" in err_str or "dataerror" in err_str or "conversion failed" in err_str:
                logger.warning(f"ClientDatabaseAdapter: Query parameter type mismatch on '{table_name}': {e}")
                return {}
            logger.error(f"ClientDatabaseAdapter: Error executing generic read on '{table_name}': {e}")
            raise RuntimeError(f"Client Database query execution failed: {str(e)}")

        if not result_row:
            logger.info(f"ClientDatabaseAdapter: No record found in '{table_name}' matching filters.")
            return {}

        raw_result = dict(result_row)

        # 4. Map output to workflow variables
        mapped_vars = {}
        if result_mapping and isinstance(result_mapping, dict):
            for client_col, wf_var_name in result_mapping.items():
                if client_col in raw_result:
                    mapped_vars[wf_var_name] = raw_result[client_col]
        else:
            mapped_vars = dict(raw_result)

        return mapped_vars

    @classmethod
    def update_entity_record_generic(
        cls,
        table_name: str,
        updates: Dict[str, Any],
        filters: Optional[List[Dict[str, Any]]] = None,
        variables: Optional[Dict[str, Any]] = None,
        allow_full_table_update: bool = False,
        result_mapping: Optional[Dict[str, str]] = None,
        schema: Optional[str] = None,
        connection_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes a secure, parameterized generic UPDATE against the Client Database
        based on structured configuration without raw SQL strings.
        Returns execution metadata (e.g. affectedRows).
        """
        target_schema = schema or settings.DB_SCHEMA or "ers"
        clean_table = table_name
        if "." in table_name:
            parts = table_name.split(".", 1)
            target_schema = parts[0]
            clean_table = parts[1]

        context_vars = variables or {}

        # 1. Validate table & inspect columns
        table_info = cls.get_table_columns(clean_table, schema=target_schema, connection_id=connection_id)
        valid_cols = {c["name"]: c for c in table_info["columns"]}
        pk_cols = table_info.get("primary_keys") or []
        primary_key = pk_cols[0] if pk_cols else "id"

        # 2. Validate update fields
        if not updates or not isinstance(updates, dict):
            raise ValueError(f"DB_UPDATE action requires a non-empty 'updates' dictionary for table '{table_name}'.")

        for col_name in updates.keys():
            if col_name not in valid_cols:
                raise ValueError(f"Update field '{col_name}' does not exist on Client DB table '{table_name}'. Valid fields: {list(valid_cols.keys())}")

        # 3. Validate safety: require filters unless explicit allow_full_table_update
        filter_list = filters or []
        if not filter_list and not allow_full_table_update:
            raise ValueError(f"Unrestricted UPDATE on '{table_name}' rejected for safety. Provide 'filters' or set 'allowFullTableUpdate': true.")

        # 4. Build SET clauses with bind params
        set_clauses = []
        bind_params = {}

        for idx, (col_name, raw_val) in enumerate(updates.items()):
            resolved_val = cls._resolve_template_value(raw_val, context_vars) if raw_val is not None else None
            param_name = f"u_param_{idx}_{col_name}"
            set_clauses.append(f"{col_name} = :{param_name}")
            bind_params[param_name] = resolved_val

        # 5. Build WHERE clauses with bind params
        allowed_operators = {
            "=": "=", "==": "=", "equals": "=",
            "!=": "!=", "<>": "!=", "not_equals": "!=",
            ">": ">", "greater_than": ">",
            "<": "<", "less_than": "<",
            ">=": ">=", "greater_than_or_equals": ">=",
            "<=": "<=", "less_than_or_equals": "<=",
            "like": "LIKE", "ilike": "ILIKE"
        }

        where_clauses = []
        for idx, flt in enumerate(filter_list):
            flt_field = flt.get("field")
            if flt_field == "id" and "id" not in valid_cols:
                flt_field = primary_key

            if not flt_field or flt_field not in valid_cols:
                raise ValueError(f"Filter references invalid field '{flt_field}' for table '{table_name}'.")

            op_raw = str(flt.get("operator", "=")).strip().lower()
            if op_raw in ("is null", "null", "is_null"):
                where_clauses.append(f"{flt_field} IS NULL")
                continue
            if op_raw in ("is not null", "not null", "is_not_null"):
                where_clauses.append(f"{flt_field} IS NOT NULL")
                continue

            if op_raw not in allowed_operators:
                raise ValueError(f"Unsupported filter operator '{flt.get('operator')}'. Allowed: {list(allowed_operators.keys())}")

            sql_op = allowed_operators[op_raw]
            raw_val = flt.get("value")
            resolved_val = cls._resolve_template_value(raw_val, context_vars) if raw_val is not None else None

            param_name = f"f_param_{idx}_{flt_field}"
            where_clauses.append(f"{flt_field} {sql_op} :{param_name}")
            bind_params[param_name] = resolved_val

        schema_prefix = f"{target_schema}." if target_schema else ""
        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query_str = f"UPDATE {schema_prefix}{clean_table} SET {', '.join(set_clauses)}{where_sql}"

        try:
            target_eng = DynamicEnginePool.get_engine(connection_id)
            with target_eng.begin() as conn:
                res = conn.execute(text(query_str), bind_params)
                affected_count = res.rowcount if res.rowcount is not None else 0
        except Exception as e:
            logger.error(f"ClientDatabaseAdapter: Error executing generic update on '{table_name}': {e}")
            raise RuntimeError(f"Client Database update execution failed: {str(e)}")

        result_data = {
            "affectedRows": affected_count,
            "affected_rows": affected_count,
            "table": table_name,
            "status": "SUCCESS"
        }

        mapped_vars = {}
        if result_mapping and isinstance(result_mapping, dict):
            for k, var_name in result_mapping.items():
                if k in result_data:
                    mapped_vars[var_name] = result_data[k]
                elif k in ("affectedRows", "affected_rows", "count", "rows"):
                    mapped_vars[var_name] = affected_count
        else:
            mapped_vars = {"affectedRows": affected_count}

        return mapped_vars

    @classmethod
    def create_entity_record_generic(
        cls,
        table_name: str,
        values: Dict[str, Any],
        variables: Optional[Dict[str, Any]] = None,
        result_mapping: Optional[Dict[str, str]] = None,
        schema: Optional[str] = None,
        connection_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes a secure, parameterized generic INSERT against the Client Database
        based on structured configuration without raw SQL strings.
        Returns created record / generated key information where supported.
        """
        target_schema = schema or settings.DB_SCHEMA or "ers"
        context_vars = variables or {}

        # 1. Validate table & inspect columns
        table_info = cls.get_table_columns(table_name, schema=target_schema, connection_id=connection_id)
        valid_cols = {c["name"]: c for c in table_info["columns"]}
        pk_cols = table_info.get("primary_keys") or []

        # 2. Validate insert fields
        if not values or not isinstance(values, dict):
            raise ValueError(f"DB_CREATE action requires a non-empty 'values' dictionary for table '{table_name}'.")

        for col_name in values.keys():
            if col_name not in valid_cols:
                raise ValueError(f"Insert field '{col_name}' does not exist on Client DB table '{table_name}'. Valid fields: {list(valid_cols.keys())}")

        # 3. Build INSERT clauses with bind params
        col_names = []
        param_names = []
        bind_params = {}

        for idx, (col_name, raw_val) in enumerate(values.items()):
            resolved_val = cls._resolve_template_value(raw_val, context_vars) if raw_val is not None else None
            p_name = f"i_param_{idx}_{col_name}"
            col_names.append(col_name)
            param_names.append(f":{p_name}")
            bind_params[p_name] = resolved_val

        schema_prefix = f"{target_schema}." if target_schema else ""
        
        # If table has a primary key and database is PostgreSQL, add RETURNING pk_col
        returning_clause = ""
        pk_to_return = pk_cols[0] if pk_cols else None
        if pk_to_return:
            returning_clause = f" RETURNING {pk_to_return}"

        query_str = f"INSERT INTO {schema_prefix}{table_name} ({', '.join(col_names)}) VALUES ({', '.join(param_names)}){returning_clause}"

        created_id = None
        try:
            target_eng = DynamicEnginePool.get_engine(connection_id)
            with target_eng.begin() as conn:
                res = conn.execute(text(query_str), bind_params)
                if returning_clause and res.returns_rows:
                    row = res.mappings().first()
                    if row and pk_to_return in row:
                        created_id = row[pk_to_return]
        except Exception as e:
            logger.error(f"ClientDatabaseAdapter: Error executing generic insert on '{table_name}': {e}")
            raise RuntimeError(f"Client Database insert execution failed: {str(e)}")

        result_data = {
            "created_id": created_id,
            "id": created_id,
            "table": table_name,
            "status": "SUCCESS"
        }
        if pk_to_return and created_id is not None:
            result_data[pk_to_return] = created_id

        # Also include any inserted values for mapping
        for k, v in bind_params.items():
            orig_col = k.split("_", 3)[-1]
            result_data[orig_col] = v

        # Result mapping
        mapped_vars = {}
        if result_mapping and isinstance(result_mapping, dict):
            for k, var_name in result_mapping.items():
                if k in result_data:
                    mapped_vars[var_name] = result_data[k]
                elif k in ("id", "created_id", "generated_id", "primary_key", "pk") and created_id is not None:
                    mapped_vars[var_name] = created_id
        else:
            if created_id is not None:
                mapped_vars["created_id"] = created_id
                if pk_to_return:
                    mapped_vars[pk_to_return] = created_id

        return mapped_vars

    @staticmethod
    def _resolve_template_value(val: Any, context_vars: Dict[str, Any]) -> Any:
        """Resolves template expressions like {{entity.id}} or {{variables.score}} from runtime context."""
        if not isinstance(val, str):
            return val
        
        def _get_val_from_path(kpath: List[str]) -> Any:
            # 1. Try exact path in context_vars
            cur = context_vars
            found = True
            for k in kpath:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    found = False
                    break
            if found:
                return cur

            # 2. If path starts with "variables" or "workflow", try stripped path
            if len(kpath) > 1 and kpath[0] in ("variables", "workflow"):
                sub_path = kpath[1:]
                cur = context_vars
                found = True
                for k in sub_path:
                    if isinstance(cur, dict) and k in cur:
                        cur = cur[k]
                    else:
                        found = False
                        break
                if found:
                    return cur

            # 3. If kpath is single key and exists in context_vars["variables"]
            if len(kpath) == 1 and isinstance(context_vars.get("variables"), dict) and kpath[0] in context_vars["variables"]:
                return context_vars["variables"][kpath[0]]

            return None

        import re
        match = re.match(r"^\s*\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}\s*$", val)
        if match:
            kpath = match.group(1).split(".")
            return _get_val_from_path(kpath)

        def _repl(m):
            kpath = m.group(1).split(".")
            res = _get_val_from_path(kpath)
            return str(res) if res is not None else ""

        return re.sub(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}", _repl, val)

    @staticmethod
    def get_entities(schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Introspects available business entity tables in the Client Database."""
        return ClientDatabaseAdapter.get_tables(schema=schema)

    @staticmethod
    def get_entity_fields(entity_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Introspects columns/fields for a specific entity in the Client Database."""
        table_info = ClientDatabaseAdapter.get_table_columns(entity_name, schema=schema)
        return table_info.get("columns", [])

    @staticmethod
    def get_statuses(schema: Optional[str] = None, entity_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves domain entity lifecycle statuses from the Client Database dynamically."""
        target_schema = schema or settings.DB_SCHEMA or "ers"
        for table in ["mst_status", "status", "statuses"]:
            try:
                full_table = f"{target_schema}.{table}" if target_schema else table
                with client_engine.connect() as conn:
                    rows = conn.execute(
                        text(f"SELECT id, status_name, type FROM {full_table} WHERE is_deleted = 0 ORDER BY id")
                    ).mappings().all()
                    return [
                        {
                            "id": str(s["id"]),
                            "name": s.get("status_name") or s.get("name") or str(s["id"]),
                            "type": s.get("type")
                        }
                        for s in rows
                    ]
            except Exception:
                continue
        raise ValueError(f"Could not discover status table in schema '{target_schema}' of Client Database.")

    @staticmethod
    def get_actions(schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves custom workflow transition actions from the Client Database if an action table exists.
        Returns an empty list if the Client Database does not define custom action tables.
        """
        target_schema = schema or settings.DB_SCHEMA or "ers"
        for table in ["mst_action", "actions", "mst_workflow_action"]:
            try:
                full_table = f"{target_schema}.{table}" if target_schema else table
                with client_engine.connect() as conn:
                    rows = conn.execute(
                        text(f"SELECT id, action_code, name, description FROM {full_table} WHERE is_deleted = 0 ORDER BY id")
                    ).mappings().all()
                    return [
                        {
                            "id": str(r["id"]),
                            "action_code": str(r.get("action_code") or r.get("name")).upper().replace(" ", "_"),
                            "name": str(r.get("name") or r.get("action_code")),
                            "description": r.get("description") or f"Action {r.get('name')}"
                        }
                        for r in rows
                    ]
            except Exception:
                continue
        return []

    @staticmethod
    def get_user_profile(user_id: int, schema: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves user metadata (role and department) dynamically from the Client Database.
        """
        target_schema = schema or settings.DB_SCHEMA or "ers"
        try:
            with client_engine.connect() as conn:
                user_table = f"{target_schema}.mst_users" if target_schema else "mst_users"
                role_table = f"{target_schema}.mst_user_role" if target_schema else "mst_user_role"
                dept_table = f"{target_schema}.mst_department" if target_schema else "mst_department"

                query = text(f"""
                    SELECT u.id, u.first_name, u.last_name, u.email, 
                           u.role_id, r.name as role_name,
                           u.dept_id, d.dept_name as department_name
                    FROM {user_table} u
                    LEFT JOIN {role_table} r ON u.role_id = r.id
                    LEFT JOIN {dept_table} d ON u.dept_id = d.id
                    WHERE u.id = :user_id AND u.is_deleted = 0
                """)
                row = conn.execute(query, {"user_id": user_id}).mappings().first()
                if row:
                    return {
                        "id": str(row["id"]),
                        "name": f"{row.get('first_name', '')} {row.get('last_name', '')}".strip() or str(row["id"]),
                        "email": row.get("email"),
                        "role_id": str(row["role_id"]) if row.get("role_id") is not None else None,
                        "role_name": row.get("role_name"),
                        "dept_id": str(row["dept_id"]) if row.get("dept_id") is not None else None,
                        "department_name": row.get("department_name")
                    }
        except Exception as e:
            logger.warning(f"ClientDatabaseAdapter: Error fetching user profile for user_id={user_id}: {e}")
        return None