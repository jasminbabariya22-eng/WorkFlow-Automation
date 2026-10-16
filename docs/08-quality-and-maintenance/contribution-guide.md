# Contribution & Development Guide

## 1. Development Principles

When contributing to the **WorkFlow-Automation** codebase, adhere to these fundamental architectural principles:
1. **Zero Domain-Specific Hardcoding**: Never commit hardcoded table names, column names, or business statuses to the Python backend. The engine must remain a generic graph traversal runtime.
2. **Dual-Database Discipline**: Maintain strict separation between workflow metadata (`WorkflowSessionLocal`) and client business database connections (`DynamicEnginePool`).
3. **Always Parameterize SQL**: Raw SQL strings must never use format strings (`%s` or `f"{var}"`) for user or context values. Always bind parameters via SQLAlchemy `text(..., {"param": val})`.
4. **Preserve Immutability**: Modifying an active workflow definition must never overwrite an existing published version graph in place; always spawn or update a draft version.

---

## 2. Branching & Commit Conventions

### Branch Strategy
- **`development`**: The primary integration branch. All feature branches, bugfixes, and refactors should target `development`.
- **`main`**: The production release branch. Merges to `main` trigger the automated production deployment pipeline (`deploy.yml`).

### Commit Message Format
The repository follows standard Conventional Commits:
```text
<type>(<scope>): <short description>
```

#### Common Types:
- `feat`: New visual node type, API endpoint, or engine capability.
- `fix`: Bugfix in graph compilation, runtime adapter, or UI inspector.
- `refactor`: Structural improvements without changing external behavior.
- `docs`: Documentation updates, architecture guides, or API notes.
- `test`: Adding or updating test cases.
- `ci`: Changes to GitHub Actions workflows or Docker configs.

#### Examples:
```text
feat(nodes): add conflict handling rule to CREATE_RECORD property panel
fix(monitoring): sanitize large process variables to prevent UI freezing
docs(api): document universal workflow hub endpoints
```

---

## 3. Pre-Commit Verification Checklist

Before submitting a pull request or pushing to `development`:

### 1. Backend Verification
```bash
cd backend

# 1. Activate venv
.\.venv\Scripts\activate   # Windows
# source .venv/bin/activate # Linux/macOS

# 2. Syntax & compilation check
python -m py_compile app/main.py

# 3. Run automated test suite
python -m pytest tests/ -v --tb=short
```
*Expected: All 14 tests pass without errors.*

### 2. Frontend Verification
```bash
cd frontend

# 1. Run Oxlint code analysis
npm run lint

# 2. Verify production bundle compilation
npm run build
```
*Expected: Linter finishes with 0 errors; Vite produces production bundle in `dist/`.*

### 3. Secret & Path Sanitization
- [ ] Ensure no local machine paths (e.g. `/absolute/path/...`) are present in code or documentation. Use repository-relative paths.
- [ ] Ensure no real credentials, private keys (`privkey.pem`), or passwords are committed to Git.
- [ ] Ensure `.env` is omitted from commits.

---

## 4. Module Ownership Map

| Directory / Module | Component Description | Primary Tech Stack |
| :--- | :--- | :--- |
| `backend/app/workflow_studio/` | Visual Studio Canvas APIs & Direct Execution Adapter | Python / FastAPI / SQLAlchemy |
| `backend/app/workflow/` | SpiffWorkflow BPMN Integration & Persistence Models | Python / SpiffWorkflow |
| `backend/app/workflow_definition/` | Generic Relational Workflow Definition Models | Python / SQLAlchemy |
| `backend/app/core/` | Configuration, Logging, Security, and WebSocket Manager | Python / Jose / Cryptography |
| `frontend/src/components/` | Visual Designer Canvas, Node Library, and Monitoring UI | React 19 / @xyflow/react |
| `frontend/src/services/` | API Communication Clients (`workflowStorage.js`) | JavaScript ES Modules |
| `.github/workflows/` | CI/CD Pipelines and Automated Deployments | GitHub Actions / YAML |

---

## 5. Related Documentation Links

- Setup Guide: [Local Development Setup](../07-operations/local-development-setup.md)
- Testing Guide: [Testing Strategy](./testing-strategy.md)
- Security Guidelines: [Security Review](./security-review.md)
