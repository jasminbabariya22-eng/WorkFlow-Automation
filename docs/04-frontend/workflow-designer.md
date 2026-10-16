# Workflow Designer

## 1. Visual Designer Overview

The **Workflow Designer** (`frontend/src/components/Designer.jsx`) is the core visual workspace of the platform. Powered by **`@xyflow/react` (v12.11.3)**, it allows users to drag, drop, connect, configure, validate, and simulate complex business workflows.

```text
+---------------------------------------------------------------------------------+
|  [< Back]  Workflow: Risk Approval Flow (v2 Draft)    [Validate] [Test] [Save]  |
+-------------------+-------------------------------------------+-----------------+
|                   |                                           |                 |
|  NODE PALETTE     |           VISUAL CANVAS                   | PROPERTIES      |
|  (NodeLibrary)    |          (@xyflow/react)                  | PANEL           |
|                   |                                           | (Context-aware) |
|  - Start          |   [Start] ---> [Check Risk]               |                 |
|  - Approval       |                   | (High)                | - Node Label    |
|  - DB CRUD        |                   v                       | - Assigned Role |
|  - API Call       |             [VP Approval] ---> [End]      | - Live SQL Map  |
|  - Condition      |                                           | - Email Form    |
|  - Communication  |                                           |                 |
|  - End            |                                           |                 |
|                   |                                           |                 |
+-------------------+-------------------------------------------+-----------------+
|  Canvas Controls: [Zoom In] [Zoom Out] [Fit View] [MiniMap]                     |
+---------------------------------------------------------------------------------+
```

---

## 2. Canvas Mechanics & React Flow Integration

### A. Node Rendering (`CustomNodes.jsx`)
All visual nodes on the canvas are rendered via custom React Flow components defined in `frontend/src/components/nodes/CustomNodes.jsx`:
- **Card Anatomy**: Each node features a color-coded header icon, title, subtitle badge (e.g. assigned role or target table), and status indicator.
- **Connection Handles**:
  - `target` handles on the left edge for incoming sequence flows.
  - `source` handles on the right edge for standard sequential outgoing flows.
  - Split multi-handles on branching nodes (e.g., `TRUE` / `FALSE` handles on condition nodes, custom action handles on approval nodes).

### B. Drag-and-Drop Workflow Composition
1. The user drags a node item from `NodeLibrary.jsx`.
2. The canvas listens to the `onDrop` event, calculates canvas coordinates via `screenToFlowPosition()`, and injects a new node object into the `nodes` state array.
3. Edges are drawn by dragging from a source handle to a target handle. React Flow emits `onConnect`, creating an edge object with custom labels and conditions.

---

## 3. Graph Validation Engine

Before a workflow can be published or executed, the designer provides an in-app validation engine (`DesignerValidationModal.jsx`):

### Structural Rules Enforced:
1. **Single Start Node**: The graph must contain exactly one active `START` node.
2. **Terminal Reachability**: The graph must contain at least one reachable `END` node.
3. **No Disconnected Orphan Nodes**: Every node (except `START`) must have at least one incoming edge, and every non-terminal node must have at least one outgoing edge.
4. **Conditional Gateways**: Branches departing from condition nodes must have explicit condition expressions or default labels.
5. **Mandatory Configuration Checks**:
   - `APPROVAL` / `USER_TASK`: Requires an assigned `role_code`.
   - `CREATE_RECORD` / `UPDATE_RECORD`: Requires a selected target `table_name` and valid column mappings.
   - `COMMUNICATION`: Requires a valid recipient (`to`) and subject template.

---

## 4. Interactive In-Designer Test Runner (`DesignerTestRunnerModal.jsx`)

The designer includes an interactive test runner that allows process engineers to simulate execution before releasing a workflow to production:

### Simulation Capabilities:
- **Step-by-Step Traversal**: Step through nodes one by one with animated visual highlight borders on the active canvas node.
- **Variable Inspector**: View runtime context variables evolve after each step (e.g. observing outputs of a `READ_RECORD` step being utilized by a downstream `CONDITION` step).
- **Live SQL Query Preview & Trace**: Displays the actual parameterized SQL statements executed against the connected database.
- **Decision Testing**: Interactively click approval buttons (`APPROVE`, `REJECT`) to verify that the graph routes to the correct branch.

---

## 5. Graph Persistence & Serialization

When the user clicks **Save**:
1. The frontend serializes the React Flow graph:
   ```json
   {
     "nodes": [
       { "id": "node_1", "type": "start", "position": {"x": 100, "y": 200}, "data": { ... } }
     ],
     "edges": [
       { "id": "edge_1", "source": "node_1", "target": "node_2", "label": "Submit" }
     ],
     "workflow": {
       "workflow_id": 4,
       "name": "Leave Approval Flow",
       "connection_id": 1
     }
   }
   ```
2. Sends payload to `PUT /workflow/definitions/{id}` with `json_content` via `workflowStorage.saveWorkflow()`.
3. The backend stores the definition and serialized JSON canvas representation in `bpmn_definition.json_content`.

---

## 6. Related Documentation Links

- Frontend Overview: [Frontend Architecture](./frontend-architecture.md)
- Node Configuration: [Node Configuration Panels](./node-configuration.md)
- Compiler Reference: [BPMN Compiler](../03-workflow-engine/bpmn-compiler.md)
