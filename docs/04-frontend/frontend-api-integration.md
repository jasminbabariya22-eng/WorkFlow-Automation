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
Every outgoing HTTP request constructed in `workflowStorage.js` automatically inspects `localStorage` for an active JWT token and attaches the standard `Authorization` header:

```javascript
const getAuthHeaders = () => {
  const headers = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};
```

### Timeout & Resiliency
Longer-running introspection and monitoring endpoints employ standard `AbortSignal.timeout(10000)` (10-second timeout) to ensure network latency or large telemetry transfers do not permanently hang UI components.

---

## 3. Key Service Methods

### A. Workflow & Canvas Lifecycle
- `workflowStorage.getWorkflows()`: Calls `GET /workflow-studio/canvas/workflows`.
- `workflowStorage.getCanvasWorkflow(id)`: Calls `GET /workflow-studio/canvas/workflows/{id}` to load nodes and edges for the Designer canvas.
- `workflowStorage.saveCanvasWorkflow(id, payload)`: Calls `PUT /workflow-studio/canvas/workflows/{id}` to commit node positions and configurations.
- `workflowStorage.validateCanvasWorkflow(id)`: Calls `POST /workflow-studio/canvas/workflows/{id}/validate`.
- `workflowStorage.publishCanvasWorkflow(id)`: Calls `POST /workflow-studio/canvas/workflows/{id}/publish`.

### B. Database Connections & Introspection
- `workflowStorage.getDbConnections()`: Calls `GET /workflow-studio/connections`.
- `workflowStorage.testDbConnection(config)`: Calls `POST /workflow-studio/connections/test` with connection parameters.
- `workflowStorage.getTables(connId)`: Calls `GET /workflow-studio/connections/{connId}/tables`.
- `workflowStorage.getColumns(connId, tableName)`: Calls `GET /workflow-studio/connections/{connId}/tables/{tableName}/columns`.
- `workflowStorage.getMasterRoles(connId)`: Calls `GET /workflow-studio/connections/{connId}/roles`.

### C. Monitoring & Telemetry
- `workflowStorage.getInstances(limit, offset)`: Calls `GET /workflow/monitoring/instances`.
- `workflowStorage.getInstanceDetails(instanceId)`: Executes parallel `Promise.allSettled()` fetching:
  - `GET /workflow/monitoring/instances/{instanceId}/variables`
  - `GET /workflow/monitoring/instances/{instanceId}/logs`
  - `GET /workflow/monitoring/instances/{instanceId}/history`
- `workflowStorage.getTelemetry()`: Calls `GET /workflow/monitoring/telemetry`.

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
