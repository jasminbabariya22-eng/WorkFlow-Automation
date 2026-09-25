import re
from typing import Dict, Any, Callable, Optional, List, Set, Tuple
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


_GLOBAL_MAIL_TBL_CACHE: Dict[str, Any] = {}

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

    # 1. Resolve Recipient Email List (Supports direct emails, role:RoleName, user:UserName, variables, lists)
    def _resolve_recipient_list(raw_input: Any) -> Optional[str]:
        if not raw_input:
            return None
        
        if isinstance(raw_input, (list, tuple, set)):
            parts = [str(p).strip().strip("'\"") for p in raw_input if str(p).strip()]
        else:
            raw_str = str(raw_input).strip()
            if not raw_str:
                return None
            parts = [p.strip().strip("'\"") for p in raw_str.split(",") if p.strip()]

        resolved_emails = []

        for p in parts:
            if not p:
                continue
            if p.startswith("role:"):
                role_target = p.replace("role:", "").strip()
                try:
                    role_users = ClientDatabaseAdapter.get_users_by_role(role_target, connection_id=conn_id)
                    matched_emails = [u["email"] for u in role_users if u.get("email")]

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

            elif "{" in p:
                interpolated = ClientDatabaseAdapter._resolve_template_value(p, context_vars)
                if interpolated:
                    resolved_emails.append(str(interpolated))
            elif "@" in p:
                resolved_emails.append(p)
            else:
                resolved_emails.append(p)

        if not resolved_emails:
            return None

        # Restrict duplicate emails using Python set (case-insensitive deduplication)
        seen_emails: set = set()
        deduped_emails = []
        for raw_e in resolved_emails:
            for sub_e in str(raw_e).split(","):
                clean_e = sub_e.strip()
                if clean_e:
                    key = clean_e.lower()
                    if key not in seen_emails:
                        seen_emails.add(key)
                        deduped_emails.append(clean_e)

        return ", ".join(deduped_emails) if deduped_emails else None

    def _collect_recipient_sources(*sources) -> List[str]:
        collected = []
        for s in sources:
            if not s:
                continue
            if isinstance(s, (list, tuple, set)):
                for item in s:
                    if item:
                        collected.append(str(item).strip().strip("'\""))
            elif isinstance(s, str):
                for sub in s.split(","):
                    clean = sub.strip().strip("'\"")
                    if clean:
                        collected.append(clean)
            else:
                clean = str(s).strip().strip("'\"")
                if clean:
                    collected.append(clean)
        return collected

    param_dict = context_vars.get("parameter") or context_vars.get("parameters") or {}
    if not isinstance(param_dict, dict):
        param_dict = {}

    # Separate workflow node configured emails vs API request emails
    node_to_sources = _collect_recipient_sources(
        config.get("to"),
        config.get("recipient"),
        config.get("to_email"),
        config.get("email_to")
    )
    node_to_raw = _resolve_recipient_list(node_to_sources)

    req_to_sources = _collect_recipient_sources(
        param_dict.get("to"),
        param_dict.get("to_email"),
        param_dict.get("email_to"),
        context_vars.get("to"),
        context_vars.get("to_email"),
        context_vars.get("email_to")
    )
    req_to_raw = _resolve_recipient_list(req_to_sources)

    # 1a. Merge all TO sources: Workflow Node configuration + API Request inputs
    to_sources = node_to_sources + req_to_sources
    to_email = _resolve_recipient_list(to_sources)
    if not to_email:
        fallback_to = _collect_recipient_sources(
            context_vars.get("employee_email"),
            context_vars.get("email"),
            context_vars.get("user_email"),
            param_dict.get("employee_email"),
            param_dict.get("email"),
            param_dict.get("user_email")
        )
        to_email = _resolve_recipient_list(fallback_to) if fallback_to else "applicant@company.com"

    node_cc_sources = _collect_recipient_sources(
        config.get("cc"),
        config.get("email_cc"),
        config.get("cc_email")
    )
    node_cc_raw = _resolve_recipient_list(node_cc_sources)

    req_cc_sources = _collect_recipient_sources(
        param_dict.get("cc"),
        param_dict.get("cc_email"),
        param_dict.get("email_cc"),
        context_vars.get("cc"),
        context_vars.get("cc_email"),
        context_vars.get("email_cc")
    )
    req_cc_raw = _resolve_recipient_list(req_cc_sources)

    # 1b. Merge all CC sources: Workflow Node configuration + API Request inputs
    cc_sources = node_cc_sources + req_cc_sources
    cc_email = _resolve_recipient_list(cc_sources)

    # Restrict duplicates across TO and CC using set
    if cc_email and to_email:
        to_set = {e.strip().lower() for e in to_email.split(",") if e.strip()}
        cc_list = [e.strip() for e in cc_email.split(",") if e.strip() and e.strip().lower() not in to_set]
        cc_email = ", ".join(cc_list) if cc_list else None

    # 1c. Merge all BCC sources: Workflow Node configuration + API Request inputs
    bcc_sources = _collect_recipient_sources(
        config.get("bcc"),
        config.get("email_bcc"),
        config.get("bcc_email"),
        context_vars.get("bcc"),
        context_vars.get("bcc_email"),
        context_vars.get("email_bcc"),
        param_dict.get("bcc"),
        param_dict.get("bcc_email"),
        param_dict.get("email_bcc")
    )
    bcc_email = _resolve_recipient_list(bcc_sources)

    # Restrict duplicates across TO, CC, and BCC using set
    if bcc_email:
        existing_set = {e.strip().lower() for e in (to_email or "").split(",") if e.strip()}
        if cc_email:
            existing_set.update({e.strip().lower() for e in cc_email.split(",") if e.strip()})
        bcc_list = [e.strip() for e in bcc_email.split(",") if e.strip() and e.strip().lower() not in existing_set]
        bcc_email = ", ".join(bcc_list) if bcc_list else None

    # 2. Resolve Subject & Body with Variable Interpolation (Supports full HTML bodies)
    display_id = f"#{entity_id}" if entity_id else ""
    raw_subject = (
        context_vars.get("subject") or 
        context_vars.get("title") or 
        config.get("subject") or 
        f"Notification for Request {display_id}"
    )
    subject = str(ClientDatabaseAdapter._resolve_template_value(raw_subject, context_vars) or raw_subject)

    raw_from = (
        context_vars.get("from_email") or
        context_vars.get("from") or
        context_vars.get("sender") or
        context_vars.get("sender_email") or
        config.get("from") or
        config.get("from_email") or
        config.get("sender") or
        ""
    )
    from_email = str(ClientDatabaseAdapter._resolve_template_value(raw_from, context_vars) or raw_from).strip() if raw_from else None
    explicit_server_id = config.get("email_server_id") or context_vars.get("email_server_id")

    raw_body = (
        context_vars.get("html_body") or
        context_vars.get("body") or 
        context_vars.get("email_body") or 
        context_vars.get("message") or 
        context_vars.get("content") or
        config.get("body") or 
        f"Your request {display_id} has been processed successfully."
    )
    body_text = str(ClientDatabaseAdapter._resolve_template_value(raw_body, context_vars) or raw_body)

    clean_body = body_text.strip()
    import re
    is_html = bool(re.search(r"<(?:!doctype|html|body|div|p|span|b|i|strong|em|h[1-6]|table|thead|tbody|tr|td|th|ul|ol|li|br|hr|img|a|style|font|pre|code)\b[^>]*>", clean_body, re.IGNORECASE))
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
        available_schemas = []
        try:
            available_schemas = inspector.get_schema_names()
        except Exception:
            pass

        schemas_to_check = []
        if target_schema:
            schemas_to_check.append(target_schema)
        for s in ["dbo", "public", "ers"]:
            if s in available_schemas and s not in schemas_to_check:
                schemas_to_check.append(s)
        for s in available_schemas:
            if s not in schemas_to_check and s.lower() not in ("information_schema", "pg_catalog", "pg_toast", "sys", "guest"):
                schemas_to_check.append(s)
        if not schemas_to_check:
            schemas_to_check = [None]

        found_mail_tbl = None
        found_mail_schema = None
        cols_dict = {}

        for sch in schemas_to_check:
            try:
                table_names = {t.lower(): t for t in inspector.get_table_names(schema=sch)}
            except Exception:
                table_names = {}

            for cand in ["mst_email_job", "email_jobs", "email_queue", "mst_email_jobs", "outgoing_emails"]:
                if cand in table_names:
                    found_mail_tbl = table_names[cand]
                    found_mail_schema = sch
                    break
            if found_mail_tbl:
                break

        if found_mail_tbl:
            raw_cols = inspector.get_columns(found_mail_tbl, schema=found_mail_schema)
            cols_dict = {c["name"].lower(): c["name"] for c in raw_cols}
            cols_type_map = {c["name"].lower(): str(c.get("type", "")).lower() for c in raw_cols}

            full_mail_tbl = f"{found_mail_schema}.{found_mail_tbl}" if found_mail_schema else found_mail_tbl

            # Lookup valid active email_server_id from client database if email_server table exists
            valid_server_id = None
            if explicit_server_id and str(explicit_server_id).isdigit():
                valid_server_id = int(explicit_server_id)

            # Match by specific from_email address if specified
            if not valid_server_id:
                for sch in schemas_to_check:
                    try:
                        raw_table_names = inspector.get_table_names(schema=sch)
                        table_map = {t.lower(): t for t in raw_table_names}
                    except Exception:
                        table_map = {}

                    for s_tbl in ["email_server", "mst_email_server", "smtp_settings", "email_config", "email_servers", "tbl_email_server"]:
                        if s_tbl in table_map:
                            actual_tbl = table_map[s_tbl]
                            s_ref = f"{sch}.{actual_tbl}" if sch else actual_tbl
                            try:
                                with eng.connect() as s_conn:
                                    rows = s_conn.execute(text(f"SELECT * FROM {s_ref}")).fetchall()
                                    for r in rows:
                                        m = dict(r._mapping)
                                        # Check is_deleted
                                        is_del = None
                                        for k, v in m.items():
                                            if k.lower() == "is_deleted":
                                                is_del = v
                                                break
                                        if is_del is not None and str(is_del).strip().lower() in ("1", "true", "t", "yes"):
                                            continue

                                        sid = None
                                        for k, v in m.items():
                                            if k.lower() in ("email_server_id", "server_id", "id"):
                                                sid = v
                                                break

                                        s_user = ""
                                        for k, v in m.items():
                                            if k.lower() in ("outgoing_email_user", "email_user", "username", "email_id", "email"):
                                                s_user = str(v or "").strip()
                                                break

                                        if from_email and "@" in from_email:
                                            if s_user.lower() == from_email.lower().strip():
                                                valid_server_id = sid or 1
                                                break
                                        else:
                                            valid_server_id = sid or 1
                                            break
                            except Exception:
                                pass
                        if valid_server_id:
                            break
                    if valid_server_id:
                        break

            if not valid_server_id:
                valid_server_id = 1

            insert_data = {}
            if "email_server_id" in cols_dict:
                insert_data[cols_dict["email_server_id"]] = valid_server_id

            if from_email:
                if "from_email" in cols_dict:
                    insert_data[cols_dict["from_email"]] = from_email
                elif "email_from" in cols_dict:
                    insert_data[cols_dict["email_from"]] = from_email
                elif "sender_email" in cols_dict:
                    insert_data[cols_dict["sender_email"]] = from_email
                elif "sender" in cols_dict:
                    insert_data[cols_dict["sender"]] = from_email

            if "to_email" in cols_dict:
                insert_data[cols_dict["to_email"]] = to_email
            elif "email_to" in cols_dict:
                insert_data[cols_dict["email_to"]] = to_email

            if cc_email:
                if "cc_email" in cols_dict:
                    insert_data[cols_dict["cc_email"]] = cc_email
                elif "email_cc" in cols_dict:
                    insert_data[cols_dict["email_cc"]] = cc_email

            if "subject" in cols_dict:
                insert_data[cols_dict["subject"]] = subject
            elif "email_subject" in cols_dict:
                insert_data[cols_dict["email_subject"]] = subject

            if "body" in cols_dict:
                insert_data[cols_dict["body"]] = final_email_body
            elif "email_body" in cols_dict:
                insert_data[cols_dict["email_body"]] = final_email_body

            if "email_type" in cols_dict:
                insert_data[cols_dict["email_type"]] = email_type_val
            if "send_status" in cols_dict:
                insert_data[cols_dict["send_status"]] = "New"
            if "total_attempts" in cols_dict:
                insert_data[cols_dict["total_attempts"]] = 3
            if "send_attempts" in cols_dict:
                insert_data[cols_dict["send_attempts"]] = 0
            if "attempt_delay" in cols_dict:
                insert_data[cols_dict["attempt_delay"]] = 5000
            if "is_deleted" in cols_dict:
                del_type = cols_type_map.get("is_deleted", "")
                if "bit" in del_type or "bool" in del_type:
                    insert_data[cols_dict["is_deleted"]] = False
                else:
                    insert_data[cols_dict["is_deleted"]] = 0
            if "created_on" in cols_dict:
                insert_data[cols_dict["created_on"]] = now_dt

            if "created_by" in cols_dict and user_id is not None:
                cb_type = cols_type_map.get("created_by", "")
                if "int" in cb_type:
                    insert_data[cols_dict["created_by"]] = int(user_id) if str(user_id).isdigit() else 1
                else:
                    insert_data[cols_dict["created_by"]] = str(user_id)

            resolved_wf_id = context_vars.get("workflow_id") or context_vars.get("definition_id")
            resolved_inst_id = context_vars.get("instance_id") or context_vars.get("job_id") or entity_id
            resolved_node_key = config.get("node_id") or config.get("id") or context_vars.get("node_key") or context_vars.get("step_key") or context_vars.get("current_task_code") or "email_node"

            if "workflow_id" in cols_dict and resolved_wf_id is not None:
                insert_data[cols_dict["workflow_id"]] = int(resolved_wf_id) if str(resolved_wf_id).isdigit() else 1
            if "instance_id" in cols_dict and resolved_inst_id is not None:
                insert_data[cols_dict["instance_id"]] = int(resolved_inst_id) if str(resolved_inst_id).isdigit() else None
            if "node_key" in cols_dict and resolved_node_key:
                insert_data[cols_dict["node_key"]] = str(resolved_node_key)

            col_names = list(insert_data.keys())
            param_names = [f":p_{i}" for i in range(len(col_names))]
            params = {f"p_{i}": v for i, v in enumerate(insert_data.values())}

            pk_name = None
            for p_cand in ["email_job_id", "job_id", "id"]:
                if p_cand in cols_dict:
                    pk_name = cols_dict[p_cand]
                    break

            insert_sql = f"INSERT INTO {full_mail_tbl} ({', '.join(col_names)}) VALUES ({', '.join(param_names)})"
            dialect_name = eng.dialect.name.lower()

            try:
                with eng.begin() as conn:
                    if "postgres" in dialect_name and pk_name:
                        ret_sql = f"INSERT INTO {full_mail_tbl} ({', '.join(col_names)}) VALUES ({', '.join(param_names)}) RETURNING {pk_name}"
                        res = conn.execute(text(ret_sql), params).first()
                        if res:
                            email_job_id = res[0]
                    else:
                        conn.execute(text(insert_sql), params)
                        if pk_name:
                            try:
                                max_res = conn.execute(text(f"SELECT MAX({pk_name}) FROM {full_mail_tbl}")).scalar()
                                if max_res is not None:
                                    email_job_id = max_res
                            except Exception:
                                email_job_id = 1
                        else:
                            email_job_id = 1
            except Exception as ins_err:
                err_str = str(ins_err).lower()
                if "unique" in err_str or "duplicate" in err_str or "2601" in err_str or "2627" in err_str:
                    logger.info(f"ActionRegistry: Duplicate email job for (wf:{resolved_wf_id}, inst:{resolved_inst_id}, node:{resolved_node_key}) safely blocked by database unique constraint.")
                    try:
                        with eng.connect() as q_conn:
                            find_sql = f"SELECT {pk_name or 'email_job_id'} FROM {full_mail_tbl} WHERE workflow_id = :w_id AND instance_id = :i_id AND node_key = :n_k"
                            existing_job = q_conn.execute(text(find_sql), {"w_id": resolved_wf_id, "i_id": resolved_inst_id, "n_k": str(resolved_node_key)}).scalar()
                            if existing_job:
                                email_job_id = existing_job
                    except Exception:
                        pass
                else:
                    raise

            logger.info(f"ActionRegistry: Successfully queued email #{email_job_id} into '{full_mail_tbl}' (To: {to_email}, Subject: '{subject}')")

            # Trigger immediate non-blocking dispatch in background thread
            try:
                import threading
                from app.workflow.services.email_dispatcher import EmailDispatcher
                threading.Thread(
                    target=EmailDispatcher.process_pending_email_jobs,
                    kwargs={"conn_id": conn_id, "limit": 20},
                    daemon=True
                ).start()
            except Exception as th_ex:
                logger.debug(f"ActionRegistry: Thread spawn notice: {th_ex}")

    except Exception as queue_err:
        logger.error(f"ActionRegistry: Failed to queue email into client database: {queue_err}", exc_info=True)

    # 4. If not queued in client DB (no email job table), send directly via SMTP in non-blocking background thread
    send_status = "Queued" if email_job_id else "Dispatched"
    if not email_job_id:
        def _async_direct_smtp():
            try:
                from app.workflow.services.email_dispatcher import EmailDispatcher
                smtp_cfg = EmailDispatcher.get_smtp_config(conn_id=conn_id, email_server_id=valid_server_id, from_email=from_email)
                if smtp_cfg:
                    EmailDispatcher.send_smtp_email(
                        smtp_cfg=smtp_cfg,
                        to_email=to_email,
                        subject=subject,
                        body=final_email_body,
                        email_type=email_type_val,
                        cc=cc_email,
                        from_email=from_email
                    )
                    logger.info(f"ActionRegistry: Background direct SMTP dispatch delivered to {to_email} (From: {from_email or smtp_cfg.get('outgoing_email_user')})")
            except Exception as direct_err:
                logger.warning(f"ActionRegistry: Direct SMTP email sending warning: {direct_err}")

        try:
            import threading
            threading.Thread(target=_async_direct_smtp, daemon=True).start()
        except Exception as th_err:
            logger.debug(f"ActionRegistry: Thread spawn notice: {th_err}")

    context_vars["email_job_id"] = email_job_id
    if email_job_id and found_mail_tbl:
        context_vars["email_queue_table"] = full_mail_tbl
    if from_email:
        context_vars["email_from"] = from_email
        context_vars["from_email"] = from_email
    context_vars["email_to"] = to_email
    if cc_email:
        context_vars["email_cc"] = cc_email
    if bcc_email:
        context_vars["email_bcc"] = bcc_email

    node_to_list = [e.strip() for e in node_to_raw.split(",") if e.strip()] if node_to_raw else []
    node_cc_list = [e.strip() for e in node_cc_raw.split(",") if e.strip()] if node_cc_raw else []
    req_to_list = [e.strip() for e in req_to_raw.split(",") if e.strip()] if req_to_raw else []
    req_cc_list = [e.strip() for e in req_cc_raw.split(",") if e.strip()] if req_cc_raw else []
    final_to_list = [e.strip() for e in to_email.split(",") if e.strip()] if to_email else []
    final_cc_list = [e.strip() for e in cc_email.split(",") if e.strip()] if cc_email else []

    context_vars["workflow_node_to"] = node_to_list
    context_vars["workflow_node_cc"] = node_cc_list
    context_vars["request_to"] = req_to_list
    context_vars["request_cc"] = req_cc_list
    context_vars["final_to"] = final_to_list
    context_vars["final_cc"] = final_cc_list
    context_vars["to"] = final_to_list
    context_vars["cc"] = final_cc_list

    return {
        "status": "SUCCESS",
        "email_job_id": email_job_id,
        "email_queue_table": full_mail_tbl if (email_job_id and found_mail_tbl) else None,
        "workflow_node_emails": {
            "to": node_to_list,
            "cc": node_cc_list
        },
        "request_emails": {
            "to": req_to_list,
            "cc": req_cc_list
        },
        "final_recipients": {
            "to": final_to_list,
            "cc": final_cc_list
        },
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






