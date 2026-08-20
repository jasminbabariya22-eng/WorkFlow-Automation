from sqlalchemy import create_engine, text
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


def get_client_db():
    """FastAPI dependency yielding a session to the Client / Domain Database."""
    db = ClientSessionLocal()
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
    def get_entity_record(table_name: str, primary_key_col: str, entity_id: Any, schema: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetches a record dynamically from any client table."""
        target_schema = schema or settings.DB_SCHEMA or "public"
        full_table = f"{target_schema}.{table_name}" if target_schema else table_name
        query = text(f"SELECT * FROM {full_table} WHERE {primary_key_col} = :entity_id LIMIT 1")
        try:
            with client_engine.connect() as conn:
                result = conn.execute(query, {"entity_id": entity_id}).mappings().first()
                return dict(result) if result else None
        except Exception as e:
            logger.warning(f"ClientDatabaseAdapter: Error fetching {full_table} ID={entity_id}: {e}")
            return None

    @staticmethod
    def update_entity_record(table_name: str, primary_key_col: str, entity_id: Any, updates: Dict[str, Any], schema: Optional[str] = None) -> bool:
        """Updates fields dynamically in any client table."""
        if not updates:
            return False
        target_schema = schema or settings.DB_SCHEMA or "public"
        full_table = f"{target_schema}.{table_name}" if target_schema else table_name
        
        set_clauses = [f"{col} = :{col}" for col in updates.keys()]
        query_str = f"UPDATE {full_table} SET {', '.join(set_clauses)} WHERE {primary_key_col} = :_pk"
        
        params = dict(updates)
        params["_pk"] = entity_id
        
        try:
            with client_engine.begin() as conn:
                conn.execute(text(query_str), params)
                logger.info(f"ClientDatabaseAdapter: Successfully updated {full_table} ID={entity_id} with {list(updates.keys())}")
                return True
        except Exception as e:
            logger.warning(f"ClientDatabaseAdapter: Error updating {full_table} ID={entity_id}: {e}")
            return False

    @staticmethod
    def execute_statement(sql_query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a parameterized read/write query against the client database."""
        with client_engine.connect() as conn:
            res = conn.execute(text(sql_query), params or {})
            if res.returns_rows:
                return [dict(row) for row in res.mappings().all()]
            return []

    @staticmethod
    def get_roles(schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves user roles from the Client Database dynamically."""
        target_schema = schema or settings.DB_SCHEMA or "ers"
        for table in ["mst_user_role", "user_role", "roles"]:
            try:
                full_table = f"{target_schema}.{table}" if target_schema else table
                with client_engine.connect() as conn:
                    rows = conn.execute(
                        text(f"SELECT id, name FROM {full_table} WHERE is_deleted = 0 ORDER BY id")
                    ).mappings().all()
                    return [{"id": str(r["id"]), "name": str(r["name"])} for r in rows]
            except Exception:
                continue
        raise ValueError(f"Could not discover role table in schema '{target_schema}' of Client Database.")

    @staticmethod
    def get_users(schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves users from the Client Database dynamically."""
        target_schema = schema or settings.DB_SCHEMA or "ers"
        for table in ["mst_users", "users"]:
            try:
                full_table = f"{target_schema}.{table}" if target_schema else table
                with client_engine.connect() as conn:
                    rows = conn.execute(
                        text(f"SELECT id, first_name, last_name, email, role_id, user_type_id, dept_id FROM {full_table} WHERE is_deleted = 0 ORDER BY id LIMIT 100")
                    ).mappings().all()
                    return [
                        {
                            "id": str(u["id"]),
                            "name": f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() or str(u["id"]),
                            "email": u.get("email"),
                            "role_id": str(u.get("role_id")) if u.get("role_id") is not None else None,
                            "user_type_id": str(u.get("user_type_id")) if u.get("user_type_id") is not None else None,
                            "dept_id": str(u.get("dept_id")) if u.get("dept_id") is not None else None,
                        }
                        for u in rows
                    ]
            except Exception:
                continue
        raise ValueError(f"Could not discover user table in schema '{target_schema}' of Client Database.")

    @staticmethod
    def get_departments(schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves departments from the Client Database dynamically."""
        target_schema = schema or settings.DB_SCHEMA or "ers"
        for table in ["mst_department", "department", "departments"]:
            try:
                full_table = f"{target_schema}.{table}" if target_schema else table
                with client_engine.connect() as conn:
                    rows = conn.execute(
                        text(f"SELECT id, dept_name, dept_short_name FROM {full_table} WHERE is_deleted = 0 ORDER BY id")
                    ).mappings().all()
                    return [
                        {
                            "id": str(d["id"]),
                            "name": d.get("dept_name") or d.get("name") or str(d["id"]),
                            "short_name": d.get("dept_short_name")
                        }
                        for d in rows
                    ]
            except Exception:
                continue
        raise ValueError(f"Could not discover department table in schema '{target_schema}' of Client Database.")

    @staticmethod
    def get_tables(schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Introspects all available tables in the Client Database dynamically."""
        from sqlalchemy import inspect
        target_schema = schema or settings.DB_SCHEMA or "ers"
        try:
            inspector = inspect(client_engine)
            tables = inspector.get_table_names(schema=target_schema)
            if not tables:
                tables = inspector.get_table_names()
            return [{"table_name": t, "name": t} for t in sorted(tables)]
        except Exception as e:
            logger.warning(f"ClientDatabaseAdapter: Error introspecting tables in schema '{target_schema}': {e}")
            raise

    @staticmethod
    def get_table_columns(table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """Introspects columns, data types, primary keys, and foreign keys for a Client DB table."""
        from sqlalchemy import inspect
        target_schema = schema or settings.DB_SCHEMA or "ers"
        try:
            inspector = inspect(client_engine)
            
            all_tables = inspector.get_table_names(schema=target_schema)
            schema_to_use = target_schema
            if table_name not in all_tables:
                all_tables_default = inspector.get_table_names()
                if table_name in all_tables_default:
                    schema_to_use = None
                else:
                    raise ValueError(f"Table '{table_name}' does not exist in Client Database.")

            cols = inspector.get_columns(table_name, schema=schema_to_use)
            if not cols:
                raise ValueError(f"Table '{table_name}' has no columns or does not exist.")

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
        schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a secure, parameterized generic SELECT against the Client Database
        based on structured configuration without raw SQL strings.
        Maps result fields to workflow variables.
        """
        target_schema = schema or settings.DB_SCHEMA or "ers"
        context_vars = variables or {}

        # 1. Validate table & inspect columns
        table_info = cls.get_table_columns(table_name, schema=target_schema)
        valid_cols = {c["name"]: c for c in table_info["columns"]}

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
        query_str = f"SELECT {escaped_fields} FROM {schema_prefix}{table_name}{where_sql} LIMIT 1"

        try:
            with client_engine.connect() as conn:
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
        schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a secure, parameterized generic UPDATE against the Client Database
        based on structured configuration without raw SQL strings.
        Returns execution metadata (e.g. affectedRows).
        """
        target_schema = schema or settings.DB_SCHEMA or "ers"
        context_vars = variables or {}

        # 1. Validate table & inspect columns
        table_info = cls.get_table_columns(table_name, schema=target_schema)
        valid_cols = {c["name"]: c for c in table_info["columns"]}

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
        query_str = f"UPDATE {schema_prefix}{table_name} SET {', '.join(set_clauses)}{where_sql}"

        try:
            with client_engine.begin() as conn:
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
        schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a secure, parameterized generic INSERT against the Client Database
        based on structured configuration without raw SQL strings.
        Returns created record / generated key information where supported.
        """
        target_schema = schema or settings.DB_SCHEMA or "ers"
        context_vars = variables or {}

        # 1. Validate table & inspect columns
        table_info = cls.get_table_columns(table_name, schema=target_schema)
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
            with client_engine.begin() as conn:
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