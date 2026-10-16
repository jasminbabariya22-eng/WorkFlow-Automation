# Testing Strategy

## 1. Testing Philosophy & Test Layering

The **WorkFlow-Automation** testing strategy ensures stability, correctness, and security across the backend engine, API routers, database persistence layer, and frontend visual components.

```text
+-------------------------------------------------------------------------+
|  4. In-Designer Simulation & Test Runner                                |
|     (frontend/src/components/designer/DesignerTestRunnerModal.jsx)      |
+-------------------------------------------------------------------------+
|  3. Standalone Integration Tests                                        |
|     (comprehensive_api_test.py, test_client_gateway.py, test_exec.py)   |
+-------------------------------------------------------------------------+
|  2. Automated Pytest Test Suite                                         |
|     (backend/tests/ - 14 verified unit/integration test cases)          |
+-------------------------------------------------------------------------+
|  1. Static Analysis & Build Verification                                |
|     (Oxlint, Vite Build, pip-audit, Trivy Docker scans)                 |
+-------------------------------------------------------------------------+
```

---

## 2. Automated Backend Pytest Suite

Located in `backend/tests/`, the test suite runs with Pytest and Pytest-Cov:

### Test Files & Covered Scenarios:

#### 1. `test_health_and_security.py` (4 tests)
- `test_health_endpoint`: Verifies `/health` returns status `healthy` and service name.
- `test_settings_fails_when_required_secrets_are_missing`: Validates that `backend/app/core/config.py` raises clean `RuntimeError` when secrets are omitted.
- `test_fernet_encryption_roundtrip`: Verifies AES encryption and decryption consistency for database passwords.
- `test_database_isolation_guard`: Validates dual-database isolation boundaries.

#### 2. `test_workflow_definitions.py` (4 tests)
- `test_create_and_inspect_workflow`: Validates creation of `wf_definition` records and inspection retrieval.
- `test_add_nodes_connections_and_validate`: Validates relational node and edge insertion into `wf_version`.
- `test_publish_workflow_and_immutability`: Verifies that publishing freezes version `N` into read-only status.
- `test_version_evolution`: Verifies that modifying a published workflow spawns version `N + 1` without altering version `N`.

#### 3. `test_workflow_runtime.py` (3 tests)
- `test_execute_studio_workflow_human_approval_lifecycle`: Verifies complete execution path: `START` &rarr; automated nodes &rarr; `APPROVAL` gate (blocks in `WAITING`) &rarr; action submission (`APPROVE`) &rarr; resumption to `COMPLETED`.
- `test_execute_studio_workflow_disallowed_action`: Verifies that submitting an unauthorized action (e.g. non-existent action code) is rejected.
- `test_execute_studio_direct_automated_flow`: Verifies straight-through automated flows without human gates.

#### 4. `test_workflow_studio.py` (3 tests)
- `test_create_and_update_studio_graph`: Tests canvas JSON saving and retrieval via Studio endpoints.
- `test_validate_and_publish_studio_workflow`: Tests full canvas validation rules before publishing.
- `test_studio_catalogs_discovery`: Verifies available node catalog enumeration.

---

## 3. Test Database Isolation & Fixtures

Configured in `backend/tests/conftest.py`:
- **In-Memory / Local SQLite**: Tests override `WORKFLOW_DATABASE_URL` with `sqlite:///main_test.db` to prevent touching production databases.
- **Fixture `test_client`**: Creates an isolated HTTP client using `httpx.Client(app=app)`.
- **Database Fixture `db_session`**: Creates clean tables via `Base.metadata.create_all()` before each test and tears them down after execution.

### Executing the Test Suite:
```bash
cd backend

# Execute all tests with verbosity
python -m pytest tests/ -v --tb=short

# Execute with code coverage report
python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## 4. Standalone Integration Scripts

In addition to pytest, the `backend/` directory provides standalone integration scripts:
- **`comprehensive_api_test.py`**: Executes an end-to-end API smoke test across definitions, tasks, monitoring, and executor endpoints.
- **`test_client_gateway.py`**: Tests external client portal query and submit flows.
- **`test_executor.py`**: Stresses the background worker thread pool (`WorkflowJobExecutor`).
- **`test_jobs_api.py`**: Tests job pause, resume, restart, and history queries.

---

## 5. Frontend Quality Verification

1. **Oxlint Static Code Analysis**:
   - Configuration: `frontend/.oxlintrc.json`.
   - Command: `npm run lint` (runs `oxlint`).
   - Validates React hook rules (`exhaustive-deps`), unused imports, syntax errors, and DOM props across 31+ frontend source files in under 150ms.
2. **Production Vite Build**:
   - Command: `npm run build` (runs `vite build`).
   - Enforces strict module resolution, CSS minification, and chunk validation.
3. **In-Designer Interactive Simulation**:
   - Executed via **`▷ Test Flow`** toolbar button.
   - Tests live branch routing and SQL execution queries step by step.

---

## 6. Related Documentation Links

- CI/CD Automation: [CI/CD Pipeline](../07-operations/ci-cd-pipeline.md)
- Security Review: [Security Review](./security-review.md)
- Development Setup: [Local Development Setup](../07-operations/local-development-setup.md)
