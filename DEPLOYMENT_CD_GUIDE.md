# WorkFlow-Automation — Continuous Deployment (CD) Guide

This guide details the Continuous Deployment (CD) pipeline for **WorkFlow-Automation** executing on a self-hosted Windows runner (`LABSERVER183` / `192.168.1.183`) using Docker Desktop and GitHub Actions.

---

## 1. Architectural Overview

```
[ Push to main ]
       │
       ▼
┌────────────────────────────────────────────────────────┐
│  Continuous Integration Quality Gate (ci.yml)         │
│  ├── Backend CI (Pytest 14/14 tests + Coverage)       │
│  ├── Frontend CI (Node 22 + Lint + Vite build)         │
│  └── Dockerfile Syntax & Compose Validation            │
└────────────────────────────────────────────────────────┘
       │  (Only if CI workflow succeeds)
       ▼
┌────────────────────────────────────────────────────────┐
│  Continuous Deployment Pipeline (deploy.yml)          │
│  Runs on: [self-hosted, Windows] (LABSERVER183)        │
│                                                        │
│  ├── 1. Check Docker Engine / Desktop Status           │
│  ├── 2. Provision Production .env from GitHub Secrets  │
│  ├── 3. Generate & Validate SSL Certificates (SAN)     │
│  ├── 4. In-Place Docker Image Build (`compose build`)  │
│  ├── 5. Seamless Container Launch (`compose up -d`)   │
│  └── 6. Dual Health Checks (Backend API + Frontend)   │
└────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────┐
│  Production Stack on Host (192.168.1.183)             │
│  ├── React/Vite Studio UI:  https://192.168.1.183      │
│  ├── FastAPI Backend:       http://192.168.1.183:8000  │
│  ├── External PostgreSQL:   192.168.1.171:5432         │
│  ├── Prometheus Monitoring: http://192.168.1.183:9090  │
│  └── Grafana Dashboards:    http://192.168.1.183:3001  │
└────────────────────────────────────────────────────────┘
```

---

## 2. GitHub Repository Secrets Configuration

The deployment pipeline automatically generates the production `.env` file on the deployment host from encrypted GitHub repository secrets.

Configure these secrets in GitHub:
**Repository Settings** $\to$ **Secrets and variables** $\to$ **Actions** $\to$ **Repository secrets**

| Secret Name | Description | Example / Target |
| :--- | :--- | :--- |
| `WORKFLOW_DATABASE_URL` | PostgreSQL connection string pointing to the external database server. | `postgresql+psycopg2://postgres:<PASS>@192.168.1.171:5432/workflow_erm` |
| `SECRET_KEY` | 256-bit cryptographic secret for signing JWT auth tokens. | `0eeedb8821a0a275fc8afb81...` |
| `FERNET_KEY` | Base64-encoded 32-byte Fernet key for encrypting database credentials. | `ia3rsWe2JkwStfuoRIOd...=` |
| `MAIN_URL` | The public/LAN endpoint used for CORS and SSL SAN generation. | `https://192.168.1.183` |
| `GRAFANA_ADMIN_PASSWORD` | Administrator password for Grafana observability dashboard. | Secure alphanumeric password |

---

## 3. Self-Hosted Windows Runner Setup (`LABSERVER183`)

The deployment workflow requires a self-hosted Windows runner registered with labels `['self-hosted', 'Windows', 'X64']`.

### Prerequisites on the Host Machine (`192.168.1.183`):
1. **Docker Desktop for Windows**: Installed and running with WSL2 backend.
2. **Python 3.10+**: Available in `PATH` with `cryptography` and `python-dotenv`.
3. **Network Access**: Port `5432` reachable to external PostgreSQL server (`192.168.1.171`).

### Running the Runner:
```powershell
# Open elevated PowerShell in the runner directory
cd C:\Windows\system32\actions-runner

# Start the runner listener
.\run.cmd
```

When connected, the runner listens for incoming GitHub Actions deployment jobs:
```text
√ Connected to GitHub
Current runner version: '2.337.0'
Listening for Jobs
```

---

## 4. Deployment Workflow Pipeline (`deploy.yml`)

The production deployment runs via [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml):

1. **Triggering**:
   - Automatically triggered upon successful completion of the `CI/CD DevSecOps Quality Gate` on `main`.
   - Manually triggerable via `workflow_dispatch` from the GitHub Actions dashboard.
2. **Environment Setup**:
   - Injects production secrets into `.env` and `backend/.env`.
   - Enforces presence of `GRAFANA_ADMIN_PASSWORD`.
3. **SSL Certificate Generation & SAN Validation**:
   - Runs `backend/generate_ssl_certs.py` to create `certs/privkey.pem` and `certs/fullchain.pem`.
   - Validates that the certificate SAN includes the hostname from `MAIN_URL`.
4. **Local Docker Image Build**:
   - Runs `docker compose build` directly on the server (no remote registry required).
   - Verifies zero exit code before proceeding.
5. **Zero-Downtime Stack Update**:
   - Runs `docker compose up -d --remove-orphans` to recreate modified containers.
   - Preserves named volumes (`workflow_backend_logs`, `workflow_backend_data`, `workflow_prometheus_data`, `workflow_grafana_data`).
6. **Dual Health Check Verification**:
   - Polls backend `http://localhost:8000/health` until status is `healthy`.
   - Polls frontend Nginx `http://localhost:80/` (or Compose container health).
   - Only reports deployment success when both services respond successfully.

---

## 5. Troubleshooting & Diagnostics

- **Container Logs**:
  If a deployment fails, the workflow automatically runs diagnostic logging:
  ```powershell
  docker compose ps -a
  docker compose logs --tail=60 backend
  docker compose logs --tail=60 frontend
  ```
- **Manual Container Verification**:
  ```powershell
  # Check running containers
  docker compose ps

  # Test backend health
  Invoke-RestMethod http://localhost:8000/health

  # Test frontend health
  Invoke-WebRequest http://localhost:80/ -UseBasicParsing
  ```
- **Volume Inspection**:
  Persistent data is retained across builds in `workflow_backend_data` and logs in `workflow_backend_logs`.
