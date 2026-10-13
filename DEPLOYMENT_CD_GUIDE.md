# WorkFlow-Automation — Continuous Deployment (CD) Guide

This guide details the Phase 2 Continuous Deployment pipeline for deploying **WorkFlow-Automation** to a Linux VPS via GitHub Actions, Docker Hub, SSH, and Docker Compose.

---

## 1. Architectural Overview

```
[ Push to main ]
       │
       ▼
┌────────────────────────────────────────────────────────┐
│  Continuous Integration Quality Gates                  │
│  ├── Backend CI (Pytest + Coverage + pip-audit)       │
│  ├── Frontend CI (Node 22 + Lint + Vite build + Audit) │
│  └── Docker Build Validation (Backend/Frontend + Trivy)│
└────────────────────────────────────────────────────────┘
       │  (Only if ALL CI jobs pass)
       ▼
┌────────────────────────────────────────────────────────┐
│  Publish Production Images to Docker Hub               │
│  ├── Tag: <dockerhub_username>/workflow-backend:<sha>  │
│  ├── Tag: <dockerhub_username>/workflow-backend:latest │
│  ├── Tag: <dockerhub_username>/workflow-frontend:<sha> │
│  └── Tag: <dockerhub_username>/workflow-frontend:latest│
└────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────┐
│  Deploy to Linux VPS via SSH                           │
│  ├── 1. Connect via SSH Key                            │
│  ├── 2. Backup currently running container tags        │
│  ├── 3. Pull exact commit SHA images from Docker Hub   │
│  ├── 4. Update running stack via `docker compose up -d`│
│  ├── 5. Verify Health Checks (Backend & Frontend)      │
│  └── 6. Auto-rollback if unhealthy, else record SHA    │
└────────────────────────────────────────────────────────┘
```

---

## 2. GitHub Repository Secrets Required

Go to your repository on GitHub:
**Settings** $\to$ **Secrets and variables** $\to$ **Actions** $\to$ **New repository secret**

| Secret Name | Description | Example / Note |
| :--- | :--- | :--- |
| `DOCKERHUB_USERNAME` | Your Docker Hub account username. | `jasminbabariya22` |
| `DOCKERHUB_TOKEN` | Docker Hub Personal Access Token (Read & Write permissions). | Generated in Docker Hub Account Settings $\to$ Security $\to$ Access Tokens |
| `VPS_HOST` | Public IP address or domain name of your Linux VPS. | `203.0.113.10` |
| `VPS_USER` | SSH user on your Linux VPS (with docker permissions). | `deploy` or `ubuntu` |
| `VPS_SSH_KEY` | Private SSH Key (ed25519 or RSA) matching `authorized_keys` on VPS. | Content of `id_ed25519` |
| `VPS_SSH_PORT` | *(Optional)* SSH Port on the VPS. | `22` (default if omitted) |
| `VPS_DEPLOY_PATH` | *(Optional)* Directory on the VPS where the app lives. | `/opt/workflow` (default if omitted) |

---

## 3. VPS Prerequisites & Initial Setup

Execute the following commands once on your Linux VPS (Ubuntu/Debian) to prepare the deployment target:

### Step 3.1: Install Docker Engine & Compose Plugin
```bash
sudo apt update
sudo apt install -y curl ca-certificates gnupg git

# Add Docker official GPG key & repository
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Grant deploy user docker permissions
sudo usermod -aG docker $USER
```

### Step 3.2: Create Deployment Directory & Copy Configuration
```bash
sudo mkdir -p /opt/workflow
sudo chown -R $USER:$USER /opt/workflow
cd /opt/workflow

# Copy docker-compose.yml to the VPS directory
# (or clone repo files: docker-compose.yml and monitoring/ directory)
```

### Step 3.3: Configure Production `.env`
Create `/opt/workflow/.env` with your secure production values:
```bash
nano /opt/workflow/.env
```
Ensure the following variables are defined:
```dotenv
WORKFLOW_DATABASE_URL=postgresql+psycopg2://user:password@db-host:5432/workflow_prod
WORKFLOW_DB_SCHEMA=workflow
SECRET_KEY=generate_with_python_secrets_token_hex_32
FERNET_KEY=generate_with_fernet_generate_key
ALGORITHM=HS256
MAIN_URL=https://your-domain-or-ip
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=strong_grafana_password
```

### Step 3.4: Generate / Install SSL Certificates
If using HTTPS (Port 443), ensure SSL certificates exist at `/opt/workflow/backend/certs`:
```bash
mkdir -p /opt/workflow/backend/certs
# Place fullchain.pem and privkey.pem in /opt/workflow/backend/certs
```

---

## 4. Reliability, Health Checks & Rollback Procedure

### Automated Rollback in Pipeline
The CD workflow automatically captures the currently running image tags before executing `docker compose up -d`. If either the FastAPI backend (`/health`) or Nginx frontend (`/`) fails to report `healthy` within 120 seconds:
1. An automated rollback command is executed on the VPS.
2. The containers are restored to the previous stable images.
3. The GitHub Actions job exits with code `1`, alerting the team.

### Manual Rollback Procedure
If you ever need to manually roll back to a specific previous release:

```bash
cd /opt/workflow

# View the previous deployment backup tag
cat .last_deploy_state

# Option A: Rollback to previous recorded state
source .last_deploy_state
IMAGE_TAG=$(echo $PREV_BACKEND | cut -d':' -f2) docker compose up -d --remove-orphans

# Option B: Rollback to any specific Git SHA tag
IMAGE_TAG=abc1234def docker compose up -d --remove-orphans
```

---

## 5. Safe Testing Before Production

1. **Pull Request Safety**: Pull requests to `main` or `development` only trigger the CI jobs (`backend-ci`, `frontend-ci`, `docker-validation`). PRs **never** publish Docker images or deploy to the VPS.
2. **Push to `development`**: Pushes to `development` run complete CI quality gates and security audits without triggering CD.
3. **Dry-Run / Staging Push**: To trigger a real deployment, create a Pull Request from `development` into `main`. Once merged into `main`, GitHub Actions will execute CI, then Docker Hub publishing, and finally the automated VPS deployment.
