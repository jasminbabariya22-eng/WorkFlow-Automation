# Project Overview

## 1. Mission and Core Purpose

**WorkFlow-Automation** is an enterprise-grade, UI-driven workflow orchestration and execution platform. It is engineered to allow organizations to visually design, validate, publish, execute, and monitor complex business processes without requiring custom backend code modifications for each workflow.

In traditional enterprise applications, business process logic—such as approval hierarchies, state transitions, conditional notifications, and database mutations—is hardcoded into backend services. WorkFlow-Automation decouples process orchestration from application business logic by providing:
1. **Visual Graph Design**: Business workflows are constructed visually on a drag-and-drop canvas using React 19 and `@xyflow/react`.
2. **Dual-Database Execution**: The workflow platform maintains its own persistence layer for specifications, execution graphs, and audit history, while interacting directly with separate client application databases using parameterized SQL.
3. **Engine Dualism**: The platform incorporates a SpiffWorkflow BPMN 2.0 compiler and runtime engine alongside a lightweight direct graph execution adapter (`StudioExecutionAdapter`).
4. **Universal Integration Gateway**: A client application gateway allows external portals, microservices, and client systems to submit records, query tasks, and process approvals through REST and real-time WebSockets.

---

## 2. Key Capabilities

### Visual Workflow Studio
- Interactive node canvas with support for 12+ functional node types (triggers, tasks, approvals, database CRUD, conditional switches, email dispatches, and API calls).
- Live validation modal verifying connectivity, missing start/end nodes, invalid configurations, and orphan steps before publishing.
- In-designer test runner (`DesignerTestRunnerModal.jsx`) allowing step-by-step simulation with live variable inspection and simulated database traces.

### Generic Database Introspection & Execution
- Dynamic connection profiles (`db_connections` table) supporting PostgreSQL, MySQL, Microsoft SQL Server, SQLite, and Oracle.
- Live schema, table, and column introspection without hardcoding domain entities.
- Type-aware CRUD nodes:
  - `CREATE_RECORD`: Parameterized `INSERT INTO ...` with conflict resolution (`ON CONFLICT DO NOTHING / UPDATE`).
  - `READ_RECORD`: Parameterized `SELECT ... WHERE ...` binding query outputs into runtime context variables.
  - `UPDATE_RECORD`: Targeted `UPDATE ... SET ... WHERE id = :id` for entity state transitions upon approval.
  - `DELETE_RECORD`: Parameterized record deletion with filter safeguards.

### Human-in-the-Loop Orchestration
- Dynamic task assignment by role (`role_code`), department, or specific user ID.
- Configurable approval decision buttons (e.g., `APPROVE`, `REJECT`, `REQUEST_CHANGES`).
- Task state machine transitions (`READY`, `COMPLETED`, `REJECTED`) persisted in `workflow_human_task`.

### Real-Time Observability & Monitoring
- Centralized execution monitoring UI (`Monitoring.jsx`) tracking active instances, execution logs, and timing metrics.
- Variable sanitization preventing UI freezes when handling large base64 attachments or repetitive JSON structures.
- Daily date-partitioned file logging (`backend/logs/app_YYYY-MM-DD.log`) with automatic 30-day cleanup.
- In-memory telemetry ring buffer (`deque(maxlen=1000)`) surfaced via `/workflow/monitoring/telemetry`.
- Real-time event broadcasting over `/ws/workflow` via `WorkflowConnectionManager`.

---

## 3. Repository Directory Structure

