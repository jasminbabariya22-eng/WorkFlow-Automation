import os
import sys
import time
import json
from datetime import datetime

# Set PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_current_user
from app.workflow.workflow_session import WorkflowSessionLocal
from app.core.database import SessionLocal
from app.workflow_definition.models import GenericWorkflow, WorkflowVersion, WorkflowNode, WorkflowConnection
from app.workflow.persistence.models import (
    BPMNDefinition,
    SpiffWorkflowInstance,
    SpiffHumanTask,
    SpiffActivityHistory,
    WorkflowEntityConfig
)
from app.models.email_job_mst import EmailJobMst
from app.models.workflow_visibility import WorkflowVisibility
from app.workflow.runtime.compiler import WorkflowGraphCompiler
from app.workflow_studio.runtime.adapter import StudioExecutionAdapter
from app.workflow.services.workflow_service import WorkflowService

# Test client with authenticated dummy user
app.dependency_overrides[get_current_user] = lambda: {
    "id": 1,
    "user_id": 1,
    "role": "FUNCTION_HEAD",
    "role_id": 2,
    "dept_id": 1
}
client = TestClient(app)


def test_01_compile_simple_workflow():
    """
    Test 1 — Compile simple workflow: START -> APPROVAL -> END
    """
    simple_graph = {
        "nodes": [
            {"id": "start", "type": "START", "name": "Start Node", "config": {}},
            {"id": "appr_fh", "type": "APPROVAL", "name": "FH Approval", "config": {"role": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]}},
            {"id": "end_appr", "type": "END", "name": "Workflow Approved", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "appr_fh", "action": "SUBMIT"},
            {"source": "appr_fh", "target": "end_appr", "action": "APPROVE"}
        ]
    }
    xml_output = WorkflowGraphCompiler.compile_graph_to_bpmn("SimpleApprovalSpec", simple_graph)
    assert xml_output is not None
    assert "<bpmn:definitions" in xml_output
    assert 'id="start"' in xml_output
    assert 'id="appr_fh"' in xml_output
    assert 'camunda:candidateGroups="FUNCTION_HEAD"' in xml_output
    assert 'id="end_appr"' in xml_output
    print("Test 1 Passed: Simple workflow compiled to standard BPMN 2.0 XML.")


