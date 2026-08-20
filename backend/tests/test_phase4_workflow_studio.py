import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.workflow.workflow_session import WorkflowSessionLocal
from app.workflow_definition.models import GenericWorkflow, WorkflowVersion

client = TestClient(app)


def test_01_create_generic_workflow_start_approval_end():
    """
    Test 1 — Create workflow:
    Create a generic workflow with START -> APPROVAL -> END.
    Verify it is stored correctly.
    """
    res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p4_test1_{int(time.time())}",
        "name": "Generic Basic Approval Workflow",
        "description": "Standard 3-node approval workflow",
        "entity_type": "PurchaseOrder",
        "nodes": [
            {"id": "node_start", "type": "START", "name": "Start Event", "position_x": 100, "position_y": 100, "config": {}},
            {"id": "node_appr", "type": "APPROVAL", "name": "Team Lead Approval", "position_x": 300, "position_y": 100, "config": {
                "role": "TEAM_LEAD",
                "actions": ["APPROVE", "REJECT"]
            }},
            {"id": "node_end", "type": "END", "name": "End Event", "position_x": 500, "position_y": 100, "config": {}}
        ],
        "edges": [
            {"source": "node_start", "target": "node_appr", "label": "Submit"},
            {"source": "node_appr", "target": "node_end", "condition": "APPROVE", "label": "Approve"}
        ]
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["workflow_id"] is not None
    assert data["status"] == "DRAFT"
    assert data["version_number"] == 1
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2
    assert any(n["id"] == "node_appr" and n["config"]["role"] == "TEAM_LEAD" for n in data["nodes"])
    print("Test 1 Passed: Created generic START -> APPROVAL -> END workflow.")
    return data["workflow_id"]


