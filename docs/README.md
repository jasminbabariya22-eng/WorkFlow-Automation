# WorkFlow-Automation Documentation Index

Welcome to the comprehensive, developer-oriented documentation for the **WorkFlow-Automation** platform. This documentation suite provides an architectural and operational guide to the repository, explaining its generic BPMN 2.0 / graph workflow engine, React 19 visual designer, dual-database architecture, external client gateway, and automated CI/CD deployment stack.

---

## Documentation Sections

### [01. Architecture & Overview](./01-overview/)
Foundational concepts, system architecture diagrams, component responsibilities, and verified technology stack.
- [Project Overview](./01-overview/project-overview.md) — Mission, capabilities, limitations, and directory layout.
- [System Architecture](./01-overview/system-architecture.md) — High-level system architecture, dual-database split, and execution flows.
- [Technology Stack](./01-overview/technology-stack.md) — Manifest-verified dependencies, libraries, and runtime runtimes.

### [02. Backend Platform](./02-backend/)
Deep dive into the FastAPI application, module organization, request lifecycle, authentication, security, and logging.
- [Backend Architecture](./02-backend/backend-architecture.md) — Entry point (`app/main.py`), routers, middleware, and dependency injection.
- [API Reference](./02-backend/api-reference.md) — Inventory of 156+ registered endpoints across 15 router modules.
- [Authentication & Security](./02-backend/authentication-security.md) — JWT token decoding, HTTPBearer authentication, Fernet symmetric encryption, and dev fallbacks.
- [Error Handling & Logging](./02-backend/error-handling-logging.md) — Custom exception handlers, daily date-partitioned log rotation, and telemetry ring buffers.

### [03. Workflow Engine & Runtime](./03-workflow-engine/)
The core workflow execution layer, SpiffWorkflow integration, visual graph-to-BPMN compilation, and task state machines.
- [Engine Architecture](./03-workflow-engine/engine-architecture.md) — SpiffWorkflow execution abstraction, `StudioExecutionAdapter`, and action registry.
- [Workflow Lifecycle](./03-workflow-engine/workflow-lifecycle.md) — States: `DRAFT`, `VALIDATED`, `PUBLISHED`, `RUNNING`, `WAITING`, `COMPLETED`, `REJECTED`.
- [BPMN Compiler](./03-workflow-engine/bpmn-compiler.md) — Visual graph JSON to standard BPMN 2.0 XML compilation via `WorkflowGraphCompiler`.
- [Runtime Execution](./03-workflow-engine/runtime-execution.md) — Asynchronous job execution, worker thread pool (`WorkflowJobExecutor`), and state progression.
- [Activities & Node Inventory](./03-workflow-engine/activities-and-nodes.md) — Complete specifications for `START`, `APPROVAL`, `USER_TASK`, `CREATE_RECORD`, `READ_RECORD`, `UPDATE_RECORD`, `DELETE_RECORD`, `API_CALL`, `CONDITION`, `SWITCH`, `COMMUNICATION`, and `END`.
- [Human Tasks & Approvals](./03-workflow-engine/human-tasks-and-approvals.md) — Task indexing, role resolution, approval/rejection handling, and execution resumption.
- [Workflow Versioning](./03-workflow-engine/workflow-versioning.md) — Version increments, draft versus published immutability, and runtime version resolution.

### [04. Frontend Studio](./04-frontend/)
Interactive React 19 application built with `@xyflow/react` and Lucide icons.
- [Frontend Architecture](./04-frontend/frontend-architecture.md) — React 19 Vite setup, views, modals, error boundaries, and state management.
- [Workflow Designer](./04-frontend/workflow-designer.md) — Canvas mechanics, custom node rendering, edge connections, test simulation, and validation modals.
- [Node Configuration Panels](./04-frontend/node-configuration.md) — Properties panel components, query builders, email templates, and conditional rules.
- [Execution & Monitoring UI](./04-frontend/execution-and-monitoring-ui.md) — Telemetry dashboard, instance inspection, activity logs, variable sanitization, and manual task execution.
- [Frontend API Integration](./04-frontend/frontend-api-integration.md) — `workflowStorage.js` service methods, environment overrides, and WebSocket real-time updates.

### [05. Database Architecture & Persistence](./05-database/)
Dual-database persistence model, schema introspection, dynamic connection pooling, and transactional boundaries.
- [Database Architecture](./05-database/database-architecture.md) — Workflow internal schema vs. external client business databases.
- [Workflow Schema](./05-database/workflow-schema.md) — SQLAlchemy models: `wf_definition`, `wf_version`, `wf_node`, `wf_connection`, `db_connections`, `spiff_workflow_instance`, `workflow_human_task`, `workflow_history`.
- [Client Database Integration](./05-database/client-database-integration.md) — Dynamic connection pool (`DynamicEnginePool`), schema introspection, and multi-engine support (PostgreSQL, MySQL, MSSQL, SQLite, Oracle).
- [Persistence & Transactions](./05-database/persistence-and-transactions.md) — Session management, atomicity boundaries, state serialization, and audit trail guarantees.

