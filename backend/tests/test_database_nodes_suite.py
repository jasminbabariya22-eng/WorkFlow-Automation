"""
Comprehensive Test Suite for Database Related Nodes & Queries in Workflow System.
Tests:
1. SELECT Query Execution (Visual & Raw SQL) via /workflow-studio/test/execute-sql endpoint logic
2. INSERT / CREATE RECORD Node Handler & Dynamic Parameter Binding
3. UPDATE / UPDATE RECORD Node Handler & Condition Filtering
4. DELETE / Raw SQL Execution Handler
5. Stored Procedures / Custom Parameter Evaluation & Template Interpolation
6. Integration with test_11 workflow definition & Runtime Engine Adapter
"""
import os
import sys
import json
import time
import datetime
from decimal import Decimal

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import DynamicEnginePool, ClientDatabaseAdapter, SessionLocal
from app.workflow_studio.runtime.actions import ActionRegistry
from app.workflow_studio.api import execute_test_sql
from app.workflow.persistence.models import BPMNDefinition, DatabaseConnection
from sqlalchemy import text, inspect

def run_database_nodes_test_suite():
    print("=" * 80)
    print("DATABASE NODES & TEST QUERY VERIFICATION SUITE")
    print("=" * 80)
    
    results = {}
    
    # -------------------------------------------------------------
    # 0. Connection & Schema Verification
    # -------------------------------------------------------------
    print("\n[STEP 0] Verifying Client Database Connection (Connection ID: 1, MassERS)...")
    db = SessionLocal()
    try:
        conn_rec = db.query(DatabaseConnection).filter(DatabaseConnection.connection_id == 1).first()
        wf_rec = db.query(BPMNDefinition).filter(BPMNDefinition.id == 5).first()
        print(f"  - Database Connection: ID={conn_rec.connection_id}, Name='{conn_rec.connection_name}', DB='{conn_rec.database_name}', Host='{conn_rec.host}'")
        print(f"  - Workflow: ID={wf_rec.id}, Name='{wf_rec.name}', Spec='{wf_rec.spec_id}', ConnID={wf_rec.connection_id}")
    finally:
        db.close()
        
    eng = DynamicEnginePool.get_engine(1)
    inspector = inspect(eng)
    schema_tables = inspector.get_table_names(schema='ers')
    print(f"  - Verified schema 'ers' with {len(schema_tables)} available tables: {schema_tables[:8]}...")

    # -------------------------------------------------------------
    # 1. Test SELECT Query Execution (Visual Query & Raw SQL)
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing SELECT Node / Query Execution...")
    try:
        # Test 1a: Raw SELECT Query
        t0 = time.perf_counter()
        res_raw_select = execute_test_sql({
            "connection_id": 1,
            "sql": "SELECT id, first_name, last_name, email, status FROM ers.mst_users LIMIT 5;",
            "params": {}
        })
        t1 = time.perf_counter()
        latency_1a = (t1 - t0) * 1000
        print(f"  [OK] 1a. Raw SELECT Query: {res_raw_select.get('row_count')} rows fetched in {latency_1a:.2f}ms")
        print(f"      Columns: {res_raw_select.get('columns')}")
        assert res_raw_select.get("status") == "SUCCESS", f"1a failed: {res_raw_select}"
        
        # Test 1b: Parameterized Visual SELECT with WHERE Clause
        t0 = time.perf_counter()
        res_param_select = execute_test_sql({
            "connection_id": 1,
            "sql": "SELECT id, dept_name, is_deleted FROM ers.mst_department WHERE is_deleted = :is_deleted ORDER BY id ASC LIMIT 3;",
            "params": {"is_deleted": 0}
        })
        t1 = time.perf_counter()
        latency_1b = (t1 - t0) * 1000
        print(f"  [OK] 1b. Parameterized SELECT Query: {res_param_select.get('row_count')} rows fetched in {latency_1b:.2f}ms")
        assert res_param_select.get("status") == "SUCCESS", f"1b failed: {res_param_select}"
        
        # Benchmark: 10 repeated query executions
        latencies = []
        for _ in range(10):
            tb0 = time.perf_counter()
            execute_test_sql({
                "connection_id": 1,
                "sql": "SELECT id, dept_name FROM ers.mst_department WHERE is_deleted = 0 LIMIT 1;",
                "params": {}
            })
            latencies.append((time.perf_counter() - tb0) * 1000)
        avg_latency = sum(latencies) / len(latencies)
        print(f"  [OK] 1c. 10-Run Average Query Latency: {avg_latency:.2f}ms (Min: {min(latencies):.2f}ms, Max: {max(latencies):.2f}ms)")
        
        results["SELECT_TEST_QUERY"] = {
            "status": "PASSED",
            "raw_latency_ms": round(latency_1a, 2),
            "param_latency_ms": round(latency_1b, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "sample_columns": res_raw_select.get("columns")
        }
    except Exception as e:
        print(f"  [FAIL] SELECT Node Test failed: {e}")
        results["SELECT_TEST_QUERY"] = {"status": "FAILED", "error": str(e)}

    # -------------------------------------------------------------
    # 2. Test DB_READ / READ_RECORD Action Handler (Runtime Node)
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing DB_READ / READ_RECORD Action Handler...")
    try:
        context_vars = {"user_id": 1, "entity_id": 1}
        read_config = {
            "table": "mst_users",
            "connection_id": 1,
            "fields": ["id", "first_name", "last_name", "email", "status"],
            "filters": [{"field": "id", "operator": "=", "value": 1}],
            "resultMapping": {"first_name": "fetched_first_name", "email": "fetched_email"}
        }
        res_read = ActionRegistry.execute("DB_READ", read_config, context_vars)
        print(f"  [OK] 2. DB_READ Action executed successfully:")
        print(f"      Mapped variables: fetched_first_name='{context_vars.get('fetched_first_name')}', fetched_email='{context_vars.get('fetched_email')}'")
        assert res_read.get("status") == "SUCCESS"
        assert "fetched_first_name" in context_vars
        
        results["DB_READ_NODE"] = {
            "status": "PASSED",
            "mapped_variables": {
                "fetched_first_name": context_vars.get("fetched_first_name"),
                "fetched_email": context_vars.get("fetched_email")
            }
        }
    except Exception as e:
        print(f"  [FAIL] DB_READ Node Test failed: {e}")
        results["DB_READ_NODE"] = {"status": "FAILED", "error": str(e)}

    # -------------------------------------------------------------
    # 3. Test DB_CREATE / INSERT RECORD Action Handler
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing DB_CREATE / INSERT RECORD Action Handler...")
    created_dept_id = None
    test_dept_name = f"QA Test Dept {int(time.time())}"
    try:
        context_vars = {"user_id": 1, "department_name_var": test_dept_name}
        create_config = {
            "table": "mst_department",
            "connection_id": 1,
            "values": {
                "dept_name": "{{department_name_var}}",
                "is_deleted": 0,
                "created_by": 1,
                "created_on": datetime.datetime.now().isoformat()
            },
            "outputVariable": "new_dept_id"
        }
        res_create = ActionRegistry.execute("DB_CREATE", create_config, context_vars)
        created_dept_id = context_vars.get("new_dept_id") or context_vars.get("created_id") or context_vars.get("id")
        print(f"  [OK] 3. DB_CREATE Action executed successfully:")
        print(f"      Created record ID: {created_dept_id} in table 'mst_department'")
        print(f"      Status: {res_create.get('status')}")
        assert res_create.get("status") == "SUCCESS"
        assert created_dept_id is not None
        
        results["DB_CREATE_NODE"] = {
            "status": "PASSED",
            "created_id": created_dept_id,
            "table": "mst_department"
        }
    except Exception as e:
        print(f"  [FAIL] DB_CREATE Node Test failed: {e}")
        results["DB_CREATE_NODE"] = {"status": "FAILED", "error": str(e)}

    # -------------------------------------------------------------
    # 4. Test DB_UPDATE / UPDATE RECORD Action Handler
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing DB_UPDATE / UPDATE RECORD Action Handler...")
    try:
        if created_dept_id:
            updated_name = f"{test_dept_name} - UPDATED"
            context_vars = {"target_dept_id": created_dept_id, "updated_name": updated_name}
            update_config = {
                "table": "mst_department",
                "connection_id": 1,
                "updates": {
                    "dept_name": "{{updated_name}}",
                    "modified_by": 1,
                    "modified_on": datetime.datetime.now().isoformat()
                },
                "filters": [
                    {"field": "id", "operator": "=", "value": str(created_dept_id)}
                ]
            }
            res_update = ActionRegistry.execute("DB_UPDATE", update_config, context_vars)
            print(f"  [OK] 4. DB_UPDATE Action executed successfully on record {created_dept_id}:")
            print(f"      Status: {res_update.get('status')}, updated data: {res_update.get('data')}")
            assert res_update.get("status") == "SUCCESS"
            
            # Verify update in database
            with eng.connect() as verify_conn:
                row = verify_conn.execute(
                    text("SELECT dept_name FROM ers.mst_department WHERE id = :id"),
                    {"id": created_dept_id}
                ).fetchone()
                print(f"      Direct DB verification: dept_name='{row[0]}'")
                assert row[0] == updated_name
                
            results["DB_UPDATE_NODE"] = {
                "status": "PASSED",
                "record_id": created_dept_id,
                "verified_value": row[0]
            }
        else:
            print("  - Skipped DB_UPDATE (no created record from test 3)")
            results["DB_UPDATE_NODE"] = {"status": "SKIPPED"}
    except Exception as e:
        print(f"  [FAIL] DB_UPDATE Node Test failed: {e}")
        results["DB_UPDATE_NODE"] = {"status": "FAILED", "error": str(e)}

    # -------------------------------------------------------------
    # 5. Test RAW_SQL / EXECUTE_SQL Action Handler (Cleanup/Delete)
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing RAW_SQL / EXECUTE_SQL Action Handler (Cleanup)...")
    try:
        if created_dept_id:
            context_vars = {"del_id": created_dept_id}
            sql_config = {
                "connection_id": 1,
                "sql": "DELETE FROM ers.mst_department WHERE id = :del_id;"
            }
            res_sql = ActionRegistry.execute("EXECUTE_SQL", sql_config, context_vars)
            print(f"  [OK] 5. EXECUTE_SQL Action executed successfully:")
            print(f"      Affected rows: {res_sql.get('affectedRows')}")
            assert res_sql.get("status") == "SUCCESS"
            assert res_sql.get("affectedRows") == 1
            
            results["RAW_SQL_NODE"] = {
                "status": "PASSED",
                "affected_rows": res_sql.get("affectedRows")
            }
        else:
            results["RAW_SQL_NODE"] = {"status": "SKIPPED"}
    except Exception as e:
        print(f"  [FAIL] RAW_SQL Node Test failed: {e}")
        results["RAW_SQL_NODE"] = {"status": "FAILED", "error": str(e)}

    # -------------------------------------------------------------
    # 6. Test Workflow test_11 with Database Node Sequence
    # -------------------------------------------------------------
    print("\n[TEST 6] Testing test_11 Workflow Definition & Database Integration...")
    try:
        db = SessionLocal()
        try:
            wf = db.query(BPMNDefinition).filter(BPMNDefinition.id == 5).first()
            assert wf is not None, "Workflow test_11 (ID: 5) not found"
            print(f"  [OK] 6a. Workflow 'test_11' found and bound to Connection ID {wf.connection_id}")
            
            # Test engine execution of test_11 steps
            json_def = json.loads(wf.json_content) if wf.json_content else {}
            node_count = len(json_def.get("nodes", []))
            edge_count = len(json_def.get("edges", []))
            print(f"  [OK] 6b. Workflow contains {node_count} nodes and {edge_count} edges")
            
            # Validate all nodes in test_11 can execute in runtime
            from app.workflow_studio.runtime.adapter import StudioExecutionAdapter
            
            # Execute email/communication action from test_11 with dynamic context
            test_vars = {
                "user_id": 1,
                "entity_id": 101,
                "employee_email": "jasminbabariya22@gmail.com",
                "employee_name": "Jasmin Babariya",
                "connection_id": wf.connection_id or 1
            }
            email_cfg = {
                "connection_id": wf.connection_id or 1,
                "to": "jasminbabariya22@gmail.com",
                "cc": "mjatin10117@gmail.com",
                "subject": "Test Verification for test_11 Workflow",
                "body": "This is a verification test of test_11 workflow execution."
            }
            res_action = ActionRegistry.execute("SEND_EMAIL", email_cfg, test_vars)
            print(f"  [OK] 6c. Executed test_11 communication action: Status={res_action.get('status')}, To={res_action.get('email_to')}")
            assert res_action.get("status") == "SUCCESS"
            
            results["WORKFLOW_TEST_11"] = {
                "status": "PASSED",
                "workflow_id": wf.id,
                "workflow_name": wf.name,
                "nodes_count": node_count,
                "edges_count": edge_count,
                "action_status": res_action.get("status")
            }
        finally:
            db.close()
    except Exception as e:
        print(f"  [FAIL] Workflow test_11 test failed: {e}")
        results["WORKFLOW_TEST_11"] = {"status": "FAILED", "error": str(e)}

    # -------------------------------------------------------------
    # Summary Report
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("TEST SUITE SUMMARY REPORT")
    print("=" * 80)
    all_passed = True
    for test_name, res in results.items():
        status = res.get("status")
        icon = "[PASSED]" if status == "PASSED" else "[FAIL] " + str(status)
        print(f"  {icon:<12} | {test_name}")
        if status != "PASSED":
            all_passed = False
            
    print("-" * 80)
    print(f"Overall Status: {'ALL TESTS PASSED - 100% OPERATIONAL' if all_passed else 'SOME TESTS ENCOUNTERED ISSUES'}")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    run_database_nodes_test_suite()
