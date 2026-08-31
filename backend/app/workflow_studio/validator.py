from typing import List, Dict, Set, Any
from collections import deque, defaultdict
from app.workflow_studio.schemas import StudioNode, StudioEdge, StudioValidationError, StudioValidationResponse

SUPPORTED_STUDIO_NODE_TYPES = {
    "START",
    "END",
    "APPROVAL",
    "CONDITION",
    "ACTION",
    "EMAIL",
    "USER_TASK",
    "DELAY",    
    "WAIT",
    "SUB_WORKFLOW",
    "WEBHOOK"
}


class WorkflowStudioValidator:
    """
    Validation engine enforcing structural, semantic, and configuration rules
    on Workflow Studio graph definitions before saving or publishing.
    """

    @classmethod
    def validate_graph(cls, nodes: List[StudioNode], edges: List[StudioEdge]) -> StudioValidationResponse:
        errors: List[StudioValidationError] = []
        warnings: List[StudioValidationError] = []

        if not nodes:
            errors.append(StudioValidationError(
                code="NO_NODES",
                message="Workflow canvas is empty. Add at least a START and an END node."
            ))
            return StudioValidationResponse(is_valid=False, status="INVALID", errors=errors, warnings=warnings)

        node_map: Dict[str, StudioNode] = {}
        start_nodes: List[StudioNode] = []
        end_nodes: List[StudioNode] = []

        # 1. Validate Node Identifiers, Types, and Configurations
        for node in nodes:
            node_id = str(node.id).strip()
            node_type = str(node.type).strip().upper()

            # Rule: Unique node ID
            if node_id in node_map:
                errors.append(StudioValidationError(
                    code="DUPLICATE_NODE_ID",
                    message=f"Duplicate node ID '{node_id}' detected. Every node on the canvas must have a unique ID.",
                    node_id=node_id
                ))
            else:
                node_map[node_id] = node

            # Rule: Supported node type
            if node_type not in SUPPORTED_STUDIO_NODE_TYPES:
                errors.append(StudioValidationError(
                    code="INVALID_NODE_TYPE",
                    message=f"Node '{node.name}' has invalid node type '{node.type}'. Supported types: {', '.join(sorted(SUPPORTED_STUDIO_NODE_TYPES))}",
                    node_id=node_id
                ))

            if node_type == "START":
                start_nodes.append(node)
            elif node_type == "END":
                end_nodes.append(node)

            # Rule: APPROVAL node must have role and at least one action
            if node_type in ("APPROVAL", "USER_TASK"):
                role = node.config.get("role") or node.config.get("candidate_group") or node.config.get("role_code")
                actions = node.config.get("actions") or node.config.get("allowed_actions") or []
                if not role:
                    errors.append(StudioValidationError(
                        code="APPROVAL_MISSING_ROLE",
                        message=f"Approval node '{node.name}' ({node_id}) has no assigned role configured.",
                        node_id=node_id
                    ))
                if not actions or (isinstance(actions, list) and len(actions) == 0):
                    errors.append(StudioValidationError(
                        code="APPROVAL_MISSING_ACTIONS",
                        message=f"Approval node '{node.name}' ({node_id}) must have at least one allowed action configured (e.g. APPROVE, REJECT).",
                        node_id=node_id
                    ))

            # Rule: CONDITION node configuration check
            elif node_type == "CONDITION":
                field = node.config.get("field")
                operator = node.config.get("operator")
                expr = node.config.get("expression") or node.config.get("condition")
                if not (field and operator) and not expr:
                    errors.append(StudioValidationError(
                        code="CONDITION_MISSING_CONFIG",
                        message=f"Condition node '{node.name}' ({node_id}) must have a field and operator or expression configured.",
                        node_id=node_id
                    ))

            # Rule: ACTION node configuration check
            elif node_type == "ACTION":
                act_code = node.config.get("action_code") or node.config.get("action_type") or node.config.get("action")
                if not act_code:
                    errors.append(StudioValidationError(
                        code="ACTION_MISSING_CODE",
                        message=f"Action node '{node.name}' ({node_id}) must have an action_code configured.",
                        node_id=node_id
                    ))

            # Rule: EMAIL node configuration check
            elif node_type == "EMAIL":
                to = node.config.get("to") or node.config.get("recipients")
                template = node.config.get("template")
                subject = node.config.get("subject")
                if not to and not template and not subject:
                    warnings.append(StudioValidationError(
                        code="EMAIL_MISSING_CONFIG",
                        message=f"Email node '{node.name}' ({node_id}) has no recipient or template configured.",
                        node_id=node_id,
                        severity="WARNING"
                    ))

            # Rule: DELAY / WAIT node configuration check
            elif node_type in ("DELAY", "WAIT"):
                duration = node.config.get("duration") or node.config.get("delay") or node.config.get("timeout")
                if not duration:
                    warnings.append(StudioValidationError(
                        code="DELAY_MISSING_DURATION",
                        message=f"Delay node '{node.name}' ({node_id}) has no delay duration configured.",
                        node_id=node_id,
                        severity="WARNING"
                    ))



        # Rule: Exactly one START node
        if len(start_nodes) == 0:
            errors.append(StudioValidationError(
                code="MISSING_START_NODE",
                message="Workflow must contain exactly one START node."
            ))
        elif len(start_nodes) > 1:
            errors.append(StudioValidationError(
                code="MULTIPLE_START_NODES",
                message=f"Workflow contains {len(start_nodes)} START nodes. Only one START node is permitted."
            ))

        # Rule: At least one END node
        if len(end_nodes) == 0:
            errors.append(StudioValidationError(
                code="MISSING_END_NODE",
                message="Workflow must contain at least one END node."
            ))

        # 2. Validate Edges / Connections
        edge_ids: Set[str] = set()
        outgoing_edges: Dict[str, List[StudioEdge]] = defaultdict(list)
        incoming_edges: Dict[str, List[StudioEdge]] = defaultdict(list)
        adj_list: Dict[str, List[str]] = defaultdict(list)
        rev_adj_list: Dict[str, List[str]] = defaultdict(list)

        for edge in edges:
            edge_id = str(edge.id) if edge.id else f"{edge.source}->{edge.target}"
            if edge_id in edge_ids:
                warnings.append(StudioValidationError(
                    code="DUPLICATE_EDGE_ID",
                    message=f"Duplicate edge ID '{edge_id}' detected.",
                    edge_id=edge_id,
                    severity="WARNING"
                ))
            edge_ids.add(edge_id)

            source_exists = edge.source in node_map
            target_exists = edge.target in node_map

            if not source_exists:
                errors.append(StudioValidationError(
                    code="INVALID_EDGE_SOURCE",
                    message=f"Connection references unknown source node '{edge.source}'.",
                    edge_id=edge_id
                ))
            if not target_exists:
                errors.append(StudioValidationError(
                    code="INVALID_EDGE_TARGET",
                    message=f"Connection references unknown target node '{edge.target}'.",
                    edge_id=edge_id
                ))

            if source_exists and target_exists:
                # Rule: Self connections
                if edge.source == edge.target:
                    errors.append(StudioValidationError(
                        code="SELF_CONNECTION",
                        message=f"Node '{node_map[edge.source].name}' ({edge.source}) cannot connect directly to itself.",
                        node_id=edge.source,
                        edge_id=edge_id
                    ))

                outgoing_edges[edge.source].append(edge)
                incoming_edges[edge.target].append(edge)
                adj_list[edge.source].append(edge.target)
                rev_adj_list[edge.target].append(edge.source)

                # Rule: START node cannot have incoming edges
                if node_map[edge.target].type.upper() == "START":
                    errors.append(StudioValidationError(
                        code="START_NODE_INCOMING_CONNECTION",
                        message="START node cannot have incoming connections.",
                        node_id=edge.target,
                        edge_id=edge_id
                    ))

                # Rule: END node cannot have outgoing edges
                if node_map[edge.source].type.upper() == "END":
                    errors.append(StudioValidationError(
                        code="END_NODE_OUTGOING_CONNECTION",
                        message="END node cannot have outgoing connections.",
                        node_id=edge.source,
                        edge_id=edge_id
                    ))

        # 3. Connection Topology Rules (Orphan, Non-END outgoing, Non-START incoming)
        for node_id, node in node_map.items():
            ntype = node.type.upper()

            # Rule: Every non-START node must have at least one incoming connection
            if ntype != "START" and len(incoming_edges[node_id]) == 0:
                errors.append(StudioValidationError(
                    code="ORPHAN_NODE_NO_INCOMING",
                    message=f"Node '{node.name}' ({node_id}) has no incoming connection.",
                    node_id=node_id
                ))

            # Rule: Every non-END node must have at least one outgoing connection
            if ntype != "END" and len(outgoing_edges[node_id]) == 0:
                errors.append(StudioValidationError(
                    code="NO_OUTGOING_CONNECTION",
                    message=f"Node '{node.name}' ({node_id}) has no outgoing connection.",
                    node_id=node_id
                ))

            # Rule: CONDITION node must have at least 2 branches
            if ntype == "CONDITION" and len(outgoing_edges[node_id]) < 2:
                warnings.append(StudioValidationError(
                    code="CONDITION_FEW_BRANCHES",
                    message=f"Condition node '{node.name}' ({node_id}) should have at least 2 outgoing decision branches.",
                    node_id=node_id,
                    severity="WARNING"
                ))

        # 4. Graph Reachability (DFS / BFS)
        if len(start_nodes) == 1 and len(end_nodes) >= 1:
            start_id = str(start_nodes[0].id)

            visited_from_start: Set[str] = set()
            queue = deque([start_id])
            visited_from_start.add(start_id)

            while queue:
                curr = queue.popleft()
                for neighbor in adj_list[curr]:
                    if neighbor not in visited_from_start:
                        visited_from_start.add(neighbor)
                        queue.append(neighbor)

            # Check if any active node is unreachable from START
            for node_id, node in node_map.items():
                if node_id not in visited_from_start:
                    errors.append(StudioValidationError(
                        code="UNREACHABLE_NODE",
                        message=f"Node '{node.name}' ({node_id}) is unreachable from START node.",
                        node_id=node_id
                    ))

            # Backward BFS from END nodes
            can_reach_end: Set[str] = set()
            end_queue = deque([str(end.id) for end in end_nodes])
            for end in end_nodes:
                can_reach_end.add(str(end.id))

            while end_queue:
                curr = end_queue.popleft()
                for pred in rev_adj_list[curr]:
                    if pred not in can_reach_end:
                        can_reach_end.add(pred)
                        end_queue.append(pred)

            if start_id not in can_reach_end:
                errors.append(StudioValidationError(
                    code="NO_PATH_TO_END",
                    message="No valid execution path exists from START node to any END node."
                ))

        is_valid = len(errors) == 0
        return StudioValidationResponse(
            is_valid=is_valid,
            status="VALIDATED" if is_valid else "INVALID",
            errors=errors,
            warnings=warnings
        )
