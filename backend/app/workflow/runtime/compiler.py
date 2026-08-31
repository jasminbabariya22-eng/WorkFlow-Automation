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
        edges = graph_data.get("edges", []) or graph_data.get("connections", [])

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
        gateway_default_flows = {}

        # Pre-scan edges to identify gateway default outgoing flows (e.g. FALSE branch)
        for node in nodes:
            node_id = node.get("id")
            raw_type = str(node.get("type", "userTask")).strip().lower()
            if raw_type in ["gateway", "condition", "exclusivegateway", "exclusive_gateway"]:
                outgoing_from_gw = [e for e in edges if e.get("source") == node_id]
                for e in outgoing_from_gw:
                    sh = str(e.get("sourceHandle") or e.get("label") or e.get("data", {}).get("action") or "").upper()
                    if "FALSE" in sh or "REJECT" in sh or "DEFAULT" in sh:
                        flow_id = e.get("id")
                        if flow_id:
                            gateway_default_flows[node_id] = flow_id
                # Fallback to last outgoing flow as default if not explicitly marked
                if node_id not in gateway_default_flows and len(outgoing_from_gw) > 1:
                    gateway_default_flows[node_id] = outgoing_from_gw[-1].get("id")

        for node in nodes:
            node_id = node.get("id")
            raw_type = str(node.get("type", "userTask")).strip().lower()
            data = node.get("data", {})
            config = node.get("config", {})
            node_name = data.get("label") or data.get("name") or node.get("name") or node_id

            if raw_type in ["start", "startevent", "start_event"]:
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}startEvent", {"id": node_id, "name": node_name})
            elif raw_type in ["approval", "usertask", "user_task", "human_task", "form"]:
                role_code = data.get("role") or data.get("roleId") or config.get("role") or config.get("role_code") or "FUNCTION_HEAD"
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}userTask", {
                    "id": node_id,
                    "name": node_name,
                    f"{{{camunda_ns}}}candidateGroups": str(role_code)
                })
            elif raw_type in ["email", "mail", "communication", "notification"]:
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}serviceTask", {
                    "id": node_id,
                    "name": node_name,
                    f"{{{camunda_ns}}}class": "SendEmailActivity",
                    f"{{{camunda_ns}}}topic": "SendEmail"
                })
            elif raw_type in ["action", "servicetask", "service_task", "webhook", "record", "dbupdate"]:
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}serviceTask", {
                    "id": node_id,
                    "name": node_name,
                    f"{{{camunda_ns}}}class": "UpdateDatabaseActivity",
                    f"{{{camunda_ns}}}topic": "UpdateDatabase"
                })
            elif raw_type in ["gateway", "condition", "exclusivegateway", "exclusive_gateway"]:
                gw_attrs = {"id": node_id, "name": node_name}
                if node_id in gateway_default_flows:
                    gw_attrs["default"] = gateway_default_flows[node_id]
                elem = ET.SubElement(process, f"{{{bpmn_ns}}}exclusiveGateway", gw_attrs)
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
            label = edge.get("label") or edge.get("data", {}).get("label") or edge.get("action") or ""

            flow_attr = {
                "id": flow_id,
                "sourceRef": source_id,
                "targetRef": target_id
            }
            if label:
                flow_attr["name"] = label

            flow_elem = ET.SubElement(process, f"{{{bpmn_ns}}}sequenceFlow", flow_attr)

            # Check if source node is a condition / exclusiveGateway
            source_node = node_map.get(source_id, {})
            source_type = str(source_node.get("type", "")).strip().lower()
            
            condition_expr = edge.get("condition") or edge.get("conditionExpression")
            
            if not condition_expr and source_type in ["gateway", "condition", "exclusivegateway", "exclusive_gateway"]:
                sh = str(edge.get("sourceHandle") or label or "").upper()
                gw_data = source_node.get("data", {})
                gw_field = gw_data.get("field") or "action"
                gw_val = gw_data.get("value") or "APPROVE"
                
                # If this flow is the TRUE branch or non-default branch
                if "TRUE" in sh or "APPROVE" in sh or (flow_id != gateway_default_flows.get(source_id)):
                    condition_expr = f"{gw_field} == '{gw_val}'"

            if condition_expr:
                cond_elem = ET.SubElement(flow_elem, f"{{{bpmn_ns}}}conditionExpression", {
                    "{http://www.w3.org/2001/XMLSchema-instance}type": "bpmn:tFormalExpression"
                })
                cond_elem.text = condition_expr

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
        Provides default starter visual graph for new definitions (empty blank canvas).
        """
        return {
            "nodes": [],
            "edges": [],
            "connections": []
        }
