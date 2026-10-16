# REST API Nodes

## 1. Overview & Capabilities

The **API Call Node** (`API_CALL`) enables workflows to orchestrate external microservices, REST APIs, and third-party webhooks directly during graph execution.

This allows organizations to integrate disparate enterprise systems—such as ERP platforms, CRM systems, payment gateways, or custom notifications—without writing custom Python backend service tasks.

```mermaid
sequenceDiagram
    autonumber
    participant Engine as StudioExecutionAdapter
    participant APINode as API_CALL Node Handler
    participant Context as Runtime Context Memory
    participant External as External REST Service

    Engine->>APINode: Execute Node (configuration, variables)
    APINode->>Context: Resolve Template Placeholders in URL, Headers, and Body
    APINode->>External: Dispatch HTTP Request (Method, Resolved Headers, Payload)
    
    alt HTTP 2xx Success Response
        External-->>APINode: 200 OK + JSON Body
        APINode->>Context: Inject Parsed JSON into {{response_variable}}
        APINode-->>Engine: Step Complete (Continue Graph)
    else HTTP 4xx / 5xx Error or Timeout
        External-->>APINode: Error Response / Connection Timeout
        APINode-->>Engine: Raise Step Failure Exception
        Note over Engine: Instance marked FAILED; error logged in activity history
    end
```

---

## 2. Configuration Schema

Configured via the visual designer properties panel:

| Field Name | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `url` | `string` | **Yes** | None | Target URL. Supports `{{variable}}` template interpolation. |
| `method` | `string` | **Yes** | `GET` | Supported: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`. |
| `headers` | `object` | No | `{}` | Key-value dictionary of HTTP request headers. |
| `body_template` | `string / JSON`| No | None | Payload template for `POST`, `PUT`, `PATCH` requests. |
| `response_variable` | `string` | No | `api_response`| Context variable key where response JSON will be stored. |
| `timeout_seconds` | `integer` | No | `15` | Maximum seconds to wait before raising a connection timeout. |

---

## 3. Dynamic Template Interpolation

The node handler scans the `url`, `headers`, and `body_template` for double curly-brace tokens (`{{variable_name}}`) and replaces them with active context values:

### Example Configuration:
```json
{
  "url": "https://erp.internal/api/v2/orders/{{order_id}}/status",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer {{env_erp_token}}"
  },
  "body_template": {
    "status": "APPROVED",
    "approver_id": "{{user_id}}",
    "approval_date": "NOW()"
  },
  "response_variable": "erp_sync_result"
}
```

### Runtime Context Injection:
If the external service returns:
```json
{
  "tracking_number": "TRK-987654",
  "estimated_delivery": "2026-10-20"
}
```
The workflow context is automatically augmented:
- `{{erp_sync_result.tracking_number}}` = `"TRK-987654"`
- `{{erp_sync_result.estimated_delivery}}` = `"2026-10-20"`
Subsequent nodes (e.g. an email communication node or database update node) can immediately reference these injected values.

---

## 4. Error Handling & Timeout Behavior

1. **Non-2xx HTTP Status Codes**:
   Any response with status &ge; `400` is treated as a step failure. The status code and response body text are recorded in `workflow_activity_history.error_message`.
2. **Network Timeouts**:
   If the remote server fails to respond within `timeout_seconds`, the request terminates with a timeout error.
3. **SSRF Considerations**:
   Calls originate from the backend application container. Production environments should enforce network egress rules or reverse proxy firewalls to prevent Server-Side Request Forgery against cloud metadata endpoints (`169.254.169.254`).

---

## 5. Related Documentation Links

- Node Inventory: [Activities & Node Inventory](../03-workflow-engine/activities-and-nodes.md)
- Runtime Engine: [Runtime Execution](../03-workflow-engine/runtime-execution.md)
- Security Review: [Security Review](../08-quality-and-maintenance/security-review.md)
