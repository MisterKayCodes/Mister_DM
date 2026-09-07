import asyncio
from fastapi.testclient import TestClient
from api.server import app
import config

client = TestClient(app)

def test_health():
    print("Testing GET /api/v1/health (Unauthenticated)...")
    res = client.get("/api/v1/health")
    print("Status:", res.status_code)
    print("Response:", res.json())
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    print("--> Health check passed!\n")

def test_auth():
    print("Testing GET /api/v1/campaigns without API key...")
    res = client.get("/api/v1/campaigns")
    print("Status:", res.status_code)
    assert res.status_code == 401
    print("--> 401 Unauthorized check passed!\n")

    print("Testing GET /api/v1/campaigns WITH valid API key...")
    headers = {"X-API-Key": config.DM_API_KEY}
    res = client.get("/api/v1/campaigns", headers=headers)
    print("Status:", res.status_code)
    print("Response:", res.json())
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    print("--> 200 OK Authenticated check passed!\n")

def test_intake_lead():
    print("Testing POST /api/v1/leads/intake (Lead Intake Stub & Merge)...")
    headers = {"X-API-Key": config.DM_API_KEY}
    payload = {
        "campaign_id": 999,
        "username": "test_lead_user",
        "telegram_user_id": 987654321,
        "source_group": "@TestGroup",
        "profile_notes": "Test profile notes",
        "profile_confidence": 2
    }
    res = client.post("/api/v1/leads/intake", json=payload, headers=headers)
    print("Status:", res.status_code)
    print("Response:", res.json())
    assert res.status_code == 200
    print("--> Lead Intake check passed!\n")

if __name__ == "__main__":
    test_health()
    test_auth()
    test_intake_lead()
    print("=== ALL PHASE 1 API TESTS PASSED SUCCESSFULLY! ===")
