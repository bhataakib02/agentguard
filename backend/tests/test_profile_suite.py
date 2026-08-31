import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_01_get_real_user_profile():
    # Register test user
    reg = client.post("/api/auth/register", json={
        "org_name": "Profile Test Org",
        "full_name": "Prof User",
        "email": "prof_user@enterprise.ai",
        "password": "Password123!"
    }).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/profile/me", headers=headers)
    assert res.status_code == 200, f"Get profile failed: {res.text}"
    data = res.json()
    assert data["email"] == "prof_user@enterprise.ai"
    assert data["role"] == "USER"
    assert data["role_level"] == 1
    assert "dashboard:read" in data["effective_permissions"]
    print("\n  [SUCCESS] TEST 1: Real user profile & permissions fetched successfully!")

def test_02_update_allowed_profile_fields():
    reg = client.post("/api/auth/register", json={
        "org_name": "Profile Edit Org",
        "full_name": "Edit Tester",
        "email": "edit_tester@enterprise.ai",
        "password": "Password123!"
    }).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(
        "/api/profile/me",
        json={
            "full_name": "Updated Name",
            "department": "Security Research",
            "job_title": "Senior Engineer",
            "phone": "+1 555-9876"
        },
        headers=headers
    )
    assert res.status_code == 200, f"Profile update failed: {res.text}"

    # Verify updated fields in database
    prof = client.get("/api/profile/me", headers=headers).json()
    assert prof["full_name"] == "Updated Name"
    assert prof["department"] == "Security Research"
    assert prof["job_title"] == "Senior Engineer"
    print("  [SUCCESS] TEST 2: Allowed profile fields updated successfully in database!")

def test_03_privilege_escalation_attempt_rejected():
    reg = client.post("/api/auth/register", json={
        "org_name": "Hacker Org",
        "full_name": "Attacker User",
        "email": "attacker@enterprise.ai",
        "password": "Password123!"
    }).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt malicious profile update with role escalation payload
    res = client.patch(
        "/api/profile/me",
        json={"role": "SUPER_ADMIN"},
        headers=headers
    )
    assert res.status_code == 403, f"Expected 403 Forbidden for role escalation, got {res.status_code}"
    print("  [SUCCESS] TEST 3: Privilege escalation via profile update rejected with 403 Forbidden!")

def test_04_user_sessions_and_activity():
    reg = client.post("/api/auth/register", json={
        "org_name": "Activity Org",
        "full_name": "Activity User",
        "email": "act_user@enterprise.ai",
        "password": "Password123!"
    }).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sess_res = client.get("/api/profile/sessions", headers=headers)
    assert sess_res.status_code == 200
    print("  [SUCCESS] TEST 4: User active sessions fetched successfully!")

    act_res = client.get("/api/profile/activity", headers=headers)
    assert act_res.status_code == 200
    print("  [SUCCESS] TEST 5: User personal activity logs fetched successfully!")

if __name__ == "__main__":
    test_01_get_real_user_profile()
    test_02_update_allowed_profile_fields()
    test_03_privilege_escalation_attempt_rejected()
    test_04_user_sessions_and_activity()
    print("\n============================================================")
    print("      ALL USER PROFILE & SECURITY MATRIX TESTS PASSED      ")
    print("============================================================")
