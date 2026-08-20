import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.logger import logger
from app.workflow.exceptions import (
    WorkflowNotFound,
    StateNotFound,
    TransitionNotFound,
    WorkflowAlreadyCompleted,
    WorkflowInstanceNotFound,
    WorkflowException
)
from app.workflow.repositories.definition import WorkflowDefinitionRepository
from app.workflow.repositories.state import WorkflowStateRepository
from app.workflow.repositories.transition import WorkflowTransitionRepository
from app.workflow.repositories.instance import WorkflowInstanceRepository
from app.workflow.repositories.history import WorkflowHistoryRepository
from app.workflow.models.instance import WorkflowInstance
from app.workflow.models.state import WorkflowState
from app.workflow.models.history import WorkflowHistory

class WorkflowEngine:
    def __init__(self, db: Session):
        self.db = db
        self.definition_repo = WorkflowDefinitionRepository(db)
        self.state_repo = WorkflowStateRepository(db)
        self.transition_repo = WorkflowTransitionRepository(db)
        self.instance_repo = WorkflowInstanceRepository(db)
        self.history_repo = WorkflowHistoryRepository(db)

    def start_workflow(
        self,
        workflow_name: str,
        entity_type: str,
        entity_id: int,
        user_id: int
    ) -> WorkflowInstance:
        logger.info(
            f"Starting workflow '{workflow_name}' for entity "
            f"type='{entity_type}', id={entity_id} by user={user_id}"
        )

        try:
            # 1. Load workflow definition by name
            definition = self.definition_repo.get_by_name(workflow_name)
            if not definition:
                raise WorkflowNotFound(f"Workflow definition '{workflow_name}' not found or inactive")

            # 2. Find START state
            start_state = self.state_repo.get_start_state(definition.workflow_id)
            if not start_state:
                raise StateNotFound(f"START state not found for workflow ID {definition.workflow_id}")

            # 3. Check for existing running instance
            existing_instance = self.instance_repo.get_by_entity(entity_type, entity_id)
            if existing_instance:
                if existing_instance.status == "Running":
                    raise WorkflowException(
                        f"An active workflow instance already exists for entity type='{entity_type}', id={entity_id}"
                    )
                # If completed/cancelled, we could delete or raise. Let's raise for safety.
                raise WorkflowException(
                    f"A completed/cancelled workflow instance already exists for entity type='{entity_type}', id={entity_id}"
                )

            # 4. Create workflow instance
            instance = self.instance_repo.create(
                workflow_id=definition.workflow_id,
                entity_type=entity_type,
                entity_id=entity_id,
                current_state_id=start_state.state_id,
                started_by=user_id
            )

            # 5. Insert starting history
            self.history_repo.create(
                instance_id=instance.instance_id,
                from_state_id=None,
                to_state_id=start_state.state_id,
                action_name="START",
                performed_by=user_id,
                performed_role=None,
                remarks="Workflow initiated"
            )

            # 6. Commit transaction
            self.db.commit()
            self.db.refresh(instance)

            logger.info(
                f"Workflow '{workflow_name}' successfully started. Instance ID: {instance.instance_id}"
            )
            return instance

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error starting workflow '{workflow_name}': {str(e)}")
            raise

    def execute_action(
        self,
        entity_type: str,
        entity_id: int,
        action_name: str,
        role_code: str,
        user_id: int,
        remarks: str = None
    ) -> WorkflowInstance:
        logger.info(
            f"Executing action '{action_name}' for entity type='{entity_type}', "
            f"id={entity_id} with role='{role_code}' by user={user_id}"
        )

        try:
            # 1. Load workflow instance
            instance = self.instance_repo.get_by_entity(entity_type, entity_id)
            if not instance:
                raise WorkflowInstanceNotFound(
                    f"Workflow instance not found for entity type='{entity_type}', id={entity_id}"
                )

            # 2. Check if instance is completed or cancelled
            if instance.status != "Running":
                raise WorkflowAlreadyCompleted(
                    f"Cannot execute action on workflow in status '{instance.status}'"
                )

            current_state_id = instance.current_state_id

            # 3. Find transition
            transition = self.transition_repo.get_transition(
                workflow_id=instance.workflow_id,
                current_state_id=current_state_id,
                action_name=action_name,
                role_code=role_code
            )
            if not transition:
                raise TransitionNotFound(
                    f"No valid transition found for current state ID {current_state_id}, "
                    f"action='{action_name}', role='{role_code}'"
                )

            next_state_id = transition.next_state_id

            # 4. Load destination state to check if it's an END state
            next_state = self.state_repo.get_by_id(next_state_id)
            if not next_state:
                raise StateNotFound(f"Destination state ID {next_state_id} not found")

            # 5. Update instance current state
            if next_state.state_type == "END":
                self.instance_repo.complete_workflow(instance.instance_id, next_state_id)
                remarks_prefix = "[WORKFLOW END] "
            else:
                self.instance_repo.update_current_state(instance.instance_id, next_state_id)
                remarks_prefix = ""

            # 6. Insert history record
            self.history_repo.create(
                instance_id=instance.instance_id,
                from_state_id=current_state_id,
                to_state_id=next_state_id,
                action_name=action_name,
                performed_by=user_id,
                performed_role=role_code,
                remarks=f"{remarks_prefix}{remarks}" if remarks else f"{remarks_prefix}Transitioned on action '{action_name}'"
            )

            # 7. Commit transaction
            self.db.commit()
            self.db.refresh(instance)

            logger.info(
                f"Action '{action_name}' executed. Instance ID: {instance.instance_id}. "
                f"State transitioned from {current_state_id} to {next_state_id}"
            )
            return instance

        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Error executing action '{action_name}' for entity type='{entity_type}', id={entity_id}: {str(e)}"
            )
            raise

    def get_current_state(
        self,
        entity_type: str,
        entity_id: int
    ) -> WorkflowState:
        # 1. Load instance
        instance = self.instance_repo.get_by_entity(entity_type, entity_id)
        if not instance:
            raise WorkflowInstanceNotFound(
                f"Workflow instance not found for entity type='{entity_type}', id={entity_id}"
            )

        # 2. Load state
        state = self.state_repo.get_by_id(instance.current_state_id)
        if not state:
            raise StateNotFound(f"Current state ID {instance.current_state_id} not found")

        return state

    def get_history(
        self,
        entity_type: str,
        entity_id: int
    ) -> List[WorkflowHistory]:
        # 1. Load instance
        instance = self.instance_repo.get_by_entity(entity_type, entity_id)
        if not instance:
            raise WorkflowInstanceNotFound(
                f"Workflow instance not found for entity type='{entity_type}', id={entity_id}"
            )

        # 2. Get history records
        return self.history_repo.get_history(instance.instance_id)
