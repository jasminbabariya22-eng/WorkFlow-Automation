# Technology Stack

This document inventories all technologies, libraries, frameworks, and runtimes used across the **WorkFlow-Automation** codebase. Every dependency listed below has been verified against the repository manifests (`backend/requirements.txt`, `frontend/package.json`, `docker-compose.yml`, and Dockerfiles).

---

## 1. Backend Application & Services

| Technology / Library | Verified Version | Purpose & Usage in Codebase | Source Manifest / Location |
| :--- | :--- | :--- | :--- |
| **Python** | `3.11` (Docker) / `3.9+` (Host) | Core runtime for backend execution and workers. | `backend/Dockerfile` |
| **FastAPI** | `0.110.0` | High-performance ASGI web framework providing routing, request validation, and OpenAPI generation. | `backend/requirements.txt` |
| **Uvicorn** | `0.27.1` (with standard extras) | Lightning-fast ASGI web server hosting the FastAPI application. | `backend/requirements.txt` |
| **SQLAlchemy** | `2.0.27` | Object-Relational Mapper (ORM) and SQL expression engine for workflow metadata and client queries. | `backend/requirements.txt` |
| **SpiffWorkflow** | `3.1.2` | Python workflow library for BPMN 2.0 execution and task state machines. | `backend/requirements.txt` |
| **Pydantic** | `2.6.1` | Data validation and schema enforcement for API requests and settings. | `backend/requirements.txt` |
| **Pydantic Settings** | `2.1.0` | Environment variable parsing and `.env` discovery (`BaseSettings`). | `backend/requirements.txt` |
| **python-jose** | `3.3.0` | JWT token decoding, encoding, and signature verification (HS256). | `backend/requirements.txt` |
| **Passlib & Bcrypt** | `1.7.4` / `4.1.2` | Password hashing and cryptographic verification utilities. | `backend/requirements.txt` |
| **Cryptography** | `>=42.0.0` | Fernet symmetric encryption for sensitive database credentials and X.509 SSL certificate generation. | `backend/requirements.txt` |
| **Email Validator** | `2.2.0` | RFC-compliant email address validation for communication nodes. | `backend/requirements.txt` |
| **Prometheus Client** | `>=0.20.0` | Python client for exporting telemetry metrics via `/workflow/monitoring/metrics`. | `backend/requirements.txt` |
| **Pandas & OpenPyXL** | `2.2.1` / `3.1.2` | Tabular data processing and Excel file manipulation for record export operations. | `backend/requirements.txt` |

### Database Client Drivers (Multi-RDBMS Connectivity)

| Driver | Verified Version | Supported Database Engine | Code Usage |
| :--- | :--- | :--- | :--- |
| **psycopg2-binary** | `2.9.9` | PostgreSQL (Primary Workflow DB & Client DB) | `DynamicEnginePool.build_connection_url` |
| **pymysql** | `1.2.0` | MySQL / MariaDB (Client DB) | `DynamicEnginePool.build_connection_url` |
| **pymssql** | `2.4.1` | Microsoft SQL Server (Client DB) | `DynamicEnginePool.build_connection_url` |
| **pyodbc** | `5.3.0` | Alternative ODBC driver for MSSQL / Legacy RDBMS | `DynamicEnginePool.build_connection_url` |
| **sqlite3** | Standard Library | SQLite (Embedded local testing & memory DBs) | `DynamicEnginePool.build_connection_url` |

---

## 2. Frontend Visual Studio

| Technology / Library | Verified Version | Purpose & Usage in Codebase | Source Manifest / Location |
| :--- | :--- | :--- | :--- |
| **Node.js** | `22-alpine` (Docker) / `18+` (Local) | JavaScript runtime for frontend development and bundling. | `frontend/Dockerfile` |
| **React** | `^19.2.8` | Core UI library for component-driven interfaces. | `frontend/package.json` |
| **React DOM** | `^19.2.8` | DOM rendering layer for React 19. | `frontend/package.json` |
| **@xyflow/react** | `^12.11.3` | Interactive visual workflow canvas, node dragging, custom handles, and edge routing. | `frontend/package.json` |
| **Vite** | `^8.2.0` | Next-generation frontend build tool and local dev server. | `frontend/package.json` |
| **Lucide React** | `^1.28.0` | Clean, modern icon set used throughout the Studio UI. | `frontend/package.json` |
| **bpmn-js** | `^18.22.1` | BPMN 2.0 diagram viewer and modeler utilities. | `frontend/package.json` |
| **camunda-bpmn-moddle**| `^7.0.1` | Moddle definitions for Camunda BPMN extensions (service tasks, execution listeners). | `frontend/package.json` |
| **Oxlint** | `^1.75.0` | Ultra-fast Rust-based JavaScript/React linter enforcing code quality. | `frontend/package.json` |
| **Nginx** | `alpine` | Production web server hosting static assets and terminating SSL/TLS. | `frontend/Dockerfile` |

---

## 3. DevOps, Infrastructure & Testing

| Technology | Verified Version | Role in Platform | Location in Repository |
| :--- | :--- | :--- | :--- |
| **Docker & Docker Compose**| Compose v2 (`services`) | Multi-container stack orchestration (backend, frontend, monitoring). | `docker-compose.yml` |
| **Prometheus** | `latest` (`prom/prometheus`) | Time-series metrics collection and health scraping. | `monitoring/prometheus/` |
| **Alertmanager** | `latest` (`prom/alertmanager`) | Alert rule routing and notification dispatching. | `monitoring/alertmanager/` |
| **Grafana** | `latest` (`grafana/grafana`) | Pre-configured visualization dashboards for workflow monitoring. | `monitoring/grafana/` |
| **Pytest** | `>=8.0.0` | Python test runner executing unit and integration tests. | `backend/tests/` |
| **Pytest-Cov** | `>=5.0.0` | Code coverage reporting plugin for Pytest. | `backend/requirements.txt` |
| **HTTPX** | `>=0.27.0, <0.28.0` | Asynchronous and synchronous HTTP client for integration testing. | `backend/requirements.txt` |
| **Trivy** | `v0.36.0` (Action) | Container vulnerability security scanner in CI pipeline. | `.github/workflows/ci.yml` |

---

## 4. Environment & Platform Configurations

| Component | Default Port | Protocol | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend UI (Dev)** | `5173` | HTTP / HTTPS | Vite development server (`npm run dev`) |
| **Frontend UI (Prod)** | `80`, `443`, `3000` | HTTP / HTTPS | Nginx production container hosting bundled React SPA |
| **Backend API** | `8000` | HTTP / HTTPS | FastAPI Uvicorn ASGI server hosting all API endpoints |
| **WebSocket Gateway**| `8000` (`/ws/workflow`) | WS / WSS | Real-time event subscription for workflow state changes |
| **Prometheus** | `9090` | HTTP | Metrics collection interface |
| **Alertmanager** | `9093` | HTTP | Alert rule evaluation interface |
| **Grafana** | `3001` (mapped to `3000`) | HTTP | Observability dashboard UI |

---

## 5. Related Documentation Links

- System Overview: [Project Overview](./project-overview.md)
- Architecture Model: [System Architecture](./system-architecture.md)
- Local Setup Guide: [Local Development Setup](../07-operations/local-development-setup.md)
- Container Orchestration: [Docker Deployment](../07-operations/docker-deployment.md)
