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

        # 1. Direct action matching (e.g. "APPROVE", "REJECT", "FORCE_APPROVE", "RESUBMIT")
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

    table_name = config.get("table") or config.get("entity") or config.get("table_name")
    if not table_name:
        raise ValueError("Database UPDATE action requires 'table' or 'entity' to be configured.")

    updates = (
        config.get("updates") or 
        config.get("values") or 
        config.get("fields") or 
        config.get("fieldMappings") or 
        config.get("field_mappings")
    )
    if isinstance(updates, list):
        update_dict = {}
        for item in updates:
            if isinstance(item, dict) and "field" in item:
                update_dict[item["field"]] = item.get("value")
        updates = update_dict

    filters = config.get("filters") or []
    if not filters and config.get("filterField"):
        filters = [{
            "field": config.get("filterField"),
            "operator": config.get("filterOperator", "="),
            "value": config.get("filterValue", "{{entity.id}}")
        }]
    elif not filters and (config.get("recordId") or config.get("record_id")):
        filters = [{
            "field": "id",
            "operator": "=",
            "value": config.get("recordId") or config.get("record_id")
        }]
    elif not filters:
        filters = [{
            "field": "id",
            "operator": "=",
            "value": "{{entity.id}}"
        }]

    allow_full = bool(config.get("allowFullTableUpdate") or config.get("allow_full_table_update"))
    result_mapping = config.get("resultMapping") or config.get("result_mapping")
    conn_id = config.get("connection_id") or context_vars.get("connection_id")

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

    values = config.get("values") or config.get("fields") or config.get("data")
    if isinstance(values, list):
        val_dict = {}
        for item in values:
            if isinstance(item, dict) and "field" in item:
                val_dict[item["field"]] = item.get("value")
        values = val_dict

    result_mapping = config.get("resultMapping") or config.get("result_mapping")
    conn_id = config.get("connection_id") or context_vars.get("connection_id")

    mapped_data = ClientDatabaseAdapter.create_entity_record_generic(
        table_name=table_name,
        values=values,
        variables=context_vars,
        result_mapping=result_mapping,
        connection_id=conn_id
    )

    context_vars.update(mapped_data)
    return {"status": "SUCCESS", "data": mapped_data}


ActionRegistry.register("DB_UPDATE", _db_update_handler)
ActionRegistry.register("DATABASE_UPDATE", _db_update_handler)
ActionRegistry.register("UPDATE_RECORD", _db_update_handler)
ActionRegistry.register("RECORD_UPDATE", _db_update_handler)

ActionRegistry.register("DB_CREATE", _db_create_handler)
ActionRegistry.register("DATABASE_CREATE", _db_create_handler)
ActionRegistry.register("CREATE_RECORD", _db_create_handler)
ActionRegistry.register("RECORD_CREATE", _db_create_handler)


