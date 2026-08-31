import unittest
import requests
import uuid

BASE_URL = "http://127.0.0.1:8000/api/v1"

class TestIamRoleMatrix(unittest.TestCase):

    def test_01_registration_forces_user_role(self):
        """TEST 1-5: Public registration MUST force role to USER even if ADMIN/SUPER_ADMIN is passed."""
        email = f"test_user_{uuid.uuid4().hex[:6]}@enterprise.ai"
        payload = {
            "org_name": "Test Org One",
            "full_name": "Alice Test User",
            "email": email,
            "password": "SecurePassword123!",
            "role": "SUPER_ADMIN"  # Intentionally attempt privilege escalation
        }
        res = requests.post(f"{BASE_URL}/auth/register", json=payload)
        self.assertEqual(res.status_code, 200, f"Registration failed: {res.text}")
        data = res.json()
        self.assertEqual(data["role"], "USER", f"Expected forced role USER, got {data['role']}")
        print(f"  [SUCCESS] TEST 1-5: Public registration with role=SUPER_ADMIN payload forced to USER role.")
        return data

    def test_02_super_admin_assignment_protection(self):
        """TEST 14: ADMIN attempting to assign SUPER_ADMIN must be rejected with 403 Forbidden."""
        # 1. Register Admin User
        admin_email = f"admin_{uuid.uuid4().hex[:6]}@enterprise.ai"
        reg_admin = requests.post(f"{BASE_URL}/auth/register", json={
            "org_name": "Org Alpha",
            "full_name": "Admin User",
            "email": admin_email,
            "password": "Password123!"
        }).json()
        admin_token = reg_admin["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Register Target User
        target_email = f"target_{uuid.uuid4().hex[:6]}@enterprise.ai"
        reg_target = requests.post(f"{BASE_URL}/auth/register", json={
            "org_name": "Org Alpha",
            "full_name": "Target User",
            "email": target_email,
            "password": "Password123!"
        }).json()
        target_id = reg_target["user_id"]

        # 3. Standard ADMIN attempts to upgrade Target User to SUPER_ADMIN -> MUST fail with 403
        res = requests.patch(
            f"{BASE_URL}/admin/users/{target_id}/role",
            json={"role": "SUPER_ADMIN"},
            headers=headers
        )
        self.assertEqual(res.status_code, 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}")
        print("  [SUCCESS] TEST 14: Standard ADMIN attempting to assign SUPER_ADMIN rejected with 403 Forbidden.")

    def test_03_self_role_modification_protection(self):
        """TEST 15-16: User attempting self role modification MUST receive 403 Forbidden."""
        user_email = f"self_user_{uuid.uuid4().hex[:6]}@enterprise.ai"
        reg_data = requests.post(f"{BASE_URL}/auth/register", json={
            "org_name": "Org Self",
            "full_name": "Self User",
            "email": user_email,
            "password": "Password123!"
        }).json()
        user_id = reg_data["user_id"]
        token = reg_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt self-escalation to ADMIN
        res = requests.patch(
            f"{BASE_URL}/admin/users/{user_id}/role",
            json={"role": "ADMIN"},
            headers=headers
        )
        self.assertEqual(res.status_code, 403, f"Expected 403 Forbidden for self modification, got {res.status_code}")
        print("  [SUCCESS] TEST 15-16: Self-role modification attempt rejected with 403 Forbidden.")

    def test_04_organization_isolation(self):
        """TEST 19: Organization A Admin accessing Organization B user must be denied."""
        # Create Org A User
        user_a = requests.post(f"{BASE_URL}/auth/register", json={
            "org_name": "Org A",
            "full_name": "User A",
            "email": f"usera_{uuid.uuid4().hex[:6]}@enterprise.ai",
            "password": "Password123!"
        }).json()
        token_a = user_a["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Create Org B User
        user_b = requests.post(f"{BASE_URL}/auth/register", json={
            "org_name": "Org B",
            "full_name": "User B",
            "email": f"userb_{uuid.uuid4().hex[:6]}@enterprise.ai",
            "password": "Password123!"
        }).json()
        target_b_id = user_b["user_id"]

        # User A attempts to modify User B -> MUST fail with 403 Forbidden
        res = requests.patch(
            f"{BASE_URL}/admin/users/{target_b_id}/role",
            json={"role": "ANALYST"},
            headers=headers_a
        )
        self.assertEqual(res.status_code, 403, f"Expected 403 for cross-org access, got {res.status_code}")
        print("  [SUCCESS] TEST 19: Cross-organization role modification attempt rejected with 403 Forbidden.")

if __name__ == "__main__":
    print("=" * 60)
    print("  AGENTGUARD PRODUCTION IAM & ROLE SECURITY MATRIX SUITE  ")
    print("=" * 60)
    unittest.main()
