# Security Review & Threat Analysis

This document provides a code-informed security review of the **WorkFlow-Automation** platform. Every finding, implemented control, and potential risk is directly derived from verified implementation code in the repository.

---

## 1. Security Architecture Summary

```text
+-------------------------------------------------------------------------+
|                        SECURITY CONTROLS MATRIX                         |
+-------------------------+--------------------+--------------------------+
| Control Category        | Implementation     | Verification Source      |
+-------------------------+--------------------+--------------------------+
| Credential Encryption   | Fernet (AES-CBC)   | app/core/security.py     |
| SQL Injection Defense   | Parameterized SQL  | app/core/database.py     |
| Secret Pre-Flight Check | Atomic Validator   | validate_env_secrets.py  |
| Request Log Masking     | Password Obfuscator| app/main.py              |
| Safe Condition Eval     | AST / Regex Rules  | actions.py               |
| Transport Encryption    | HTTPS / TLS        | generate_ssl_certs.py    |
+-------------------------+--------------------+--------------------------+
```

---

## 2. In-Depth Security Findings & Vulnerability Assessment

### Finding SEC-01: Authentication Dev Fallback in `get_current_user`
- **Location**: `backend/app/core/dependencies.py` (lines 11–30)
- **Status**: **Identified Risk (Dev Convenience Feature)**
- **Severity**: **HIGH** (for public internet deployments) / **LOW** (for isolated local development)
- **Evidence**:
  ```python
  def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
      if not credentials:
          return {"id": 1, "username": "admin", "role_code": "admin", "user_type_name": "ADMIN"}
      try:
          ...
      except JWTError:
          return {"id": 1, "username": "admin", "role_code": "admin", "user_type_name": "ADMIN"}
  ```
- **Impact**: Any unauthenticated HTTP request will be automatically treated as having administrative privileges (`admin`).
- **Remediation**:
  In production environments, replace the fallback with an explicit 401 error:
  ```python
  if not credentials:
      raise HTTPException(status_code=401, detail="Authentication required")
  ```

---

### Finding SEC-02: SQL Injection Defense (Implemented Control for Structured Actions)
- **Location**: `backend/app/core/database.py` and `backend/app/workflow_studio/runtime/actions.py`
- **Status**: **VERIFIED SECURE (STRUCTURED ACTIONS ONLY)**
- **Severity**: Informational (Structured DB Nodes) / Medium Operational Risk (Raw SQL Nodes)
- **Evidence**:
  All structured database CRUD nodes (`READ_RECORD`, `CREATE_RECORD`, `UPDATE_RECORD`, `DELETE_RECORD`) use SQLAlchemy `text()` constructs with named parameter bindings:
  ```python
  conn.execute(
      text(f"SELECT * FROM {clean_table} WHERE {clean_col} = :bind_val"),
      {"bind_val": filter_value}
  )
  ```
  Values supplied by users or upstream context memory are bound as query parameters rather than concatenated into SQL strings, and table and column identifiers are validated against live schema introspection before query execution.
  
  **Explicit Exception — `RAW_SQL` / `EXECUTE_SQL` Action**:
  The engine includes dedicated `RAW_SQL` and `EXECUTE_SQL` action handlers that execute caller-supplied SQL statements directly against client database connections. These raw SQL actions represent an explicit exception to the automated validation and parameterization guarantees; workflow authors utilizing `RAW_SQL` or `EXECUTE_SQL` nodes are responsible for manual query sanitization, and execution should be restricted to trusted administrative workflows.

---

### Finding SEC-03: Sensitive Credential Encryption (Implemented Control)
- **Location**: `backend/app/core/security.py` and `backend/app/workflow_studio/connections_api.py`
- **Status**: **VERIFIED SECURE**
- **Severity**: Informational (Control Implemented)
- **Evidence**:
  Client database passwords configured via the UI are encrypted before database insertion:
  ```python
  password_encrypted = encrypt_text(payload.password)
  ```
  Passwords returned to the frontend via `GET /workflow-studio/connections` are explicitly masked (`"********"`).

---

### Finding SEC-04: Server-Side Request Forgery (SSRF) in `API_CALL` Node
- **Location**: `backend/app/workflow_studio/runtime/actions.py`
- **Status**: **POTENTIAL RISK**
- **Severity**: **MEDIUM**
- **Evidence**:
  The `API_CALL` node allows workflow designers to configure outbound HTTP requests to arbitrary URLs (`url: "https://..."`).
- **Impact**: If an untrusted user is granted process design permissions, they could configure an `API_CALL` node targeting internal infrastructure (e.g. AWS/GCP cloud metadata `http://169.254.169.254` or internal intranet services).
- **Remediation**:
  1. Restrict visual designer permissions to trusted process architects.
  2. Implement an IP/domain whitelist in `actions.py` that rejects connections to link-local (`169.254.0.0/16`) or loopback (`127.0.0.0/8`) ranges unless explicitly whitelisted.

---

### Finding SEC-05: WebSocket Connection Authentication
- **Location**: `backend/app/main.py` (lines 122–134)
- **Status**: **POTENTIAL RISK**
- **Severity**: **LOW**
- **Evidence**:
  The WebSocket endpoint `/ws/workflow` accepts connections and reads optional `user_id` query parameters without validating an `access_token` or JWT signature.
- **Impact**: An unauthenticated client on the network can connect and eavesdrop on broadcast events (`WORKFLOW_STARTED`, `TASK_READY`, etc.).
- **Remediation**: Require `token` in the WebSocket connection query string and validate it against `SECRET_KEY` in `websocket_endpoint()` before calling `ws_manager.connect()`.

---

### Finding SEC-06: CORS Wildcard Configuration
- **Location**: `backend/app/main.py` (lines 55–61)
- **Status**: **ACCEPTABLE FOR DEV / RESTRICT FOR PROD**
- **Severity**: **LOW**
- **Evidence**: `allow_origins=["*"]` is currently enabled.
- **Remediation**: For production domain deployments, set `allow_origins=[settings.MAIN_URL]`.

---

## 3. Pre-Flight Security Checklist for Production

Before exposing the platform beyond a secure private network, verify:
- [ ] `SECRET_KEY` has been generated with 32+ characters of cryptographic randomness.
- [ ] `FERNET_KEY` is a valid 32-byte URL-safe base64 key generated via `Fernet.generate_key()`.
- [ ] Authentication dev fallback in `get_current_user` is disabled or guarded by an environment flag.
- [ ] `MAIN_URL` is configured with valid HTTPS hostnames.
- [ ] SSL certificates generated via `generate_ssl_certs.py` include valid Subject Alternative Names.
- [ ] Grafana default password `admin` has been replaced with a strong secret.

---

## 4. Related Documentation Links

- Authentication Mechanics: [Authentication & Security](../02-backend/authentication-security.md)
- Secret Validation: [Local Development Setup](../07-operations/local-development-setup.md)
- Testing Strategy: [Testing Strategy](./testing-strategy.md)
