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
│  ├── 1. Lineage, Stale-Commit & CI Verification Gates  │
│  ├── 2. Atomic Production .env Secrets Validation      │
│  ├── 3. Generate & Validate SSL Certificates (SAN)     │
│  ├── 4. Image Rollback Tagging & In-Place Build        │
│  ├── 5. Seamless Container Launch (`compose up -d`)   │
│  └── 6. Multi-Service Health Checks (BE, FE HTTP/S)   │
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

The deployment pipeline automatically generates the production `.env` file on the deployment host from encrypted GitHub repository secrets using the standalone validator `backend/validate_env_secrets.py`.

Configure these secrets in GitHub:
**Repository Settings** $\to$ **Secrets and variables** $\to$ **Actions** $\to$ **Repository secrets**

| Secret Name | Description | Example / Target |
| :--- | :--- | :--- |
| `WORKFLOW_DATABASE_URL` | PostgreSQL connection string pointing to the external database server. | `postgresql+psycopg2://postgres:<PASS>@192.168.1.171:5432/workflow_erm` |
| `SECRET_KEY` | 256-bit cryptographic secret for signing JWT auth tokens (min 32 chars). | `0eeedb8821a0a275fc8afb81...` |
| `FERNET_KEY` | Base64-encoded 32-byte Fernet key for encrypting database credentials. | `ia3rsWe2JkwStfuoRIOd...=` |
| `MAIN_URL` | The public/LAN endpoint used for CORS and SSL SAN generation. | `https://192.168.1.183` |
| `GRAFANA_ADMIN_PASSWORD` | Administrator password for Grafana observability dashboard (min 8 chars). | Secure alphanumeric password |

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

1. **Triggering & Safety Gates**:
   - **Automatic**: Triggered upon completion of the `Continuous Integration` workflow on `main`. Requires `workflow_run.conclusion == 'success'`.
   - **Manual Dispatch (`workflow_dispatch`)**: Allows deploying a specific commit or `main`. It verifies:
     - The target commit is present on `origin/main`.
     - The target commit has an explicit successful `Continuous Integration` run verified via GitHub API.
     - Rejects unverified, failed, or out-of-tree commits.
   - **Anti-Stale Protection**: Rejects automatic deployment if a newer commit has reached `main` while CI was running.
2. **Atomic Environment Validation**:
   - Executes `backend/validate_env_secrets.py --write` to validate all incoming secrets.
   - Rejects missing, empty, or placeholder values.
   - Atomically generates `.env` and `backend/.env` without risk of corrupting existing files on failure.
3. **SSL Certificate Generation & SAN Validation**:
   - Runs `backend/generate_ssl_certs.py` to create `certs/privkey.pem` and `certs/fullchain.pem`.
   - Validates that certificate public key matches private key, certificate is within validity dates, and the certificate SAN includes the hostname from `MAIN_URL`.
4. **Local Docker Image Build & Safety Tagging**:
   - Preserves previous container image IDs as `workflow-backend:previous` and `workflow-frontend:previous` before build.
   - Runs `docker compose build` directly on the server (no remote registry required).
   - Verifies zero exit code before proceeding.
5. **Stack Update**:
   - Runs `docker compose up -d --remove-orphans` to recreate modified containers.
   - Preserves named volumes (`workflow_backend_logs`, `workflow_backend_data`, `workflow_prometheus_data`, `workflow_grafana_data`).
   - Never runs destructive volume removal (`docker compose down -v`).
6. **Multi-Service Health Check Verification**:
   - Polls backend `http://localhost:8000/health` until status is `healthy`.
   - Polls frontend Nginx `http://localhost:80/` (HTTP).
   - Polls frontend Nginx `https://localhost:443/` (HTTPS).
   - Verifies container states are `running`.
   - Only reports deployment success when all services pass health validation.

---

## 5. Rollback and Recovery Procedure

If a deployment fails:
1. **Automated Diagnostics**:
   The workflow immediately dumps container states and the last 60 lines of backend and frontend logs:
   ```powershell
   docker compose ps -a
   docker compose logs --tail=60 backend
   docker compose logs --tail=60 frontend
   ```
2. **Previous Image Rollback**:
   Prior to updating containers, existing images are tagged with `:previous`. If a deployment fails health checks, rollback can be executed immediately on the host without data loss:
   ```powershell
   # Re-tag previous images as active
   docker tag workflow-backend:previous jasminbabariya22/workflow-backend:latest
   docker tag workflow-frontend:previous jasminbabariya22/workflow-frontend:latest
   docker compose up -d --remove-orphans
   ```
3. **Database Safety**:
   - Persistent volume data (`backend_data`, `backend_logs`) is untouched.
   - External PostgreSQL (`192.168.1.171:5432`) is untouched and maintains full transaction integrity.