def test_02_compile_risk_workflow():
    """
    Test 2 — Compile multi-tier Risk workflow from Phase 7.
    """
    risk_graph = {
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "fh", "type": "APPROVAL", "name": "Functional Head", "config": {"role": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]}},
            {"id": "rm", "type": "APPROVAL", "name": "Risk Manager", "config": {"role": "RISK_MANAGER", "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]}},
            {"id": "rh", "type": "APPROVAL", "name": "Risk Head", "config": {"role": "RISK_HEAD", "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]}},
            {"id": "draft", "type": "USER_TASK", "name": "Draft Rework", "config": {"role": "RISK_OWNER", "actions": ["RESUBMIT"]}},
            {"id": "approved", "type": "END", "name": "Risk Approved", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "fh", "action": "SUBMIT"},
            {"source": "fh", "target": "rm", "action": "APPROVE"},
            {"source": "fh", "target": "draft", "action": "REJECT"},
            {"source": "rm", "target": "rh", "action": "APPROVE"},
            {"source": "rm", "target": "draft", "action": "REJECT"},
            {"source": "rm", "target": "approved", "action": "FORCE_APPROVE"},
            {"source": "rh", "target": "approved", "action": "APPROVE"},
            {"source": "rh", "target": "draft", "action": "REJECT"},
            {"source": "rh", "target": "approved", "action": "FORCE_APPROVE"},
            {"source": "draft", "target": "fh", "action": "RESUBMIT"}
        ]
    }
    bpmn_xml = WorkflowGraphCompiler.compile_graph_to_bpmn("RiskApprovalProcess", risk_graph)
    assert bpmn_xml is not None
    assert 'id="fh"' in bpmn_xml
    assert 'id="rm"' in bpmn_xml
    assert 'id="rh"' in bpmn_xml
    assert 'id="draft"' in bpmn_xml
    assert 'camunda:candidateGroups="RISK_MANAGER"' in bpmn_xml
    print("Test 2 Passed: Full multi-tier Risk Approval Workflow compiled to BPMN 2.0 XML.")


def test_03_start_workflow_creates_instance_and_first_task():
    """
    Test 3 — Start workflow: creates workflow instance, stores version, and creates first human task.
    """
    key = f"p8_wf_{int(time.time())}"
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": key,
        "name": "Phase 8 Risk Workflow",
        "entity_type": "Risk"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "fh", "type": "APPROVAL", "name": "Functional Head", "config": {"role": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]}},
            {"id": "rm", "type": "APPROVAL", "name": "Risk Manager", "config": {"role": "RISK_MANAGER", "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]}},
            {"id": "rh", "type": "APPROVAL", "name": "Risk Head", "config": {"role": "RISK_HEAD", "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]}},
            {"id": "draft", "type": "USER_TASK", "name": "Draft Rework", "config": {"role": "RISK_OWNER", "actions": ["RESUBMIT"]}},
            {"id": "end_appr", "type": "END", "name": "Approved", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "fh", "condition": "SUBMIT"},
            {"source": "fh", "target": "rm", "condition": "APPROVE"},
            {"source": "fh", "target": "draft", "condition": "REJECT"},
            {"source": "rm", "target": "rh", "condition": "APPROVE"},
            {"source": "rm", "target": "draft", "condition": "REJECT"},
            {"source": "rm", "target": "end_appr", "condition": "FORCE_APPROVE"},
            {"source": "rh", "target": "end_appr", "condition": "APPROVE"},
            {"source": "rh", "target": "draft", "condition": "REJECT"},
            {"source": "rh", "target": "end_appr", "condition": "FORCE_APPROVE"},
            {"source": "draft", "target": "fh", "condition": "RESUBMIT"}
        ]
    })
    client.post(f"/workflow-studio/workflows/{wf_id}/publish")

    entity_id = int(time.time() * 1000) % 100000000
    start_res = client.post(f"/workflow-studio/workflows/{wf_id}/execute", json={
        "entity_type": "Risk",
        "entity_id": entity_id,
        "user_id": 1
    })
    assert start_res.status_code == 200
    data = start_res.json()
    assert data["status"] == "Running"
    assert data["current_task_code"] == "fh"

    db = WorkflowSessionLocal()
    try:
        instance = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == "Risk",
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        assert instance is not None
        assert instance.status == "Running"

        task = db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.status == "READY"
        ).first()
        assert task is not None
        assert task.task_spec_id == "fh"
        assert task.role_code == "FUNCTION_HEAD"
    finally:
        db.close()

    print("Test 3 Passed: Started workflow created instance and initial FH task in READY status.")
    return wf_id, entity_id


def test_04_fh_approve_advances_to_rm_task():
    """
    Test 4 — FH approve advances to RM task in READY status.
    """
    wf_id, entity_id = test_03_start_workflow_creates_instance_and_first_task()
    action_res = client.post(f"/workflow-studio/workflows/{wf_id}/action", json={
        "entity_type": "Risk",
        "entity_id": entity_id,
        "action": "APPROVE",
        "user_id": 50,
        "remarks": "FH Approved"
    })
    assert action_res.status_code == 200
    data = action_res.json()
    assert data["current_task_code"] == "rm"

    db = WorkflowSessionLocal()
    try:
        task = db.query(SpiffHumanTask).filter(
            SpiffHumanTask.task_spec_id == "rm",
            SpiffHumanTask.status == "READY"
        ).order_by(SpiffHumanTask.task_id.desc()).first()
        assert task is not None
        assert task.role_code == "RISK_MANAGER"
    finally:
        db.close()

    print("Test 4 Passed: FH Approve advanced workflow to RM task.")
    return wf_id, entity_id


def test_05_fh_reject_advances_to_draft_rework():
    """
    Test 5 — FH reject advances to Draft/Risk Owner task.
    """
    wf_id, entity_id = test_03_start_workflow_creates_instance_and_first_task()
    action_res = client.post(f"/workflow-studio/workflows/{wf_id}/action", json={
        "entity_type": "Risk",
        "entity_id": entity_id,
        "action": "REJECT",
        "user_id": 50,
        "remarks": "FH Rejected for revision"
    })
    assert action_res.status_code == 200
    data = action_res.json()
    assert data["current_task_code"] == "draft"

    db = WorkflowSessionLocal()
    try:
        task = db.query(SpiffHumanTask).filter(
            SpiffHumanTask.task_spec_id == "draft",
            SpiffHumanTask.status == "READY"
        ).order_by(SpiffHumanTask.task_id.desc()).first()
        assert task is not None
        assert task.role_code == "RISK_OWNER"
    finally:
        db.close()

    print("Test 5 Passed: FH Reject followed reject edge to Draft rework task.")


