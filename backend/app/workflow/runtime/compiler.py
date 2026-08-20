import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

class WorkflowGraphCompiler:
    """
    Translates visual n8n-style node graph JSON into valid, executable BPMN 2.0 XML.
    Visual graph schema format:
    {
      "nodes": [
         { "id": "node_1", "type": "start", "name": "Start", "position": {"x": 100, "y": 200}, "config": {} },
         { "id": "node_2", "type": "approval", "name": "FH Approval", "position": {"x": 300, "y": 200}, "config": {"role_code": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]} },
         { "id": "node_3", "type": "end_approved", "name": "Approved", "position": {"x": 500, "y": 200}, "config": {} }
      ],
      "edges": [
         { "id": "edge_1", "source": "node_1", "target": "node_2", "label": "Submit" },
         { "id": "edge_2", "source": "node_2", "target": "node_3", "label": "Approve" }
      ]
    }
    """

    @classmethod
    def compile_graph_to_bpmn(cls, spec_id: str, graph_data: Dict[str, Any]) -> str:
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        # Default fallback if graph empty
        if not nodes:
            nodes = [
                {"id": "StartEvent_1", "type": "start", "name": "Start", "position": {"x": 180, "y": 160}, "config": {}},
                {"id": "UserTask_FH", "type": "approval", "name": "Functional Head Approval", "position": {"x": 320, "y": 160}, "config": {"role_code": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]}},
                {"id": "EndEvent_Approved", "type": "end_approved", "name": "Approved", "position": {"x": 520, "y": 160}, "config": {}}
            ]
            edges = [
                {"id": "Flow_1", "source": "StartEvent_1", "target": "UserTask_FH", "label": ""},
                {"id": "Flow_2", "source": "UserTask_FH", "target": "EndEvent_Approved", "label": "Approve"}
            ]

        # Namespaces
        bpmn_ns = "http://www.omg.org/spec/BPMN/20100524/MODEL"
        bpmndi_ns = "http://www.omg.org/spec/BPMN/20100524/DI"
        omgdc_ns = "http://www.omg.org/spec/DD/20100524/DC"
        omgdi_ns = "http://www.omg.org/spec/DD/20100524/DI"
        camunda_ns = "http://camunda.org/schema/1.0/bpmn"

        ET.register_namespace("bpmn", bpmn_ns)
        ET.register_namespace("bpmndi", bpmndi_ns)
        ET.register_namespace("dc", omgdc_ns)
        ET.register_namespace("di", omgdi_ns)
        ET.register_namespace("camunda", camunda_ns)

        definitions = ET.Element(
            f"{{{bpmn_ns}}}definitions",
            {
                "id": "Definitions_1",
                "targetNamespace": "http://bpmn.io/schema/bpmn",
                "exporter": "Workflow Studio n8n Compiler",
                "exporterVersion": "2.0"
            }
        )

        process_id = spec_id
        process = ET.SubElement(definitions, f"{{{bpmn_ns}}}process", {"id": process_id, "name": spec_id, "isExecutable": "true"})

        # Map node elements
        node_map = {}
        for node in nodes:
            node_id = node.get("id")
            raw_type = str(node.get("type", "userTask")).strip().lower()
            node_name = node.get("name", node_id)
            config = node.get("config", {})

            if raw_type in ["start", "startevent", "start_event"]:
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}startEvent", {"id": node_id, "name": node_name})
            elif raw_type in ["approval", "usertask", "user_task", "human_task", "form"]:
                role_code = config.get("role") or config.get("role_code") or "FUNCTION_HEAD"
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}userTask", {
                    "id": node_id,
                    "name": node_name,
                    f"{{{camunda_ns}}}candidateGroups": role_code
                })
            elif raw_type in ["email", "mail"]:
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}serviceTask", {"id": node_id, "name": node_name})
            elif raw_type in ["action", "servicetask", "service_task", "webhook"]:
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}serviceTask", {"id": node_id, "name": node_name})
            elif raw_type in ["gateway", "condition", "exclusivegateway", "exclusive_gateway"]:
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}exclusiveGateway", {"id": node_id, "name": node_name})
            elif raw_type in ["wait", "delay"]:
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}intermediateCatchEvent", {"id": node_id, "name": node_name})
            elif raw_type in ["end", "endevent", "end_event", "end_approved", "end_rejected"]:
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}endEvent", {"id": node_id, "name": node_name})
            else:
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}userTask", {"id": node_id, "name": node_name})

            node_map[node_id] = node

        # Map sequence flows
        flow_counter = 1
        for edge in edges:
            source_id = edge.get("source")
            target_id = edge.get("target")
            flow_id = edge.get("id") or f"Flow_{flow_counter}"
            flow_counter += 1
            label = edge.get("label") or edge.get("action") or ""

            flow_attr = {
                "id": flow_id,
                "sourceRef": source_id,
                "targetRef": target_id
            }
            if label:
                flow_attr["name"] = label

            flow_elem = ET.SubElement(process, f"{{{bpmn_ns}}}sequenceFlow", flow_attr)

            condition = edge.get("condition") or edge.get("action")
            if condition:
                cond_elem = ET.SubElement(flow_elem, f"{{{bpmn_ns}}}conditionExpression", {
                    "{http://www.w3.org/2001/XMLSchema-instance}type": "bpmn:tFormalExpression"
                })
                cond_elem.text = condition

        # Build BPMNDiagram layout
        diagram = ET.SubElement(definitions, f"{{{bpmndi_ns}}}BPMNDiagram", {"id": "BPMNDiagram_1"})
        plane = ET.SubElement(diagram, f"{{{bpmndi_ns}}}BPMNPlane", {"id": "BPMNPlane_1", "bpmnElement": process_id})

        for node in nodes:
            node_id = node.get("id")
            pos = node.get("position", {"x": 200, "y": 200})
            shape = ET.SubElement(plane, f"{{{bpmndi_ns}}}BPMNShape", {
                "id": f"{node_id}_di",
                "bpmnElement": node_id
            })
            ET.SubElement(shape, f"{{{omgdc_ns}}}Bounds", {
                "x": str(pos.get("x", 200)),
                "y": str(pos.get("y", 200)),
                "width": "100",
                "height": "80"
            })

        for edge in edges:
            edge_id = edge.get("id") or "Flow_1"
            bpmn_edge = ET.SubElement(plane, f"{{{bpmndi_ns}}}BPMNEdge", {
                "id": f"{edge_id}_di",
                "bpmnElement": edge_id
            })
            source_pos = next((n.get("position", {"x": 200, "y": 200}) for n in nodes if n.get("id") == edge.get("source")), {"x": 200, "y": 200})
            target_pos = next((n.get("position", {"x": 400, "y": 200}) for n in nodes if n.get("id") == edge.get("target")), {"x": 400, "y": 200})

            ET.SubElement(bpmn_edge, f"{{{omgdi_ns}}}waypoint", {"x": str(source_pos.get("x", 200) + 100), "y": str(source_pos.get("y", 200) + 40)})
            ET.SubElement(bpmn_edge, f"{{{omgdi_ns}}}waypoint", {"x": str(target_pos.get("x", 400)), "y": str(target_pos.get("y", 400) + 40)})

        xml_str = ET.tostring(definitions, encoding="utf-8").decode("utf-8")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

    @classmethod
    def get_default_starter_graph(cls, spec_id: str, name: str) -> Dict[str, Any]:
        """
        Provides default starter visual graph for new definitions.
        """
        return {
            "nodes": [
                {
                    "id": "StartEvent_1",
                    "type": "start",
                    "name": "Start Process",
                    "position": { "x": 100, "y": 220 },
                    "config": {}
                },
                {
                    "id": "UserTask_1",
                    "type": "approval",
                    "name": "Reviewer Approval",
                    "position": { "x": 300, "y": 220 },
                    "config": {
                        "role_code": "REVIEWER",
                        "actions": ["APPROVE", "REJECT"]
                    }
                },
                {
                    "id": "UserTask_2",
                    "type": "approval",
                    "name": "Manager Approval",
                    "position": { "x": 550, "y": 220 },
                    "config": {
                        "role_code": "MANAGER",
                        "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]
                    }
                },
                {
                    "id": "EndEvent_Approved",
                    "type": "end_approved",
                    "name": "Process Completed",
                    "position": { "x": 800, "y": 220 },
                    "config": {}
                }
            ],
            "connections": [
                { "id": "conn_1", "source": "StartEvent_1", "target": "UserTask_1", "action": None },
                { "id": "conn_2", "source": "UserTask_1", "target": "UserTask_2", "action": "APPROVE" },
                { "id": "conn_3", "source": "UserTask_2", "target": "EndEvent_Approved", "action": "APPROVE" }
            ]
        }
