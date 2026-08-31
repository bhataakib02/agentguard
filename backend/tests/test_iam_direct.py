import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models

client = TestClient(app)

def test_01_public_registration_forces_user_role():
    res = client.post("/api/auth/register", json={
        "org_name": "Direct Test Org",
        "full_name": "Bob Test User",
        "email": "bob_direct_test@enterprise.ai",
        "password": "Password123!",
        "role": "SUPER_ADMIN"  # Privilege escalation attempt
    })
    assert res.status_code == 200, f"Registration failed: {res.text}"
    data = res.json()
    assert data["role"] == "USER", f"Expected forced role USER, got {data['role']}"
    print("\n  [SUCCESS] TEST 1: Public registration forced role to USER (privilege override ignored)")

def test_02_super_admin_assignment_protection():
    # Register Admin User
    admin_res = client.post("/api/auth/register", json={
        "org_name": "Org Security",
        "full_name": "Admin Tester",
        "email": "admin_security@enterprise.ai",
        "password": "Password123!"
    }).json()
    admin_token = admin_res["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Register Target User
    target_res = client.post("/api/auth/register", json={
        "org_name": "Org Security",
        "full_name": "Target Tester",
        "email": "target_security@enterprise.ai",
        "password": "Password123!"
    }).json()
    target_id = target_res["user_id"]

    # ADMIN attempts to assign SUPER_ADMIN -> MUST fail with 403 Forbidden
    res = client.patch(
        f"/api/admin/users/{target_id}/role",
        json={"role": "SUPER_ADMIN"},
        headers=headers
    )
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"
    print("  [SUCCESS] TEST 2: Standard ADMIN assigning SUPER_ADMIN rejected with 403 Forbidden")

def test_03_self_role_modification_protection():
    user_res = client.post("/api/auth/register", json={
        "org_name": "Self Org",
        "full_name": "Self Tester",
        "email": "self_tester@enterprise.ai",
        "password": "Password123!"
    }).json()
    user_id = user_res["user_id"]
    token = user_res["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(
        f"/api/admin/users/{user_id}/role",
        json={"role": "ADMIN"},
        headers=headers
    )
    assert res.status_code == 403, f"Expected 403 Forbidden for self modification, got {res.status_code}"
    print("  [SUCCESS] TEST 3: Self-role modification attempt rejected with 403 Forbidden")

def test_04_organization_isolation():
    user_a = client.post("/api/auth/register", json={
        "org_name": "Org Alpha Direct",
        "full_name": "User Alpha",
        "email": "user_alpha_direct@enterprise.ai",
        "password": "Password123!"
    }).json()
    token_a = user_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    user_b = client.post("/api/auth/register", json={
        "org_name": "Org Beta Direct",
        "full_name": "User Beta",
        "email": "user_beta_direct@enterprise.ai",
        "password": "Password123!"
    }).json()
    target_b_id = user_b["user_id"]

    res = client.patch(
        f"/api/admin/users/{target_b_id}/role",
        json={"role": "ANALYST"},
        headers=headers_a
    )
    assert res.status_code == 403, f"Expected 403 Forbidden for cross-org access, got {res.status_code}"
    print("  [SUCCESS] TEST 4: Cross-organization access rejected with 403 Forbidden")

if __name__ == "__main__":
    test_01_public_registration_forces_user_role()
    test_02_super_admin_assignment_protection()
    test_03_self_role_modification_protection()
    test_04_organization_isolation()
    print("\n============================================================")
    print("      ALL IAM ROLE & AUTHORIZATION MATRIX TESTS PASSED      ")
    print("============================================================")