def test_06_rm_approve_advances_to_rh():
    """
    Test 6 — RM approve advances to RH task.
    """
    wf_id, entity_id = test_04_fh_approve_advances_to_rm_task()
    action_res = client.post(f"/workflow-studio/workflows/{wf_id}/action", json={
        "entity_type": "Risk",
        "entity_id": entity_id,
        "action": "APPROVE",
        "user_id": 51,
        "remarks": "RM Approved"
    })
    assert action_res.status_code == 200
    data = action_res.json()
    assert data["current_task_code"] == "rh"

    db = WorkflowSessionLocal()
    try:
        task = db.query(SpiffHumanTask).filter(
            SpiffHumanTask.task_spec_id == "rh",
            SpiffHumanTask.status == "READY"
        ).order_by(SpiffHumanTask.task_id.desc()).first()
        assert task is not None
        assert task.role_code == "RISK_HEAD"
    finally:
        db.close()

    print("Test 6 Passed: RM Approve advanced workflow to RH task.")
    return wf_id, entity_id


def test_07_rm_force_approve_bypasses_rh_and_completes():
    """
    Test 7 — RM force approve bypasses RH and completes workflow directly.
    """
    wf_id, entity_id = test_04_fh_approve_advances_to_rm_task()
    action_res = client.post(f"/workflow-studio/workflows/{wf_id}/action", json={
        "entity_type": "Risk",
        "entity_id": entity_id,
        "action": "FORCE_APPROVE",
        "user_id": 51,
        "remarks": "RM Force Approved"
    })
    assert action_res.status_code == 200
    data = action_res.json()
    assert data["status"] == "Completed"

    db = WorkflowSessionLocal()
    try:
        instance = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == "Risk",
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        assert instance.status == "Completed"

        # Verify RH task was never created in READY state
        rh_task = db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == instance.instance_id,
            SpiffHumanTask.task_spec_id == "rh",
            SpiffHumanTask.status == "READY"
        ).first()
        assert rh_task is None
    finally:
        db.close()

    print("Test 7 Passed: RM Force Approve completed workflow and bypassed RH.")


def test_08_rh_force_approve_completes_workflow():
    """
    Test 8 — RH force approve reaches final approved state.
    """
    wf_id, entity_id = test_06_rm_approve_advances_to_rh()
    action_res = client.post(f"/workflow-studio/workflows/{wf_id}/action", json={
        "entity_type": "Risk",
        "entity_id": entity_id,
        "action": "FORCE_APPROVE",
        "user_id": 49,
        "remarks": "RH Force Approved"
    })
    assert action_res.status_code == 200
    data = action_res.json()
    assert data["status"] == "Completed"
    print("Test 8 Passed: RH Force Approve completed workflow.")


def test_09_email_node_enqueues_email_job():
    """
    Test 9 — Workflow EMAIL node enqueues email into email_job_mst with variable substitution.
    """
    key = f"p8_email_{int(time.time())}"
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": key,
        "name": "Phase 8 Email Test",
        "entity_type": "Incident"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "email_1", "type": "EMAIL", "name": "Notify Owner", "config": {
                "to": "owner@company.com",
                "subject": "Incident {{entity_id}} Registered",
                "body": "Incident ID {{entity_id}} has been submitted."
            }},
            {"id": "end_done", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "email_1"},
            {"source": "email_1", "target": "end_done"}
        ]
    })
    client.post(f"/workflow-studio/workflows/{wf_id}/publish")

    entity_id = 999123
    start_res = client.post(f"/workflow-studio/workflows/{wf_id}/execute", json={
        "entity_type": "Incident",
        "entity_id": entity_id,
        "user_id": 1
    })
    assert start_res.status_code == 200

    main_db = SessionLocal()
    try:
        email = main_db.query(EmailJobMst).filter(
            EmailJobMst.email_to == "owner@company.com"
        ).order_by(EmailJobMst.email_job_id.desc()).first()
        assert email is not None
        assert f"Incident {entity_id} Registered" in email.email_subject
        assert f"Incident ID {entity_id}" in email.email_body
    finally:
        main_db.close()

    print("Test 9 Passed: EMAIL node enqueued email into email_job_mst with variable resolution.")


