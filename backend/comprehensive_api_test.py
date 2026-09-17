import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"
test_results = []

def run_test(group: str, name: str, fn):
    try:
        passed, details = fn()
        test_results.append({
            "group": group,
            "name": name,
            "passed": passed,
            "details": details
        })
        status_str = "[PASS]" if passed else "[FAIL]"
        print(f"{status_str} | {group:<25} -> {name:<50}: {details}")
    except Exception as e:
        test_results.append({
            "group": group,
            "name": name,
            "passed": False,
            "details": f"Exception: {str(e)}"
        })
        print(f"[FAIL] | {group:<25} -> {name:<50}: Exception: {str(e)}")

# =========================================================================
# 1. CORE & HEALTH
# =========================================================================
def test_health():
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    return r.status_code == 200 and r.json().get("status") == "healthy", f"HTTP {r.status_code}, data={r.json()}"

run_test("1. Core & Health", "GET /health", test_health)

# =========================================================================
# 2. DATABASE CONNECTIONS (STUDIO)
# =========================================================================
def test_list_connections():
    r = requests.get(f"{BASE_URL}/workflow-studio/connections", timeout=5)
    return r.status_code == 200 and isinstance(r.json(), list), f"HTTP {r.status_code}, count={len(r.json())}"

def test_sqlserver_connection():
    payload = {
        "db_type": "sql server",
        "host": "192.168.1.192",
        "port": 1433,
        "database_name": "BPCLDemo",
        "username": "sa",
        "password": "Alethe@123",
        "default_schema": "dbo"
    }
    r = requests.post(f"{BASE_URL}/workflow-studio/connections/test", json=payload, timeout=10)
    data = r.json()
    return r.status_code == 200 and data.get("success") == True, f"HTTP {r.status_code}, latency={data.get('latency_ms')}ms, version={data.get('version', '')[:40]}..."

run_test("2. Connections", "GET /workflow-studio/connections", test_list_connections)
run_test("2. Connections", "POST /workflow-studio/connections/test (MSSQL)", test_sqlserver_connection)

# =========================================================================
# 3. WORKFLOW DEFINITIONS & LIFECYCLE (BPMN / DASHBOARD)
# =========================================================================
created_wf_id = None
test_spec_id = "test_suite_wf"

def test_save_draft_definition():
    global created_wf_id
    payload = {
        "spec_id": test_spec_id,
        "name": "Test Suite Workflow",
        "description": "Workflow created by comprehensive test suite",
        "xml_content": f'<?xml version="1.0" encoding="UTF-8"?><bpmn:definitions id="Def_1" targetNamespace="http://bpmn.io/schema/bpmn"><bpmn:process id="{test_spec_id}" isExecutable="true"><bpmn:startEvent id="Start_1"/><bpmn:endEvent id="End_1"/></bpmn:process></bpmn:definitions>'
    }
    r = requests.post(f"{BASE_URL}/workflow/definitions/save", json=payload, timeout=5)
    return r.status_code == 200, f"HTTP {r.status_code}"

def test_list_definitions():
    global created_wf_id
    r = requests.get(f"{BASE_URL}/workflow/definitions", timeout=5)
    data = r.json().get("data", [])
    for d in data:
        if d.get("spec_id") == test_spec_id:
            created_wf_id = d.get("id")
    return r.status_code == 200 and isinstance(data, list) and created_wf_id is not None, f"HTTP {r.status_code}, total={len(data)}, test_wf_id={created_wf_id}"

def test_get_definition_by_id():
    global created_wf_id
    r = requests.get(f"{BASE_URL}/workflow/definitions/{created_wf_id}", timeout=5)
    return r.status_code == 200 and r.json().get("data", {}).get("spec_id") == test_spec_id, f"HTTP {r.status_code}"

def test_activate_definition():
    global created_wf_id
    r = requests.post(f"{BASE_URL}/workflow/definitions/{created_wf_id}/activate", timeout=5)
    return r.status_code == 200, f"HTTP {r.status_code}"

def test_delete_active_blocked():
    global created_wf_id
    r = requests.delete(f"{BASE_URL}/workflow/definitions/{created_wf_id}", timeout=5)
    err = r.json().get("Error", {}).get("Error_Code") or r.status_code
    return err == 400, f"HTTP {r.status_code} (Active Guard Enforced: {r.json().get('Error', {}).get('Error_message')})"

