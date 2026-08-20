from abc import ABC, abstractmethod
from typing import Any, Dict
from app.workflow.runtime.context import WorkflowContext

class BaseActivity(ABC):
    """
    Abstract base class that all workflow activities must inherit from.
    Ensures a consistent lifecycle interface for validation, execution, and rollback/compensation.
    Activities must never query the database directly; they must receive repository abstractions via dependency injection.
    """

    @abstractmethod
    def validate(self, context: WorkflowContext) -> bool:
        """
        Validates whether the necessary parameters and state variables exist in the context
        before executing the activity. Must return True if validation passes, or raise a validation exception.
        """
        pass

    @abstractmethod
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        Executes the core business logic of the activity, interacting only with injected repositories
        and service dependencies. Returns a dictionary of updated execution variables.
        """
        pass

    @abstractmethod
    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        Executes compensation/rollback steps if the transaction fails or the workflow path calls
        for cancellation/reversion.
        """
        pass
