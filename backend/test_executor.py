import time
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("==========================================")
    print("TESTING WORKFLOW JOB EXECUTOR (STEP 2)")
    print("==========================================")

    # 1. GET EXECUTOR STATUS
    print("\n[Step 1] Checking Executor Status...")
    res = client.get("/workflow/executor/status")
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    metrics = res.json()["data"]
    assert metrics["status"] == "HEALTHY"
    assert metrics["max_workers"] > 0
    print(f"==> Executor is HEALTHY with {metrics['max_workers']} worker threads.")

    # 2. PAUSE EXECUTOR
    print("\n[Step 2] Pausing Executor...")
    res = client.post("/workflow/executor/pause")
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "PAUSED"
    print("==> Executor successfully PAUSED!")

    # Verify status reflects PAUSED
    res = client.get("/workflow/executor/status")
    assert res.json()["data"]["status"] == "PAUSED"

    # 3. RESUME EXECUTOR
    print("\n[Step 3] Resuming Executor...")
    res = client.post("/workflow/executor/resume")
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "HEALTHY"
    print("==> Executor successfully RESUMED!")

    # 4. ASYNC JOB SUBMISSION
    print("\n[Step 4] Submitting Asynchronous Job (async_execution=True)...")
    start_t = time.time()
    payload = {
        "workflow_id": 1124,
        "title": "Async Executor Test Job",
        "entity_type": "generic_job",
        "async_execution": True,
        "variables": {
            "employee_id": 12,
            "days": 2,
            "reason": "Testing asynchronous executor worker execution"
        }
    }
    res = client.post("/workflow/jobs/create", json=payload)
    elapsed_ms = round((time.time() - start_t) * 1000, 2)
    print(f"Response ({res.status_code}) in {elapsed_ms}ms:", res.json())
    assert res.status_code == 202
    job_data = res.json()["data"]
    job_id = job_data["job_id"]
    assert job_data["status"] == "QUEUED"
    assert job_data["async_dispatched"] is True
    print(f"==> Non-blocking response in {elapsed_ms}ms! Job #{job_id} is QUEUED.")

    # 5. WAIT FOR BACKGROUND WORKER TO PROCESS
    print(f"\n[Step 5] Waiting for background worker to process Job #{job_id}...")
    time.sleep(1.5)

    # 6. VERIFY JOB WAS PROCESSED BY WORKER
    res = client.get(f"/workflow/jobs/{job_id}/status")
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    updated_status = res.json()["data"]["status"]
    print(f"==> Job #{job_id} was picked up and processed by background worker! Current Status: {updated_status}")
    assert updated_status in ["WAITING", "Running", "Completed"]

    # 7. DISPATCH EXISTING JOB TO EXECUTOR
    print(f"\n[Step 7] Testing manual dispatch of Job #{job_id} to executor...")
    res = client.post("/workflow/executor/dispatch", json={"job_id": job_id})
    print(f"Response ({res.status_code}):", res.json())
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "DISPATCHED"
    print(f"==> Job #{job_id} successfully re-dispatched to worker pool.")

    # 8. VERIFY METRICS UPDATED
    res = client.get("/workflow/executor/status")
    final_metrics = res.json()["data"]
    print("\n[Step 8] Final Executor Metrics:", final_metrics)
    assert final_metrics["total_submitted"] >= 1
    print(f"==> Total Submitted: {final_metrics['total_submitted']}, Total Completed: {final_metrics['total_completed']}")

    print("\n==========================================")
    print("ALL EXECUTOR TESTS PASSED PERFECTLY!")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