### [06. External Integrations & Gateways](./06-integrations/)
Decoupled integration surfaces for client portals, webhooks, and third-party systems.
- [Client Application Gateway](./06-integrations/client-application-gateway.md) — `/client` and `/api/v1/workflow-hub` REST endpoints for external systems.
- [REST API Nodes](./06-integrations/rest-api-nodes.md) — External HTTP request execution (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) with template interpolation and response variable capture.
- [Email & Notification Services](./06-integrations/email-and-notifications.md) — Database-driven SMTP discovery (`EmailDispatcher`), HTML templating, and background delivery.
- [WebSocket Events](./06-integrations/websocket-events.md) — `/ws/workflow` gateway, connection lifecycle, and broadcast event taxonomy (`JOB_*`, `WORKFLOW_*`, `TASK_*`).

### [07. Operations, CI/CD & Deployment](./07-operations/)
Operational runbooks, local environment bootstrapping, containerization, CI/CD pipelines, and health monitoring.
- [Local Development Setup](./07-operations/local-development-setup.md) — Step-by-step setup for Python virtual environment, Node dependencies, environment files, and local servers.
- [Docker Deployment](./07-operations/docker-deployment.md) — Multi-container Docker Compose deployment (backend, frontend Nginx, Prometheus, Alertmanager, Grafana).
- [CI/CD Pipeline](./07-operations/ci-cd-pipeline.md) — GitHub Actions workflows: `ci.yml` (automated tests, linting, Trivy image scan) and `deploy.yml` (self-hosted runner deployment with atomic secret validation and rollback tagging).
- [Monitoring & Alerting](./07-operations/monitoring-and-alerting.md) — Prometheus metrics collection, Grafana dashboards, and application health checks.
- [Troubleshooting Runbook](./07-operations/troubleshooting.md) — Diagnostic guides for common startup errors, database connectivity issues, node execution errors, and SSL handshake failures.

### [08. Quality, Security & Governance](./08-quality-and-maintenance/)
Codebase governance, test coverage, security audits, and contribution guidelines.
- [Testing Strategy](./08-quality-and-maintenance/testing-strategy.md) — Pytest test suite, mock fixtures, test databases, in-browser simulation, and coverage reports.
- [Security Review](./08-quality-and-maintenance/security-review.md) — Code-informed security analysis covering authentication fallbacks, SQL parameterization, secret validation, Fernet encryption, and SSRF mitigations.
- [Contribution Guide](./08-quality-and-maintenance/contribution-guide.md) — Development workflow, pull request expectations, coding conventions, and pre-commit verification checklists.

### [09. Architectural Diagrams](./diagrams/)
Mermaid diagram references detailing system topography and execution traces.
- [System Context Diagram](./diagrams/system-context.md) — C4 Level 1/2 system context and container boundaries.
- [Workflow Execution Sequence](./diagrams/workflow-execution-sequence.md) — Detailed sequence trace from client trigger to node execution, DB update, and task blocking.
- [Deployment Architecture](./diagrams/deployment-architecture.md) — Production container topology, reverse proxy routing, and network segmentation.

---

## Target Audience & Reading Guide

| Role / Responsibility | Recommended Starting Documents |
| :--- | :--- |
| **New Platform Developer** | [Project Overview](./01-overview/project-overview.md) &rarr; [Local Development Setup](./07-operations/local-development-setup.md) &rarr; [System Architecture](./01-overview/system-architecture.md) |
| **Workflow Engine Developer** | [Engine Architecture](./03-workflow-engine/engine-architecture.md) &rarr; [Activities & Node Inventory](./03-workflow-engine/activities-and-nodes.md) &rarr; [Runtime Execution](./03-workflow-engine/runtime-execution.md) |
| **Frontend / UI Engineer** | [Frontend Architecture](./04-frontend/frontend-architecture.md) &rarr; [Workflow Designer](./04-frontend/workflow-designer.md) &rarr; [Frontend API Integration](./04-frontend/frontend-api-integration.md) |
| **Client App Integrator** | [Client Application Gateway](./06-integrations/client-application-gateway.md) &rarr; [API Reference](./02-backend/api-reference.md) &rarr; [WebSocket Events](./06-integrations/websocket-events.md) |
| **DevOps / SRE** | [Docker Deployment](./07-operations/docker-deployment.md) &rarr; [CI/CD Pipeline](./07-operations/ci-cd-pipeline.md) &rarr; [Monitoring & Alerting](./07-operations/monitoring-and-alerting.md) |
| **Security Engineer** | [Security Review](./08-quality-and-maintenance/security-review.md) &rarr; [Authentication & Security](./02-backend/authentication-security.md) |
