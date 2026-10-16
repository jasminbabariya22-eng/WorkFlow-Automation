# System Context & Container Diagram

This document presents the high-level system context and container boundaries of the **WorkFlow-Automation** platform using Mermaid C4-style diagramming.

---

## 1. System Context Diagram (Level 1)

```mermaid
C4Context
    title System Context Diagram for WorkFlow-Automation Platform

    Person(designer, "Process Designer / Admin", "Designs, configures, tests, and publishes business workflows.")
    Person(business_user, "Business User / Employee", "Submits business requests (e.g. Leave, PO) and performs approvals.")
    
    System(workflow_platform, "WorkFlow-Automation Platform", "Orchestrates visual workflows, manages task state machines, executes database actions, and dispatches notifications.")

    System_Ext(client_db, "Client Database", "External RDBMS (PostgreSQL, MySQL, MSSQL) storing organization business records.")
    System_Ext(smtp_server, "SMTP Mail Server", "Delivers automated notification emails to users.")
    System_Ext(ext_api, "External REST Microservices", "Third-party enterprise APIs called via API_CALL workflow nodes.")

    Rel(designer, workflow_platform, "Designs, validates, and monitors workflows via", "HTTPS / WebSocket")
    Rel(business_user, workflow_platform, "Submits records and processes approvals via", "REST API / Portal UI")
    
    Rel(workflow_platform, client_db, "Reads schema & executes parameterized SQL via", "TCP / JDBC / Native Driver")
    Rel(workflow_platform, smtp_server, "Sends transactional emails via", "SMTP / STARTTLS")
    Rel(workflow_platform, ext_api, "Orchestrates webhooks & REST actions via", "HTTPS / REST")
```

---

## 2. Container Diagram (Level 2)

```mermaid
C4Container
    title Container Diagram for WorkFlow-Automation Platform

    Person(user, "Platform User / Client App", "Interacts via browser or API")

    Container_Boundary(c1, "WorkFlow-Automation System") {
        Container(frontend_spa, "Workflow Studio Frontend", "React 19, @xyflow/react, Vite, Nginx", "Provides visual drag-and-drop designer, node properties, and real-time monitoring.")
        Container(backend_api, "Workflow Engine Backend", "FastAPI, Python 3.11, Uvicorn", "Provides REST APIs, SpiffWorkflow & StudioExecutionAdapter runtimes, and WebSocket streaming.")
        ContainerDb(workflow_db, "Workflow Database", "PostgreSQL / SQLite", "Persists workflow definitions, versions, instances, human tasks, and immutable audit logs.")
        Container(prometheus, "Prometheus", "Prometheus Engine", "Scrapes and evaluates time-series metrics from /workflow/monitoring/metrics.")
        Container(grafana, "Grafana", "Grafana Dashboards", "Visualizes platform throughput, queue depth, and task SLAs.")
    }

    ContainerDb_Ext(client_db, "Client Application Database", "PostgreSQL, MySQL, MSSQL", "Stores enterprise business entities, master users, roles, and departments.")
    System_Ext(smtp_server, "External SMTP Server", "Standard SMTP", "Routes outgoing emails.")

    Rel(user, frontend_spa, "Accesses UI via", "HTTPS (Port 443 / 80)")
    Rel(user, backend_api, "Calls Client Gateway APIs via", "HTTPS (Port 8000)")
    
    Rel(frontend_spa, backend_api, "Proxies REST calls & WebSockets via", "HTTP / WS (Port 8000)")
    Rel(backend_api, workflow_db, "Reads/writes specifications and state via", "SQLAlchemy (SessionLocal)")
    Rel(backend_api, client_db, "Executes dynamic parameterized CRUD via", "DynamicEnginePool")
    Rel(backend_api, smtp_server, "Dispatches emails via", "smtplib (Port 587 / 465)")
    
    Rel(prometheus, backend_api, "Scrapes metrics via", "HTTP GET :8000/workflow/monitoring/metrics")
    Rel(grafana, prometheus, "Queries metrics via", "HTTP (Port 9090)")
```

---

## 3. Related Documentation Links

- High-Level Architecture: [System Architecture](../01-overview/system-architecture.md)
- Execution Sequence: [Workflow Execution Sequence](./workflow-execution-sequence.md)
- Deployment Topology: [Deployment Architecture](./deployment-architecture.md)