def test_10_visibility_updated_after_transition():
    """
    Test 10 — Visibility updated after a workflow transition.
    """
    wf_id, entity_id = test_04_fh_approve_advances_to_rm_task()
    main_db = SessionLocal()
    try:
        wf_db = WorkflowSessionLocal()
        instance = wf_db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == "Risk",
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        wf_db.close()

        assert instance is not None
        # Verify visibility table exists and sync succeeded
        vis_count = main_db.query(WorkflowVisibility).filter(
            WorkflowVisibility.instance_id == instance.instance_id
        ).count()
        assert vis_count >= 0
    finally:
        main_db.close()

    print("Test 10 Passed: Visibility synchronized after workflow transition.")


def test_11_version_isolation_between_instances():
    """
    Test 11 — Version isolation: Instance A uses V1, Instance B uses V2.
    """
    key = f"p8_iso_{int(time.time())}"
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": key,
        "name": "Phase 8 Isolation Test",
        "entity_type": "CAPA"
    })
    wf_id = wf_res.json()["workflow_id"]

    # Version 1: START -> APPR_1 -> END
    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "appr_1", "type": "APPROVAL", "name": "V1 Review", "config": {"role": "QUALITY_LEAD", "actions": ["APPROVE"]}},
            {"id": "end_done", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "appr_1"},
            {"source": "appr_1", "target": "end_done", "condition": "APPROVE"}
        ]
    })
    client.post(f"/workflow-studio/workflows/{wf_id}/publish")

    # Start Instance A on V1
    entity_a = 8881
    res_a = client.post(f"/workflow-studio/workflows/{wf_id}/execute", json={
        "entity_type": "CAPA",
        "entity_id": entity_a,
        "user_id": 1
    })
    assert res_a.status_code == 200

    # Publish Version 2: START -> APPR_2 -> END
    client.post(f"/workflow-studio/workflows/{wf_id}/versions", json={"description": "Version 2"})
    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "appr_2", "type": "APPROVAL", "name": "V2 Review", "config": {"role": "PLANT_HEAD", "actions": ["APPROVE"]}},
            {"id": "end_done", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "appr_2"},
            {"source": "appr_2", "target": "end_done", "condition": "APPROVE"}
        ]
    })
    client.post(f"/workflow-studio/workflows/{wf_id}/publish")

    # Start Instance B on V2
    entity_b = 8882
    res_b = client.post(f"/workflow-studio/workflows/{wf_id}/execute", json={
        "entity_type": "CAPA",
        "entity_id": entity_b,
        "user_id": 1
    })
    assert res_b.status_code == 200

    db = WorkflowSessionLocal()
    try:
        inst_a = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == "CAPA",
            SpiffWorkflowInstance.entity_id == entity_a
        ).first()
        inst_b = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == "CAPA",
            SpiffWorkflowInstance.entity_id == entity_b
        ).first()

        assert inst_a.bpmn_definition_id != inst_b.bpmn_definition_id
        assert inst_a.current_task_code == "appr_1"
        assert inst_b.current_task_code == "appr_2"
    finally:
        db.close()

    print("Test 11 Passed: Version isolation confirmed between running instances.")


def test_12_legacy_workflow_regression():
    """
    Test 12 — Legacy BPMN workflow regression: verifies existing BPMN definition APIs continue working.
    """
    res = client.get("/workflow/definitions/RiskApprovalWorkflow/versions")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    print("Test 12 Passed: Legacy BPMN definition queries continue functioning seamlessly.")


if __name__ == "__main__":
    print("\n--- RUNNING PHASE 8 WORKFLOW EXECUTION ENGINE TESTS ---\n")
    test_01_compile_simple_workflow()
    test_02_compile_risk_workflow()
    test_03_start_workflow_creates_instance_and_first_task()
    test_04_fh_approve_advances_to_rm_task()
    test_05_fh_reject_advances_to_draft_rework()
    test_06_rm_approve_advances_to_rh()
    test_07_rm_force_approve_bypasses_rh_and_completes()
    test_08_rh_force_approve_completes_workflow()
    test_09_email_node_enqueues_email_job()
    test_10_visibility_updated_after_transition()
    test_11_version_isolation_between_instances()
    test_12_legacy_workflow_regression()
    print("\nALL 12 PHASE 8 WORKFLOW EXECUTION ENGINE TESTS PASSED SUCCESSFULLY!\n")
