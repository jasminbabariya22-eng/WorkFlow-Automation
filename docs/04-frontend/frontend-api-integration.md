# Frontend API Integration

## 1. Integration Service Overview

All communication between the React 19 frontend and the backend FastAPI application is centralized in `frontend/src/services/workflowStorage.js`.

The service client provides type-safe abstractions for:
- Canvas graph saving, loading, validation, and publication.
- Client database profile management, connection testing, and live schema introspection.
- Execution monitoring, activity logs, variable inspection, and telemetry.
- Task retrieval, approvals, rejections, and manual simulation runs.

---

## 2. Request Handling & Authentication

### Token Injection Pattern
In `workflowStorage.js`, only monitoring instance queries (`getInstances` and `getInstanceDetails`) inspect `localStorage` for an active JWT token and attach the standard `Authorization` header:

```javascript
const token = localStorage.getItem('token');
const headers = { 'Content-Type': 'application/json' };
if (token) headers['Authorization'] = `Bearer ${token}`;
```

Other requests across the service—including workflow definitions, database connections, schema introspection, telemetry, and metrics—do not send an `Authorization` header.

### Timeout & Resiliency
Longer-running introspection and monitoring endpoints employ standard `AbortSignal.timeout(...)` (e.g., 5-second to 12-second timeouts) to ensure network latency or large telemetry transfers do not permanently hang UI components.

---

## 3. Key Service Methods

### A. Workflow Lifecycle
- `workflowStorage.getWorkflows()`: Calls `GET /workflow/definitions` to retrieve stored workflow definitions.
- `workflowStorage.getWorkflowById(id)`: Calls `GET /workflow/definitions/{id}` to load a definition with its `json_content` (nodes and edges) and BPMN XML.
- `workflowStorage.createWorkflow(draft)`: Calls `POST /workflow/definitions` to initialize a new workflow specification.
- `workflowStorage.saveWorkflow(id, updates)`: Calls `PUT /workflow/definitions/{id}` with serialized `json_content` and metadata.
- `workflowStorage.duplicateWorkflow(id)`: Calls `POST /workflow/definitions/{id}/duplicate`.
- `workflowStorage.publishWorkflow(id)`: Calls `POST /workflow/definitions/{id}/publish`.
- `workflowStorage.deleteWorkflow(id)`: Calls `DELETE /workflow/definitions/{id}`.

### B. Database Connections & Introspection
- `workflowStorage.getDbConnections()`: Calls `GET /workflow-studio/connections`.
- `workflowStorage.testDatabaseConnection(payload)`: Calls `POST /workflow-studio/connections/test` with connection credentials.
- `workflowStorage.getConnectionTables(connectionId, schema)`: Calls `GET /workflow-studio/connections/{connectionId}/tables`.
- `workflowStorage.getMetadataTableColumns(tableName, connectionId)`: Calls `GET /workflow-studio/metadata/tables/{tableName}/columns`.
- `workflowStorage.getMetadataRoles(connectionId)`: Calls `GET /workflow-studio/metadata/roles`.

### C. Monitoring & Telemetry
- `workflowStorage.getInstances()`: Calls `GET /workflow/monitoring/instances` (takes no arguments; passes bearer token).
- `workflowStorage.getInstanceDetails(instanceId)`: Executes parallel `Promise.allSettled()` fetching (with bearer token):
  - `GET /workflow/monitoring/instances/{instanceId}/variables`
  - `GET /workflow/monitoring/instances/{instanceId}/logs`
  - `GET /workflow/monitoring/instances/{instanceId}/history`
- `workflowStorage.getLiveTelemetry(params)`: Calls `GET /workflow/monitoring/telemetry` with optional query filters.
- `workflowStorage.getObservabilityMetrics()`: Calls `GET /workflow/monitoring/metrics`.
- `workflowStorage.clearTelemetryBuffer()`: Calls `POST /workflow/monitoring/telemetry/clear`.

---

## 4. WebSocket Client Management

Real-time updates are established using native browser `WebSocket`:

```javascript
export const createWorkflowWebSocket = (onMessage, onOpen, onError) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host; // Routed via Vite proxy or Nginx
  const wsUrl = `${protocol}//${host}/ws/workflow`;

  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    if (onOpen) onOpen();
    // Start heartbeat keepalive
    const pingTimer = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);
    ws._pingTimer = pingTimer;
  };

  ws.onmessage = (event) => {
    if (event.data === 'pong') return;
    try {
      const data = JSON.parse(event.data);
      if (onMessage) onMessage(data);
    } catch (e) {
      console.warn('Failed to parse WebSocket event:', e);
    }
  };

  ws.onclose = () => {
    if (ws._pingTimer) clearInterval(ws._pingTimer);
  };

  return ws;
};
```

---

## 5. Related Documentation Links

- Frontend Architecture: [Frontend Architecture](./frontend-architecture.md)
- Backend API Specification: [API Reference](../02-backend/api-reference.md)
- Real-time Events: [WebSocket Events](../06-integrations/websocket-events.md)
