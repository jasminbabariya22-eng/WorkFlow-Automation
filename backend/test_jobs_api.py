import json
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("==========================================")
    print("TESTING WORKFLOW JOB & TASK LIFECYCLE APIS")
    print("==========================================")

    # 1. CREATE JOB
    print("\n[Step 1] Creating new execution job for Workflow #1125...")
    create_payload = {
        "workflow_id": 1124,
        "title": "Automated WFH Test Job",
        "entity_type": "generic_job",
        "variables": {
            "employee_id": 10,
            "days": 1,
            "reason": "Remote collaboration day"
        }
    }
    res = client.post("/workflow/jobs/create", json=create_payload)
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 201, f"Failed to create job: {res.text}"
    job_data = res.json()["data"]
    job_id = job_data["job_id"]
    print(f"==> Job Created successfully! Job ID: {job_id}, Status: {job_data['status']}")

    # 2. GET JOB STATUS
    print(f"\n[Step 2] Fetching status for Job #{job_id}...")
    res = client.get(f"/workflow/jobs/{job_id}/status")
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    status_data = res.json()["data"]
    assert status_data["job_id"] == job_id
    print(f"==> Status: {status_data['status']}, Current Node: {status_data['current_node_key']}, Progress: {status_data['progress_percent']}%")

    # 3. LIST JOBS
    print("\n[Step 3] Listing jobs with filter...")
    res = client.get("/workflow/jobs?limit=5")
    print(f"Response ({res.status_code}): total={res.json()['data']['total']}")
    assert res.status_code == 200
    assert len(res.json()["data"]["jobs"]) > 0

    # 4. PAUSE JOB
    print(f"\n[Step 4] Pausing Job #{job_id}...")
    res = client.post(f"/workflow/jobs/{job_id}/pause", json={"reason": "Testing pause operation"})
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "Paused"
    print(f"==> Job #{job_id} successfully PAUSED!")

    # Verify status reflects Paused
    res = client.get(f"/workflow/jobs/{job_id}/status")
    assert res.json()["data"]["status"] == "Paused"

    # 5. RESUME / START JOB
    print(f"\n[Step 5] Resuming Job #{job_id} via /start...")
    res = client.post(f"/workflow/jobs/{job_id}/start", json={"reason": "Resuming after test pause"})
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    assert res.json()["data"]["status"] in ["Running", "WAITING"]
    print(f"==> Job #{job_id} successfully RESUMED to {res.json()['data']['status']}!")

    # 6. STOP JOB
    print(f"\n[Step 6] Stopping Job #{job_id}...")
    res = client.post(f"/workflow/jobs/{job_id}/stop", json={"reason": "Testing stop operation"})
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "Stopped"
    print(f"==> Job #{job_id} successfully STOPPED!")

    # Verify status reflects Stopped
    res = client.get(f"/workflow/jobs/{job_id}/status")
    assert res.json()["data"]["status"] == "Stopped"

    # 7. RESTART JOB
    print(f"\n[Step 7] Restarting Job #{job_id}...")
    res = client.post(f"/workflow/jobs/{job_id}/restart", json={
        "variables": {"restarted": True, "notes": "Restarted via Lifecycle API"}
    })
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    assert res.json()["data"]["status"] in ["Running", "WAITING", "Completed"]
    print(f"==> Job #{job_id} successfully RESTARTED (status: {res.json()['data']['status']})!")

    # 8. GET JOB HISTORY
    print(f"\n[Step 8] Fetching execution history for Job #{job_id}...")
    res = client.get(f"/workflow/jobs/{job_id}/history")
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    history_data = res.json()["data"]
    print(f"==> Activity History Count: {history_data['activity_count']}")
    assert history_data["activity_count"] > 0

    print("\n==========================================")
    print("ALL LIFECYCLE TESTS PASSED PERFECTLY!")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
