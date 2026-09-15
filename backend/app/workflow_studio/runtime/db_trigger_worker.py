import asyncio
import datetime
import json
import time
from typing import Dict, Any, List, Optional, Set
from sqlalchemy import text
from app.core.logger import logger
from app.core.database import DynamicEnginePool, ClientDatabaseAdapter
from app.workflow.database import WorkflowSessionLocal
from app.workflow.persistence.models import SpiffWorkflowInstance, SpiffActivityHistory, BPMNDefinition
from app.workflow_definition.models import WorkflowDefinition
from app.workflow.models.history import WorkflowHistory
from app.workflow_studio.runtime.actions import ActionRegistry

class DatabaseTriggerWorker:
    """
    Autonomous background worker that scans Client Database tables for raw SQL INSERT / UPDATE
    events matching published workflow Start Node trigger configurations, and automatically
    executes the full downstream workflow graph.
    """
    _running: bool = False
    _task: Optional[asyncio.Task] = None
    _processed_ids: Dict[str, Set[int]] = {}
    _table_max_ids: Dict[str, int] = {}
    _initialized: bool = False

    @classmethod
    async def start(cls):
        if cls._running:
            return
        cls._running = True
        cls._task = asyncio.create_task(cls._run_loop())
        logger.info("DatabaseTriggerWorker started: Automatic database event scanner active.")

    @classmethod
    async def stop(cls):
        cls._running = False
        if cls._task:
            cls._task.cancel()
            try:
                await cls._task
            except asyncio.CancelledError:
                pass
        logger.info("DatabaseTriggerWorker stopped.")

    @classmethod
    async def _run_loop(cls):
        # Initial delay on server startup to allow DB pool & tables to stabilize
        await asyncio.sleep(3)
        while cls._running:
            try:
                await asyncio.to_thread(cls._scan_and_execute)
            except Exception as e:
                logger.error(f"DatabaseTriggerWorker scan error: {e}", exc_info=False)
            await asyncio.sleep(4)

    @classmethod
    def _scan_and_execute(cls):
        db = WorkflowSessionLocal()
        try:
            # 1. Discover all published workflows with Database Start Node triggers
            triggers = cls._discover_active_triggers(db)
            if not triggers:
                return

            for trig in triggers:
                try:
                    cls._process_table_trigger(db, trig)
                except Exception as ex:
                    logger.error(f"Error processing trigger for workflow '{trig.get('workflow_name')}': {ex}")
        finally:
            db.close()

    @classmethod
    def _discover_active_triggers(cls, db) -> List[Dict[str, Any]]:
        triggers = []
        try:
            # Check BPMNDefinition
            bpmn_list = db.query(BPMNDefinition).filter(
                BPMNDefinition.is_active == True,
                BPMNDefinition.status.in_(["Published", "Active", "Draft"])
            ).all()

            for b in bpmn_list:
                if not b.json_content:
                    continue
                try:
                    jc = json.loads(b.json_content) if isinstance(b.json_content, str) else b.json_content
                    nodes = jc.get("nodes", [])
                    edges = jc.get("edges", []) or jc.get("connections", [])
                    start_node = next((n for n in nodes if n.get("type") == "start" or str(n.get("id", "")).startswith("start")), None)
                    if start_node:
                        s_data = start_node.get("data", {})
                        t_type = s_data.get("triggerType") or s_data.get("trigger_type")
                        if t_type == "Database" or s_data.get("table") or s_data.get("entity"):
                            table_name = s_data.get("table") or s_data.get("entity") or s_data.get("target_entity")
                            if table_name and str(table_name).strip().lower() not in ("", "target_table", "undefined", "null"):
                                triggers.append({
                                    "workflow_id": b.id,
                                    "workflow_name": b.name or b.spec_id or f"Workflow #{b.id}",
                                    "connection_id": b.connection_id or 4,
                                    "table_name": str(table_name).strip(),
                                    "event_type": s_data.get("eventType") or s_data.get("event_type") or "INSERT_OR_UPDATE",
                                    "filter_field": s_data.get("filterField") or s_data.get("filter_field") or "",
                                    "filter_operator": s_data.get("filterOperator") or s_data.get("filter_operator") or "==",
                                    "filter_value": s_data.get("filterValue") if s_data.get("filterValue") is not None else "",
                                    "nodes": nodes,
                                    "edges": edges
                                })
                except Exception:
                    pass

            # Check WorkflowDefinition / GenericWorkflow
            wfs = db.query(WorkflowDefinition).filter(
                WorkflowDefinition.status.in_(["ACTIVE", "Active", "DRAFT", "Draft"])
            ).all()
            for w in wfs:
                jc = getattr(w, "json_content", None)
                if not jc:
                    continue
                try:
                    parsed = json.loads(jc) if isinstance(jc, str) else jc
                    nodes = parsed.get("nodes", [])
                    edges = parsed.get("edges", []) or parsed.get("connections", [])
                    start_node = next((n for n in nodes if n.get("type") == "start" or str(n.get("id", "")).startswith("start")), None)
                    if start_node:
                        s_data = start_node.get("data", {})
                        t_type = s_data.get("triggerType") or s_data.get("trigger_type")
                        if t_type == "Database" or s_data.get("table") or s_data.get("entity"):
                            table_name = s_data.get("table") or s_data.get("entity") or s_data.get("target_entity")
                            if table_name and str(table_name).strip().lower() not in ("", "target_table", "undefined", "null"):
                                w_id = w.workflow_id
                                # Avoid duplicates if already discovered
                                if not any(t["workflow_name"] == (w.name or w.spec_id) for t in triggers):
                                    triggers.append({
                                        "workflow_id": w_id,
                                        "workflow_name": w.name or w.spec_id or f"Workflow #{w_id}",
                                        "connection_id": getattr(w, "connection_id", None) or 4,
                                        "table_name": str(table_name).strip(),
                                        "event_type": s_data.get("eventType") or s_data.get("event_type") or "INSERT_OR_UPDATE",
                                        "filter_field": s_data.get("filterField") or s_data.get("filter_field") or "",
                                        "filter_operator": s_data.get("filterOperator") or s_data.get("filter_operator") or "==",
                                        "filter_value": s_data.get("filterValue") if s_data.get("filterValue") is not None else "",
                                        "nodes": nodes,
                                        "edges": edges
                                    })
                except Exception:
                    pass

        except Exception as ex:
            logger.error(f"Error discovering active triggers: {ex}")

        return triggers

    @classmethod
    def _process_table_trigger(cls, db, trigger_info: Dict[str, Any]):
        table_name = trigger_info["table_name"]
        conn_id = trigger_info.get("connection_id") or 4
        wf_name = trigger_info["workflow_name"]
        wf_id = trigger_info["workflow_id"]
        event_type = trigger_info.get("event_type", "INSERT_OR_UPDATE").upper()
        filter_field = trigger_info.get("filter_field", "")
        filter_operator = trigger_info.get("filter_operator", "==")
        filter_val = trigger_info.get("filter_value", "")
        nodes = trigger_info.get("nodes", [])
        edges = trigger_info.get("edges", [])

        eng = DynamicEnginePool.get_engine(conn_id)
        target_schema = ClientDatabaseAdapter._resolve_target_schema(None, conn_id)
        clean_table = table_name.split(".")[-1] if "." in table_name else table_name
        full_table = f"{target_schema}.{clean_table}" if target_schema else clean_table

        col_meta = ClientDatabaseAdapter.get_table_columns(clean_table, schema=target_schema, connection_id=conn_id)
        pks = col_meta.get("primary_keys") or []
        pk_col = pks[0] if pks else "id"

        cache_key = f"{conn_id}:{clean_table}"
        if cache_key not in cls._processed_ids:
            cls._processed_ids[cache_key] = set()

        with eng.connect() as conn:
            # Query recent rows from client database table
            query_sql = f"SELECT * FROM {full_table} ORDER BY {pk_col} DESC LIMIT 50"
            rows = conn.execute(text(query_sql)).mappings().all()

        if not rows:
            return

        # First scan initialization: record existing rows so we only trigger on NEW changes
        if cache_key not in cls._table_max_ids:
            cls._table_max_ids[cache_key] = max(r[pk_col] for r in rows if r.get(pk_col) is not None)
            for r in rows:
                if r.get(pk_col) is not None:
                    cls._processed_ids[cache_key].add(int(r[pk_col]))
            logger.info(f"DatabaseTriggerWorker initialized for '{full_table}' (max PK: {cls._table_max_ids[cache_key]})")
            return

        max_known_id = cls._table_max_ids[cache_key]
        for row in reversed(rows):
            rec_id = row.get(pk_col)
            if rec_id is None:
                continue
            rec_id = int(rec_id)

            # Check if this record is a newly inserted row
            is_new_insert = rec_id > max_known_id
            
            # Check filter condition
            matches_condition = True
            if filter_field and filter_field in row:
                actual_val = str(row[filter_field] if row[filter_field] is not None else "")
                expected_val = str(filter_val)
                if filter_operator in ("==", "=", "equals", "changes_to"):
                    matches_condition = actual_val.strip().upper() == expected_val.strip().upper()
                elif filter_operator in ("!=", "<>", "not_equals"):
                    matches_condition = actual_val.strip().upper() != expected_val.strip().upper()
                elif filter_operator == "is_not_null":
                    matches_condition = actual_val.strip() != ""

            # Trigger condition matching
            should_trigger = False
            if is_new_insert and event_type in ("INSERT", "INSERT_OR_UPDATE") and matches_condition:
                should_trigger = True
            elif event_type in ("UPDATE", "INSERT_OR_UPDATE") and matches_condition and rec_id not in cls._processed_ids[cache_key]:
                should_trigger = True

            if should_trigger:
                logger.info(f"⚡ [DatabaseTriggerWorker] Triggering workflow '{wf_name}' for {full_table} Record #{rec_id} (Data: {dict(row)})")
                cls._execute_triggered_workflow(
                    db=db,
                    workflow_id=wf_id,
                    workflow_name=wf_name,
                    connection_id=conn_id,
                    table_name=full_table,
                    clean_table=clean_table,
                    record_id=rec_id,
                    record_data=dict(row),
                    nodes=nodes,
                    edges=edges
                )
                cls._processed_ids[cache_key].add(rec_id)
                if rec_id > cls._table_max_ids[cache_key]:
                    cls._table_max_ids[cache_key] = rec_id

    @classmethod
    def _execute_triggered_workflow(
        cls,
        db,
        workflow_id: Any,
        workflow_name: str,
        connection_id: int,
        table_name: str,
        clean_table: str,
        record_id: int,
        record_data: Dict[str, Any],
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ):
        now_dt = datetime.datetime.now()
        eng = DynamicEnginePool.get_engine(connection_id)
        target_schema = ClientDatabaseAdapter._resolve_target_schema(None, connection_id)

        # 1. Create or update SpiffWorkflowInstance for Monitoring
        bpmn_id = int(workflow_id) if str(workflow_id).isdigit() else 128
        inst = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == clean_table,
            SpiffWorkflowInstance.entity_id == record_id
        ).first()

        state_data = {
            "workflow_name": workflow_name,
            "wf_name": workflow_name,
            "table": clean_table,
            "record_id": record_id,
            "initial_data": record_data,
            "status": record_data.get("status")
        }

        if not inst:
            inst = SpiffWorkflowInstance(
                entity_type=clean_table,
                entity_id=record_id,
                bpmn_definition_id=bpmn_id,
                status="Running",
                serialized_state=json.dumps(state_data, default=str),
                current_task_code="Database Trigger Activated",
                started_on=now_dt
            )
            db.add(inst)
        else:
            inst.bpmn_definition_id = bpmn_id
            inst.status = "Running"
            inst.started_on = now_dt
            inst.completed_on = None
            inst.current_task_code = "Database Trigger Activated"
            inst.serialized_state = json.dumps(state_data, default=str)

        db.flush()

        # 2. Traverse nodes sequentially along the workflow graph
        current_vars = {**record_data, "id": record_id, "entity_id": record_id, "record_id": record_id}
        start_node = next((n for n in nodes if n.get("type") == "start" or str(n.get("id", "")).startswith("start")), nodes[0] if nodes else None)
        
        current_node = start_node
        visited_nodes = set()

        while current_node and current_node.get("id") not in visited_nodes:
            node_id = current_node.get("id")
            visited_nodes.add(node_id)
            n_type = current_node.get("type", "generic")
            n_data = current_node.get("data", {})
            node_name = n_data.get("label") or n_data.get("name") or n_type

            step_start = time.time()
            diff_fields = {}
            sql_executed = []

            # A. DATABASE ACTION / UPDATE NODE
            if n_type in ("record", "dbUpdate", "db_update"):
                mappings = n_data.get("fieldMappings") or []
                updates = {}
                for m in mappings:
                    if m.get("field"):
                        val = m.get("value")
                        # Resolve variable if any
                        val = ClientDatabaseAdapter._resolve_template_value(val, current_vars)
                        updates[m["field"]] = val

                if updates:
                    set_clauses = []
                    bind_params = {"pk_val": record_id}
                    for k, v in updates.items():
                        param_key = f"val_{k}"
                        set_clauses.append(f"{k} = :{param_key}")
                        bind_params[param_key] = v

                    sql_str = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE id = :pk_val"
                    sql_executed.append(sql_str)
                    with eng.begin() as conn:
                        conn.execute(text(sql_str), bind_params)
                    
                    diff_fields = {k: {"new": v} for k, v in updates.items()}
                    current_vars.update(updates)
                    inst.current_task_code = node_name

            # B. SEND EMAIL / NOTIFICATION NODE
            elif n_type in ("communication", "notification", "email"):
                to_email = n_data.get("to") or current_vars.get("employee_email") or current_vars.get("email") or "jasminbabariya22@gmail.com"
                to_email = str(ClientDatabaseAdapter._resolve_template_value(to_email, current_vars) or to_email)
                subj = n_data.get("subject") or f"Record #{record_id} Notification"
                subj = str(ClientDatabaseAdapter._resolve_template_value(subj, current_vars) or subj)
                body = n_data.get("body") or "Your workflow request has been processed."
                body = str(ClientDatabaseAdapter._resolve_template_value(body, current_vars) or body)

                email_cfg = {
                    "to": to_email,
                    "cc": n_data.get("cc"),
                    "bcc": n_data.get("bcc"),
                    "subject": subj,
                    "body": body,
                    "connection_id": connection_id
                }
                ActionRegistry.execute("SEND_EMAIL", email_cfg, current_vars)
                inst.current_task_code = node_name

            # C. TIMER DELAY NODE
            elif n_type in ("timer", "delay", "wait"):
                dur_val = n_data.get("durationValue") or n_data.get("duration") or 5
                dur_unit = n_data.get("durationUnit") or "seconds"
                diff_fields = {"timer": {"status": "ELAPSED", "duration": f"{dur_val} {dur_unit}"}}
                inst.current_task_code = node_name

            # D. END NODE
            elif n_type in ("end", "endevent"):
                inst.status = "Completed"
                inst.completed_on = datetime.datetime.now()
                inst.current_task_code = node_name

            elapsed_ms = round((time.time() - step_start) * 1000, 1)

            # Record Activity History Trace
            act_hist = SpiffActivityHistory(
                instance_id=inst.instance_id,
                activity_id=str(node_id),
                activity_name=node_name,
                activity_type=n_type,
                status="COMPLETED",
                variables=json.dumps({**diff_fields, "duration_ms": elapsed_ms, "sql": sql_executed}, default=str),
                timestamp=datetime.datetime.now()
            )
            db.add(act_hist)

            # Record Workflow History Log
            wf_hist = WorkflowHistory(
                instance_id=inst.instance_id,
                action_name=n_type.upper(),
                performed_by=1,
                performed_role="SYSTEM_TRIGGER_WORKER",
                remarks=f"Automatic trigger executed step '{node_name}'",
                performed_on=datetime.datetime.now()
            )
            db.add(wf_hist)
            db.flush()

            # Find next connected node
            outgoing = [e for e in edges if e.get("source") == node_id]
            if outgoing:
                next_node_id = outgoing[0].get("target")
                current_node = next((n for n in nodes if n.get("id") == next_node_id), None)
            else:
                current_node = None

        state_data["status"] = current_vars.get("status")
        state_data["final_vars"] = current_vars
        inst.serialized_state = json.dumps(state_data, default=str)
        if inst.status != "Completed":
            inst.status = "Completed"
            inst.completed_on = datetime.datetime.now()

        db.commit()
        logger.info(f"✅ [DatabaseTriggerWorker] Finished workflow '{workflow_name}' for Record #{record_id} successfully (Instance #{inst.instance_id}).")
