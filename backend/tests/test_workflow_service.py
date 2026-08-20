import pytest
from app.workflow.services.workflow_service import WorkflowService
from app.workflow.persistence.models import BPMNDefinition, SpiffWorkflowInstance, WorkflowEntityConfig

def test_workflow_service_lifecycle(db_session):
    # Setup test BPMN definition entry in db
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                      id="Definitions_1"
                      targetNamespace="http://bpmn.io/schema/bpmn">
      <bpmn:process id="TestApprovalWorkflow" isExecutable="true">
        <bpmn:startEvent id="StartEvent_1"/>
      </bpmn:process>
    </bpmn:definitions>
    """
    
    definition = BPMNDefinition(
        spec_id="TestApprovalWorkflow",
        name="Test Approval Workflow",
        version=1,
        xml_content=xml_content,
        is_active=True,
        status="Active"
    )
    db_session.add(definition)
    
    config = WorkflowEntityConfig(
        entity_type="Test",
        specification_id="TestApprovalWorkflow",
        is_active=True
    )
    db_session.add(config)
    
    db_session.commit()

    service = WorkflowService()
    service.db = db_session  # Swap standard connection with test isolated session
    service.repository.db = db_session  # Swap repository session too!
    
    # 1. Start dynamic workflow instance
    instance = service.start_workflow(
        workflow_name="Test Instantiation",
        entity_type="Test",
        entity_id=45,
        user_id=1
    )
    
    assert instance is not None
    assert instance.entity_type == "Test"
    assert instance.entity_id == 45
