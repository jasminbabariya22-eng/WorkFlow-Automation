import re
from typing import Dict, Any, Callable, Optional
from app.core.logger import logger


class ConditionEvaluator:
    """
    Safely evaluates condition strings against runtime variables/action codes
    without using arbitrary Python eval().
    """

    @classmethod
    def evaluate(cls, condition_str: Optional[str], action: str, variables: Dict[str, Any]) -> bool:
        if not condition_str:
            # If no condition is specified, default to True (unconditional edge)
            return True

        cond = condition_str.strip()

        # 1. Direct action matching (e.g. "APPROVE", "REJECT", "SUBMIT", "RESUBMIT")
        if cond.upper() == action.upper():
            return True

        # 2. Simple equality: action == 'APPROVE' or action == "APPROVE"
        action_eq_match = re.match(r"^\s*action\s*==\s*['\"]([^'\"]+)['\"]\s*$", cond, re.IGNORECASE)
        if action_eq_match:
            return action_eq_match.group(1).strip().upper() == action.upper()

        # 3. Simple inequality: action != 'REJECT'
        action_neq_match = re.match(r"^\s*action\s*!=\s*['\"]([^'\"]+)['\"]\s*$", cond, re.IGNORECASE)
        if action_neq_match:
            return action_neq_match.group(1).strip().upper() != action.upper()

        # 4. Variable boolean check: e.g. "approved == true" or "is_high_risk == true"
        bool_match = re.match(r"^\s*(?:\{\{\s*)?([a-zA-Z0-9_.]+)(?:\s*\}\})?\s*==\s*(true|false)\s*$", cond, re.IGNORECASE)
        if bool_match:
            var_name, expected_bool = bool_match.group(1), bool_match.group(2).lower() == "true"
            from app.core.database import ClientDatabaseAdapter
            actual_val = ClientDatabaseAdapter._resolve_template_value(f"{{{{{var_name}}}}}", variables)
            return bool(actual_val) == expected_bool

        # 5. String comparison: e.g. status == "ACTIVE" or {{customer_status}} == "ACTIVE" or dept_name != ""
        str_match = re.match(r"^\s*(?:\{\{\s*)?([a-zA-Z0-9_.]+)(?:\s*\}\})?\s*(==|!=)\s*['\"]([^'\"]*)['\"]\s*$", cond)
        if str_match:
            var_name, op, expected_str = str_match.group(1), str_match.group(2), str_match.group(3)
            from app.core.database import ClientDatabaseAdapter
            actual_val = ClientDatabaseAdapter._resolve_template_value(f"{{{{{var_name}}}}}", variables)
            if op == "==":
                return str(actual_val or "").strip().upper() == expected_str.strip().upper()
            if op == "!=":
                return str(actual_val or "").strip().upper() != expected_str.strip().upper()

        # 6. Numeric comparison: e.g. "amount > 100000" or "risk_score >= 70"
        num_match = re.match(r"^\s*(?:\{\{\s*)?([a-zA-Z0-9_.]+)(?:\s*\}\})?\s*(>|<|>=|<=|==|!=)\s*([0-9.]+)\s*$", cond)
        if num_match:
            var_name, op, val_str = num_match.group(1), num_match.group(2), float(num_match.group(3))
            from app.core.database import ClientDatabaseAdapter
            actual_val = ClientDatabaseAdapter._resolve_template_value(f"{{{{{var_name}}}}}", variables)
            if actual_val is None:
                return False
            try:
                actual_num = float(actual_val)
                if op == ">": return actual_num > val_str
                if op == "<": return actual_num < val_str
                if op == ">=": return actual_num >= val_str
                if op == "<=": return actual_num <= val_str
                if op == "==": return actual_num == val_str
                if op == "!=": return actual_num != val_str
            except (ValueError, TypeError):
                return False

        # Fallback: case-insensitive equality against action
        return cond.upper() == action.upper()

    @classmethod
    def evaluate_node_condition(cls, config: Dict[str, Any], variables: Dict[str, Any]) -> bool:
        """
        Evaluates a generic Condition Node's configuration ({field, operator, value} or expression)
        against the runtime context variables.
        """
        if not config:
            return True

        field = config.get("field")
        operator = str(config.get("operator", "equals")).strip().lower()
        expected_val = config.get("value")

        # If full expression is provided instead of field/operator/value
        if not field:
            expr = config.get("expression") or config.get("condition")
            if expr:
                return cls.evaluate(expr, action="", variables=variables)
            return True

        actual_val = variables.get(field)
        if actual_val is None:
            # Check nested dictionary lookup if field has dot notation
            parts = field.split(".")
            cur = variables
            for p in parts:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    cur = None
                    break
            actual_val = cur

        # Normalize operator names
        if operator in ("equals", "==", "eq", "is"):
            if actual_val is None:
                return expected_val is None or expected_val == "" or str(expected_val).lower() == "none"
            if isinstance(actual_val, bool) or str(expected_val).lower() in ("true", "false"):
                return bool(actual_val) == (str(expected_val).lower() == "true")
            try:
                return float(actual_val) == float(expected_val)
            except (ValueError, TypeError):
                return str(actual_val).strip().upper() == str(expected_val).strip().upper()

        elif operator in ("not_equals", "!=", "neq", "is_not"):
            if actual_val is None:
                return expected_val is not None and expected_val != "" and str(expected_val).lower() != "none"
            if isinstance(actual_val, bool) or str(expected_val).lower() in ("true", "false"):
                return bool(actual_val) != (str(expected_val).lower() == "true")
            try:
                return float(actual_val) != float(expected_val)
            except (ValueError, TypeError):
                return str(actual_val).strip().upper() != str(expected_val).strip().upper()

        elif operator in ("greater_than", ">", "gt"):
            try:
                return float(actual_val) > float(expected_val)
            except (ValueError, TypeError):
                return False

        elif operator in ("less_than", "<", "lt"):
            try:
                return float(actual_val) < float(expected_val)
            except (ValueError, TypeError):
                return False

        elif operator in ("greater_than_or_equals", ">=", "gte"):
            try:
                return float(actual_val) >= float(expected_val)
            except (ValueError, TypeError):
                return False

        elif operator in ("less_than_or_equals", "<=", "lte"):
            try:
                return float(actual_val) <= float(expected_val)
            except (ValueError, TypeError):
                return False

        elif operator in ("contains", "in"):
            if actual_val is None:
                return False
            return str(expected_val).lower() in str(actual_val).lower()

        # Default fallback
        return str(actual_val).strip().upper() == str(expected_val).strip().upper()