def test_deactivate_definition():
    global created_wf_id
    r = requests.post(f"{BASE_URL}/workflow/definitions/{created_wf_id}/deactivate", timeout=5)
    return r.status_code == 200, f"HTTP {r.status_code}"

def test_delete_inactive_definition():
    global created_wf_id
    r = requests.delete(f"{BASE_URL}/workflow/definitions/{created_wf_id}", timeout=5)
    return r.status_code == 200, f"HTTP {r.status_code}"

run_test("3. BPMN Lifecycle", "POST /workflow/definitions/save", test_save_draft_definition)
run_test("3. BPMN Lifecycle", "GET /workflow/definitions", test_list_definitions)
run_test("3. BPMN Lifecycle", "GET /workflow/definitions/{id}", test_get_definition_by_id)
run_test("3. BPMN Lifecycle", "POST /workflow/definitions/{id}/activate", test_activate_definition)
run_test("3. BPMN Lifecycle", "DELETE /workflow/definitions/{id} (Active Protected)", test_delete_active_blocked)
run_test("3. BPMN Lifecycle", "POST /workflow/definitions/{id}/deactivate", test_deactivate_definition)
run_test("3. BPMN Lifecycle", "DELETE /workflow/definitions/{id} (Inactive Deletion)", test_delete_inactive_definition)

# =========================================================================
# 4. WORKFLOW RETRIEVAL & INSPECTION (/workflows)
# =========================================================================
def test_get_all_workflows():
    r = requests.get(f"{BASE_URL}/workflows", timeout=5)
    data = r.json().get("data", {})
    return r.status_code == 200 and "workflows" in data, f"HTTP {r.status_code}, count={data.get('total')}"

def test_get_workflows_by_status():
    r = requests.get(f"{BASE_URL}/workflows/by-status/ACTIVE", timeout=5)
    data = r.json().get("data", {})
    return r.status_code == 200 and "workflows" in data, f"HTTP {r.status_code}, count={data.get('total')}"

def test_get_workflows_by_client_db():
    r = requests.get(f"{BASE_URL}/workflows/by-client-db/7", timeout=5)
    data = r.json().get("data", {})
    return r.status_code == 200 and "workflows" in data, f"HTTP {r.status_code}, count={data.get('total')}"

def test_get_workflows_catalog():
    r = requests.get(f"{BASE_URL}/workflows/catalog", timeout=5)
    data = r.json().get("data", {})
    return r.status_code == 200 and "workflows" in data, f"HTTP {r.status_code}, count={data.get('total')}"

def test_inspect_workflow():
    r = requests.get(f"{BASE_URL}/workflows/inspect/email_notification", timeout=5)
    data = r.json().get("data")
    return r.status_code == 200 and data is not None, f"HTTP {r.status_code}, name='{data.get('name')}', nodes={data.get('statistics', {}).get('total_nodes')}"

def test_get_workflow_by_code():
    r = requests.get(f"{BASE_URL}/workflows/email_notification", timeout=5)
    data = r.json().get("data")
    return r.status_code == 200 and data is not None, f"HTTP {r.status_code}, nodes={len(data.get('nodes', []))}, edges={len(data.get('edges', []))}"

run_test("4. Workflow Query", "GET /workflows", test_get_all_workflows)
run_test("4. Workflow Query", "GET /workflows/by-status/ACTIVE", test_get_workflows_by_status)
run_test("4. Workflow Query", "GET /workflows/by-client-db/7", test_get_workflows_by_client_db)
run_test("4. Workflow Query", "GET /workflows/catalog", test_get_workflows_catalog)
run_test("4. Workflow Query", "GET /workflows/inspect/{code}", test_inspect_workflow)
run_test("4. Workflow Query", "GET /workflows/{code}", test_get_workflow_by_code)

# =========================================================================
# 5. WORKFLOW STUDIO METADATA & CATALOG
# =========================================================================
def test_studio_workflows_list():
    r = requests.get(f"{BASE_URL}/workflow-studio/workflows", timeout=5)
    return r.status_code == 200 and isinstance(r.json(), list), f"HTTP {r.status_code}, total={len(r.json())}"

def test_studio_roles():
    r = requests.get(f"{BASE_URL}/workflow-studio/roles", timeout=5)
    return r.status_code == 200 and isinstance(r.json(), list), f"HTTP {r.status_code}, count={len(r.json())}"