def _email_notification_handler(config: Dict[str, Any], context_vars: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates an outgoing email job in Client DB (ers.mst_email_job) for the ERM notification queue:
    - Resolves recipient email from context / ers.mst_users
    - Renders subject and formatted HTML body
    - Inserts into ers.mst_email_job with send_status = 'New'
    """
    import datetime
    from sqlalchemy import text
    from app.core.database import engine as client_engine

    entity_id = context_vars.get("entity_id") or context_vars.get("record_id") or context_vars.get("risk_register_id")
    now_dt = datetime.datetime.now()
    user_id = context_vars.get("user_id", 1)

    # 1. Inspect risk record if entity_id is available
    risk_info = {}
    owner_email = None
    owner_name = "Risk Owner"

    if entity_id:
        try:
            with client_engine.connect() as conn:
                r_row = conn.execute(
                    text("SELECT risk_register_id, risk_id, risk_name, risk_owner_id, financial_year FROM ers.risk_register WHERE risk_register_id = :id"),
                    {"id": int(entity_id)}
                ).mappings().first()
                if r_row:
                    risk_info = dict(r_row)
                    owner_id = risk_info.get("risk_owner_id")
                    if owner_id:
                        u_row = conn.execute(
                            text("SELECT first_name, last_name, email FROM ers.mst_users WHERE id = :uid"),
                            {"uid": int(owner_id)}
                        ).mappings().first()
                        if u_row:
                            owner_email = u_row.get("email")
                            owner_name = f"{u_row.get('first_name', '')} {u_row.get('last_name', '')}".strip() or "Risk Owner"
        except Exception as e:
            logger.warning(f"Error fetching risk owner for email job: {e}")

    # 2. Resolve recipient email
    raw_to = config.get("to") or config.get("recipient") or "{{risk_owner_email}}"
    to_email = owner_email or "risk_owner@example.com"
    if raw_to and raw_to != "{{risk_owner_email}}" and "@" in raw_to:
        to_email = raw_to

    # 3. Resolve Subject
    risk_display_id = risk_info.get("risk_id") or f"#{entity_id}" if entity_id else "Risk Record"
    risk_title = risk_info.get("risk_name") or "Operational Risk"
    
    raw_subject = config.get("subject") or f"Risk {risk_display_id} Approved by Function Head"
    subject = raw_subject.replace("{{workflow.entity_id}}", str(risk_display_id)).replace("{{risk_id}}", str(risk_display_id))

    # 4. Construct formatted ERM HTML Body
    custom_body = config.get("body") or "Your risk record has been successfully approved by the Function Head."
    if "{{workflow.entity_id}}" in custom_body:
        custom_body = custom_body.replace("{{workflow.entity_id}}", str(risk_display_id))

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color:#f4f6f8; padding:20px;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td align="center">
                    <table width="600px" style="background:#ffffff; border-radius:8px; padding:20px; border:1px solid #e2e8f0;">
                        <tr>
                            <td style="background:#0d6efd; color:white; padding:15px; border-radius:6px;">
                                <h2 style="margin:0; font-size:18px;">Function Head Approval Notification</h2>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:20px; color:#333; line-height: 1.6;">
                                <p>Dear <b>{owner_name}</b>,</p>
                                <p>{custom_body}</p>
                                <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width:100%; margin:15px 0; border-color:#e2e8f0;">
                                    <tr><td style="width:35%; background:#f8fafc;"><b>Risk Code</b></td><td>{risk_display_id}</td></tr>
                                    <tr><td style="background:#f8fafc;"><b>Risk Title</b></td><td>{risk_title}</td></tr>
                                    <tr><td style="background:#f8fafc;"><b>Approval Status</b></td><td><span style="color:#16a34a; font-weight:bold;">Approved (10)</span></td></tr>
                                </table>
                                <p>Regards,<br><b>Enterprise Risk Management System</b></p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:12px; font-size:11px; color:#94a3b8; border-top:1px solid #eee; text-align:center;">
                                This is an automated notification generated by Workflow Automation Studio.
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # 5. Insert into ers.mst_email_job
    email_job_id = None
    try:
        with client_engine.begin() as conn:
            res = conn.execute(
                text("""
                    INSERT INTO ers.mst_email_job (
                        email_server_id,
                        email_module,
                        email_to,
                        email_subject,
                        email_type,
                        email_body,
                        send_status,
                        total_attempts,
                        send_attempts,
                        attempt_delay,
                        next_attempt_at,
                        created_on,
                        created_by,
                        is_deleted
                    ) VALUES (
                        1,
                        'RISK_MANAGEMENT',
                        :email_to,
                        :email_subject,
                        'HTML',
                        :email_body,
                        'New',
                        3,
                        0,
                        5000,
                        :now_dt,
                        :now_dt,
                        :uid,
                        0
                    ) RETURNING email_job_id
                """),
                {
                    "email_to": to_email,
                    "email_subject": subject,
                    "email_body": html_body,
                    "now_dt": now_dt,
                    "uid": user_id
                }
            )
            email_job_id = res.scalar()
            logger.info(f"Created email job #{email_job_id} in ers.mst_email_job for {to_email}")
    except Exception as e:
        logger.error(f"Failed to insert into ers.mst_email_job: {e}")
        raise RuntimeError(f"Email job insertion failed: {str(e)}")

    context_vars["email_job_id"] = email_job_id
    context_vars["email_to"] = to_email
    return {
        "status": "SUCCESS",
        "email_job_id": email_job_id,
        "email_to": to_email,
        "email_subject": subject,
        "send_status": "New"
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