class ActionRegistry:
    """
    Extensible registry for automated action handlers executed by ACTION nodes.
    """
    _handlers: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = {}

    @classmethod
    def register(cls, action_type: str, handler: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]):
        cls._handlers[action_type.upper()] = handler

    @classmethod
    def execute(cls, action_type: str, config: Dict[str, Any], context_vars: Dict[str, Any]) -> Dict[str, Any]:
        if config.get("simulate_error") or config.get("fail"):
            err_msg = config.get("error_message") or f"Simulated failure in action '{action_type}'"
            logger.error(f"ActionRegistry: {err_msg}")
            raise RuntimeError(err_msg)

        handler = cls._handlers.get(action_type.upper())
        if handler:
            try:
                return handler(config, context_vars)
            except Exception as e:
                logger.error(f"ActionRegistry: Execution of '{action_type}' failed: {e}")
                raise e
        else:
            logger.info(f"ActionRegistry: Executing generic action handler for '{action_type}'")
            # Apply any configured variables / field mappings
            field_mappings = config.get("fieldMappings") or config.get("field_mappings") or []
            if isinstance(field_mappings, list):
                for m in field_mappings:
                    if isinstance(m, dict) and "field" in m and "value" in m:
                        context_vars[m["field"]] = m["value"]
            if isinstance(config.get("variables"), dict):
                context_vars.update(config["variables"])
            return {"status": "SUCCESS", "action_type": action_type}