def test_02_update_workflow_graph():
    """
    Test 2 — Update workflow graph:
    Add/change a node and connection.
    Verify the updated graph is persisted.
    """
    wf_id = test_01_create_generic_workflow_start_approval_end()

    # Add a Finance Approval node in between Team Lead and End
    update_res = client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "name": "Updated Purchase Order Workflow",
        "nodes": [
            {"id": "node_start", "type": "START", "name": "Start Event", "config": {}},
            {"id": "node_appr", "type": "APPROVAL", "name": "Team Lead Approval", "config": {"role": "TEAM_LEAD", "actions": ["APPROVE", "REJECT"]}},
            {"id": "node_finance", "type": "APPROVAL", "name": "Finance Approval", "config": {"role": "FINANCE_OFFICER", "actions": ["APPROVE", "REJECT"]}},
            {"id": "node_end", "type": "END", "name": "End Event", "config": {}}
        ],
        "edges": [
            {"source": "node_start", "target": "node_appr"},
            {"source": "node_appr", "target": "node_finance", "condition": "APPROVE"},
            {"source": "node_finance", "target": "node_end", "condition": "APPROVE"}
        ]
    })
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert len(updated_data["nodes"]) == 4
    assert len(updated_data["edges"]) == 3
    assert any(n["id"] == "node_finance" for n in updated_data["nodes"])

    # Retrieve to confirm persistence
    get_res = client.get(f"/workflow-studio/workflows/{wf_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert len(get_data["nodes"]) == 4
    print("Test 2 Passed: Updated workflow graph and verified persistence.")


def test_03_validation_rejects_invalid_workflow():
    """
    Test 3 — Validation:
    Verify an invalid workflow such as START -> APPROVAL without END is rejected.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p4_invalid_{int(time.time())}",
        "name": "Incomplete Workflow (No END)",
        "entity_type": "Incident"
    })
    wf_id = wf_res.json()["workflow_id"]

    # Put invalid graph: START -> APPROVAL (no END node)
    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "mgr_appr", "type": "APPROVAL", "name": "Manager Approval", "config": {"role": "MANAGER", "actions": ["APPROVE"]}}
        ],
        "edges": [
            {"source": "start", "target": "mgr_appr"}
        ]
    })

    # Validate endpoint
    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert any(e["code"] in ["MISSING_END_NODE", "NO_OUTGOING_CONNECTION"] for e in val_data["errors"])

    # Publish attempt must be rejected with 400
    pub_res = client.post(f"/workflow-studio/workflows/{wf_id}/publish")
    assert pub_res.status_code == 400
    print("Test 3 Passed: Incomplete workflow correctly rejected by validation and publishing blocked.")


def test_04_valid_workflow_passes_validation():
    """
    Test 4 — Valid workflow:
    Verify START -> APPROVAL -> END passes validation.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p4_valid_{int(time.time())}",
        "name": "Clean Valid Workflow",
        "entity_type": "Audit"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "lead_appr", "type": "APPROVAL", "name": "Lead Audit Approval", "config": {"role": "LEAD_AUDITOR", "actions": ["APPROVE", "REJECT"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "lead_appr"},
            {"source": "lead_appr", "target": "end", "condition": "APPROVE"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is True
    assert len(val_data["errors"]) == 0
    print("Test 4 Passed: Clean valid workflow passed all structural validation checks.")


def test_05_publish_valid_workflow():
    """
    Test 5 — Publish:
    Verify a valid workflow can be published.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p4_pub_{int(time.time())}",
        "name": "Publishable Workflow",
        "entity_type": "VendorOnboarding"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "compliance", "type": "APPROVAL", "name": "Compliance Review", "config": {"role": "COMPLIANCE_OFFICER", "actions": ["APPROVE", "REJECT"]}},
            {"id": "end", "type": "END", "name": "Approved", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "compliance"},
            {"source": "compliance", "target": "end", "condition": "APPROVE"}
        ]
    })

    pub_res = client.post(f"/workflow-studio/workflows/{wf_id}/publish")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["version_status"] == "PUBLISHED"
    assert pub_data["status"] == "ACTIVE"
    assert pub_data["published_at"] is not None
    print("Test 5 Passed: Successfully published valid workflow definition.")


def test_06_version_isolation_and_immutability():
    """
    Test 6 — Version isolation:
    Publish version 1.
    Create version 2.
    Verify version 1 remains unchanged.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p4_ver_iso_{int(time.time())}",
        "name": "Version Isolation Test Workflow",
        "entity_type": "ChangeRequest"
    })
    wf_id = wf_res.json()["workflow_id"]

    # Version 1 definition (1 approval stage)
    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "stage_1", "type": "APPROVAL", "name": "Stage 1 (v1)", "config": {"role": "STAGE1_REVIEWER", "actions": ["APPROVE"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "stage_1"},
            {"source": "stage_1", "target": "end", "condition": "APPROVE"}
        ]
    })
    v1_published = client.post(f"/workflow-studio/workflows/{wf_id}/publish").json()
    assert v1_published["version_number"] == 1

    # Create Version 2 in Draft
    client.post(f"/workflows/{wf_id}/versions", json={"version_number": 2})

    # Update Version 2 (2 approval stages)
    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "stage_1", "type": "APPROVAL", "name": "Stage 1 (v2)", "config": {"role": "STAGE1_REVIEWER", "actions": ["APPROVE"]}},
            {"id": "stage_2", "type": "APPROVAL", "name": "Stage 2 (v2)", "config": {"role": "STAGE2_APPROVER", "actions": ["APPROVE"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "stage_1"},
            {"source": "stage_1", "target": "stage_2", "condition": "APPROVE"},
            {"source": "stage_2", "target": "end", "condition": "APPROVE"}
        ]
    })
    v2_published = client.post(f"/workflow-studio/workflows/{wf_id}/publish").json()
    assert v2_published["version_number"] == 2
    assert len(v2_published["nodes"]) == 4

    # Fetch Version 1 by version number and verify it still has 3 nodes
    v1_check = client.get(f"/workflow-studio/workflows/{wf_id}/versions/1")
    assert v1_check.status_code == 200
    v1_data = v1_check.json()
    assert len(v1_data["nodes"]) == 3
    assert not any(n["id"] == "stage_2" for n in v1_data["nodes"])

    # Verify version history endpoint lists both versions
    versions_list = client.get(f"/workflow-studio/workflows/{wf_id}/versions").json()
    assert len(versions_list) >= 2
    print("Test 6 Passed: Version 1 remains completely isolated and unchanged after Version 2 publication.")


