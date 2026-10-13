import json
import time
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.database import WorkflowSessionLocal
from app.workflow.persistence.models import BPMNDefinition

client = TestClient(app)

def test_execute_workflow():
    # 1. Create a fresh workflow draft using the creation API with valid starter BPMN XML
    spec_id = f"exec_test_{int(time.time())}"
    bpmn_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                  id="Definitions_{spec_id}"
                  targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="{spec_id}" isExecutable="true">
    <bpmn:startEvent id="StartEvent" name="Start">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent" targetRef="UserTask_1" />
    <bpmn:userTask id="UserTask_1" name="Pending Review" camunda:candidateGroups="admin">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:sequenceFlow id="Flow_2" sourceRef="UserTask_1" targetRef="EndEvent_1" />
    <bpmn:endEvent id="EndEvent_1" name="End">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
  </bpmn:process>
</bpmn:definitions>"""

    create_res = client.post("/workflow/definitions", json={
        "spec_id": spec_id,
        "name": "Automated Runner Test Spec",
        "description": "Workflow for verifying execution engine",
        "xml_content": bpmn_xml
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
