import os
import logging
from typing import List, Optional, Any
from datetime import datetime

from app.core.logger import logger
from app.workflow.workflow_session import WorkflowSessionLocal

# Import SpiffWorkflow runtime and persistence components
from app.workflow.runtime.context import WorkflowContext
from app.workflow.runtime.parser import SpiffBPMNParser
from app.workflow.runtime.engine import SpiffWorkflowEngine
from app.workflow.runtime.bpmn_execution import BPMNExecutionLayer
from app.workflow.persistence.repository import SpiffWorkflowRepository
from app.workflow.persistence.models import SpiffWorkflowInstance, SpiffHumanTask, BPMNDefinition, WorkflowEntityConfig, WorkflowTaskPermission
from app.workflow.runtime.bpmn_utils import get_candidate_role_from_xml
import app.workflow.activities

# Generic action constants
ACTION_SUBMIT = "SUBMIT"
ACTION_APPROVE = "APPROVE"
ACTION_REJECT = "REJECT"


class WorkflowService:
    """
    WorkflowService acts as a Process-Agnostic Adapter pattern over the new SpiffWorkflow engine.
    Resolves specifications, definitions, role validations, and gateway routes dynamically from BPMN.
    """
    def __init__(self, db: Optional[Any] = None):
        # Initialize connection session.
        # If db is the main database session, discard it and use WorkflowSessionLocal to connect to workflow_erm database.
        from app.core.database import engine as main_engine
        self.main_db = None
        if db is not None and db.bind == main_engine:
            self.main_db = db
            self.db = WorkflowSessionLocal()
            self._own_db = True
        else:
            if db is not None:
                self.db = db
                self._own_db = False
                self.main_db = db
            else:
                self.db = WorkflowSessionLocal()
                self._own_db = True
        
        # Build core engine dependencies
        self.parser = SpiffBPMNParser()
        self.engine = SpiffWorkflowEngine()
        self.repository = SpiffWorkflowRepository(self.db)
        self.execution_layer = BPMNExecutionLayer(self.parser, self.engine, self.repository)

    def __del__(self):
        if getattr(self, "_own_db", False):
            try:
                self.db.close()
            except Exception:
                pass

    def get_entity_workflow_config(self, entity_type: str) -> WorkflowEntityConfig:
        """
        Retrieves the active workflow configuration for a given entity type.
        """
        config = self.db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.entity_type == entity_type,
            WorkflowEntityConfig.is_active == True
        ).first()
        if not config:
            raise ValueError(f"No active workflow configuration found for entity type '{entity_type}'")
        return config

    def _get_definition_for_entity(self, entity_type: str) -> BPMNDefinition:
        """
        Loads the active process definition matching the entity_type dynamically from the DB.
        """
        config = self.get_entity_workflow_config(entity_type)

        definition = self.db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == config.specification_id,
            BPMNDefinition.is_active == True
        ).order_by(BPMNDefinition.version.desc(), BPMNDefinition.id.desc()).first()

        if not definition:
            raise ValueError(f"BPMN definition for specification '{config.specification_id}' is inactive or does not exist.")

        return definition


    def start_workflow(
        self,
        workflow_name: str,
        entity_type: str,
        entity_id: int,
        user_id: int
    ) -> Any:
        logger.info(f"Starting SpiffWorkflow for entity type='{entity_type}', id={entity_id} by user={user_id}")
        
        # Resolve creator's role dynamically from database
        user_role_name = "INITIATOR"
        try:
            from app.core.database import ClientDatabaseAdapter
            res = ClientDatabaseAdapter.execute_statement(
                "SELECT r.role_name FROM ers.mst_users u JOIN ers.mst_user_role r ON u.role_id = r.id WHERE u.id = :uid",
                {"uid": user_id}
            )
            if res and len(res) > 0 and res[0].get("role_name"):
                user_role_name = res[0]["role_name"]
        except Exception:
            pass

        # Resolve active definition record dynamically
        definition = self._get_definition_for_entity(entity_type)

        # 1. Initialize context variables
        context = WorkflowContext(
            variables={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "workflow_name": workflow_name,
                "created_by": user_id,
                "approved": True
            }
        )
        result = self.execution_layer.start_workflow(
            xml_content=definition.xml_content,
            spec_id=definition.spec_id,
            definition_db_id=definition.id,
            context=context,
            db_session=self.db
        )
        
        # 3. Fetch and return instance model
        return self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()

    def _log_history_and_activity(
        self,
        instance_id: int,
        from_state: Optional[str],
        to_state: Optional[str],
        action_name: str,
        user_id: int,
        role_code: str,
        remarks: Optional[str],
        variables: dict = None
    ):
        import json
        from app.workflow.models.history import WorkflowHistory
        from app.workflow.persistence.models import SpiffActivityHistory
        
        # 1. Log transition to WorkflowHistory (Approval Audit Trails)
        history = WorkflowHistory(
            instance_id=instance_id,
            from_state_code=from_state,
            to_state_code=to_state,
            action_name=action_name,
            performed_by=user_id,
            performed_role=role_code,
            remarks=remarks,
            performed_on=datetime.now()
        )
        self.db.add(history)
        
        # 2. Log activity execution to SpiffActivityHistory (Activity Steps Logs)
        activity_name = f"{action_name} task '{from_state or 'START'}'"
        activity_log = SpiffActivityHistory(
            instance_id=instance_id,
            activity_id=from_state or "StartEvent",
            activity_name=activity_name,
            activity_type="UserTask" if from_state else "StartEvent",
            status="COMPLETED",
            variables=json.dumps(variables or {}),
            timestamp=datetime.now()
        )
        self.db.add(activity_log)
        self.db.flush()

    def submit(
        self,
        entity_type: str,
        entity_id: int,
        user_id: int,
        remarks: str = None
    ) -> Any:
        logger.info(f"Executing submit action for entity type='{entity_type}', id={entity_id} by user={user_id}")
        
        # Check if workflow instance already exists
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()

        if not instance:
            # Check for published Studio definition first
            try:
                from app.workflow_studio.runtime.adapter import StudioExecutionAdapter
                StudioExecutionAdapter.start_workflow(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    user_id=user_id,
                    db=self.db
                )
                instance = self.db.query(SpiffWorkflowInstance).filter(
                    SpiffWorkflowInstance.entity_type == entity_type,
                    SpiffWorkflowInstance.entity_id == entity_id
                ).first()
                if instance:
                    self.db.flush()
                    from app.workflow.services.visibility_service import WorkflowVisibilityService
                    WorkflowVisibilityService.sync_visibility(self.main_db or self.db, instance.instance_id, entity_type, entity_id)
                    return instance
            except Exception as studio_err:
                logger.info(f"Studio workflow start not matched ({studio_err}), falling back to BPMN definition")

            config = self.get_entity_workflow_config(entity_type)
            definition = self._get_definition_for_entity(entity_type)
            # Create a brand new workflow instance (enters START state)
            instance = self.start_workflow(
                workflow_name=f"{entity_type} Approval Workflow",
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id
            )
            self._log_history_and_activity(
                instance_id=instance.instance_id,
                from_state=None,
                to_state=instance.current_task_code,
                action_name="Create Risk",
                user_id=user_id,
                role_code="RISK_OWNER",
                remarks="Initial Risk Registration"
            )
            
            # Find the active human task (enters PENDING_FH state)
            active_task = self.db.query(SpiffHumanTask).filter(
                SpiffHumanTask.instance_id == instance.instance_id,
                SpiffHumanTask.status == "READY"
            ).first()

            logger.info(
                f"Workflow config resolved:\n"
                f"entity_type={entity_type}\n"
                f"entity_id={entity_id}\n"
                f"config_id={config.config_id}\n"
                f"bpmn_definition_id={definition.id}\n"
                f"spec_id={definition.spec_id}\n"
                f"workflow_instance_id={instance.instance_id}\n"
                f"human_task_id={active_task.task_id if active_task else None}\n"
                f"role={active_task.role_code if active_task else None}"
            )
            self.db.flush()
            from app.workflow.services.visibility_service import WorkflowVisibilityService
            WorkflowVisibilityService.sync_visibility(self.main_db or self.db, instance.instance_id, entity_type, entity_id)
            return instance

        # If instance already exists, use the definition associated with it
        definition = self.db.query(BPMNDefinition).filter(
            BPMNDefinition.id == instance.bpmn_definition_id
        ).first()
        if not definition:
            raise ValueError(f"BPMN definition with ID {instance.bpmn_definition_id} not found for workflow instance {instance.instance_id}")

        config = self.db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.entity_type == entity_type,
            WorkflowEntityConfig.is_active == True
        ).first()

        # Resolve creator's role dynamically from database
        user_role_name = "INITIATOR"
        try:
            from app.core.database import ClientDatabaseAdapter
            res = ClientDatabaseAdapter.execute_statement(
                "SELECT r.role_name FROM ers.mst_users u JOIN ers.mst_user_role r ON u.role_id = r.id WHERE u.id = :uid",
                {"uid": user_id}
            )
            if res and len(res) > 0 and res[0].get("role_name"):
                user_role_name = res[0]["role_name"]
        except Exception:
            pass

        # Determine the active task dynamically from the engine
        current_task_code = instance.current_task_code or "DRAFT"

        # Validate candidate role dynamically from XML definition
        candidate_role = get_candidate_role_from_xml(definition.xml_content, current_task_code)
        if candidate_role and user_role_name != candidate_role:
            raise PermissionError(f"Authorization failure: User role '{user_role_name}' does not match candidate group '{candidate_role}'")

        # Resume workflow execution loop generically
        result = self.execution_layer.resume_workflow(
            xml_content=definition.xml_content,
            spec_id=definition.spec_id,
            entity_type=entity_type,
            entity_id=entity_id,
            task_spec_id=current_task_code,
            payload={
                "approved": True,
                "user_id": user_id,
                "role_code": user_role_name,
                "remarks": remarks
            },
            db_session=self.db
        )
        
        # Mark index human task as completed if it exists
        draft_task = self.db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.task_spec_id == current_task_code,
            SpiffHumanTask.status == "READY"
        ).first()
        
        if draft_task:
            draft_task.status = "COMPLETED"
            draft_task.completed_on = datetime.now()
            self.db.flush()

        self._log_history_and_activity(
            instance_id=instance.instance_id,
            from_state=current_task_code,
            to_state=instance.current_task_code,
            action_name="Submit",
            user_id=user_id,
            role_code=user_role_name,
            remarks=remarks,
            variables={"approved": True}
        )

        active_task = self.db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.status == "READY"
        ).first()

        logger.info(
            f"Workflow config resolved:\n"
            f"entity_type={entity_type}\n"
            f"entity_id={entity_id}\n"
            f"config_id={config.config_id if config else None}\n"
            f"bpmn_definition_id={definition.id}\n"
            f"spec_id={definition.spec_id}\n"
            f"workflow_instance_id={instance.instance_id}\n"
            f"human_task_id={active_task.task_id if active_task else None}\n"
            f"role={active_task.role_code if active_task else None}"
        )

        self.db.flush()
        from app.workflow.services.visibility_service import WorkflowVisibilityService
        WorkflowVisibilityService.sync_visibility(self.main_db or self.db, instance.instance_id, entity_type, entity_id)
        return instance


    def execute_action(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        user_id: int,
        remarks: str = None
    ) -> Any:
        logger.info(f"Executing workflow action '{action}' for entity type='{entity_type}', id={entity_id} by user={user_id}")
        
        # 1 & 2 & 3. Validate using is_action_allowed
        auth_result = self.is_action_allowed(entity_type, entity_id, user_id, action)
        if not auth_result["allowed"]:
            reason = auth_result["reason"]
            if "not found" in reason or "completed" in reason:
                raise ValueError(reason)
            raise PermissionError(reason)

        # Get resolved variables
        db_to_use = self.main_db if self.main_db is not None else self.db
        user_record = db_to_use.query(User).filter(User.id == user_id).first()
        user_role_name = user_record.role.name if user_record and user_record.role else None

        instance = db_to_use.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()

        definition = db_to_use.query(BPMNDefinition).filter(
            BPMNDefinition.id == instance.bpmn_definition_id
        ).first()

        human_task = db_to_use.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.status == "READY"
        ).first()

        current_task_code = human_task.task_spec_id

        # Check if pinned definition is a WorkflowVersion from Studio
        from app.workflow_definition.models import WorkflowVersion
        studio_version = self.db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_version_id == instance.bpmn_definition_id
        ).first()

        if studio_version:
            from app.workflow_studio.runtime.adapter import StudioExecutionAdapter
            StudioExecutionAdapter.execute_action(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                user_id=user_id,
                remarks=remarks,
                db=self.db
            )
            from app.workflow.services.visibility_service import WorkflowVisibilityService
            WorkflowVisibilityService.sync_visibility(self.main_db or self.db, instance.instance_id, entity_type, entity_id)
            if action == "FORCE_APPROVE":
                from app.core.constants import ROLE_TO_APPROVAL_LEVEL
                role_code = self.get_current_role(entity_type, entity_id)
                level = ROLE_TO_APPROVAL_LEVEL.get(role_code) if role_code else None
                return [level] if level else [1, 2, 3]
            return instance

        # 6 & 7. Legacy BPMN Action Execution
        if action == "FORCE_APPROVE":
            approved_levels = []
            from app.core.constants import ROLE_TO_APPROVAL_LEVEL
            
            while True:
                role_code = self.get_current_role(entity_type, entity_id)
                if not role_code:
                    break
                    
                inst = self.db.query(SpiffWorkflowInstance).filter(
                    SpiffWorkflowInstance.entity_type == entity_type,
                    SpiffWorkflowInstance.entity_id == entity_id
                ).first()
                if inst.status != "Running":
                    break
                    
                task_code = inst.current_task_code
                
                if not check_task_permission(self.db, definition.spec_id, task_code, user_role_name, "FORCE_APPROVE"):
                    break
                    
                level = ROLE_TO_APPROVAL_LEVEL.get(role_code)
                if level and level not in approved_levels:
                    approved_levels.append(level)
                    
                curr_human_task = self.db.query(SpiffHumanTask).filter(
                    SpiffHumanTask.instance_id == inst.instance_id,
                    SpiffHumanTask.task_spec_id == task_code,
                    SpiffHumanTask.status == "READY"
                ).first()
                
                self.execution_layer.resume_workflow(
                    xml_content=definition.xml_content,
                    spec_id=definition.spec_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    task_spec_id=task_code,
                    payload={
                        "approved": True,
                        "action": "FORCE_APPROVE",
                        "user_id": user_id,
                        "role_code": user_role_name,
                        "remarks": remarks
                    },
                    db_session=self.db
                )
                
                if curr_human_task:
                    curr_human_task.status = "COMPLETED"
                    curr_human_task.completed_on = datetime.now()
                    self.db.flush()
                    
                self._log_history_and_activity(
                    instance_id=inst.instance_id,
                    from_state=task_code,
                    to_state=inst.current_task_code,
                    action_name="Force Approve",
                    user_id=user_id,
                    role_code=user_role_name,
                    remarks=remarks,
                    variables={"approved": True, "action": "FORCE_APPROVE"}
                )
            
            self.db.commit()
            from app.workflow.services.visibility_service import WorkflowVisibilityService
            WorkflowVisibilityService.sync_visibility(self.main_db or self.db, instance.instance_id, entity_type, entity_id)
            return approved_levels
            
        else:
            is_approved = (action == "APPROVE")
            
            self.execution_layer.resume_workflow(
                xml_content=definition.xml_content,
                spec_id=definition.spec_id,
                entity_type=entity_type,
                entity_id=entity_id,
                task_spec_id=current_task_code,
                payload={
                    "approved": is_approved,
                    "action": action,
                    "user_id": user_id,
                    "role_code": user_role_name,
                    "remarks": remarks
                },
                db_session=self.db
            )
            
            human_task.status = "COMPLETED" if is_approved else "REJECTED"
            human_task.completed_on = datetime.now()
            self.db.flush()
            
            self._log_history_and_activity(
                instance_id=instance.instance_id,
                from_state=current_task_code,
                to_state=instance.current_task_code,
                action_name=action.capitalize(),
                user_id=user_id,
                role_code=user_role_name,
                remarks=remarks,
                variables={"approved": is_approved, "action": action}
            )
            
            self.db.flush()
            from app.workflow.services.visibility_service import WorkflowVisibilityService
            WorkflowVisibilityService.sync_visibility(self.main_db or self.db, instance.instance_id, entity_type, entity_id)
            return instance

    def approve(
        self,
        entity_type: str,
        entity_id: int,
        role_code: str,
        user_id: int,
        remarks: str = None
    ) -> Any:
        return self.execute_action(
            entity_type=entity_type,
            entity_id=entity_id,
            action="APPROVE",
            user_id=user_id,
            remarks=remarks
        )

    def reject(
        self,
        entity_type: str,
        entity_id: int,
        role_code: str,
        user_id: int,
        remarks: str = None
    ) -> Any:
        return self.execute_action(
            entity_type=entity_type,
            entity_id=entity_id,
            action="REJECT",
            user_id=user_id,
            remarks=remarks
        )

    def validate_instance_active(
        self,
        entity_type: str,
        entity_id: int
    ) -> None:
        logger.info(f"Validating workflow instance state for entity type='{entity_type}', id={entity_id}")
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        
        if not instance:
            raise Exception("No active workflow state or transition found for this entity")
            
        if instance.status != "Running":
            raise Exception("Task not found or already completed")

    def get_current_role(
        self,
        entity_type: str,
        entity_id: int
    ) -> Optional[str]:
        logger.info(f"Determining required role for entity type='{entity_type}', id={entity_id}")
        
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        
        if not instance or instance.status != "Running":
            return None
            
        # Check active human task first (works identically for Studio & BPMN)
        active_task = self.db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.status == "READY"
        ).first()
        if active_task and active_task.role_code:
            return active_task.role_code
            
        current_task_code = instance.current_task_code
        definition = self.db.query(BPMNDefinition).filter(
            BPMNDefinition.id == instance.bpmn_definition_id
        ).first()
        if definition and definition.xml_content:
            return get_candidate_role_from_xml(definition.xml_content, current_task_code)
        
        return None

    def force_approve(
        self,
        entity_type: str,
        entity_id: int,
        user_id: int,
        remarks: str = None
    ) -> List[int]:
        logger.info(f"Executing force_approve for entity type='{entity_type}', id={entity_id} by user={user_id}")
        return self.execute_action(
            entity_type=entity_type,
            entity_id=entity_id,
            action="FORCE_APPROVE",
            user_id=user_id,
            remarks=remarks
        )

    def is_action_allowed(
        self,
        entity_type: str,
        entity_id: int,
        user_id: int,
        action_code: str
    ) -> dict:
        db_to_use = self.main_db if self.main_db is not None else self.db
        
        # 1. User check
        user_record = db_to_use.query(User).filter(User.id == user_id).first()
        if not user_record:
            return {"allowed": False, "reason": f"User ID {user_id} does not exist"}
            
        user_role_name = user_record.role.name if user_record and user_record.role else None
        if not user_role_name:
            return {"allowed": False, "reason": "User has no effective role"}

        # 2. Find active workflow instance
        instance = db_to_use.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        
        if not instance:
            return {"allowed": False, "reason": f"Workflow instance not found for {entity_type} {entity_id}."}
        if instance.status == "Completed":
            return {"allowed": False, "reason": "Workflow already completed"}
        if instance.status != "Running":
            return {"allowed": False, "reason": f"Workflow instance status is {instance.status}, expected Running"}

        # 3. Determine current active task
        active_tasks = db_to_use.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.status == "READY"
        ).all()
        
        if not active_tasks:
            return {"allowed": False, "reason": "Active workflow task could not be found"}
        if len(active_tasks) > 1:
            return {"allowed": False, "reason": "Multiple active tasks found where only one is expected"}
            
        task = active_tasks[0]
        task_spec_id = task.task_spec_id
        task_role = task.role_code

        # 4. Check if Studio definition or legacy BPMN definition
        from app.workflow_definition.models import WorkflowVersion
        studio_version = db_to_use.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_version_id == instance.bpmn_definition_id
        ).first()

        if studio_version:
            node = next((n for n in studio_version.nodes if n.node_key == task_spec_id and n.is_active), None)
            import json
            current_cfg = {}
            if node:
                try:
                    current_cfg = json.loads(node.configuration) if isinstance(node.configuration, str) else (node.configuration or {})
                except Exception:
                    current_cfg = {}
            allowed_actions = current_cfg.get("actions") or current_cfg.get("allowed_actions") or []
            if not allowed_actions:
                allowed_actions = ["APPROVE", "REJECT", "FORCE_APPROVE"]
            allowed_upper = [a.upper() for a in allowed_actions]

            node_role = current_cfg.get("role") or current_cfg.get("role_code") or task_role
            if action_code.upper() in ["APPROVE", "REJECT"] and user_role_name != node_role:
                return {
                    "allowed": False,
                    "reason": f"Action not allowed. User role '{user_role_name}' does not match required task role '{node_role}'"
                }

            if action_code.upper() not in allowed_upper:
                return {
                    "allowed": False,
                    "reason": f"Action {action_code} is not permitted for role {user_role_name} at task {task_spec_id}."
                }
        else:
            definition = db_to_use.query(BPMNDefinition).filter(
                BPMNDefinition.id == instance.bpmn_definition_id
            ).first()
            if not definition:
                return {"allowed": False, "reason": f"BPMN definition with ID {instance.bpmn_definition_id} not found"}

            has_config = db_to_use.query(WorkflowTaskPermission).filter(
                WorkflowTaskPermission.spec_id == definition.spec_id
            ).first() is not None

            if action_code.upper() in ["APPROVE", "REJECT"] and user_role_name != task_role:
                return {
                    "allowed": False,
                    "reason": f"Action not allowed. User role '{user_role_name}' does not match required task role '{task_role}'"
                }

            permission = db_to_use.query(WorkflowTaskPermission).filter(
                WorkflowTaskPermission.spec_id == definition.spec_id,
                WorkflowTaskPermission.task_spec_id == task_spec_id,
                WorkflowTaskPermission.role_code == user_role_name,
                WorkflowTaskPermission.is_active == True
            ).first()
            
            if permission:
                allowed_actions = [a.strip().upper() for a in permission.actions.split(",")]
            elif has_config:
                allowed_actions = []
            else:
                if action_code.upper() in ["APPROVE", "REJECT"]:
                    allowed_actions = ["APPROVE", "REJECT"] if user_role_name == task_role else []
                elif action_code.upper() == "FORCE_APPROVE":
                    allowed_actions = ["FORCE_APPROVE"] if user_role_name in ["MANAGER", "EXECUTIVE", "ADMIN"] else []
                else:
                    allowed_actions = []

            if action_code.upper() not in allowed_actions:
                return {
                    "allowed": False,
                    "reason": f"Action {action_code} is not permitted for role {user_role_name} at task {task_spec_id}."
                }

        # 6. Additional validation: Visibility check (except for FORCE_APPROVE)
        if action_code.upper() != "FORCE_APPROVE":
            is_admin = user_record.user_type.name.upper() == "ADMIN" if user_record and user_record.user_type else False
            is_owner = False
            
            # Resolve owner generically using ENTITY_CONFIG
            ENTITY_CONFIG = {
                "Risk": {
                    "model_name": "RiskRegister",
                    "owner_field": "risk_owner_id",
                    "co_owner_field": "risk_co_owner_id",
                    "dept_field": "dept_id"
                }
            }
            cfg = ENTITY_CONFIG.get(entity_type)
            if cfg and cfg.get("owner_field"):
                from app.core.database import Base
                model_cls = None
                for mapper in Base.registry.mappers:
                    cls = mapper.class_
                    if cls.__name__ == cfg["model_name"]:
                        model_cls = cls
                        break
                if model_cls:
                    from sqlalchemy import inspect
                    pk_col = inspect(model_cls).primary_key[0]
                    entity = db_to_use.query(model_cls).filter(pk_col == entity_id).first()
                    if entity:
                        owner_id = getattr(entity, cfg["owner_field"], None)
                        co_owner_id = getattr(entity, cfg["co_owner_field"], None) if cfg.get("co_owner_field") else None
                        is_owner = user_id in [owner_id, co_owner_id] if owner_id else False

            # Non-admin non-owner users require active visibility
            if not is_admin and not is_owner:
                from app.models.workflow_visibility import WorkflowVisibility
                vis = db_to_use.query(WorkflowVisibility).filter(
                    WorkflowVisibility.instance_id == instance.instance_id,
                    WorkflowVisibility.role_id == user_record.role_id,
                    WorkflowVisibility.visibility == 1
                ).first()
                if not vis:
                    return {
                        "allowed": False,
                        "reason": "User is not authorized to perform this action (no visibility/access)"
                    }

        # Return successful result
        return {
            "allowed": True,
            "action": action_code.upper(),
            "role": user_role_name,
            "task_spec_id": task_spec_id,
            "workflow_instance_id": instance.instance_id
        }

    def get_workflow_state_details(self, entity_type: str, entity_id: int, user_id: int) -> dict:
        db_to_use = self.main_db if self.main_db is not None else self.db
        
        # Find active workflow instance
        instance = db_to_use.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        
        if not instance:
            raise ValueError(f"No active workflow instance found for {entity_type} {entity_id}.")
            
        # Determine current active task
        active_tasks = db_to_use.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.status == "READY"
        ).all()
        
        current_state = instance.current_task_code or "DRAFT"
        allowed_actions = []
        
        # User details
        user_record = db_to_use.query(User).filter(User.id == user_id).first()
        user_role_name = user_record.role.name if user_record and user_record.role else None

        if instance.status == "Running" and active_tasks:
            task = active_tasks[0]
            current_state = task.task_spec_id
            current_role = task.role_code
            
            # Find what actions the user's role is allowed to perform
            if user_role_name:
                from app.workflow_definition.models import WorkflowVersion
                studio_version = db_to_use.query(WorkflowVersion).filter(
                    WorkflowVersion.workflow_version_id == instance.bpmn_definition_id
                ).first()
                
                if studio_version:
                    node = next((n for n in studio_version.nodes if n.node_key == current_state and n.is_active), None)
                    import json
                    cfg = {}
                    if node:
                        try:
                            cfg = json.loads(node.configuration) if isinstance(node.configuration, str) else (node.configuration or {})
                        except Exception:
                            cfg = {}
                    node_role = cfg.get("role") or cfg.get("role_code") or current_role
                    actions = cfg.get("actions") or cfg.get("allowed_actions") or []
                    if not actions and user_role_name == node_role:
                        actions = ["APPROVE", "REJECT"]
                    allowed_actions = [a.upper() for a in actions]
                else:
                    definition = db_to_use.query(BPMNDefinition).filter(
                        BPMNDefinition.id == instance.bpmn_definition_id
                    ).first()
                    
                    if definition:
                        permission = db_to_use.query(WorkflowTaskPermission).filter(
                            WorkflowTaskPermission.spec_id == definition.spec_id,
                            WorkflowTaskPermission.task_spec_id == current_state,
                            WorkflowTaskPermission.role_code == user_role_name,
                            WorkflowTaskPermission.is_active == True
                        ).first()
                        
                        if permission:
                            allowed_actions = [a.strip().upper() for a in permission.actions.split(",")]
                        else:
                            # Fallback logic
                            if user_role_name == current_role:
                                allowed_actions = ["APPROVE", "REJECT"]
                            elif user_role_name in ["RISK_MANAGER", "RISK_HEAD"]:
                                allowed_actions = ["FORCE_APPROVE"]
                        
        return {
            "risk_register_id": entity_id,
            "workflow_instance_id": instance.instance_id,
            "current_state": current_state,
            "current_role": user_role_name,
            "allowed_actions": allowed_actions
        }


def check_task_permission(db, spec_id: str, task_spec_id: str, role_code: str, action: str) -> bool:
    from app.workflow.persistence.models import WorkflowTaskPermission
    
    has_config = db.query(WorkflowTaskPermission).filter(
        WorkflowTaskPermission.spec_id == spec_id
    ).first() is not None

    permission = db.query(WorkflowTaskPermission).filter(
        WorkflowTaskPermission.spec_id == spec_id,
        WorkflowTaskPermission.task_spec_id == task_spec_id,
        WorkflowTaskPermission.role_code == role_code,
        WorkflowTaskPermission.is_active == True
    ).first()
    
    if permission:
        # Check if the requested action is in the allowed actions list
        allowed_actions = [a.strip().upper() for a in permission.actions.split(",")]
        return action.upper() in allowed_actions

    if has_config:
        return False
        
    # Default fallback behavior for backward compatibility with existing tests/runs
    if action.upper() in ["APPROVE", "REJECT"]:
        return True
    if action.upper() == "FORCE_APPROVE":
        return role_code in ["RISK_MANAGER", "RISK_HEAD"]
        
    return False