# Client Database Integration

## 1. Integration Mission & Zero-Hardcoding Principle

A central architectural requirement of WorkFlow-Automation is **Zero Domain-Specific Hardcoding for Domain CRUD**. For business domain record operations (querying, inserting, updating, and state synchronization of client entities), the backend contains no hardcoded table definitions, business column names, or domain status identifiers.

Instead, the platform interacts with client databases through dynamic schema introspection, dynamic connection pooling, and runtime SQL parameterization implemented in `backend/app/core/database.py`. Helper inspection services (such as master role discovery) use configurable candidate table sets without binding business entity CRUD to fixed tables.

```mermaid
flowchart LR
    StudioUI["Studio UI / Designer"] -->|Request Schema| IntrospectionAPI["Introspection API\n(/workflow-studio/connections/*)"]
    IntrospectionAPI --> DynamicPool["DynamicEnginePool"]
    DynamicPool -->|Decrypt Password (Fernet)| ClientDB[("Client Database\n(PostgreSQL, MySQL, MSSQL)")]
    ClientDB -->|Live Schema Data| DynamicPool
    DynamicPool -->|Tables, Columns, Types, PKs| IntrospectionAPI
    IntrospectionAPI -->|JSON Schema Grid| StudioUI
```

---

## 2. Dynamic Connection Pool Manager (`DynamicEnginePool`)

The `DynamicEnginePool` class in `backend/app/core/database.py` manages connections to arbitrary client databases:
- **Thread-Safe Caching**: Cached engines are stored in a dictionary keyed by `connection_id` with a `threading.Lock()` protecting creation and eviction.
- **Engine Resolution**:
  ```python
  engine = DynamicEnginePool.get_engine(connection_id)
  ```
  If not cached, the manager:
  1. Queries the `db_connections` table in the workflow database.
  2. Decrypts `password_encrypted` using `app.core.security.decrypt_text()`.
  3. Formats the connection URI according to the database engine type.
  4. Initializes a SQLAlchemy engine with `pool_pre_ping=True`.
  5. Caches the engine for reuse across subsequent node executions.

---

## 3. Supported Database Engines & Driver Matrix

| Engine | Normalized Key | Driver Packages | Default Port | Connection URL Template |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | `postgresql` | `psycopg2-binary` | `5432` | `postgresql+psycopg2://user:pwd@host:port/dbname?sslmode=...` |
| **MySQL / MariaDB** | `mysql` | `pymysql` | `3306` | `mysql+pymysql://user:pwd@host:port/dbname` |
| **Microsoft SQL Server** | `mssql` | `pymssql` (primary) / `pyodbc` (fallback) | `1433` | `mssql+pymssql://user:pwd@host:port/dbname` |
| **SQLite** | `sqlite` | Python standard library | N/A | `sqlite:///dbname` |
| **Oracle** | `oracle` | `cx_oracle` | `1521` | `oracle+cx_oracle://user:pwd@host:port/dbname` |

---

## 4. Live Schema Introspection

The backend exposes schema introspection endpoints that the visual designer uses to populate dropdowns and mapping tables dynamically:

### Introspection Endpoints (`backend/app/workflow_studio/connections_api.py`):
- **`GET /workflow-studio/connections/{id}/tables`**:
  Uses SQLAlchemy `inspect(engine).get_table_names()` and `get_view_names()` to enumerate all accessible tables in the configured schema.
- **`GET /workflow-studio/connections/{id}/tables/{table_name}/columns`**:
  Uses `inspect(engine).get_columns(table_name)`. Returns an array of column objects:
  ```json
  [
    {
      "name": "leave_id",
      "type": "INTEGER",
      "nullable": false,
      "primary_key": true,
      "default": "nextval('leave_id_seq'::regclass)"
    },
    {
      "name": "employee_id",
      "type": "INTEGER",
      "nullable": false,
      "primary_key": false,
      "default": null
    }
  ]
  ```
- **`GET /workflow-studio/connections/{id}/roles`**:
  Introspects role definition tables (scanning candidates such as `mst_user_role`, `roles`, `user_roles`) to supply live role chips for the `APPROVAL` node inspector.

---

## 5. Intelligent Connection Error Diagnostics

When testing database connectivity (`POST /workflow-studio/connections/test`), raw database driver errors can be cryptic. `DynamicEnginePool.parse_connection_error()` translates raw driver exceptions into human-readable diagnostic messages:

| Raw Driver Error Clues | Normalized UI Error Message |
| :--- | :--- |
| `password authentication failed`, `access denied for user`, `1045`, `18456` | *"Authentication failed: Incorrect password or invalid user '{username}'."* |
| `role does not exist`, `unknown user` | *"User not found: Username/Role '{username}' does not exist on this database server."* |
| `database does not exist`, `unknown database`, `1049` | *"Database not found: Database '{database_name}' does not exist on server '{host}:{port}'."* |
| `connection refused`, `10061`, `could not connect to server`, `adaptive server is unavailable` | *"Server unreachable: Could not connect to host '{host}' on port {port}. Please verify the host IP and check if the database server is running."* |
| `timed out`, `timeout` | *"Connection timed out: Server at '{host}:{port}' took too long to respond. Check network/firewall settings."* |
| `ssl`, `certificate`, `handshake failure` | *"SSL error: SSL negotiation failed with mode '{ssl_mode}'. Please verify SSL settings."* |

---

## 6. Related Documentation Links

- Database Architecture: [Database Architecture](./database-architecture.md)
- Node Configuration: [Node Configuration Panels](../04-frontend/node-configuration.md)
- Activities Inventory: [Activities & Node Inventory](../03-workflow-engine/activities-and-nodes.md)
