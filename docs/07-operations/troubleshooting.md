# Troubleshooting Runbook

This guide covers common operational, deployment, runtime, and development issues encountered in the **WorkFlow-Automation** platform, detailing symptoms, root causes, verification steps, and verified solutions.

---

## 1. Backend Startup Failures

### Issue: `RuntimeError: The following required environment variables are missing: [WORKFLOW_DATABASE_URL, SECRET_KEY, FERNET_KEY]`
- **Symptom**: The FastAPI server immediately exits upon executing `uvicorn app.main:app`.
- **Cause**: `backend/app/core/config.py` enforces strict validation on startup via Pydantic `BaseSettings`. Required secrets are missing from the active environment or `.env` file.
- **Verification**: Run `python -c "from app.core.config import settings"` inside `backend/`.
- **Solution**:
  1. Copy `backend/.env.example` to `backend/.env`.
  2. Populate `WORKFLOW_DATABASE_URL`, `SECRET_KEY`, and `FERNET_KEY`.
  3. Ensure `.env` is located in the `backend/` directory or root workspace.

### Issue: `ModuleNotFoundError: No module named 'jose'` or `'cryptography'`
- **Symptom**: Server startup or pytest fails with import errors.
- **Cause**: Executing using the global system Python rather than the project virtual environment (`backend/.venv/`).
- **Verification**: Check which interpreter is executing via `which python` or `where python`.
- **Solution**: Activate the project virtual environment before running commands:
  - Windows: `.\backend\.venv\Scripts\activate`
  - Linux: `source backend/.venv/bin/activate`

### Issue: `ImportError: libpq.so` or `unixODBC error: freetds driver not found` (Linux/Docker)
- **Symptom**: SQLAlchemy fails when connecting to PostgreSQL or Microsoft SQL Server in containerized environments.
- **Cause**: Missing underlying C libraries for database drivers (`libpq-dev`, `unixodbc-dev`, `freetds-dev`).
- **Solution**: Install the system compilation packages before pip install (already baked into `backend/Dockerfile`):
  ```bash
  sudo apt-get update && sudo apt-get install -y unixodbc-dev freetds-dev libpq-dev
  ```

---

## 2. Database Connection Issues

### Issue: `Authentication failed: Incorrect password or invalid user`
- **Symptom**: `POST /workflow-studio/connections/test` returns HTTP 400 with authentication error.
- **Cause**: The password or username specified in the `DatabaseConnection` modal is incorrect for the target database server.
- **Verification**: Verify credentials directly using a native database CLI (`psql`, `mysql`, or `sqlcmd`).
- **Solution**: Update the connection profile in the Studio UI with the correct password.

### Issue: `Server unreachable: Could not connect to host on port 5432 / 1433`
- **Symptom**: Connection times out or returns `10061 Connection Refused`.
- **Cause**:
  1. Target database service is stopped.
  2. Database server is bound strictly to `127.0.0.1` and refusing external container/LAN connections.
  3. Firewall is blocking the database port.
- **Solution**:
  1. Verify the database service is running.
  2. In `postgresql.conf`, set `listen_addresses = '*'`.
  3. In `pg_hba.conf`, grant access to the host or Docker subnet (`172.18.0.0/16`).

---

## 3. Workflow Definition & Designer Errors

### Issue: Canvas Validation Fails: `"Graph must contain exactly one Start node"`
- **Symptom**: Designer displays error modal upon clicking **Publish** or **Validate**.
- **Cause**: The canvas has zero `START` nodes or multiple `START` nodes.
- **Solution**: Delete duplicate start nodes until exactly one is present.

### Issue: Execution Fails at Condition Gateway: `"No outgoing branch satisfied"`
- **Symptom**: Instance terminates with `FAILED` at an exclusive gateway node.
- **Cause**: Condition expressions on outgoing edges evaluated to `False`, and no default edge was designated.
- **Solution**:
  1. Inspect runtime variable values in the instance monitoring drawer.
  2. Add an outgoing edge labeled `DEFAULT` or `FALSE` to catch unhandled cases.

---

## 4. Frontend & Proxy Communication Problems

### Issue: Frontend Displays `Network Error` / `502 Bad Gateway`
- **Symptom**: Studio UI loads, but workflow lists and connection dropdowns fail to load.
- **Cause**: The FastAPI backend server is not running on port `8000`, or Vite proxy is attempting to connect via HTTP while backend is running in HTTPS mode.
- **Verification**: Test the backend directly in your browser: `http://localhost:8000/health`.
- **Solution**:
  1. Ensure backend is running (`uvicorn app.main:app --port 8000`).
  2. Check `backend/certs/fullchain.pem`: if SSL certificates exist, backend runs HTTPS. Ensure `VITE_BACKEND_PROTOCOL=https` in `frontend/.env.local` or remove certs for plain HTTP development.

### Issue: Browser SSL Warning: `NET::ERR_CERT_AUTHORITY_INVALID`
- **Symptom**: Red warning screen in Chrome/Edge when accessing `https://localhost:5173` or `https://<LAN_IP>:8000`.
- **Cause**: The platform generated a self-signed X.509 certificate for local encryption.
- **Solution**: Click **Advanced &rarr; Proceed to localhost (unsafe)** in your browser. For production domain deployments, install a signed certificate from Let's Encrypt or your corporate Certificate Authority.

---

## 5. WebSocket Connection Drops

### Issue: Telemetry Dashboard Does Not Update in Real Time
- **Symptom**: WebSocket status in the console shows `WebSocket connection closed`.
- **Cause**: Corporate proxy or firewall terminating idle TCP connections.
- **Verification**: Check browser developer tools **Network &rarr; WS** tab. Look for `ping` frames every 30 seconds.
- **Solution**: Verify that the browser client is sending `"ping"` keepalives (handled automatically in `createWorkflowWebSocket()`).

---

## 6. Related Documentation Links

- Setup Guide: [Local Development Setup](./local-development-setup.md)
- Docker Runbook: [Docker Deployment](./docker-deployment.md)
- Monitoring & Metrics: [Monitoring & Alerting](./monitoring-and-alerting.md)