# Register default built-in action handlers
def _update_status_handler(config: Dict[str, Any], context_vars: Dict[str, Any]) -> Dict[str, Any]:
    new_status = config.get("new_status") or config.get("status")
    if new_status:
        context_vars["status"] = new_status
    return {"status": "SUCCESS", "new_status": new_status}

def _log_audit_handler(config: Dict[str, Any], context_vars: Dict[str, Any]) -> Dict[str, Any]:
    message = config.get("message", "Audit log created")
    logger.info(f"ActionRegistry Audit Log: {message} | Context: {context_vars}")
    return {"status": "SUCCESS", "message": message}

def _set_variable_handler(config: Dict[str, Any], context_vars: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in config.get("variables", {}).items():
        context_vars[k] = v
    return {"status": "SUCCESS", "variables": config.get("variables", {})}

ActionRegistry.register("UPDATE_STATUS", _update_status_handler)
ActionRegistry.register("LOG_AUDIT", _log_audit_handler)
ActionRegistry.register("SET_VARIABLE", _set_variable_handler)
ActionRegistry.register("GENERIC_ACTION", lambda cfg, ctx: {"status": "SUCCESS"})


def _db_read_handler(config: Dict[str, Any], context_vars: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a structured, parameterized read against the Client Database
    and maps result columns to workflow variables dynamically.
    """
    from app.core.database import ClientDatabaseAdapter

    table_name = config.get("table") or config.get("entity") or config.get("table_name")
    if not table_name:
        raise ValueError("Database READ action requires 'table' or 'entity' to be configured.")

    fields = config.get("fields")
    filters = config.get("filters") or []

    # Handle filter shorthand if filters is not an explicit list
    if not filters and config.get("filterField"):
        filters = [{
            "field": config.get("filterField"),
            "operator": config.get("filterOperator", "="),
            "value": config.get("filterValue", "{{entity.id}}")
        }]
    elif not filters and config.get("recordId"):
        filters = [{
            "field": "id",
            "operator": "=",
            "value": config.get("recordId")
        }]
    elif not filters:
        entity_val = context_vars.get("entity_id") or context_vars.get("record_id") or "{{entity_id}}"
        target_pk = config.get("primary_key") or ("leave_request_id" if "leave" in str(table_name).lower() else "id")
        filters = [{
            "field": target_pk,
            "operator": "=",
            "value": str(entity_val)
        }]

    result_mapping = config.get("resultMapping") or config.get("result_mapping") or config.get("fieldMappings")
    if isinstance(result_mapping, list):
        mapping_dict = {}
        for m in result_mapping:
            if isinstance(m, dict):
                src = m.get("field") or m.get("source") or m.get("from")
                tgt = m.get("value") or m.get("target") or m.get("to") or src
                if src:
                    mapping_dict[src] = tgt
        result_mapping = mapping_dict

    conn_id = config.get("connection_id") or context_vars.get("connection_id")

    mapped_data = ClientDatabaseAdapter.read_entity_record(
        table_name=table_name,
        fields=fields,
        filters=filters,
        variables=context_vars,
        result_mapping=result_mapping,
        connection_id=conn_id
    )

    context_vars.update(mapped_data)
    if config.get("outputVariable"):
        context_vars[config["outputVariable"]] = mapped_data

    return {"status": "SUCCESS", "read_fields": list(mapped_data.keys()), "data": mapped_data}


ActionRegistry.register("DB_READ", _db_read_handler)
ActionRegistry.register("DATABASE_READ", _db_read_handler)
ActionRegistry.register("READ_RECORD", _db_read_handler)
ActionRegistry.register("RECORD_READ", _db_read_handler)
ActionRegistry.register("DB_LOOKUP", _db_read_handler)


def _db_update_handler(config: Dict[str, Any], context_vars: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a structured, parameterized UPDATE against the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter

    table_name = config.get("table") or config.get("entity") or config.get("table_name") or config.get("tableName")
    if not table_name:
        raise ValueError("Database UPDATE action requires 'table' or 'entity' to be configured.")

    updates = (
        config.get("updates") or 
        config.get("values") or 
        config.get("fields") or 
        config.get("fieldsToUpdate") or
        config.get("fieldMappings") or 
        config.get("field_mappings")
    )
    if not updates and config.get("statusValue"):
        status_col = config.get("statusColumn") or "status"
        updates = {status_col: config["statusValue"]}

    if isinstance(updates, list):
        update_dict = {}
        for item in updates:
            if isinstance(item, dict) and "field" in item:
                update_dict[item["field"]] = item.get("value")
        updates = update_dict

    filters = config.get("filters") or []
    entity_val = str(context_vars.get("entity_id") or context_vars.get("entityId") or "{{entity_id}}")

    if not filters and config.get("filterField"):
        filters = [{
            "field": config.get("filterField"),
            "operator": config.get("filterOperator", "="),
            "value": config.get("filterValue", entity_val)
        }]
    elif not filters and (config.get("recordId") or config.get("record_id")):
        filters = [{
            "field": "id",
            "operator": "=",
            "value": config.get("recordId") or config.get("record_id")
        }]
    elif not filters:
        target_pk = config.get("primary_key") or ("leave_request_id" if "leave" in str(table_name).lower() else "id")
        filters = [{
            "field": target_pk,
            "operator": "=",
            "value": entity_val
        }]

    allow_full = bool(config.get("allowFullTableUpdate") or config.get("allow_full_table_update"))
    result_mapping = config.get("resultMapping") or config.get("result_mapping")
    conn_id = config.get("connection_id") or config.get("connectionId") or context_vars.get("connection_id")

    mapped_data = ClientDatabaseAdapter.update_entity_record_generic(
        table_name=table_name,
        updates=updates,
        filters=filters,
        variables=context_vars,
        allow_full_table_update=allow_full,
        result_mapping=result_mapping,
        connection_id=conn_id
    )

    context_vars.update(mapped_data)
    return {"status": "SUCCESS", "data": mapped_data}


def _db_create_handler(config: Dict[str, Any], context_vars: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a structured, parameterized INSERT against the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter

    table_name = config.get("table") or config.get("entity") or config.get("table_name")
    if not table_name:
        raise ValueError("Database CREATE action requires 'table' or 'entity' to be configured.")

    values = (
        config.get("values") or 
        config.get("fields") or 
        config.get("fieldMappings") or 
        config.get("fieldsToInsert") or
        config.get("data")
    )
    if isinstance(values, list):
        val_dict = {}
        for item in values:
            if isinstance(item, dict) and "field" in item:
                val_dict[item["field"]] = item.get("value")
        values = val_dict

    result_mapping = config.get("resultMapping") or config.get("result_mapping")
    conn_id = config.get("connection_id") or context_vars.get("connection_id")
    conflict_res = config.get("conflictResolution") or config.get("conflict_resolution")

    mapped_data = ClientDatabaseAdapter.create_entity_record_generic(
        table_name=table_name,
        values=values,
        variables=context_vars,
        result_mapping=result_mapping,
        connection_id=conn_id,
        conflict_resolution=conflict_res
    )

    out_var = config.get("outputVariable")
    if out_var:
        context_vars[out_var] = mapped_data.get("created_id") or mapped_data.get("id")

    context_vars.update(mapped_data)
    return {"status": "SUCCESS", "data": mapped_data}


ActionRegistry.register("DB_UPDATE", _db_update_handler)
ActionRegistry.register("DATABASE_UPDATE", _db_update_handler)
ActionRegistry.register("UPDATE_RECORD", _db_update_handler)
ActionRegistry.register("RECORD_UPDATE", _db_update_handler)
ActionRegistry.register("UPDATE", _db_update_handler)

ActionRegistry.register("DB_CREATE", _db_create_handler)
ActionRegistry.register("DATABASE_CREATE", _db_create_handler)
ActionRegistry.register("CREATE_RECORD", _db_create_handler)
ActionRegistry.register("RECORD_CREATE", _db_create_handler)
ActionRegistry.register("CREATE", _db_create_handler)
ActionRegistry.register("INSERT", _db_create_handler)


def _email_notification_handler(config: Dict[str, Any], context_vars: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic Email Notification Handler:
    - Resolves recipient dynamically from role, user, context variable (e.g. {{employee_email}}), or static email
    - Renders subject and body with dynamic context variable interpolation
    - Dispatches to client email queue if available or records delivery event
    """
    import datetime
    from sqlalchemy import text
    from app.core.database import DynamicEnginePool, ClientDatabaseAdapter

    entity_id = context_vars.get("entity_id") or context_vars.get("record_id") or context_vars.get("id")
    conn_id = config.get("connection_id") or context_vars.get("connection_id") or context_vars.get("_workflow_connection_id") or context_vars.get("workflow_connection_id")
    now_dt = datetime.datetime.now()
    user_id = context_vars.get("user_id", 1)

    # 1. Resolve Recipient Email List (Supports direct emails, role:RoleName, user:UserName, variables)
    def _resolve_recipient_list(raw_input: Any) -> Optional[str]:
        if not raw_input:
            return None
        raw_str = str(raw_input).strip()
        if not raw_str:
            return None

        parts = [p.strip() for p in raw_str.split(",") if p.strip()]
        resolved_emails = []

        for p in parts:
            if p.startswith("role:"):
                role_target = p.replace("role:", "").strip()
                try:
                    # 1. Query all users assigned to this role in the connected DB (via mapping table or role col)
                    role_users = ClientDatabaseAdapter.get_users_by_role(role_target, connection_id=conn_id)
                    matched_emails = [u["email"] for u in role_users if u.get("email")]

                    # 2. Fallback: check get_users()
                    if not matched_emails:
                        users = ClientDatabaseAdapter.get_users(connection_id=conn_id)
                        matched_emails = [
                            u["email"] for u in users
                            if u.get("email") and (
                                str(u.get("role_id", "")).lower() == role_target.lower() or
                                str(u.get("role_name", "")).lower() == role_target.lower() or
                                any(str(r).lower() == role_target.lower() for r in u.get("roles", [])) or
                                str(u.get("name", "")).lower() == role_target.lower()
                            )
                        ]

                    if matched_emails:
                        resolved_emails.extend(matched_emails)
                    else:
                        logger.warning(f"ActionRegistry SEND_EMAIL: No users found assigned to role '{role_target}' (connection_id={conn_id})")
                except Exception as ex:
                    logger.error(f"ActionRegistry SEND_EMAIL: Error resolving role '{role_target}': {ex}")

            elif p.startswith("user:"):
                user_target = p.replace("user:", "").strip()
                try:
                    users = ClientDatabaseAdapter.get_users(connection_id=conn_id)
                    matched_user = next(
                        (u for u in users if str(u.get("name", "")).lower() == user_target.lower() or str(u.get("id")) == user_target),
                        None
                    )
                    if matched_user and matched_user.get("email"):
                        resolved_emails.append(matched_user["email"])
                    else:
                        logger.warning(f"ActionRegistry SEND_EMAIL: No user found for user target '{user_target}' (connection_id={conn_id})")
                except Exception as ex:
                    logger.error(f"ActionRegistry SEND_EMAIL: Error resolving user '{user_target}': {ex}")
            elif "{{" in p:
                interpolated = ClientDatabaseAdapter._resolve_template_value(p, context_vars)
                if interpolated:
                    resolved_emails.append(str(interpolated))
            elif "@" in p:
                resolved_emails.append(p)
            else:
                resolved_emails.append(p)

        if not resolved_emails:
            return None

        deduped = []
        for e in resolved_emails:
            if e not in deduped:
                deduped.append(e)
        return ", ".join(deduped)

    raw_to = context_vars.get("to") or context_vars.get("to_email") or context_vars.get("email_to") or config.get("to") or config.get("recipient")
    to_email = _resolve_recipient_list(raw_to)
    if not to_email:
        to_email = context_vars.get("employee_email") or context_vars.get("email") or context_vars.get("user_email") or "applicant@company.com"

    raw_cc = context_vars.get("cc") or context_vars.get("cc_email") or context_vars.get("email_cc") or config.get("cc") or config.get("email_cc")
    cc_email = _resolve_recipient_list(raw_cc)

    raw_bcc = context_vars.get("bcc") or context_vars.get("bcc_email") or context_vars.get("email_bcc") or config.get("bcc") or config.get("email_bcc")
    bcc_email = _resolve_recipient_list(raw_bcc)

    # 2. Resolve Subject & Body with Variable Interpolation
    display_id = f"#{entity_id}" if entity_id else ""
    raw_subject = config.get("subject") or f"Notification for Request {display_id}"
    subject = str(ClientDatabaseAdapter._resolve_template_value(raw_subject, context_vars) or raw_subject)

    raw_body = config.get("body") or f"Your request {display_id} has been processed successfully."
    body_text = str(ClientDatabaseAdapter._resolve_template_value(raw_body, context_vars) or raw_body)

    clean_body = body_text.strip()
    is_html = clean_body.startswith("<html") or clean_body.startswith("<div") or clean_body.startswith("<p") or "<br" in clean_body or "<table" in clean_body
    final_email_body = clean_body if is_html else body_text
    email_type_val = "HTML" if is_html else "TEXT"

    # 3. Attempt insert into client email queue if table exists
    # 3. Attempt insert into client email queue if table exists
    email_job_id = None
    try:
        from sqlalchemy import inspect
        eng = DynamicEnginePool.get_engine(conn_id)
        inspector = inspect(eng)
        target_schema = ClientDatabaseAdapter._resolve_target_schema(None, conn_id)

        all_tbls = inspector.get_table_names(schema=target_schema) if target_schema else inspector.get_table_names()
        tbl_map = {t.lower(): t for t in all_tbls}

        found_mail_tbl = None
        for cand in ["mst_email_job", "email_jobs", "email_queue", "mst_email_jobs", "outgoing_emails"]:
            if cand in tbl_map:
                found_mail_tbl = tbl_map[cand]
                break

        if found_mail_tbl:
            cols = {c["name"].lower(): c["name"] for c in inspector.get_columns(found_mail_tbl, schema=target_schema)}
            full_mail_tbl = f"{target_schema}.{found_mail_tbl}" if target_schema else found_mail_tbl

            insert_data = {}
            if "email_server_id" in cols:
                insert_data[cols["email_server_id"]] = 1
            if "to_email" in cols:
                insert_data[cols["to_email"]] = to_email
            elif "email_to" in cols:
                insert_data[cols["email_to"]] = to_email

            if cc_email:
                if "cc_email" in cols:
                    insert_data[cols["cc_email"]] = cc_email
                elif "email_cc" in cols:
                    insert_data[cols["email_cc"]] = cc_email

            if "subject" in cols:
                insert_data[cols["subject"]] = subject
            elif "email_subject" in cols:
                insert_data[cols["email_subject"]] = subject

            if "body" in cols:
                insert_data[cols["body"]] = final_email_body
            elif "email_body" in cols:
                insert_data[cols["email_body"]] = final_email_body

            if "email_type" in cols:
                insert_data[cols["email_type"]] = email_type_val
            if "send_status" in cols:
                insert_data[cols["send_status"]] = "New"
            if "total_attempts" in cols:
                insert_data[cols["total_attempts"]] = 3
            if "send_attempts" in cols:
                insert_data[cols["send_attempts"]] = 0
            if "attempt_delay" in cols:
                insert_data[cols["attempt_delay"]] = 5000
            if "is_deleted" in cols:
                insert_data[cols["is_deleted"]] = 0
            if "created_on" in cols:
                insert_data[cols["created_on"]] = now_dt
            if "created_by" in cols and user_id:
                insert_data[cols["created_by"]] = user_id

            col_names = list(insert_data.keys())
            param_names = [f":p_{i}" for i in range(len(col_names))]
            params = {f"p_{i}": v for i, v in enumerate(insert_data.values())}

            insert_sql = f"INSERT INTO {full_mail_tbl} ({', '.join(col_names)}) VALUES ({', '.join(param_names)})"
            with eng.begin() as conn:
                conn.execute(text(insert_sql), params)
                email_job_id = 1  # Successfully queued

            # Trigger email dispatcher in background thread immediately (Non-blocking)
            try:
                import threading
                from app.workflow.services.email_dispatcher import EmailDispatcher
                threading.Thread(
                    target=EmailDispatcher.process_pending_email_jobs,
                    kwargs={"conn_id": conn_id, "limit": 10},
                    daemon=True
                ).start()
            except Exception as dispatch_ex:
                logger.debug(f"ActionRegistry: Immediate dispatch notice: {dispatch_ex}")
    except Exception as queue_err:
        logger.debug(f"ActionRegistry: Email queue insert skipped: {queue_err}")

    # 4. If not queued in client DB (no email job table), send directly via SMTP in background thread
    send_status = "Queued" if email_job_id else "Pending"
    if not email_job_id:
        try:
            import threading
            from app.workflow.services.email_dispatcher import EmailDispatcher
            smtp_cfg = EmailDispatcher.get_smtp_config(conn_id=conn_id)
            if smtp_cfg:
                threading.Thread(
                    target=EmailDispatcher.send_smtp_email,
                    kwargs={
                        "smtp_cfg": smtp_cfg,
                        "to_email": to_email,
                        "subject": subject,
                        "body": final_email_body,
                        "email_type": email_type_val,
                        "cc": cc_email
                    },
                    daemon=True
                ).start()
                send_status = "Sent"
                logger.info(f"ActionRegistry: Background direct SMTP dispatch started for {to_email}")
        except Exception as direct_err:
            logger.warning(f"ActionRegistry: Direct SMTP email sending warning: {direct_err}")

    context_vars["email_to"] = to_email
    if cc_email:
        context_vars["email_cc"] = cc_email
    if bcc_email:
        context_vars["email_bcc"] = bcc_email

    return {
        "status": "SUCCESS",
        "email_job_id": email_job_id,
        "email_to": to_email,
        "email_cc": cc_email,
        "email_bcc": bcc_email,
        "email_subject": subject,
        "send_status": send_status
    }


ActionRegistry.register("NOTIFICATION", _email_notification_handler)
ActionRegistry.register("EMAIL", _email_notification_handler)
ActionRegistry.register("COMMUNICATION", _email_notification_handler)
ActionRegistry.register("SEND_EMAIL", _email_notification_handler)
ActionRegistry.register("EMAIL_JOB", _email_notification_handler)
ActionRegistry.register("EMAIL_NOTIFICATION", _email_notification_handler)

ActionRegistry.register("DB_UPDATE", _db_update_handler)
ActionRegistry.register("DATABASE_UPDATE", _db_update_handler)
ActionRegistry.register("UPDATE_RECORD", _db_update_handler)
ActionRegistry.register("RECORD_UPDATE", _db_update_handler)
ActionRegistry.register("RECORD", _db_update_handler)

ActionRegistry.register("DB_CREATE", _db_create_handler)
ActionRegistry.register("DATABASE_CREATE", _db_create_handler)
ActionRegistry.register("CREATE_RECORD", _db_create_handler)
ActionRegistry.register("INSERT_RECORD", _db_create_handler)


def _raw_sql_handler(config: Dict[str, Any], context_vars: Dict[str, Any]) -> Dict[str, Any]:
    from sqlalchemy import text
    from app.core.database import DynamicEnginePool

    sql = config.get("sql") or config.get("query") or config.get("statement")
    if not sql:
        raise ValueError("EXECUTE_SQL action requires 'sql' or 'query' parameter.")

    conn_id = config.get("connection_id") or context_vars.get("connection_id")
    eng = DynamicEnginePool.get_engine(conn_id)

    with eng.begin() as conn:
        res = conn.execute(text(sql), context_vars)
        affected = res.rowcount if res.rowcount is not None else 0

    return {"status": "SUCCESS", "affectedRows": affected}


ActionRegistry.register("SQL", _raw_sql_handler)
ActionRegistry.register("RAW_SQL", _raw_sql_handler)
ActionRegistry.register("EXECUTE_SQL", _raw_sql_handler)






