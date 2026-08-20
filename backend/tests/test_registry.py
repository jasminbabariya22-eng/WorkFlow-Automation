import pytest
from app.workflow.runtime.registry import registry
from app.workflow.runtime.context import WorkflowContext
from app.workflow.runtime.base_activity import BaseActivity

@registry.register("TestDummyActivity")
class TestDummyActivity(BaseActivity):
    def validate(self, context: WorkflowContext) -> bool:
        return context.get_variable("val") is not None

    def execute(self, context: WorkflowContext) -> dict:
        val = context.get_variable("val")
        return {"result": val * 2}

    def rollback(self, context: WorkflowContext) -> dict:
        return {"compensated": True}

def test_registry_registration():
    activities = registry.get_registered_activities()
    assert "TestDummyActivity" in activities

def test_registry_execution():
    context = WorkflowContext(variables={"val": 10})
    outputs = registry.resolve_and_execute("TestDummyActivity", context)
    assert outputs["result"] == 20
