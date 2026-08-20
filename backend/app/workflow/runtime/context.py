from typing import Any, Dict

class WorkflowContext:
    """
    WorkflowContext encapsulates runtime parameters, variables, and actor data 
    passed from the business API into the SpiffWorkflow engine.
    """
    def __init__(
        self,
        variables: Dict[str, Any] = None,
        user_id: int = None,
        user_role: str = None,
        activity_config: Dict[str, Any] = None,
        db: Any = None
    ):
        self.variables = variables or {}
        self.user_id = user_id
        self.user_role = user_role
        self.activity_config = activity_config or {}
        self.db = db

    def set_variable(self, key: str, value: Any):
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variables": self.variables,
            "user_id": self.user_id,
            "user_role": self.user_role
        }
