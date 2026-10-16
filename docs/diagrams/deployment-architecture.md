# Deployment Architecture Diagram

This document illustrates the physical and container deployment topology supported by the repository's configuration artifacts (`docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, and `deploy.yml`).

---

## 1. Production Container Topology

```mermaid
flowchart TB
    subgraph ClientNetwork["Client Network / Internet"]
        Browser["User Browser / Client Apps\n(HTTPS: Port 443 / HTTP: Port 80)"]
        DirectAPI["Direct API Clients / Prometheus Scrapers\n(Port 8000, 3001, 9090)"]
    end

    subgraph HostServer["Production Host Server (Self-Hosted Runner / Windows / Linux)"]
        subgraph Ports["Exposed Ingress Ports"]
            P80["80 (HTTP)"]
            P443["443 (HTTPS)"]
            P8000["8000 (FastAPI API)"]
            P3001["3001 (Grafana)"]
            P9090["9090 (Prometheus)"]
        end

        subgraph DockerEngine["Docker Engine (docker-compose)"]
            subgraph BridgeNet["Docker Network: workflow-net (Bridge)"]
                Frontend["workflow-frontend\n(Nginx 1.25 Alpine)\nStatic Assets + SSL Termination"]
                Backend["workflow-backend\n(FastAPI / Python 3.11-slim)\nUvicorn ASGI Server"]
                Prometheus["workflow-prometheus\n(prom/prometheus:latest)\nMetrics Engine"]
                Alertmgr["workflow-alertmanager\n(prom/alertmanager:latest)\nAlert Dispatcher"]
                Grafana["workflow-grafana\n(grafana/grafana:latest)\nVisual Dashboards"]
            end

            subgraph Volumes["Named Docker Volumes & Mounts"]
                CertMount["./backend/certs (Host SSL Dir)\n-> /etc/nginx/ssl:ro"]
                VolLogs[("workflow_backend_logs\n-> /app/logs")]
                VolData[("workflow_backend_data\n-> /app/data")]
                VolProm[("workflow_prometheus_data\n-> /prometheus")]
                VolGraf[("workflow_grafana_data\n-> /var/lib/grafana")]
            end
        end

        subgraph ExternalDatabases["External Database Infrastructure"]
            WfPostgres[("Workflow PostgreSQL DB\n(Configured via WORKFLOW_DATABASE_URL)")]
            ClientDB[("Client Enterprise DBs\n(PostgreSQL / MySQL / MSSQL)")]
        end
    end

    Browser --> P80 & P443
    DirectAPI --> P8000 & P3001 & P9090

    P80 --> Frontend
    P443 --> Frontend
    P8000 --> Backend
    P3001 --> Grafana
    P9090 --> Prometheus

    Frontend -->|Reverse Proxy /api, /workflow, /ws| Backend
    Frontend --- CertMount

    Backend --- VolLogs
    Backend --- VolData
    Backend <-->|SQLAlchemy TCP| WfPostgres
    Backend <-->|DynamicEnginePool TCP| ClientDB

    Prometheus -->|Scrape :8000/workflow/monitoring/metrics| Backend
    Prometheus --> Alertmgr
    Prometheus --- VolProm

    Grafana -->|Query Datasource:9090| Prometheus
    Grafana --- VolGraf
```

---

## 2. Port Mapping & Ingress Summary

| Container Name | Internal Port | Host Port | Protocol | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`workflow-frontend`** | `80` | `80`, `3000` | HTTP | Nginx HTTP web server (redirects to HTTPS or serves SPA). |
| **`workflow-frontend`** | `443` | `443` | HTTPS | Nginx SSL/TLS termination with mounted certificates. |
| **`workflow-backend`** | `8000` | `8000` | HTTP / HTTPS | FastAPI Uvicorn application server and WebSocket gateway. |
| **`workflow-prometheus`**| `9090` | `9090` | HTTP | Prometheus time-series metrics interface. |
| **`workflow-alertmanager`**| `9093` | `9093` | HTTP | Alertmanager rule evaluation dashboard. |
| **`workflow-grafana`** | `3000` | `3001` | HTTP | Grafana analytics portal. |

---

## 3. Related Documentation Links

- Docker Deployment Guide: [Docker Deployment](../07-operations/docker-deployment.md)
- CI/CD Deployment: [CI/CD Pipeline](../07-operations/ci-cd-pipeline.md)
- System Context: [System Context Diagram](./system-context.md)
