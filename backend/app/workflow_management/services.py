import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.workflow.persistence.models import BPMNDefinition, WorkflowTaskPermission
from app.workflow.runtime.parser import SpiffBPMNParser
from app.workflow.runtime.registry import registry
from app.workflow.runtime.bpmn_utils import get_candidate_role_from_xml
from app.workflow_management.schemas import ValidationErrorDetail

class WorkflowManagementService:
    """
    WorkflowManagementService coordinates workflow validations, version control,
    cloning, and publishes specifications using standard BPMN 2.0.
    """
    
    @staticmethod
    def validate_bpmn(xml_content: str, spec_id: str) -> List[ValidationErrorDetail]:
        errors: List[ValidationErrorDetail] = []
        if not xml_content:
            errors.append(ValidationErrorDetail(
                severity="Error",
                message="BPMN XML content is empty or missing."
            ))
            return errors

        # Rule 1: Validate compilation using SpiffBPMNParser
        try:
            parser = SpiffBPMNParser()
            parser.parse_xml(xml_content, spec_id)
        except Exception as compile_err:
            errors.append(ValidationErrorDetail(
                severity="Error",
                message=f"BPMN Parser Compilation Failed: {str(compile_err)}"
            ))
            return errors

        # Rule 2: Run fine-grained structural validation using ElementTree
        try:
            root = ET.fromstring(xml_content)
            namespaces = {
                'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
                'camunda': 'http://camunda.org/schema/1.0/bpmn'
            }

            # Gather all elements by ID and check duplicate IDs
            all_elements = root.findall('.//*[@id]')
            ids_set = set()
            for elem in all_elements:
                elem_id = elem.attrib.get('id')
                if elem_id in ids_set:
                    errors.append(ValidationErrorDetail(
                        node_id=elem_id,
                        severity="Error",
                        message=f"Duplicate element ID attribute '{elem_id}' exists in XML."
                    ))
                ids_set.add(elem_id)

            # Assert Start Event exists
            start_events = root.findall('.//{http://www.omg.org/spec/BPMN/20100524/MODEL}startEvent')
            if len(start_events) == 0:
                errors.append(ValidationErrorDetail(
                    severity="Error",
                    message="BPMN diagram is invalid: Missing at least one Start Event node."
                ))

            # Assert End Event exists
            end_events = root.findall('.//{http://www.omg.org/spec/BPMN/20100524/MODEL}endEvent')
            if len(end_events) == 0:
                errors.append(ValidationErrorDetail(
                    severity="Error",
                    message="BPMN diagram is invalid: Missing at least one End Event node."
                ))

            # Gather all flow node elements and validate connections (no disconnected nodes)
            flow_node_tags = ['userTask', 'serviceTask', 'scriptTask', 'exclusiveGateway', 'parallelGateway', 'manualTask']
            all_flow_nodes = []
            for tag in flow_node_tags:
                all_flow_nodes.extend(root.findall(f'.//{{http://www.omg.org/spec/BPMN/20100524/MODEL}}{tag}'))

            # Gather sequence flow source/target attributes
            seq_flows = root.findall('.//{http://www.omg.org/spec/BPMN/20100524/MODEL}sequenceFlow')
            flow_sources = {flow.attrib.get('sourceRef') for flow in seq_flows if flow.attrib.get('sourceRef')}
            flow_targets = {flow.attrib.get('targetRef') for flow in seq_flows if flow.attrib.get('targetRef')}

            for node in all_flow_nodes:
                node_id = node.attrib.get('id')
                node_name = node.attrib.get('name') or node_id
                
                # Check disconnected nodes (must have at least one incoming or outgoing route)
                has_incoming = node.findall('.//{http://www.omg.org/spec/BPMN/20100524/MODEL}incoming')
                has_outgoing = node.findall('.//{http://www.omg.org/spec/BPMN/20100524/MODEL}outgoing')
                
                is_connected = (
                    len(has_incoming) > 0 or 
                    len(has_outgoing) > 0 or 
                    node_id in flow_sources or 
                    node_id in flow_targets
                )
                
                if not is_connected:
                    errors.append(ValidationErrorDetail(
                        node_id=node_id,
                        node_name=node_name,
                        severity="Warning",
                        message=f"Node '{node_name}' is disconnected (has no incoming or outgoing sequence flows)."
                    ))

                # Check Candidate Groups configuration for User Tasks
                if node.tag.endswith('userTask'):
                    # Check for camunda:candidateGroups attribute
                    has_role = False
                    for key in node.attrib.keys():
                        if 'candidateGroups' in key:
                            has_role = True
                            break
                    if not has_role:
                        errors.append(ValidationErrorDetail(
                            node_id=node_id,
                            node_name=node_name,
                            severity="Warning",
                            message=f"User Task '{node_name}' has no Candidate Group role config defined."
                        ))

                # Check Service Task maps to registry entries
                if node.tag.endswith('serviceTask'):
                    task_spec_name = node.attrib.get('name') or node_id
                    camunda_class = None
                    camunda_topic = None
                    for k, v in node.attrib.items():
                        if 'class' in k:
                            camunda_class = v
                        elif 'topic' in k:
                            camunda_topic = v

                    registered_items = registry.get_registered_activities()
                    is_valid_service = (
                        task_spec_name in registered_items or
                        camunda_class in registered_items or
                        camunda_class in registered_items.values() or
                        camunda_topic in registered_items or
                        any(c in task_spec_name for c in ["Update", "Email", "Notification", "Create", "Audit", "Log", "DB"])
                    )

                    if not is_valid_service:
                        errors.append(ValidationErrorDetail(
                            node_id=node_id,
                            node_name=node_name,
                            severity="Warning",
                            message=f"Service Task '{node_name}' targets name '{task_spec_name}', which is not registered in the Activity Registry."
                        ))

            # Validate sequence flow targets exist in the diagram
            for flow in seq_flows:
                flow_id = flow.attrib.get('id') or "SequenceFlow"
                source_ref = flow.attrib.get('sourceRef')
                target_ref = flow.attrib.get('targetRef')
                
                if source_ref not in ids_set:
                    errors.append(ValidationErrorDetail(
                        node_id=flow_id,
                        severity="Error",
                        message=f"Sequence flow '{flow_id}' has invalid or missing source reference '{source_ref}'."
                    ))
                if target_ref not in ids_set:
                    errors.append(ValidationErrorDetail(
                        node_id=flow_id,
                        severity="Error",
                        message=f"Sequence flow '{flow_id}' has invalid or missing target reference '{target_ref}'."
                    ))

        except Exception as err:
            errors.append(ValidationErrorDetail(
                severity="Error",
                message=f"Structural analysis failed: {str(err)}"
            ))

        return errors

    @staticmethod
    def publish_workflow(db: Session, definition_id: int, user_id: int) -> BPMNDefinition:
        """
        Validates the draft definition, copies it as a new locked published version,
        and sets it as the active version.
        """
        draft = db.query(BPMNDefinition).filter(BPMNDefinition.id == definition_id).first()
        if not draft:
            raise HTTPException(status_code=404, detail="BPMN draft definition not found")

        # 1. Validate BPMN structure
        validation_errors = WorkflowManagementService.validate_bpmn(draft.xml_content, draft.spec_id)
        critical_errors = [e for e in validation_errors if e.severity == "Error"]
        if critical_errors:
            raise HTTPException(
                status_code=400, 
                detail=f"BPMN Validation failed: {[e.message for e in critical_errors]}"
            )

        # 2. Deactivate all other existing versions of this spec_id
        db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == draft.spec_id,
            BPMNDefinition.id != draft.id
        ).update({"is_active": False})

        # 3. If currently a Draft, publish this definition directly in place
        if draft.status == "Draft":
            draft.status = "Published"
            draft.is_active = True
            draft.published_on = datetime.now()
            draft.updated_on = datetime.now()
            published = draft
        else:
            # If already published, increment version number for release
            latest_version = db.query(BPMNDefinition.version).filter(
                BPMNDefinition.spec_id == draft.spec_id
            ).order_by(BPMNDefinition.version.desc()).first()
            next_version = (latest_version[0] + 1) if latest_version else (draft.version + 1)

            published = BPMNDefinition(
                spec_id=draft.spec_id,
                name=draft.name or draft.spec_id,
                version=next_version,
                description=draft.description or f"Version {next_version} Release",
                xml_content=draft.xml_content,
                json_content=draft.json_content,
                is_active=True,
                status="Published",
                tags=draft.tags,
                created_by=user_id,
                created_on=datetime.now(),
                published_on=datetime.now()
            )
            db.add(published)
            db.flush()

        # 5. Sync permissions from visual graph nodes to WorkflowTaskPermission table
        if draft.json_content:
            try:
                graph = json.loads(draft.json_content)
                nodes = graph.get("nodes", [])
                for node in nodes:
                    if node.get("type") in ["approval", "userTask"]:
                        node_id = node.get("id")
                        config = node.get("config", {})
                        role_code = config.get("role_code", "FUNCTION_HEAD")
                        actions_list = config.get("actions", ["APPROVE", "REJECT"])
                        actions_str = ",".join(actions_list)

                        # Existing permission check
                        perm = db.query(WorkflowTaskPermission).filter(
                            WorkflowTaskPermission.spec_id == draft.spec_id,
                            WorkflowTaskPermission.task_spec_id == node_id
                        ).first()

                        if perm:
                            perm.role_code = role_code
                            perm.actions = actions_str
                            perm.is_active = True
                        else:
                            new_perm = WorkflowTaskPermission(
                                spec_id=draft.spec_id,
                                task_spec_id=node_id,
                                role_code=role_code,
                                actions=actions_str,
                                is_active=True
                            )
                            db.add(new_perm)
            except Exception as e:
                print(f"Warning: Failed to sync permissions from json_content: {e}")

        db.commit()
        db.refresh(published)
        return published

    @staticmethod
    def duplicate_workflow(db: Session, definition_id: int, user_id: int) -> BPMNDefinition:
        """
        Clones an existing workflow spec into a new distinct Draft specification.
        """
        source = db.query(BPMNDefinition).filter(BPMNDefinition.id == definition_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source definition not found")

        new_spec_id = f"{source.spec_id}_copy"
        new_name = f"{source.name or source.spec_id} (Copy)"

        # Check if copy spec ID already exists to prevent duplicate key clash
        exists = db.query(BPMNDefinition).filter(BPMNDefinition.spec_id == new_spec_id).first()
        if exists:
            # Append random timestamp
            suffix = datetime.now().strftime("%f")[:3]
            new_spec_id = f"{new_spec_id}_{suffix}"
            new_name = f"{new_name} {suffix}"

        # Adjust the ID in XML content to match new spec_id dynamically
        updated_xml = source.xml_content.replace(f'process id="{source.spec_id}"', f'process id="{new_spec_id}"') if source.xml_content else ""

        # Insert draft copy (version 1)
        draft_copy = BPMNDefinition(
            spec_id=new_spec_id,
            name=new_name,
            version=1,
            description=f"Draft copy of {source.name or source.spec_id}",
            xml_content=updated_xml,
            json_content=source.json_content,
            is_active=False,
            status="Draft",
            tags=source.tags,
            created_by=user_id,
            created_on=datetime.now()
        )
        db.add(draft_copy)
        db.commit()
        db.refresh(draft_copy)
        return draft_copy
