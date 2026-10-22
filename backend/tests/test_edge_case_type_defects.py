import unittest
import uuid
import sys
import os
import shutil

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
test_db_path = os.path.join(backend_dir, "test_agentguard_global.db")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{test_db_path}")
os.environ.setdefault("SECRET_KEY", "agentguard-test-secret-key-32charactersmin")
os.environ.setdefault("ALLOW_DEMO_SEED", "true")
os.environ.setdefault("AGENTGUARD_ALLOW_LOCAL_TOOLS", "false")

sys.path.insert(0, backend_dir)
from starlette.testclient import TestClient
from main import app
from database import SessionLocal
from core import security
import models
from engines.digital_twin_engine import digital_twin_engine
from routers.profile import build_profile_response
from routers.reports import STORAGE_DIR

client = TestClient(app)


class TestEdgeCaseTypeDefects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Guarantee cleanup runs even if setUpClass fails partway through
        cls.addClassCleanup(cls.cleanup_resources)
        cls.db = SessionLocal()

        # Isolated test tenant
        cls.org = models.Organization(
            name=f"EdgeCase Org {uuid.uuid4().hex[:6]}",
            status="ACTIVE"
        )
        cls.db.add(cls.org)
        cls.db.commit()
        cls.db.refresh(cls.org)

        cls.user = models.User(
            org_id=cls.org.id,
            email=f"user_edge_{uuid.uuid4().hex[:6]}@example.com",
            full_name="Edge Case User",
            role="ADMIN",
            status="ACTIVE"
        )
        cls.db.add(cls.user)
        cls.db.commit()
        cls.db.refresh(cls.user)

        cls.token = security.create_access_token(
            cls.user.id, email=cls.user.email, role="ADMIN"
        )

        cls.agent = models.Agent(
            org_id=cls.org.id,
            owner_id=cls.user.id,
            agent_code=f"AG-EDGE-{uuid.uuid4().hex[:4].upper()}",
            name="Edge Case Agent",
            purpose="Testing edge cases",
            department="Operations",
            autonomy_level="MEDIUM",
            status="NORMAL"
        )
        cls.db.add(cls.agent)
        cls.db.commit()
        cls.db.refresh(cls.agent)

    @classmethod
    def cleanup_resources(cls):
        """Clean up all database records and disk artifacts created by this test class."""
        org_id = str(cls.org.id) if (hasattr(cls, "org") and cls.org is not None) else None
        user_id = str(cls.user.id) if (hasattr(cls, "user") and cls.user is not None) else None
        agent_id = str(cls.agent.id) if (hasattr(cls, "agent") and cls.agent is not None) else None

        if org_id is not None:
            db = SessionLocal()
            try:
                # 1. Delete audit logs associated with this org or actor
                if user_id:
                    db.query(models.AuditLog).filter(
                        (models.AuditLog.org_id == org_id)
                        | ((models.AuditLog.actor_id == user_id) & models.AuditLog.org_id.is_(None))
                    ).delete(synchronize_session=False)
                else:
                    db.query(models.AuditLog).filter(models.AuditLog.org_id == org_id).delete(synchronize_session=False)

                # 2. Delete report histories
                db.query(models.ReportHistory).filter(models.ReportHistory.org_id == org_id).delete(synchronize_session=False)

                # 3. Delete budget configurations
                db.query(models.AgentBudgetConfig).filter(models.AgentBudgetConfig.org_id == org_id).delete(synchronize_session=False)

                # 4. Delete telemetry & execution risk signals
                db.query(models.RuntimeRiskSignal).filter(models.RuntimeRiskSignal.org_id == org_id).delete(synchronize_session=False)
                db.query(models.AgentExecution).filter(models.AgentExecution.org_id == org_id).delete(synchronize_session=False)

                # 5. Delete agent child records if any were created
                if agent_id:
                    db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent_id).delete(synchronize_session=False)
                    db.query(models.BehaviorProfile).filter(models.BehaviorProfile.agent_id == agent_id).delete(synchronize_session=False)
                    db.query(models.Decision).filter(models.Decision.agent_id == agent_id).delete(synchronize_session=False)
                    db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == agent_id).delete(synchronize_session=False)
                    db.query(models.AgentCredential).filter(models.AgentCredential.agent_id == agent_id).delete(synchronize_session=False)
                    db.query(models.Permission).filter(models.Permission.agent_id == agent_id).delete(synchronize_session=False)
                    db.query(models.Agent).filter(models.Agent.id == agent_id).delete(synchronize_session=False)
                else:
                    db.query(models.Agent).filter(models.Agent.org_id == org_id).delete(synchronize_session=False)

                # 6. Delete user(s)
                if user_id:
                    db.query(models.User).filter(models.User.id == user_id).delete(synchronize_session=False)
                else:
                    db.query(models.User).filter(models.User.org_id == org_id).delete(synchronize_session=False)

                # 7. Delete organization
                db.query(models.Organization).filter(models.Organization.id == org_id).delete(synchronize_session=False)
                db.commit()

                # Clean up any generated report directory on disk for this org
                org_dir = os.path.join(STORAGE_DIR, f"org_{org_id}")
                if os.path.exists(org_dir):
                    if os.path.abspath(org_dir) != os.path.abspath(STORAGE_DIR):
                        shutil.rmtree(org_dir)
            except Exception as exc:
                db.rollback()
                raise RuntimeError(f"Database cleanup failed in TestEdgeCaseTypeDefects: {exc}") from exc
            finally:
                db.close()
                cls.org = None
                cls.user = None
                cls.agent = None

        if hasattr(cls, "db") and cls.db is not None:
            try:
                cls.db.close()
            finally:
                cls.db = None

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_resources()

    def test_01_optimization_compute_usage_empty_dataset(self):
        """Confirm get_compute_usage handles None/empty stats safely without 500 error."""
        resp = client.get(
            "/api/optimization/compute",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["observed_executions"], 0)
        self.assertEqual(data["active_agents_count"], 0)
        self.assertEqual(data["total_tokens_consumed"], 0)
        self.assertEqual(data["total_cost_incurred"], "₹0.00")
        self.assertIsNone(data["avg_latency_ms"])

    def test_02_telemetry_token_usage_empty_dataset(self):
        """Confirm get_token_usage handles None/empty stats safely without 500 error."""
        resp = client.get(
            "/api/telemetry/token-usage",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["input_tokens"], 0)
        self.assertEqual(data["output_tokens"], 0)
        self.assertEqual(data["total_tokens"], 0)
        self.assertEqual(data["total_cost"], 0.0)
        self.assertEqual(data["execution_count"], 0)
        self.assertEqual(data["avg_latency_ms"], 0.0)

    def test_03_profile_build_response_handles_string_and_none_roles(self):
        """Confirm /api/profile/me and build_profile_response safely handle None or string roles."""
        # 1. Test externally visible endpoint /api/profile/me
        resp = client.get(
            "/api/profile/me",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(resp.status_code, 200)
        p_data = resp.json()
        self.assertEqual(p_data["role"], "ADMIN")
        self.assertEqual(p_data["role_level"], 8)
        self.assertIn("effective_permissions", p_data)

        # 2. Test helper response builder with normal user
        profile_res = build_profile_response(self.user, self.db)
        self.assertIn("effective_permissions", profile_res)
        self.assertIn("role_level", profile_res)
        self.assertEqual(profile_res["role_level"], 8)  # ADMIN role level

        # 3. Test proxy user with role=None
        temp_user = models.User(
            id=str(uuid.uuid4()),
            org_id=self.org.id,
            email="norole@example.com",
            role=None,
            status="ACTIVE"
        )
        profile_res_fallback = build_profile_response(temp_user, self.db)
        self.assertEqual(profile_res_fallback["role_level"], 1)  # Fallback to USER (1)

    def test_04_digital_twin_float_budget_comparison(self):
        """Confirm digital twin engine properly compares total_projected_tokens and limit_tokens."""
        # 1. Budget with high token limit (should NOT trip circuit breaker)
        b_cfg = models.AgentBudgetConfig(
            org_id=self.org.id,
            agent_id=self.agent.id,
            daily_token_limit=100000000,  # 100M tokens
            daily_cost_limit=50000.0
        )
        self.db.add(b_cfg)
        self.db.commit()

        res_ok = digital_twin_engine.run_simulation(
            agent=self.agent,
            scenario_type="TRAFFIC_SPIKE",
            db=self.db
        )
        self.assertFalse(res_ok["metrics"]["circuit_breaker_tripped"])

        # 2. Tight budget (should trip circuit breaker under 50k simulated requests)
        b_cfg.daily_token_limit = 100  # Extremely low limit
        self.db.commit()

        res_trip = digital_twin_engine.run_simulation(
            agent=self.agent,
            scenario_type="TRAFFIC_SPIKE",
            db=self.db
        )
        self.assertTrue(res_trip["metrics"]["circuit_breaker_tripped"])

    def test_05_runtime_agent_summary_empty_dataset(self):
        """Confirm get_agent_runtime_summary handles agent with zero telemetry."""
        resp = client.get(
            f"/api/telemetry/agent-summary/{self.agent.id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["executions"], 0)
        self.assertEqual(data["total_tokens"], 0)
        self.assertEqual(data["total_cost"], 0.0)
        self.assertEqual(data["avg_risk_score"], 0.0)

    def test_06_reports_excel_generation_and_safe_path(self):
        """Confirm Excel report generation handles workbook worksheet safely and file downloads handle missing files."""
        # 1. Generate Excel report
        gen_resp = client.post(
            "/api/reports/generate",
            json={
                "report_type": "AUDIT",
                "file_format": "EXCEL",
                "include_charts": False
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(gen_resp.status_code, 200)
        report_data = gen_resp.json()
        self.assertIn("report_id", report_data)
        report_id = report_data["report_id"]

        # 2. Download valid generated report
        dl_resp = client.get(
            f"/api/reports/download/{report_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(dl_resp.status_code, 200)
        self.assertEqual(dl_resp.headers.get("content-type"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # 3. Create dummy report record pointing to a non-existent file on disk
        missing_rec = models.ReportHistory(
            org_id=self.org.id,
            user_id=self.user.id,
            title="Missing Report",
            report_type="AUDIT",
            file_format="EXCEL",
            file_path="C:\\non_existent_dir\\missing_report.xlsx",
            file_size_bytes=0,
            filters_json={}
        )
        self.db.add(missing_rec)
        self.db.commit()

        # 4. Attempt download -> should return clean 404 without crashing or 500
        dl_missing_resp = client.get(
            f"/api/reports/download/{missing_rec.id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(dl_missing_resp.status_code, 404)
        self.assertIn("Report file not found on disk", dl_missing_resp.json()["detail"])

    def test_07_passport_service_null_key_fail_closed(self):
        """Confirm PassportSigningService fails closed with RuntimeError if keys are uninitialized."""
        from services.passport_service import PassportSigningService
        service = PassportSigningService()

        # Simulate uninitialized key failure condition
        service._public_key = None
        service._private_key = None
        service._initialize_keys = lambda: None  # Prevent automatic HKDF derivation

        with self.assertRaises(RuntimeError) as cm_pub:
            service.get_public_key_bytes()
        self.assertIn("Platform public key is uninitialized", str(cm_pub.exception))

        with self.assertRaises(RuntimeError) as cm_priv:
            class MockPassport:
                def __init__(self, agent_id):
                    self.id = uuid.uuid4()
                    self.agent_id = agent_id
                    self.passport_number = "PASS-TEST-1234"
                    self.issued_at = None
                    self.expires_at = None
                    self.capabilities = []
                    self.digital_signature = None
                    self.algorithm = "Ed25519"
                    self.key_id = None
                    self.passport_version = "1.0"
                    self.claims = {}

            dummy_passport = MockPassport(agent_id=self.agent.id)
            service.sign_passport(self.agent, dummy_passport, capabilities=[])
        self.assertIn("Platform private key is uninitialized", str(cm_priv.exception))

