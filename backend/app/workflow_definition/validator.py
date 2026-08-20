from typing import List, Dict, Set, Any
from collections import deque, defaultdict
from app.workflow_definition.models import WorkflowVersion, WorkflowNode, WorkflowConnection
from app.workflow_definition.schemas import ValidationErrorItem, WorkflowValidationResponse

SUPPORTED_NODE_TYPES = {
    "START",
    "END",
    "APPROVAL",
    "CONDITION",
    "ACTION",
    "EMAIL",
    "FORM",
    "WAIT",
    "WEBHOOK"
}


class WorkflowDefinitionValidator:
    """
    Validates structural and semantic correctness of a workflow version graph.
    Prevents invalid workflow graphs before publication.
    """

    @classmethod
    def validate_version(cls, version: WorkflowVersion) -> WorkflowValidationResponse:
        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationErrorItem] = []

        nodes: List[WorkflowNode] = [n for n in version.nodes if n.is_active]
        connections: List[WorkflowConnection] = version.connections

        if not nodes:
            errors.append(ValidationErrorItem(
                code="NO_NODES",
                message="Workflow version contains no active nodes."
            ))
            return WorkflowValidationResponse(
                is_valid=False,
                status="INVALID",
                errors=errors,
                warnings=warnings
            )

        node_map: Dict[int, WorkflowNode] = {n.node_id: n for n in nodes}
        node_keys: Dict[str, int] = {}
        start_nodes: List[WorkflowNode] = []
        end_nodes: List[WorkflowNode] = []

        # 1. Validate Nodes
        for node in nodes:
            # Check supported node_type
            if node.node_type.upper() not in SUPPORTED_NODE_TYPES:
                errors.append(ValidationErrorItem(
                    code="UNSUPPORTED_NODE_TYPE",
                    message=f"Node '{node.name}' has unsupported node_type '{node.node_type}'. Supported types: {', '.join(sorted(SUPPORTED_NODE_TYPES))}",
                    node_id=node.node_id
                ))

            # Check duplicate node_key
            normalized_key = node.node_key.strip().lower()
            if normalized_key in node_keys:
                errors.append(ValidationErrorItem(
                    code="DUPLICATE_NODE_KEY",
                    message=f"Duplicate node_key '{node.node_key}' detected in version. Node keys must be unique within a workflow version.",
                    node_id=node.node_id
                ))
            else:
                node_keys[normalized_key] = node.node_id

            if node.node_type.upper() == "START":
                start_nodes.append(node)
            elif node.node_type.upper() == "END":
                end_nodes.append(node)

        # Rule 1: Exactly one START node
        if len(start_nodes) == 0:
            errors.append(ValidationErrorItem(
                code="MISSING_START_NODE",
                message="Workflow must contain exactly one START node."
            ))
        elif len(start_nodes) > 1:
            errors.append(ValidationErrorItem(
                code="MULTIPLE_START_NODES",
                message=f"Workflow contains {len(start_nodes)} START nodes. Exactly one START node is permitted."
            ))

        # Rule 2: At least one END node
        if len(end_nodes) == 0:
            errors.append(ValidationErrorItem(
                code="MISSING_END_NODE",
                message="Workflow must contain at least one END node."
            ))

        # 2. Validate Connections
        adj_list: Dict[int, List[int]] = defaultdict(list)
        rev_adj_list: Dict[int, List[int]] = defaultdict(list)

        for conn in connections:
            source_exists = conn.source_node_id in node_map
            target_exists = conn.target_node_id in node_map

            if not source_exists:
                errors.append(ValidationErrorItem(
                    code="INVALID_CONNECTION_SOURCE",
                    message=f"Connection references unknown or deleted source node ID {conn.source_node_id}.",
                    connection_id=conn.connection_id
                ))
            if not target_exists:
                errors.append(ValidationErrorItem(
                    code="INVALID_CONNECTION_TARGET",
                    message=f"Connection references unknown or deleted target node ID {conn.target_node_id}.",
                    connection_id=conn.connection_id
                ))

            if source_exists and target_exists:
                adj_list[conn.source_node_id].append(conn.target_node_id)
                rev_adj_list[conn.target_node_id].append(conn.source_node_id)

                # START node cannot have incoming connections
                if node_map[conn.target_node_id].node_type.upper() == "START":
                    errors.append(ValidationErrorItem(
                        code="START_NODE_INCOMING_CONNECTION",
                        message="START node cannot have incoming connections.",
                        node_id=conn.target_node_id,
                        connection_id=conn.connection_id
                    ))

                # END node cannot have outgoing connections
                if node_map[conn.source_node_id].node_type.upper() == "END":
                    errors.append(ValidationErrorItem(
                        code="END_NODE_OUTGOING_CONNECTION",
                        message="END node cannot have outgoing connections.",
                        node_id=conn.source_node_id,
                        connection_id=conn.connection_id
                    ))

        # 3. Graph Reachability Analysis
        if len(start_nodes) == 1 and len(end_nodes) >= 1:
            start_node_id = start_nodes[0].node_id

            # BFS from START node to find all forward-reachable nodes
            visited_from_start: Set[int] = set()
            queue = deque([start_node_id])
            visited_from_start.add(start_node_id)

            while queue:
                current = queue.popleft()
                for neighbor in adj_list[current]:
                    if neighbor not in visited_from_start:
                        visited_from_start.add(neighbor)
                        queue.append(neighbor)

            # Check if any active node is unreachable from START
            for node in nodes:
                if node.node_id not in visited_from_start:
                    warnings.append(ValidationErrorItem(
                        code="UNREACHABLE_NODE",
                        message=f"Node '{node.name}' ({node.node_key}) is unreachable from START node.",
                        node_id=node.node_id,
                        severity="WARNING"
                    ))

            # Backward BFS from all END nodes to find nodes that can reach an END
            can_reach_end: Set[int] = set()
            end_queue = deque([end.node_id for end in end_nodes])
            for end in end_nodes:
                can_reach_end.add(end.node_id)

            while end_queue:
                current = end_queue.popleft()
                for predecessor in rev_adj_list[current]:
                    if predecessor not in can_reach_end:
                        can_reach_end.add(predecessor)
                        end_queue.append(predecessor)

            # Verify that START can reach at least one END node
            if start_node_id not in can_reach_end:
                errors.append(ValidationErrorItem(
                    code="NO_PATH_TO_END",
                    message="No valid execution path exists from START node to any END node."
                ))

            # Check for reachable nodes that are dead-ends (cannot reach any END node)
            for node_id in visited_from_start:
                if node_id not in can_reach_end:
                    errors.append(ValidationErrorItem(
                        code="DEAD_END_NODE",
                        message=f"Node '{node_map[node_id].name}' ({node_map[node_id].node_key}) cannot reach any END node.",
                        node_id=node_id
                    ))

        is_valid = len(errors) == 0
        return WorkflowValidationResponse(
            is_valid=is_valid,
            status="VALIDATED" if is_valid else "INVALID",
            errors=errors,
            warnings=warnings
        )
