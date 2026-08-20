class WorkflowException(Exception):
    """Base exception for all workflow engine errors."""
    pass

class WorkflowNotFound(WorkflowException):
    """Raised when a workflow definition is not found."""
    pass

class StateNotFound(WorkflowException):
    """Raised when a workflow state is not found."""
    pass

class TransitionNotFound(WorkflowException):
    """Raised when no valid transition is found for the given current state, action, and role."""
    pass

class WorkflowAlreadyCompleted(WorkflowException):
    """Raised when trying to execute an action on a completed or cancelled workflow instance."""
    pass

class WorkflowInstanceNotFound(WorkflowException):
    """Raised when a workflow instance is not found."""
    pass
