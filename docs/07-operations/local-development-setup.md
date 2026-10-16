# Local Development Setup

## 1. Prerequisites

Before setting up the **WorkFlow-Automation** platform locally, ensure your machine meets the following verified system prerequisites:

| Software / Tool | Recommended Version | Minimum Version | Verification Command |
| :--- | :--- | :--- | :--- |
| **Python** | `3.11.x` | `3.9+` | `python --version` |
| **Node.js** | `22.x LTS` | `18+` | `node --version` |
| **npm** | `10.x` | `9+` | `npm --version` |
| **Database** | PostgreSQL 15+ (or SQLite) | PostgreSQL 12+ / SQLite 3 | `psql --version` |
| **Git** | Latest | 2.30+ | `git --version` |

---

## 2. Step-by-Step Setup Guide

### Step 1: Clone the Repository
```bash
git clone https://github.com/jasminbabariya22-eng/WorkFlow-Automation.git
cd WorkFlow-Automation
```

### Step 2: Configure Backend Environment
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create your `.env` configuration file from the template:
   - **Windows**:
     ```powershell
     copy .env.example .env
     ```
   - **Linux / macOS**:
     ```bash
     cp .env.example .env
     ```
3. Generate secure secrets and populate `.env`:
   ```bash
   # Generate SECRET_KEY (JWT Auth)
   python -c "import secrets; print(secrets.token_hex(32))"

   # Generate FERNET_KEY (Credential Encryption)
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
4. Update `backend/.env` with your values:
   ```env
   # Backend .env configuration
   WORKFLOW_DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/workflow_db
   # For local lightweight testing without PostgreSQL, SQLite is supported:
   # WORKFLOW_DATABASE_URL=sqlite:///workflow.db

   WORKFLOW_DB_SCHEMA=workflow
   SECRET_KEY=your_generated_32_character_hex_secret_key
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   FERNET_KEY=your_generated_base64_fernet_key=
   MAIN_URL=http://localhost:5173
   ```

### Step 3: Set Up Backend Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Set Up Frontend Dependencies
In a separate terminal window:
```bash
cd frontend
npm install
```

---

## 3. Starting the Platform

### Option A: One-Click Startup Scripts (Windows)

The repository provides automated startup batch files that verify dependencies, auto-detect local network IPs, and launch both backend and frontend in parallel:

1. **Standard HTTP Development**:
   Double-click `run_workflow_server.bat` (or execute from PowerShell):
   ```powershell
   .\run_workflow_server.bat
   ```
2. **Secure HTTPS / SSL Development**:
   Double-click `run_workflow_server_ssl.bat`:
   ```powershell
   .\run_workflow_server_ssl.bat
   ```
   *(Automatically generates local self-signed certificates in `backend/certs/` if missing).*

---

### Option B: Manual Cross-Platform Startup

#### Terminal 1 — Start Backend Server (FastAPI / Uvicorn):
```bash
cd backend

# Windows
.\.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Linux / macOS
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 2 — Start Frontend Studio (Vite Dev Server):
```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

---

## 4. Local Service URLs & Endpoints

| Service / Interface | Local URL | Network / LAN URL |
| :--- | :--- | :--- |
| **Workflow Studio UI** | `http://localhost:5173` | `http://<YOUR_IP>:5173` |
| **FastAPI Backend API** | `http://localhost:8000` | `http://<YOUR_IP>:8000` |
| **Interactive Swagger Docs**| `http://localhost:8000/docs` | `http://<YOUR_IP>:8000/docs` |
| **Alternative Redoc API** | `http://localhost:8000/redoc`| `http://<YOUR_IP>:8000/redoc` |
| **Health Check Endpoint** | `http://localhost:8000/health`| `http://<YOUR_IP>:8000/health` |
| **WebSocket Gateway** | `ws://localhost:8000/ws/workflow` | `ws://<YOUR_IP>:8000/ws/workflow` |

---

## 5. Running Tests & Linters

### Backend Automated Test Suite
From the `backend/` directory:
```bash
# Run pytest with short traceback
python -m pytest tests/ -v --tb=short

# Run with test coverage report
python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

### Frontend Linter & Build Validation
From the `frontend/` directory:
```bash
# Run Oxlint linter
npm run lint

# Run production Vite build
npm run build
```

---

## 6. Related Documentation Links

- Architecture Overview: [System Architecture](../01-overview/system-architecture.md)
- Docker Deployment: [Docker Deployment](./docker-deployment.md)
- Troubleshooting Guide: [Troubleshooting](./troubleshooting.md)
