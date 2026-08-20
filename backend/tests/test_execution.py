import json
import time
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.database import WorkflowSessionLocal
from app.workflow.persistence.models import BPMNDefinition

client = TestClient(app)

def test_execute_workflow():
    # 1. Create a fresh workflow draft using the creation API (which generates valid starter BPMN XML)
    spec_id = f"exec_test_{int(time.time())}"
    create_res = client.post("/workflow/definitions", json={
        "spec_id": spec_id,
        "name": "Automated Runner Test Spec",
        "description": "Workflow for verifying execution engine"
    })
    assert create_res.status_code == 200, f"Failed to create draft: {create_res.text}"
    wf_id = create_res.json()["data"]["id"]
    print(f"Created workflow draft ID {wf_id} ({spec_id})")

    # 2. Trigger execution with test variables
    exec_res = client.post(f"/workflow/definitions/{wf_id}/execute", json={
        "initial_variables": {
            "test_input": "hello world",
            "risk_score": 90,
            "priority": "HIGH"
        }
    })
    print("Execution status code:", exec_res.status_code)
    print("Execution response:", json.dumps(exec_res.json(), indent=2))
    assert exec_res.status_code == 200
    assert exec_res.json().get("Error", {}).get("Error") is False
    print("Workflow Execution Test Passed Successfully!")

    data = exec_res.json().get("data", {})
    assert data.get("instance_id") is not None
    print(f"Workflow executed successfully! Instance ID: {data.get('instance_id')}, Status: {data.get('status')}")

    # 3. If there are ready human tasks, complete the task
    ready_tasks = data.get("ready_tasks", [])
    if ready_tasks:
        task_id = ready_tasks[0]["task_id"]
        print(f"Completing ready human task #{task_id} ({ready_tasks[0]['task_spec_id']})...")
        complete_res = client.post(f"/workflow/tasks/{task_id}/complete", json={
            "variables": {
                "action": "APPROVE",
                "approved": True
            },
            "remark": "Approved in automated test"
        })
        assert complete_res.status_code == 200
        print("Task completed successfully:", complete_res.json().get("data", {}).get("status"))

    print("ALL WORKFLOW CREATION AND EXECUTION TESTS PASSED!")

if __name__ == "__main__":
    test_execute_workflow()