def test_07_generic_risk_workflow_representation():
    """
    Test 7 — Generic Risk workflow:
    Verify the Studio can represent:
        START -> FH APPROVAL -> RM APPROVAL -> RH APPROVAL -> END
    with configured actions (APPROVE, REJECT, FORCE_APPROVE).
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p4_risk_flow_{int(time.time())}",
        "name": "Full Multi-tier Enterprise Risk Workflow",
        "entity_type": "Risk"
    })
    wf_id = wf_res.json()["workflow_id"]

    studio_graph = {
        "nodes": [
            {"id": "start", "type": "START", "name": "Risk Submitted", "config": {"entity_type": "Risk", "trigger": "SUBMIT"}},
            {"id": "fh_approval", "type": "APPROVAL", "name": "Functional Head Approval", "config": {
                "role": "FUNCTION_HEAD",
                "actions": ["APPROVE", "REJECT"],
                "visibility": {"owner": True, "current_role": True}
            }},
            {"id": "rm_approval", "type": "APPROVAL", "name": "Risk Manager Approval", "config": {
                "role": "RISK_MANAGER",
                "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"],
                "visibility": {"owner": True, "current_role": True}
            }},
            {"id": "rh_approval", "type": "APPROVAL", "name": "Risk Head Approval", "config": {
                "role": "RISK_HEAD",
                "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"],
                "visibility": {"owner": True, "current_role": True}
            }},
            {"id": "draft_rework", "type": "USER_TASK", "name": "Draft Rework", "config": {
                "role": "RISK_OWNER",
                "actions": ["RESUBMIT"]
            }},
            {"id": "end_approved", "type": "END", "name": "Risk Approved", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "fh_approval", "label": "Submit"},
            {"source": "fh_approval", "target": "rm_approval", "condition": "APPROVE", "label": "Approve"},
            {"source": "fh_approval", "target": "draft_rework", "condition": "REJECT", "label": "Reject to Draft"},
            {"source": "rm_approval", "target": "rh_approval", "condition": "APPROVE", "label": "Approve"},
            {"source": "rm_approval", "target": "draft_rework", "condition": "REJECT", "label": "Reject to Draft"},
            {"source": "rm_approval", "target": "end_approved", "condition": "FORCE_APPROVE", "label": "Force Approve"},
            {"source": "rh_approval", "target": "end_approved", "condition": "APPROVE", "label": "Approve"},
            {"source": "rh_approval", "target": "draft_rework", "condition": "REJECT", "label": "Reject to Draft"},
            {"source": "draft_rework", "target": "fh_approval", "condition": "RESUBMIT", "label": "Resubmit"}
        ]
    }

    client.put(f"/workflow-studio/workflows/{wf_id}", json=studio_graph)
    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    pub_res = client.post(f"/workflow-studio/workflows/{wf_id}/publish")
    assert pub_res.status_code == 200
    assert pub_res.json()["version_status"] == "PUBLISHED"
    print("Test 7 Passed: Multi-tier Risk Approval Workflow with approval, rejection, and force-approve represented cleanly.")


def test_08_no_hardcoded_role_behavior_and_dynamic_catalogs():
    """
    Test 8 — No hardcoded role behavior:
    Verify changing role/action configuration does not require code changes.
    Verify dynamic discovery of roles and actions via catalog APIs.
    """
    roles_res = client.get("/workflow-studio/roles")
    assert roles_res.status_code == 200
    roles = roles_res.json()
    assert len(roles) >= 1
    assert any("role_code" in r for r in roles)

    actions_res = client.get("/workflow-studio/actions")
    assert actions_res.status_code == 200
    actions = actions_res.json()
    assert len(actions) >= 4
    action_codes = [a["action_code"] for a in actions]
    assert "APPROVE" in action_codes
    assert "REJECT" in action_codes
    assert "FORCE_APPROVE" in action_codes

    # Define a completely custom domain workflow (e.g., Hospital Emergency Triage)
    custom_wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p4_custom_{int(time.time())}",
        "name": "Emergency Triage Workflow",
        "entity_type": "PatientTriage"
    })
    custom_wf_id = custom_wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{custom_wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Admit Patient", "config": {}},
            {"id": "doctor_eval", "type": "APPROVAL", "name": "Chief Physician Evaluation", "config": {
                "role": "CHIEF_PHYSICIAN",
                "actions": ["ADMIT", "DISCHARGE", "TRANSFER_ICU"]
            }},
            {"id": "end_discharged", "type": "END", "name": "Patient Discharged", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "doctor_eval"},
            {"source": "doctor_eval", "target": "end_discharged", "condition": "DISCHARGE"}
        ]
    })

    val = client.post(f"/workflow-studio/workflows/{custom_wf_id}/validate").json()
    assert val["is_valid"] is True
    pub = client.post(f"/workflow-studio/workflows/{custom_wf_id}/publish")
    assert pub.status_code == 200
    print("Test 8 Passed: Domain-agnostic role and action configurations work dynamically without Python code changes.")


if __name__ == "__main__":
    test_01_create_generic_workflow_start_approval_end()
    test_02_update_workflow_graph()
    test_03_validation_rejects_invalid_workflow()
    test_04_valid_workflow_passes_validation()
    test_05_publish_valid_workflow()
    test_06_version_isolation_and_immutability()
    test_07_generic_risk_workflow_representation()
    test_08_no_hardcoded_role_behavior_and_dynamic_catalogs()
    print("\nALL PHASE 4 WORKFLOW STUDIO TESTS PASSED SUCCESSFULLY!")
