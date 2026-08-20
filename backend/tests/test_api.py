import pytest

def test_list_definitions_empty(client):
    response = client.get("/workflow/definitions")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["Error"]["Error"] is False

def test_create_definition_draft(client):
    payload = {
        "spec_id": "ApiTestWorkflow",
        "name": "API Test Process",
        "description": "Validation checks process definition",
        "tags": "test, api"
    }
    response = client.post("/workflow/definitions", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["Error"]["Error"] is False
    assert res_data["data"]["spec_id"] == "ApiTestWorkflow"


def test_approval_action_api(client, db_session):
    from app.core.database import get_db
    from app.workflow.database import get_workflow_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_workflow_db] = lambda: db_session

    from app.models.department import Department
    from app.models.role import UserRole
    from app.models.user_type import UserType
    from app.models.user import User
    from app.models.mst_status import Status
    from app.models.risk_register import RiskRegister
    from app.workflow.persistence.models import BPMNDefinition, WorkflowEntityConfig, WorkflowTaskPermission, SpiffWorkflowInstance
    from datetime import datetime, timezone

    # 1. Setup departments, roles, user types, statuses
    dept = Department(dept_name="API Dept", dept_short_name="API-DEPT", is_deleted=0)
    db_session.add(dept)
    db_session.flush()

    role_fh = UserRole(name="FUNCTION_HEAD", description="FH")
    db_session.add(role_fh)
    db_session.flush()

    utype_fh = UserType(name="Functional Head", description="FH")
    db_session.add(utype_fh)
    db_session.flush()

    # Create the user with ID 1 so mock authentication maps to them!
    db_session.query(User).filter(User.id == 1).delete()
    db_session.flush()
    
    user_fh = User(id=1, log_id="fh_api_user", password="pwd", first_name="FH", last_name="U", email="fh_api@example.com", dept_id=dept.id, role_id=role_fh.id, user_type_id=utype_fh.id, status="Active")
    db_session.add(user_fh)
    db_session.flush()

    status_approved = Status(id=77, status_name="Approved", type="approval")
    status_pending_act = Status(id=71, status_name="Pending for Action", type="risk")
    db_session.add_all([status_approved, status_pending_act])
    db_session.flush()

    bpmn_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                      xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                      id="Definitions_API"
                      targetNamespace="http://bpmn.io/schema/bpmn">
      <bpmn:process id="ApiWorkflow" isExecutable="true">
        <bpmn:startEvent id="StartEvent" name="Start">
          <bpmn:outgoing>Flow_1</bpmn:outgoing>
        </bpmn:startEvent>
        <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent" targetRef="PENDING_FH" />
        <bpmn:userTask id="PENDING_FH" name="Pending FH" camunda:candidateGroups="FUNCTION_HEAD">
          <bpmn:incoming>Flow_1</bpmn:incoming>
          <bpmn:outgoing>Flow_2</bpmn:outgoing>
        </bpmn:userTask>
        <bpmn:sequenceFlow id="Flow_2" sourceRef="PENDING_FH" targetRef="APPROVED" />
        <bpmn:endEvent id="APPROVED" name="End">
          <bpmn:incoming>Flow_2</bpmn:incoming>
        </bpmn:endEvent>
      </bpmn:process>
    </bpmn:definitions>
    """
    definition = BPMNDefinition(
        spec_id="ApiWorkflow",
        name="Api Workflow Process",
        version=1,
        xml_content=bpmn_xml,
        is_active=True,
        status="Active"
    )
    db_session.add(definition)
    db_session.flush()

    config = WorkflowEntityConfig(
        entity_type="Risk",
        specification_id="ApiWorkflow",
        is_active=True
    )
    db_session.add(config)
    db_session.flush()

    perm = WorkflowTaskPermission(spec_id="ApiWorkflow", task_spec_id="PENDING_FH", role_code="FUNCTION_HEAD", actions="APPROVE,REJECT", is_active=True)
    db_session.add(perm)
    db_session.flush()

    # Create Risk
    risk = RiskRegister(
        risk_id="R-API-TEST", risk_name="Risk API", dept_id=dept.id, risk_owner_id=user_fh.id,
        risk_status=status_pending_act.id, is_active=1, is_deleted=0,
        created_by=user_fh.id, created_on=datetime.now(timezone.utc)
    )
    db_session.add(risk)
    db_session.flush()

    from app.workflow.services.workflow_service import WorkflowService
    service = WorkflowService(db=db_session)
    instance = service.submit(entity_type="Risk", entity_id=risk.risk_register_id, user_id=user_fh.id, remarks="Submit API")
    db_session.flush()

    # 2. Call the API `/approval/action` endpoint
    payload = {
        "risk_register_id": risk.risk_register_id,
        "approval_status_id": 7,
        "remark": "Approved via API action endpoint"
    }
    response = client.post("/approval/action", json=payload)
    
    # Clean up overrides
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_workflow_db, None)

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["Error"]["Error"] is False
    assert res_data["data"]["risk_status_name"] == "Approved"

    # Verify state was completed
    inst_check = db_session.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == instance.instance_id).first()
    assert inst_check.status == "Completed"

