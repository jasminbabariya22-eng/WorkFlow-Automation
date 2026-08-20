import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.logger import logger
from app.workflow.workflow_session import WorkflowSessionLocal
from app.workflow.persistence.models import (
    SpiffWorkflowInstance,
    SpiffHumanTask,
    SpiffActivityHistory,
    WorkflowEntityConfig
)
from app.workflow_definition.models import (
    GenericWorkflow,
    WorkflowVersion,
    WorkflowNode,
    WorkflowConnection
)
from app.workflow.services.visibility_service import WorkflowVisibilityService
from app.workflow_studio.runtime.actions import ConditionEvaluator, ActionRegistry


class StudioExecutionAdapter:
    """
    StudioExecutionAdapter executes published Workflow Studio definitions (WorkflowVersion graph)
    step-by-step. Integrates human tasks, automated actions, emails, visibility, and history.
    """

    @classmethod
    def resolve_published_version(
        cls,
        db: Session,
        entity_type: str,
        definition_id: Optional[int] = None
    ) -> WorkflowVersion:
        """
        Resolves the active PUBLISHED WorkflowVersion for a given entity_type or explicit definition_id (workflow_id or version_id).
        """
        if definition_id:
            # 1. Check by workflow_id with status PUBLISHED
            version = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == definition_id,
                WorkflowVersion.status == "PUBLISHED"
            ).order_by(WorkflowVersion.version_number.desc()).first()
            if version:
                return version

            # 2. Check by workflow_id (latest draft/validated)
            version = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == definition_id
            ).order_by(WorkflowVersion.version_number.desc()).first()
            if version:
                return version

            # 3. Check by workflow_version_id directly
            version = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_version_id == definition_id
            ).first()
            if version:
                return version


        # 1. Check WorkflowEntityConfig mapping
        entity_cfg = db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.entity_type == entity_type,
            WorkflowEntityConfig.is_active == True
        ).first()

        if entity_cfg:
            wf = db.query(GenericWorkflow).filter(
                GenericWorkflow.workflow_key == entity_cfg.specification_id
            ).first()
            if wf:
                pub_v = db.query(WorkflowVersion).filter(
                    WorkflowVersion.workflow_id == wf.workflow_id,
                    WorkflowVersion.status == "PUBLISHED"
                ).order_by(WorkflowVersion.version_number.desc()).first()
                if pub_v:
                    return pub_v

        # 2. Check GenericWorkflow directly by entity_type
        wf = db.query(GenericWorkflow).filter(
            GenericWorkflow.entity_type == entity_type,
            GenericWorkflow.status.in_(["ACTIVE", "DRAFT"])
        ).order_by(GenericWorkflow.updated_at.desc()).first()

        if wf:
            pub_v = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == wf.workflow_id,
                WorkflowVersion.status == "PUBLISHED"
            ).order_by(WorkflowVersion.version_number.desc()).first()
            if pub_v:
                return pub_v
            # Fallback to latest validated/draft version if no published version exists
            latest_v = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == wf.workflow_id
            ).order_by(WorkflowVersion.version_number.desc()).first()
            if latest_v:
                return latest_v

        raise HTTPException(
            status_code=404,
            detail=f"No published Studio workflow definition found for entity_type '{entity_type}'."
        )

    @classmethod
    def start_workflow(
        cls,
        entity_type: str,
        entity_id: int,
        user_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
        definition_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Starts a new workflow instance from the published Studio definition.
        Advances from START through automated nodes to the first APPROVAL or END.
        """
        db_to_use = db or WorkflowSessionLocal()
        own_db = db is None

        try:
            version = cls.resolve_published_version(db_to_use, entity_type, definition_id=definition_id)
            current_time = datetime.now()
            vars_dict = dict(variables or {})
            if "entity" not in vars_dict:
                vars_dict["entity"] = {"id": entity_id, "type": entity_type}
            vars_dict.setdefault("entity_id", entity_id)
            vars_dict.setdefault("entity_type", entity_type)
            if user_id:
                if "user" not in vars_dict:
                    vars_dict["user"] = {"id": user_id}
                vars_dict.setdefault("user_id", user_id)

            # Find START and END nodes
            start_node = next((n for n in version.nodes if n.node_type == "START" and n.is_active), None)
            end_node = next((n for n in version.nodes if n.node_type == "END" and n.is_active), None)
            if not start_node:
                raise HTTPException(status_code=400, detail="Workflow definition has no START node.")
            if not end_node:
                raise HTTPException(status_code=400, detail="Workflow definition has no END node.")


            # Create or update SpiffWorkflowInstance
            instance = db_to_use.query(SpiffWorkflowInstance).filter(
                SpiffWorkflowInstance.entity_type == entity_type,
                SpiffWorkflowInstance.entity_id == entity_id
            ).first()

            if not instance:
                instance = SpiffWorkflowInstance(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    bpmn_definition_id=version.workflow_version_id,
                    status="Running",
                    serialized_state=json.dumps({"version_id": version.workflow_version_id, "variables": vars_dict}),
                    current_task_code=start_node.node_key,
                    started_on=current_time
                )
                db_to_use.add(instance)
            else:
                instance.bpmn_definition_id = version.workflow_version_id
                instance.status = "Running"
                instance.serialized_state = json.dumps({"version_id": version.workflow_version_id, "variables": vars_dict})
                instance.current_task_code = start_node.node_key
                instance.completed_on = None

            db_to_use.flush()

            # Advance from START node to first actionable node
            res = cls._advance_graph(
                db=db_to_use,
                instance=instance,
                version=version,
                from_node=start_node,
                action="SUBMIT",
                user_id=user_id,
                variables=vars_dict
            )

            db_to_use.commit()
            return res

        except Exception as e:
            db_to_use.rollback()
            raise e
        finally:
            if own_db:
                db_to_use.close()

    @classmethod
    def is_user_authorized_for_task(
        cls,
        user_id: int,
        node_cfg: Dict[str, Any],
        task: Optional[SpiffHumanTask] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determines if a user is authorized to view or execute a human task
        based on the task's assignment configuration (role, user, department)
        resolved dynamically against the Client Database.
        """
        if user_profile is None:
            from app.core.database import ClientDatabaseAdapter
            user_profile = ClientDatabaseAdapter.get_user_profile(user_id)
        if not user_profile:
            return False

        # Admin bypass
        role_name = str(user_profile.get("role_name") or "").strip().upper()
        if role_name in ("ADMIN", "SUPERADMIN"):
            return True

        assignment = node_cfg.get("assignment", {}) if isinstance(node_cfg.get("assignment"), dict) else {}
        assign_type = str(assignment.get("type") or "role").lower()

        # 1. User Assignment
        if assign_type == "user":
            target_user_id = assignment.get("userId") or assignment.get("id")
            target_user_name = assignment.get("userName") or assignment.get("name")
            if target_user_id and str(target_user_id) == str(user_id):
                return True
            if target_user_name and str(target_user_name).strip().lower() == str(user_profile.get("name")).strip().lower():
                return True
            return False

        # 2. Department Assignment
        elif assign_type == "department":
            target_dept_id = assignment.get("departmentId") or assignment.get("id")
            target_dept_name = assignment.get("departmentName") or assignment.get("name")
            user_dept_id = user_profile.get("dept_id")
            user_dept_name = user_profile.get("department_name")
            if target_dept_id and user_dept_id and str(target_dept_id) == str(user_dept_id):
                return True
            if target_dept_name and user_dept_name and str(target_dept_name).strip().lower() == str(user_dept_name).strip().lower():
                return True
            return False

        # 3. Role Assignment (Default)
        else:
            target_role_id = assignment.get("roleId") or assignment.get("id")
            target_role_name = (
                assignment.get("roleName") or 
                assignment.get("role") or 
                node_cfg.get("role") or 
                node_cfg.get("role_code") or 
                (task.role_code if task else None)
            )
            user_role_id = user_profile.get("role_id")
            if target_role_id and user_role_id and str(target_role_id) == str(user_role_id):
                return True
            if target_role_name and role_name and str(target_role_name).strip().upper() == role_name:
                return True
            return False

    @classmethod
    def get_pending_tasks_for_user(cls, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all human tasks currently in READY state that the given user
        is authorized to view/execute according to generic assignment rules.
        """
        from app.core.database import ClientDatabaseAdapter
        user_profile = ClientDatabaseAdapter.get_user_profile(user_id)
        if not user_profile:
            return []

        active_items = (
            db.query(SpiffHumanTask, SpiffWorkflowInstance)
            .join(SpiffWorkflowInstance, SpiffHumanTask.instance_id == SpiffWorkflowInstance.instance_id)
            .filter(
                SpiffHumanTask.status == "READY",
                SpiffWorkflowInstance.status.in_(["WAITING", "Running"])
            )
            .order_by(SpiffHumanTask.created_on.desc())
            .all()
        )

        if not active_items:
            return []

        version_ids = {inst.bpmn_definition_id for _, inst in active_items if inst.bpmn_definition_id}
        versions = db.query(WorkflowVersion).filter(WorkflowVersion.workflow_version_id.in_(version_ids)).all()
        version_map = {v.workflow_version_id: v for v in versions}

        results = []
        for task, instance in active_items:
            version = version_map.get(instance.bpmn_definition_id)
            if not version:
                continue

            # Find corresponding node
            matching_node = None
            for n in version.nodes:
                if n.node_key == instance.current_task_code or n.node_key == task.task_spec_id:
                    matching_node = n
                    break
                try:
                    cfg = json.loads(n.configuration) if isinstance(n.configuration, str) else (n.configuration or {})
                    if cfg.get("taskCode") == task.task_spec_id:
                        matching_node = n
                        break
                except Exception:
                    pass

            if not matching_node:
                continue

            try:
                node_cfg = json.loads(matching_node.configuration) if isinstance(matching_node.configuration, str) else (matching_node.configuration or {})
            except Exception:
                node_cfg = {}

            if cls.is_user_authorized_for_task(user_id, node_cfg, task, user_profile=user_profile):
                raw_actions = node_cfg.get("actions") or node_cfg.get("allowed_actions") or []
                results.append({
                    "task_id": task.task_id,
                    "instance_id": task.instance_id,
                    "entity_type": instance.entity_type,
                    "entity_id": instance.entity_id,
                    "task_key": matching_node.node_key,
                    "task_name": matching_node.name,
                    "task_code": node_cfg.get("taskCode") or matching_node.node_key,
                    "role_code": task.role_code,
                    "assignment": node_cfg.get("assignment", {}),
                    "allowed_actions": raw_actions,
                    "created_on": task.created_on.isoformat() if task.created_on else None
                })

        return results

    @classmethod
    def execute_action(
        cls,
        entity_type: str,
        entity_id: int,
        action: str,
        user_id: Optional[int] = None,
        remarks: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Resumes workflow execution upon human action (e.g. APPROVE, REJECT, FORCE_APPROVE).
        Completes the current human task, follows matching outgoing edge, and advances.
        """
        db_to_use = db or WorkflowSessionLocal()
        own_db = db is None

        try:
            instance = db_to_use.query(SpiffWorkflowInstance).filter(
                SpiffWorkflowInstance.entity_type == entity_type,
                SpiffWorkflowInstance.entity_id == entity_id
            ).first()

            if not instance:
                raise HTTPException(status_code=404, detail=f"No workflow instance found for {entity_type} ID {entity_id}.")

            if instance.status not in ("Running", "WAITING"):
                raise HTTPException(status_code=400, detail=f"Workflow instance is in '{instance.status}' state and cannot accept actions.")

            # Load pinned version
            version = db_to_use.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_version_id == instance.bpmn_definition_id
            ).first()
            if not version:
                raise HTTPException(status_code=404, detail=f"Workflow version {instance.bpmn_definition_id} not found.")

            # Find current node
            current_node = None
            for n in version.nodes:
                if not n.is_active:
                    continue
                if n.node_key == instance.current_task_code:
                    current_node = n
                    break
                try:
                    cfg = json.loads(n.configuration) if isinstance(n.configuration, str) else (n.configuration or {})
                    if cfg.get("taskCode") == instance.current_task_code:
                        current_node = n
                        break
                except Exception:
                    pass

            if not current_node:
                raise HTTPException(status_code=400, detail=f"Current node '{instance.current_task_code}' not found in workflow definition.")

            # Parse node configuration
            try:
                current_cfg = json.loads(current_node.configuration) if isinstance(current_node.configuration, str) else (current_node.configuration or {})
            except Exception:
                current_cfg = {}

            # Validate action is allowed on this node
            raw_allowed = current_cfg.get("actions") or current_cfg.get("allowed_actions") or []
            allowed_actions = []
            for a in raw_allowed:
                if isinstance(a, str):
                    allowed_actions.append(a.strip().upper())
                elif isinstance(a, dict):
                    code = a.get("action_code") or a.get("id") or a.get("code") or a.get("name")
                    if code:
                        allowed_actions.append(str(code).strip().upper())

            if allowed_actions:
                if action.strip().upper() not in allowed_actions:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Action '{action}' is not permitted for task '{current_node.name}'. Allowed actions: {allowed_actions}"
                    )

            # Locate active human task
            task_code = current_cfg.get("taskCode") or current_node.node_key
            active_task = db_to_use.query(SpiffHumanTask).filter(
                SpiffHumanTask.instance_id == instance.instance_id,
                SpiffHumanTask.status == "READY"
            ).filter(
                (SpiffHumanTask.task_spec_id == current_node.node_key) | 
                (SpiffHumanTask.task_spec_id == task_code)
            ).first()

            if not active_task and current_node.node_type in ("APPROVAL", "USER_TASK"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Task '{current_node.name}' has already been completed or is not in READY state."
                )

            # Check user assignment authorization
            if user_id:
                if not cls.is_user_authorized_for_task(user_id, current_cfg, active_task):
                    raise HTTPException(
                        status_code=403,
                        detail=f"User ID {user_id} is not authorized to perform task '{current_node.name}'."
                    )

            # Parse state variables
            try:
                state_data = json.loads(instance.serialized_state) if instance.serialized_state else {}
                vars_dict = state_data.get("variables", {})
            except Exception:
                vars_dict = {}

            if variables:
                vars_dict.update(variables)
            if "entity" not in vars_dict:
                vars_dict["entity"] = {"id": entity_id, "type": entity_type}
            vars_dict.setdefault("entity_id", entity_id)
            vars_dict.setdefault("entity_type", entity_type)
            if user_id:
                if "user" not in vars_dict:
                    vars_dict["user"] = {"id": user_id}
                vars_dict.setdefault("user_id", user_id)
            vars_dict["last_action"] = action
            vars_dict["last_remarks"] = remarks or ""
            vars_dict["last_actor_id"] = user_id

            # Complete active human task
            if active_task:
                active_task.status = "COMPLETED"
                active_task.completed_on = datetime.now()
                active_task.assignee_id = user_id
                db_to_use.flush()

            # Advance graph from current node based on action
            res = cls._advance_graph(
                db=db_to_use,
                instance=instance,
                version=version,
                from_node=current_node,
                action=action,
                user_id=user_id,
                variables=vars_dict
            )

            db_to_use.commit()
            return res

        except Exception as e:
            db_to_use.rollback()
            raise e
        finally:
            if own_db:
                db_to_use.close()

    @classmethod
    def _advance_graph(
        cls,
        db: Session,
        instance: SpiffWorkflowInstance,
        version: WorkflowVersion,
        from_node: WorkflowNode,
        action: str,
        user_id: Optional[int],
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Navigates across outgoing connections from from_node matching action/condition.
        Executes automated nodes until next human task (APPROVAL) or END.
        """
        current_node = from_node
        node_map = {n.node_id: n for n in version.nodes if n.is_active}
        steps_taken = 0
        MAX_AUTO_STEPS = 50

        while True:
            steps_taken += 1
            if steps_taken > MAX_AUTO_STEPS:
                raise HTTPException(
                    status_code=500,
                    detail=f"Execution loop limit exceeded ({MAX_AUTO_STEPS} steps). Possible cycle detected at node '{current_node.name}'."
                )

            # 1. Find matching outgoing connection
            outgoing_conns = [c for c in version.connections if c.source_node_id == current_node.node_id]

            if not outgoing_conns:
                if current_node.node_type == "END":
                    break
                raise HTTPException(
                    status_code=400,
                    detail=f"Node '{current_node.name}' ({current_node.node_key}) has no outgoing connections."
                )

            # If current node is a CONDITION node, evaluate its condition configuration to determine route
            if current_node.node_type.upper() == "CONDITION":
                try:
                    cur_cfg = json.loads(current_node.configuration) if isinstance(current_node.configuration, str) else (current_node.configuration or {})
                except Exception:
                    cur_cfg = {}
                
                cond_result = ConditionEvaluator.evaluate_node_condition(cur_cfg, variables)
                action = "TRUE" if cond_result else "FALSE"
                logger.info(f"StudioEngine: Evaluated Condition '{current_node.name}' ({current_node.node_key}) -> {action} with config={cur_cfg}")

            # Match connection based on condition / action / sourceHandle
            matched_conn = None
            for conn in outgoing_conns:
                # 1. Match sourceHandle or metadata_json route identifier
                try:
                    c_meta = json.loads(conn.metadata_json) if isinstance(conn.metadata_json, str) else (conn.metadata_json or {})
                except Exception:
                    c_meta = {}
                source_handle = str(c_meta.get("sourceHandle") or "").strip().upper()
                if source_handle and source_handle == action:
                    matched_conn = conn
                    break

                # 2. Match label (e.g. "TRUE", "FALSE")
                if conn.label and conn.label.strip().upper() == action:
                    matched_conn = conn
                    break

                # 3. Check condition expression matching
                if conn.condition and ConditionEvaluator.evaluate(conn.condition, action, variables):
                    matched_conn = conn
                    break

            if not matched_conn:
                if current_node.node_type.upper() == "CONDITION" and len(outgoing_conns) >= 2:
                    # If 2 outgoing routes and action is TRUE, use 1st edge; if FALSE, use 2nd edge
                    matched_conn = outgoing_conns[0] if action == "TRUE" else outgoing_conns[1]
                else:
                    # Fallback to first unconditional connection
                    unconditional = [c for c in outgoing_conns if not c.condition and not c.label]
                    matched_conn = unconditional[0] if unconditional else outgoing_conns[0]

            target_node = node_map.get(matched_conn.target_node_id)
            if not target_node:
                raise HTTPException(status_code=400, detail=f"Target node ID {matched_conn.target_node_id} not found in version.")

            target_type = target_node.node_type.upper()
            logger.info(f"StudioEngine: {current_node.node_key} ({current_node.node_type}) --[{action}]--> {target_node.node_key} ({target_type})")

            # Parse target node configuration
            try:
                node_cfg = json.loads(target_node.configuration) if isinstance(target_node.configuration, str) else (target_node.configuration or {})
            except Exception:
                node_cfg = {}

            # Record atomic state transition in workflow_history
            cls._log_workflow_history(
                db=db,
                instance=instance,
                from_node=current_node,
                to_node=target_node,
                action=action,
                user_id=user_id,
                remarks=variables.get("last_remarks") if variables else None
            )

            # Handle Node Types:
            if target_type in ("APPROVAL", "USER_TASK"):
                # Human interaction node: Create SpiffHumanTask and pause execution
                assignment_cfg = node_cfg.get("assignment", {}) if isinstance(node_cfg.get("assignment"), dict) else {}
                role_code = (
                    assignment_cfg.get("roleName") or 
                    assignment_cfg.get("role") or 
                    assignment_cfg.get("userName") or 
                    assignment_cfg.get("departmentName") or 
                    node_cfg.get("role") or 
                    node_cfg.get("candidate_group") or 
                    "INITIATOR"
                )
                task_code = node_cfg.get("taskCode") or target_node.node_key

                human_task = SpiffHumanTask(
                    instance_id=instance.instance_id,
                    task_spec_id=task_code,
                    role_code=role_code,
                    status="READY",
                    created_on=datetime.now()
                )
                db.add(human_task)
                db.flush()

                instance.status = "WAITING"
                instance.current_task_code = task_code
                instance.serialized_state = json.dumps({"version_id": version.workflow_version_id, "variables": variables})
                db.flush()

                # Sync visibility
                cls._sync_visibility(instance)

                # Log activity history
                cls._log_history(db, instance, target_node, "READY", user_id, variables)

                return {
                    "instance_id": instance.instance_id,
                    "entity_type": instance.entity_type,
                    "entity_id": instance.entity_id,
                    "status": "WAITING",
                    "current_task_code": task_code,
                    "role_code": role_code,
                    "task_id": human_task.task_id,
                    "message": f"Workflow paused at user task '{target_node.name}' ({task_code})"
                }

            elif target_type == "EMAIL":
                # Execute automated email notification
                cls._execute_email_node(instance, node_cfg, variables)
                cls._log_history(db, instance, target_node, "COMPLETED", user_id, variables)
                current_node = target_node
                action = "DEFAULT"
                continue

            elif target_type in ("ACTION", "RECORD", "API"):
                # Execute automated action handler
                action_type = (
                    node_cfg.get("actionType") or 
                    node_cfg.get("action_type") or 
                    node_cfg.get("subType") or 
                    "GENERIC_ACTION"
                )
                try:
                    ActionRegistry.execute(action_type, node_cfg, variables)
                except Exception as ex:
                    logger.error(f"StudioEngine: Action '{target_node.name}' ({target_node.node_key}) failed: {ex}")
                    raise HTTPException(status_code=500, detail=f"Action '{target_node.name}' execution failed: {str(ex)}")

                cls._log_history(db, instance, target_node, "COMPLETED", user_id, variables)
                current_node = target_node
                action = "DEFAULT"
                continue

            elif target_type == "CONDITION":
                # Decision node evaluates condition and continues
                cls._log_history(db, instance, target_node, "EVALUATED", user_id, variables)
                current_node = target_node
                action = "DEFAULT"
                continue

            elif target_type == "END":
                # Terminal node: Mark instance completed
                final_code = node_cfg.get("taskCode") or target_node.node_key or "END"
                instance.status = "Completed"
                instance.current_task_code = final_code
                instance.completed_on = datetime.now()
                instance.serialized_state = json.dumps({"version_id": version.workflow_version_id, "variables": variables})

                # Ensure no lingering READY human task remains for this instance
                db.query(SpiffHumanTask).filter(
                    SpiffHumanTask.instance_id == instance.instance_id,
                    SpiffHumanTask.status == "READY"
                ).update({
                    "status": "COMPLETED",
                    "completed_on": datetime.now()
                })
                db.flush()

                # Sync final visibility
                cls._sync_visibility(instance)

                cls._log_history(db, instance, target_node, "COMPLETED", user_id, variables)

                return {
                    "instance_id": instance.instance_id,
                    "entity_type": instance.entity_type,
                    "entity_id": instance.entity_id,
                    "status": "Completed",
                    "current_task_code": final_code,
                    "message": f"Workflow completed successfully at {target_node.name}"
                }

            else:
                current_node = target_node
                action = "DEFAULT"
                continue

    @classmethod
    def _execute_email_node(cls, instance: SpiffWorkflowInstance, config: Dict[str, Any], variables: Dict[str, Any]):
        """Dispatches generic automated workflow notifications."""
        to_recipients = config.get("to") or config.get("recipients") or variables.get("recipient_email") or "user@example.com"
        subject = config.get("subject") or variables.get("email_subject") or f"Workflow Notification for {instance.entity_type} #{instance.entity_id}"
        logger.info(f"StudioEngine: Dispatched notification email to '{to_recipients}' with subject: '{subject}'")

    @classmethod
    def _sync_visibility(cls, instance: SpiffWorkflowInstance):
        """Synchronizes visibility if visibility service is configured."""
        try:
            from app.core.database import SessionLocal as MainSessionLocal
            main_db = MainSessionLocal()
            try:
                WorkflowVisibilityService.sync_visibility(main_db, instance.instance_id, instance.entity_type, instance.entity_id)
                main_db.commit()
            finally:
                main_db.close()
        except Exception as vis_err:
            logger.debug(f"Visibility sync info: {vis_err}")

    @classmethod
    def _log_workflow_history(
        cls,
        db: Session,
        instance: SpiffWorkflowInstance,
        from_node: WorkflowNode,
        to_node: WorkflowNode,
        action: str,
        user_id: Optional[int],
        remarks: Optional[str] = None
    ):
        """
        Records a generic workflow transition audit record into workflow_history.
        Atomic within the caller's transaction.
        """
        try:
            from app.workflow.models.history import WorkflowHistory
            from app.core.database import ClientDatabaseAdapter

            performed_role = None
            if user_id:
                profile = ClientDatabaseAdapter.get_user_profile(user_id)
                if profile:
                    performed_role = profile.get("role_name")

            from_cfg = json.loads(from_node.configuration) if isinstance(from_node.configuration, str) else (from_node.configuration or {})
            to_cfg = json.loads(to_node.configuration) if isinstance(to_node.configuration, str) else (to_node.configuration or {})

            history = WorkflowHistory(
                instance_id=instance.instance_id,
                from_state_id=from_node.node_id,
                to_state_id=to_node.node_id,
                action_name=action,
                performed_by=user_id,
                performed_role=performed_role,
                remarks=remarks if remarks else None,
                performed_on=datetime.now(),
                from_state_code=from_cfg.get("taskCode") or from_node.node_key,
                to_state_code=to_cfg.get("taskCode") or to_node.node_key
            )
            db.add(history)
            db.flush()
        except Exception as e:
            logger.warning(f"WorkflowHistory recording error: {e}")
            raise

    @classmethod
    def _log_history(
        cls,
        db: Session,
        instance: SpiffWorkflowInstance,
        node: WorkflowNode,
        status: str,
        user_id: Optional[int],
        variables: Dict[str, Any]
    ):
        """Records execution trace in SpiffActivityHistory."""
        try:
            history = SpiffActivityHistory(
                instance_id=instance.instance_id,
                activity_id=node.node_key,
                activity_name=node.name,
                activity_type=node.node_type,
                status=status,
                variables=json.dumps(variables or {}),
                timestamp=datetime.now()
            )
            db.add(history)
            db.flush()
        except Exception as log_err:
            logger.warning(f"History log error: {log_err}")

    @classmethod
    def _sync_erm_status(cls, instance: SpiffWorkflowInstance, node: WorkflowNode):
        """Generic hook for entity lifecycle updates."""
        pass