```text
WorkFlow-Automation/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Automated testing, oxlint, Trivy scans
│       └── deploy.yml             # Self-hosted Windows runner CD deployment
├── backend/
│   ├── app/
│   │   ├── core/                  # Configuration, logging, database pooling, security, websockets
│   │   ├── workflow/              # SpiffWorkflow BPMN APIs, services, and persistence models
│   │   ├── workflow_activities/   # Custom SpiffWorkflow service tasks
│   │   ├── workflow_definition/   # Generic workflow definitions, versions, nodes, connections
│   │   ├── workflow_management/   # Definition lifecycle, duplication, export, and migration
│   │   └── workflow_studio/       # Studio canvas APIs, connections API, and runtime adapters
│   ├── certs/                     # Generated self-signed SSL certificates (fullchain.pem, privkey.pem)
│   ├── logs/                      # Partitioned daily log files and frontend log ingestion
│   ├── tests/                     # Pytest automated test suite
│   ├── Dockerfile                 # Python 3.11-slim production container
│   ├── requirements.txt           # Python dependency manifest
│   ├── generate_ssl_certs.py      # SAN-aware X.509 SSL certificate generator
│   └── validate_env_secrets.py    # Strict atomic environment and secret validator
├── frontend/
│   ├── public/                    # Static public assets
│   ├── src/
│   │   ├── assets/                # Design assets and logos
│   │   ├── components/            # Studio React components (Dashboard, Designer, Monitoring)
│   │   │   ├── common/            # Error boundaries and shared components
│   │   │   ├── designer/          # Toolbar, test runner modal, validation modal
│   │   │   ├── nodes/             # Custom React Flow node components
│   │   │   └── properties/        # Tabbed node configuration panels and query builders
│   │   ├── services/              # API clients: workflowStorage.js and frontendLogger.js
│   │   ├── App.jsx                # Main application view manager and routing
│   │   └── main.jsx               # React 19 entry point
│   ├── Dockerfile                 # Multi-stage Node 22 build & Alpine Nginx runner
│   ├── nginx.conf                 # Production reverse proxy configuration with SSL termination
│   ├── package.json               # Frontend dependencies and build scripts
│   └── vite.config.js             # Vite 8 bundling and dynamic backend proxy configuration
├── monitoring/
│   ├── alertmanager/              # Alertmanager alert rules and notification configuration
│   ├── grafana/                   # Pre-provisioned Grafana dashboards and data sources
│   └── prometheus/                # Prometheus scraper configuration and alert definitions
├── docker-compose.yml             # Full-stack container orchestration specification
├── docker_deploy.bat              # Windows script for one-click Docker stack launch
├── docker_rollback.bat            # Windows script for container revocation and rollback
├── run_workflow_server.bat        # Local dual-server launcher (HTTP)
└── run_workflow_server_ssl.bat    # Local dual-server launcher with HTTPS/SSL certificates
```

---

## 4. Current Implementation Status & Boundaries

To ensure architectural clarity, the current implementation status of all major subsystems is explicitly categorized below:

| Subsystem / Feature | Implementation Status | Implementation Notes |
| :--- | :--- | :--- |
| **Visual Workflow Designer** | **Production Ready** | Built with React 19 and `@xyflow/react`. Supports drag-and-drop, connection snapping, layout persistence, and properties inspection. |
| **Generic Database Operations** | **Production Ready** | Implemented in `ClientDatabaseAdapter` and `actions.py`. Parameterized SQL execution across PostgreSQL, MySQL, MSSQL, SQLite, and Oracle. |
| **Dynamic DB Connection Pooling** | **Production Ready** | Managed by `DynamicEnginePool` with thread-safe caching and password decryption via Fernet. |
| **Studio Direct Execution Adapter** | **Production Ready** | `StudioExecutionAdapter` executes published node graphs directly with atomic task blocking and resume capabilities. |
| **BPMN 2.0 XML Compiler** | **Implemented** | `WorkflowGraphCompiler` generates valid standard BPMN 2.0 XML with DI layout from React Flow node graphs. |
| **SpiffWorkflow Execution Engine** | **Partially Implemented** | `SpiffWorkflowEngine` wraps SpiffWorkflow 3.1.2. Basic script and user tasks run; complex sub-process boundary events and timers are currently delegated to the direct graph adapter. |
| **Client Gateway REST APIs** | **Production Ready** | Standardized `/client` and `/api/v1/workflow-hub` endpoints for workflow triggering, task completion, and queries. |
| **WebSocket Real-time Events** | **Production Ready** | Active at `/ws/workflow` broadcasting lifecycle events across thread boundaries. |
| **Email Dispatcher** | **Production Ready** | `EmailDispatcher` dynamically discovers SMTP settings from client database tables and dispatches via standard `smtplib`. |
| **Observability & Dashboards** | **Production Ready** | Prometheus metrics endpoint (`/workflow/monitoring/metrics`), Grafana provisioning, and in-app telemetry buffer. |
| **Authentication & RBAC** | **Hybrid / Dev Fallback** | Token validation via `python-jose` (HS256) is implemented, but `get_current_user` falls back to a default mock admin user when no header is present to facilitate local Studio testing. |

---

## 5. Related Documentation Links

- Architecture Overview: [System Architecture](./system-architecture.md)
- Technology Inventory: [Technology Stack](./technology-stack.md)
- Backend Deep Dive: [Backend Architecture](../02-backend/backend-architecture.md)
- Complete API Listing: [API Reference](../02-backend/api-reference.md)
- Operations & Setup: [Local Development Setup](../07-operations/local-development-setup.md)