def test_studio_actions():
    r = requests.get(f"{BASE_URL}/workflow-studio/actions", timeout=5)
    return r.status_code == 200 and isinstance(r.json(), list), f"HTTP {r.status_code}, count={len(r.json())}"

def test_studio_metadata_entities():
    r = requests.get(f"{BASE_URL}/workflow-studio/metadata/entities", timeout=5)
    return r.status_code == 200 and isinstance(r.json(), list), f"HTTP {r.status_code}, count={len(r.json())}"

def test_studio_metadata_tables():
    r = requests.get(f"{BASE_URL}/workflow-studio/metadata/tables", timeout=5)
    return r.status_code == 200 and isinstance(r.json(), list), f"HTTP {r.status_code}, count={len(r.json())}"

def test_studio_catalog_workflows():
    r = requests.get(f"{BASE_URL}/workflow-studio/catalog/workflows", timeout=5)
    data = r.json()
    return r.status_code == 200 and "workflows" in data, f"HTTP {r.status_code}, count={data.get('total')}"

run_test("5. Studio Catalog", "GET /workflow-studio/workflows", test_studio_workflows_list)
run_test("5. Studio Catalog", "GET /workflow-studio/roles", test_studio_roles)
run_test("5. Studio Catalog", "GET /workflow-studio/actions", test_studio_actions)
run_test("5. Studio Catalog", "GET /workflow-studio/metadata/entities", test_studio_metadata_entities)
run_test("5. Studio Catalog", "GET /workflow-studio/metadata/tables", test_studio_metadata_tables)
run_test("5. Studio Catalog", "GET /workflow-studio/catalog/workflows", test_studio_catalog_workflows)

# =========================================================================
# 6. HUMAN TASKS, JOBS, MONITORING & EXECUTOR
# =========================================================================
def test_human_tasks():
    r = requests.get(f"{BASE_URL}/workflow/tasks", timeout=5)
    return r.status_code == 200, f"HTTP {r.status_code}, data={len(r.json().get('data', [])) if r.json().get('data') else 0} pending tasks"

def test_monitoring_instances():
    r = requests.get(f"{BASE_URL}/workflow/monitoring/instances", timeout=5)
    return r.status_code == 200, f"HTTP {r.status_code}"

def test_jobs_list():
    r = requests.get(f"{BASE_URL}/workflow/jobs", timeout=5)
    return r.status_code == 200, f"HTTP {r.status_code}"

def test_executor_status():
    r = requests.get(f"{BASE_URL}/workflow/executor/status", timeout=5)
    return r.status_code == 200, f"HTTP {r.status_code}, data={r.json().get('data')}"

run_test("6. Engine & Tasks", "GET /workflow/tasks", test_human_tasks)
run_test("6. Engine & Tasks", "GET /workflow/monitoring/instances", test_monitoring_instances)
run_test("6. Engine & Tasks", "GET /workflow/jobs", test_jobs_list)
run_test("6. Engine & Tasks", "GET /workflow/executor/status", test_executor_status)

# =========================================================================
# 7. CLIENT GATEWAYS & BINDINGS
# =========================================================================
def test_client_bindings():
    r = requests.get(f"{BASE_URL}/client/bindings", timeout=5)
    return r.status_code == 200, f"HTTP {r.status_code}, bindings={len(r.json().get('data', []))}"

def test_universal_gateway():
    payload = {
        "spec_id": "email_notification",
        "operation": "QUERY_STATUS",
        "data": {"id": 1},
        "user_id": 1,
        "user_name": "Jasmin"
    }
    r = requests.post(f"{BASE_URL}/api/v1/workflow-hub/gateway", json=payload, timeout=5)
    return r.status_code in [200, 201, 400], f"HTTP {r.status_code}, message={r.json().get('Error', {}).get('Error_message') or r.json().get('message')}"

run_test("7. Client Gateways", "GET /client/bindings", test_client_bindings)
run_test("7. Client Gateways", "POST /api/v1/workflow-hub/gateway", test_universal_gateway)

# =========================================================================
# SUMMARY
# =========================================================================
total = len(test_results)
passed = sum(1 for t in test_results if t["passed"])
failed = total - passed

print("\n" + "=" * 90)
print(f"ALL APIS VERIFICATION COMPLETE: {passed}/{total} Passed, {failed} Failed")
print("=" * 90)

if failed > 0:
    sys.exit(1)
