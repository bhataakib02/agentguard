"""
Test Suite: AI Model Governance, Pricing, Dynamic Router & AI Admin Assistant
Verifies database-backed AI model catalog, token pricing schedules,
complexity-driven dynamic model selection, and AI Assistant copilot querying.
"""

import unittest
from starlette.testclient import TestClient

from main import app
from database import SessionLocal
import models
from core.security import create_access_token

client = TestClient(app)


class TestAiModelAndAssistantSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        cls.org = cls.db.query(models.Organization).filter(
            models.Organization.name == "AI Governance Enterprise"
        ).first()
        if not cls.org:
            cls.org = models.Organization(
                name="AI Governance Enterprise",
                domain="ai.agentguard.dev",
                status="ACTIVE"
            )
            cls.db.add(cls.org)
            cls.db.commit()
            cls.db.refresh(cls.org)

        cls.user = cls.db.query(models.User).filter(
            models.User.email == "ai_admin@agentguard.dev"
        ).first()
        if not cls.user:
            cls.user = models.User(
                org_id=cls.org.id,
                email="ai_admin@agentguard.dev",
                full_name="AI Governance Administrator",
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

    def test_01_get_ai_models_catalog(self):
        """Verifies database-backed AI model catalog retrieval."""
        res = client.get("/api/ai/models", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        models_data = res.json()
        self.assertIsInstance(models_data, list)
        self.assertGreaterEqual(len(models_data), 3)

        model_names = [m["model_name"] for m in models_data]
        self.assertIn("gpt-4o", model_names)
        self.assertIn("claude-3-5-sonnet", model_names)
        self.assertIn("gemini-1.5-pro", model_names)

    def test_02_register_custom_ai_model(self):
        """Verifies custom enterprise AI model registration in catalog."""
        payload = {
            "model_name": "llama-3-70b-instruct",
            "provider": "Meta/Local",
            "cost_per_1k_tokens": 0.0008,
            "avg_latency_ms": 180,
            "accuracy_rating": 0.96,
            "status": "ACTIVE"
        }
        res = client.post("/api/ai/models", headers=self.headers, json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["model_name"], "llama-3-70b-instruct")
        self.assertEqual(data["provider"], "Meta/Local")
        self.assertEqual(data["cost_per_1k_tokens"], 0.0008)

    def test_03_get_model_pricing_schedule(self):
        """Verifies token pricing schedule retrieval from database."""
        res = client.get("/api/ai/pricing", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        pricings = res.json()
        self.assertIsInstance(pricings, list)
        self.assertGreaterEqual(len(pricings), 1)
        for p in pricings:
            self.assertIn("provider", p)
            self.assertIn("input_cost_per_1k", p)
            self.assertIn("output_cost_per_1k", p)

    def test_04_dynamic_model_routing_high_complexity(self):
        """Verifies flagship model selection for high-complexity governance tasks."""
        payload = {"task_complexity": "HIGH"}
        res = client.post("/api/ai/select", headers=self.headers, json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["tier"], "FLAGSHIP")
        self.assertIn(data["selected_model"], ["gpt-4o", "claude-3-5-sonnet"])
        self.assertGreaterEqual(data["accuracy_rating"], 0.98)

    def test_05_dynamic_model_routing_low_complexity_fast(self):
        """Verifies lightweight model selection for low-complexity high-throughput tasks."""
        payload = {"task_complexity": "LOW", "max_latency_ms": 200}
        res = client.post("/api/ai/select", headers=self.headers, json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["tier"], "LIGHTWEIGHT")
        self.assertLessEqual(data["avg_latency_ms"], 200)

    def test_06_get_llm_provider_status(self):
        """Verifies truthful inspection of external LLM provider API credentials."""
        res = client.get("/api/ai/providers", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("providers", data)
        self.assertIn("openai", data["providers"])
        self.assertIn("anthropic", data["providers"])
        self.assertIn("gemini", data["providers"])

    def test_07_ai_admin_assistant_query_copilot(self):
        """Verifies AI Assistant processes governance queries with live data synthesis."""
        payload = {"question": "What is our current agent headcount and security status?"}
        res = client.post("/api/assistant/query", headers=self.headers, json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("question", data)
        self.assertIn("answer", data)
        self.assertIn("data", data)
        self.assertIn("recommendations", data)
        self.assertIn("provider", data)


if __name__ == "__main__":
    unittest.main()
