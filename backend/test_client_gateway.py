"""
test_client_gateway.py
Automated end-to-end verification of Step 4: Client Gateway & Client-side DB Query.
Tests:
1. Client Module Bindings: GET /client/bindings
2. Client DB Query (SELECT with filter, order, limit): POST /client/query
3. Client DB Query (INSERT): POST /client/query
4. Client DB Query (UPDATE): POST /client/query
5. Module Records Retrieval: GET /client/bindings/{module_key}/records
6. Client User Task Inbox: GET /client/tasks/my-tasks
"""

import sys
import json
from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)
    print("=" * 60)
    print("STEP 4 VERIFICATION: CLIENT GATEWAY & CLIENT-SIDE DB QUERY")
    print("=" * 60)

    # 1. GET /client/bindings
    print("\n[TEST 1] GET /client/bindings")
    res = client.get("/client/bindings")
    print(f"Status: {res.status_code}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    bindings = res.json()
    print(f"Registered module bindings count: {len(bindings)}")
    for key, val in list(bindings.items())[:3]:
        print(f"  - Module: {key} -> Table: {val.get('table_name')} (Workflow #{val.get('workflow_id')})")
    assert isinstance(bindings, dict), "Bindings must be a dictionary"
    print("PASSED [TEST 1]")

    # 2. POST /client/query - SELECT
    print("\n[TEST 2] POST /client/query (SELECT query on leave_requests)")
    select_payload = {
        "table_name": "leave_requests",
        "operation": "SELECT",
        "limit": 5,
        "order_direction": "DESC"
    }
    res = client.post("/client/query", json=select_payload)
    print(f"Status: {res.status_code}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert body.get("success") is True or "data" in body
    records = body.get("data", {}).get("records", [])
    print(f"Query returned {len(records)} records from leave_requests")
    if records:
        print(f"  Sample record: ID={records[0].get('leave_request_id')}, Status={records[0].get('status')}")
    print("PASSED [TEST 2]")

    # 3. POST /client/query - INSERT
    print("\n[TEST 3] POST /client/query (INSERT into leave_requests)")
    insert_payload = {
        "table_name": "leave_requests",
        "operation": "INSERT",
        "values": {
            "employee_id": 3,
            "leave_type_id": 1,
            "start_date": "2026-09-10",
            "end_date": "2026-09-12",
            "days": 2,
            "reason": "Automated Client Gateway Test",
            "status": "PENDING"
        }
    }
    res = client.post("/client/query", json=insert_payload)
    print(f"Status: {res.status_code}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    insert_res = res.json().get("data", {})
    created_id = insert_res.get("record_id")
    print(f"Inserted record #{created_id}")
    assert created_id is not None, "Created ID should not be None"
    print("PASSED [TEST 3]")

    # 4. POST /client/query - UPDATE
    print(f"\n[TEST 4] POST /client/query (UPDATE leave_requests record #{created_id})")
    update_payload = {
        "table_name": "leave_requests",
        "operation": "UPDATE",
        "filters": [
            {"field": "leave_request_id", "operator": "=", "value": created_id}
        ],
        "values": {
            "reason": "Updated by Client Gateway Automated Test",
            "status": "CANCELLED"
        }
    }
    res = client.post("/client/query", json=update_payload)
    print(f"Status: {res.status_code}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    affected = res.json().get("data", {}).get("affected_rows")
    print(f"Updated {affected} row(s)")
    assert affected >= 1, f"Expected at least 1 affected row, got {affected}"
    print("PASSED [TEST 4]")

    # 5. POST /client/query - SELECT with filter
    print(f"\n[TEST 5] POST /client/query (SELECT with WHERE filter for record #{created_id})")
    filter_payload = {
        "table_name": "leave_requests",
        "operation": "SELECT",
        "filters": [
            {"field": "leave_request_id", "operator": "=", "value": created_id}
        ]
    }
    res = client.post("/client/query", json=filter_payload)
    print(f"Status: {res.status_code}")
    assert res.status_code == 200
    filtered_records = res.json().get("data", {}).get("records", [])
    assert len(filtered_records) == 1, f"Expected 1 record, got {len(filtered_records)}"
    assert filtered_records[0].get("status") == "CANCELLED"
    print(f"Verified updated record: {filtered_records[0].get('reason')}")
    print("PASSED [TEST 5]")

    # 6. GET /client/bindings/leave_requests/records
    print("\n[TEST 6] GET /client/bindings/leave_requests/records")
    res = client.get("/client/bindings/leave_requests/records?limit=5")
    print(f"Status: {res.status_code}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    records = res.json().get("data", [])
    print(f"Fetched {len(records)} records for leave_requests module")
    assert isinstance(records, list)
    print("PASSED [TEST 6]")

    # 7. GET /client/tasks/my-tasks
    print("\n[TEST 7] GET /client/tasks/my-tasks?user_id=1")
    res = client.get("/client/tasks/my-tasks?user_id=1")
    print(f"Status: {res.status_code}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    tasks = res.json().get("data", [])
    print(f"User #1 pending task count: {len(tasks)}")
    assert isinstance(tasks, list)
    print("PASSED [TEST 7]")

    # 8. POST /client/bindings/leave_requests/submit (Clean decoupled workflow dispatch)
    print("\n[TEST 8] POST /client/bindings/leave_requests/submit")
    submit_payload = {
        "data": {
            "employee_id": 3,
            "leave_type_id": 1,
            "start_date": "2026-09-15",
            "end_date": "2026-09-16",
            "days": 1,
            "reason": "Workflow Submission from Client Gateway"
        },
        "user_id": 3,
        "user_name": "Gateway Test Bot",
        "user_email": "bot@company.com",
        "async_execution": True
    }
    res = client.post("/client/bindings/leave_requests/submit", json=submit_payload)
    print(f"Status: {res.status_code}")
    assert res.status_code in (200, 201), f"Expected 200/201, got {res.status_code}: {res.text}"
    sub_data = res.json().get("data", {})
    print(f"Submitted record #{sub_data.get('record_id')} with async job #{sub_data.get('job_id')}")
    print("PASSED [TEST 8]")

    # Cleanup test record
    print(f"\n[CLEANUP] Deleting test record #{created_id}")
    delete_payload = {
        "table_name": "leave_requests",
        "operation": "DELETE",
        "filters": [
            {"field": "leave_request_id", "operator": "=", "value": created_id}
        ]
    }
    del_res = client.post("/client/query", json=delete_payload)
    print(f"Cleanup status: {del_res.status_code}, affected: {del_res.json().get('data', {}).get('affected_rows')}")

    print("\n" + "=" * 60)
    print("ALL 8 STEP 4 CLIENT GATEWAY TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
