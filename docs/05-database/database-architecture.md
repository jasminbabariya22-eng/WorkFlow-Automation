# Database Architecture

## 1. Dual-Database Paradigm

WorkFlow-Automation uses a **Dual-Database Architecture** to enforce separation of concerns between workflow orchestration metadata and client business domain data.

```mermaid
flowchart TB
    subgraph WorkflowPlatform["Workflow Engine & Studio Platform"]
        WfEngine["Workflow Engine / API Server"]
    end

    subgraph WorkflowStorage["1. Workflow Engine Database (Internal)"]
        WfSchema["Schema: workflow (or public / sqlite)"]
        WfTables["• wf_definition / wf_version\n• wf_node / wf_connection\n• spiff_workflow_instance\n• workflow_human_task\n• workflow_history\n• db_connections"]
        WfSchema --- WfTables
    end

    subgraph ClientStorage["2. Client Application Database (External Domain)"]
        ClientTables["• Business Entities (e.g. leave_requests, risk_register)\n• Master Users (mst_users)\n• Master Roles (mst_user_role)\n• Master Departments (mst_department)\n• SMTP Server Configs (email_server)"]
    end

    WfEngine <-->|"Read / Write Process State\n(WorkflowSessionLocal)"| WorkflowStorage
    WfEngine <-->|"Parameterized CRUD & Schema Discovery\n(DynamicEnginePool)"| ClientStorage
```

---

## 2. Database Responsibilities & Ownership

| Characteristic | 1. Workflow Engine Database | 2. Client Application Database |
| :--- | :--- | :--- |
| **Primary Responsibility** | Process specifications, versioned graphs, node configurations, active instance state machines, human task queues, and immutable audit logs. | Business domain records, employee master data, operational transactions, customer accounts, and client SMTP configurations. |
| **Configured Via** | Environment variable `WORKFLOW_DATABASE_URL` (in `backend/.env`). | Relational rows stored in `db_connections` table; selectable dynamically per workflow. |
| **Engine Abstraction** | `WorkflowSessionLocal` in `backend/app/workflow/database.py`. | `DynamicEnginePool` in `backend/app/core/database.py`. |
| **Supported RDBMS** | PostgreSQL (Production) / SQLite (Development/Tests). | PostgreSQL, MySQL, MariaDB, Microsoft SQL Server, SQLite, Oracle. |
| **Schema Scope** | Isolated under `WORKFLOW_DB_SCHEMA` (defaults to `"workflow"` in PostgreSQL). | Target database's native schemas (e.g., `public`, `dbo`, `ers`). |
| **Domain Hardcoding** | Zero domain business fields (strictly generic graph tables). | Domain-specific entity structures defined by the client organization. |

---

## 3. Dynamic Multi-RDBMS Connection Management

The platform does not assume a single static database connection for client operations. The `DynamicEnginePool` class in `backend/app/core/database.py` manages connections dynamically:

### Thread-Safe Engine Caching
```python
class DynamicEnginePool:
    _lock = threading.Lock()
    _cached_engines: Dict[int, Engine] = {}

    @classmethod
    def get_engine(cls, connection_id: Optional[int] = None) -> Engine:
        with cls._lock:
            if connection_id in cls._cached_engines:
                return cls._cached_engines[connection_id]
            # Fetches profile, decrypts password, creates SQLAlchemy engine
            ...
```

### Supported URL Builders
`DynamicEnginePool.build_connection_url()` dynamically resolves connection strings for multiple database drivers:
- **PostgreSQL**: `postgresql+psycopg2://user:pass@host:port/dbname`
- **MySQL / MariaDB**: `mysql+pymysql://user:pass@host:port/dbname`
- **Microsoft SQL Server**: `mssql+pymssql://user:pass@host:port/dbname` (with `pyodbc` fallback)
- **SQLite**: `sqlite:///dbname`
- **Oracle**: `oracle+cx_oracle://user:pass@host:port/dbname`

---

## 4. Connection Pool Parameters & Health Verification

All engines created by `DynamicEnginePool` and the primary `workflow_engine` enforce:
- `pool_pre_ping=True`: Tests connections with a lightweight `SELECT 1` ping before handing them to a transaction, preventing stale connection errors after database restarts or network timeouts.
- `echo=False`: Disables raw SQL stdout logging to protect production logs from query data dumps.
- Configurable pool sizes (`pool_size` default 10, `max_overflow` 20).

---

## 5. Related Documentation Links

- Workflow Schema Details: [Workflow Schema](./workflow-schema.md)
- Client DB Integration: [Client Database Integration](./client-database-integration.md)
- Transactions & Persistence: [Persistence & Transactions](./persistence-and-transactions.md)
