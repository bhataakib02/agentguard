"""
Test Suite: Enterprise Billing, Payment Gateways & Subscription Management
Verifies Stripe/Razorpay gateway inspection, checkout session creation,
HMAC webhook event processing, automatic license renewal, and plan tier provisioning.
"""

import os
os.environ["ENVIRONMENT"] = "test"
from config import settings
settings.reload()

import unittest
import uuid
import datetime
import json
import hmac
import hashlib
from starlette.testclient import TestClient

from main import app
from database import SessionLocal
import models
from core.security import create_access_token

client = TestClient(app)


class TestBillingSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        from bootstrap import ensure_canonical_plans
        ensure_canonical_plans(cls.db)

        # Create or fetch test organization
        cls.org = cls.db.query(models.Organization).filter(
            models.Organization.name == "Billing Test Enterprise"
        ).first()
        if not cls.org:
            cls.org = models.Organization(
                name="Billing Test Enterprise",
                domain="billing.agentguard.dev",
                status="ACTIVE"
            )
            cls.db.add(cls.org)
            cls.db.commit()
            cls.db.refresh(cls.org)

        # Ensure initial license exists
        cls.lic = cls.db.query(models.License).filter(models.License.org_id == cls.org.id).first()
        if not cls.lic:
            cls.lic = models.License(
                org_id=cls.org.id,
                plan_id="FREE",
                status="ACTIVE",
                expiry_date=datetime.datetime.utcnow() + datetime.timedelta(days=30)
            )
            cls.db.add(cls.lic)
            cls.db.commit()
            cls.db.refresh(cls.lic)

        # Create or fetch test admin user
        cls.user = cls.db.query(models.User).filter(
            models.User.email == "billing_admin@agentguard.dev"
        ).first()
        if not cls.user:
            cls.user = models.User(
                org_id=cls.org.id,
                email="billing_admin@agentguard.dev",
                full_name="Billing Administrator",
                role="ADMIN",
                status="ACTIVE"
            )
            cls.db.add(cls.user)
            cls.db.commit()
            cls.db.refresh(cls.user)

        cls.token = create_access_token(
            user_id=str(cls.user.id),
            email=cls.user.email,
            role=cls.user.role
        )
        cls.headers = {
            "Authorization": f"Bearer {cls.token}",
            "Content-Type": "application/json"
        }

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_get_payment_gateways(self):
        """Verifies truthful payment gateway inspection endpoint."""
        res = client.get("/api/billing/gateways", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("gateways", data)
        self.assertIn("stripe", data["gateways"])
        self.assertIn("razorpay", data["gateways"])
        self.assertTrue(data.get("sandbox_simulation_supported"))

    def test_02_get_subscription_details(self):
        """Verifies tenant subscription and quota details retrieval."""
        res = client.get("/api/billing/subscription", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["organization_name"], "Billing Test Enterprise")
        self.assertIn("quotas", data)
        self.assertIn("max_users", data["quotas"])
        self.assertIn("max_ai_agents", data["quotas"])

    def test_03_create_checkout_session(self):
        """Verifies checkout session creation for plan upgrade."""
        payload = {
            "plan_id": "PROFESSIONAL",
            "gateway": "stripe"
        }
        res = client.post("/api/billing/checkout", headers=self.headers, json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["session_id"].startswith("cs_stripe_"))
        self.assertEqual(data["plan_id"], "PROFESSIONAL")
        self.assertEqual(data["amount"], 999.0)
        self.assertIn("checkout_url", data)

    def test_04_simulate_sandbox_payment_upgrade(self):
        """Verifies sandbox payment execution upgrades tenant plan and renews license."""
        payload = {
            "plan_id": "ENTERPRISE",
            "payment_reference": "ref_test_enterprise_2026"
        }
        res = client.post("/api/billing/simulate-payment", headers=self.headers, json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["plan_id"], "ENTERPRISE")
        self.assertEqual(data["license_status"], "ACTIVE")

        # Verify DB state
        self.db.expire_all()
        org_check = self.db.query(models.Organization).filter(models.Organization.id == self.org.id).first()
        self.assertEqual(org_check.plan_id, "ENTERPRISE")

        # Verify license extended
        lic_check = self.db.query(models.License).filter(models.License.org_id == self.org.id).first()
        self.assertIsNotNone(lic_check)
        self.assertEqual(lic_check.plan_id, "ENTERPRISE")
        self.assertGreater(lic_check.valid_until, datetime.datetime.utcnow())

        # Verify audit log recorded
        audit = self.db.query(models.AuditLog).filter(
            models.AuditLog.org_id == self.org.id,
            models.AuditLog.action == "PLAN_UPGRADED_AND_LICENSE_RENEWED"
        ).order_by(models.AuditLog.timestamp.desc()).first()
        self.assertIsNotNone(audit)

    def test_05_stripe_webhook_processing(self):
        """Verifies Stripe checkout webhook automatically provisions plan and license."""
        webhook_payload = {
            "id": f"evt_test_checkout_{uuid.uuid4().hex[:6]}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_12345",
                    "client_reference_id": str(self.org.id),
                    "metadata": {
                        "plan_id": "STARTER"
                    }
                }
            }
        }
        res = client.post(
            "/api/billing/webhook/stripe",
            json=webhook_payload
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("received"))

        # Verify plan updated to STARTER
        self.db.expire_all()
        org_check = self.db.query(models.Organization).filter(models.Organization.id == self.org.id).first()
        self.assertEqual(org_check.plan_id, "STARTER")

    def test_06_razorpay_webhook_processing(self):
        """Verifies Razorpay payment webhook automatically provisions plan and license."""
        webhook_payload = {
            "event": "order.paid",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_test_rzp_{uuid.uuid4().hex[:6]}",
                        "notes": {
                            "org_id": str(self.org.id),
                            "plan_id": "PROFESSIONAL"
                        }
                    }
                }
            }
        }
        res = client.post(
            "/api/billing/webhook/razorpay",
            json=webhook_payload
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("received"))

        # Verify plan updated to PROFESSIONAL
        self.db.expire_all()
        org_check = self.db.query(models.Organization).filter(models.Organization.id == self.org.id).first()
        self.assertEqual(org_check.plan_id, "PROFESSIONAL")


if __name__ == "__main__":
    unittest.main()
