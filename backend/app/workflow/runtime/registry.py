import inspect
from typing import Any, Dict, Type

from app.workflow.runtime.context import WorkflowContext
from app.workflow.runtime.base_activity import BaseActivity

class ActivityRegistry:
    """
    Extensible registry mapping string activity identifiers from BPMN Service Task definitions 
    to executable Python Activity classes. Supports constructor dependency injection.
    """
    def __init__(self):
        self._activities: Dict[str, Type[BaseActivity]] = {}
        self._dependencies: Dict[str, Any] = {}

    def register_dependency(self, name: str, dependency: Any) -> None:
        """
        Registers a shared dependency (e.g. database sessions, mail clients, adapters)
        for injection into activity constructors at run-time.
        """
        self._dependencies[name] = dependency

    def register(self, name: str):
        """
        Decorator to register an activity class dynamically.
        """
        def decorator(cls: Type[BaseActivity]):
            if not issubclass(cls, BaseActivity):
                raise TypeError(f"Class '{cls.__name__}' must inherit from BaseActivity.")
            self._activities[name] = cls
            return cls
        return decorator

    def get_registered_activities(self) -> Dict[str, str]:
        """
        Returns a dictionary of registered activity keys and their class names
        to support discoverability.
        """
        return {key: cls.__name__ for key, cls in self._activities.items()}

    def resolve_and_execute(self, name: str, context: WorkflowContext) -> Dict[str, Any]:
        """
        Locates the registered activity class, instantiates it dynamically,
        runs validation, and executes logic.
        """
        if name not in self._activities:
            raise ValueError(f"Activity '{name}' is not registered.")
        
        activity_cls = self._activities[name]
        
        # Instantiate activity dynamically
        try:
            sig = inspect.signature(activity_cls.__init__)
            if "db" in sig.parameters:
                instance = activity_cls(db=context.db)
            elif "risk_db_service" in sig.parameters:
                instance = activity_cls(risk_db_service=None)
            else:
                instance = activity_cls()
        except Exception:
            instance = activity_cls()
        
        # A. Run pre-execution validation checks
        if not instance.validate(context):
            raise ValueError(f"Pre-execution validation failed for activity '{name}'")
            
        try:
            # B. Execute the business logic
            return instance.execute(context)
        except Exception as e:
            # C. Rollback in case of execution failure
            print(f"[Registry] Execution of '{name}' failed. Initiating rollback compensation...")
            instance.rollback(context)
            raise e


# Create a global registry instance for the application
registry = ActivityRegistry()


# ============================================================================
# REGISTRATION EXAMPLES (IMPLEMENTING VALIDATE, EXECUTE, AND ROLLBACK)
# ============================================================================

@registry.register("CreateEntity")
class CreateEntityActivity(BaseActivity):
    def __init__(self, db_service: Any = None):
        self.db_service = db_service

    def validate(self, context: WorkflowContext) -> bool:
        return context.get_variable("entity_type") is not None or context.get_variable("entity_name") is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        entity_name = context.get_variable("entity_name") or "New Entity"
        print(f"[Activity] Creating entity '{entity_name}' via DB service: {self.db_service}")
        context.set_variable("entity_status", "Draft")
        return {"entity_id": 101, "status": "Draft"}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        print("[Activity] Rollback CreateEntity: removing draft entity.")
        return {"rollback_complete": True}


@registry.register("ApproveEntity")
class ApproveEntityActivity(BaseActivity):
    def validate(self, context: WorkflowContext) -> bool:
        return context.get_variable("approval_level") is not None or context.get_variable("action") is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        level = context.get_variable("approval_level") or 1
        print(f"[Activity] Approving entity at level {level}")
        return {"approved": True, "level": level}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        print("[Activity] Rollback ApproveEntity: reverting approval status.")
        return {"rollback_complete": True}


@registry.register("RejectEntity")
class RejectEntityActivity(BaseActivity):
    def validate(self, context: WorkflowContext) -> bool:
        return True

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        remark = context.get_variable("remark") or "Rejected"
        print(f"[Activity] Rejecting entity with remark: {remark}")
        return {"approved": False, "remark": remark}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        print("[Activity] Rollback RejectEntity: reverting rejection remarks.")
        return {"rollback_complete": True}


@registry.register("SendEmail")
class SendEmailActivity(BaseActivity):
    def __init__(self, email_sender: Any = None):
        # Dynamic Dependency Injection Example
        self.email_sender = email_sender

    def validate(self, context: WorkflowContext) -> bool:
        return (
            context.get_variable("recipient_email") is not None 
            and context.get_variable("email_subject") is not None
        )

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        to_email = context.get_variable("recipient_email")
        subject = context.get_variable("email_subject")
        print(f"[Activity] Sending email to '{to_email}' using sender: {self.email_sender}")
        
        # In a real setup, we would call: self.email_sender.send(...)
        return {"email_sent": True}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        # Sending email cannot be undone physically, but we can write a compensation log
        print("[Activity] Rollback SendEmail: logging compensation event (email cannot be unsent).")
        return {"rollback_complete": True}


@registry.register("CreateHistory")
class CreateHistoryActivity(BaseActivity):
    def validate(self, context: WorkflowContext) -> bool:
        return context.get_variable("action_name") is not None

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        action = context.get_variable("action_name")
        print(f"[Activity] Creating transition history log for action '{action}'")
        return {"history_created": True}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        print("[Activity] Rollback CreateHistory: removing history audit trail entry.")
        return {"rollback_complete": True}


@registry.register("WaitForApproval")
class WaitForApprovalActivity(BaseActivity):
    def validate(self, context: WorkflowContext) -> bool:
        return True

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        print("[Activity] Execution paused. Waiting for human approval.")
        return {"waiting": True}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        print("[Activity] Rollback WaitForApproval: closing active wait handles.")
        return {"rollback_complete": True}
