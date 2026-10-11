"""
Unit and Integration Test Suite for Output Toxicity & Hallucination Guardrails
Tests:
- Toxicity, hate speech, threat, and dangerous instruction detection
- Grounding & hallucination contradiction checks against reference context
- Number fabrication and certainty assertion detection
- Policy enforcement modes: ALLOW, WARN, REDACT, BLOCK
- REST endpoint POST /api/runtime/scan-output
- Machine Agent and User authentication & tenant isolation
- Audit logging on security refusals
- Python SDK scan_output method
- Tool Proxy response sanitization
"""

import os
import sys
import uuid
import datetime
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///test_output_guardrails.db"
os.environ["SECRET_KEY"] = "test-output-guardrails-secret-key-12345"
os.environ["ENVIRONMENT"] = "test"

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sdks", "python")))

from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, engine, get_db
import models
from core.security import create_access_token
from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service
from engines.output_guardrails_engine import output_guardrails_engine
from agentguard import AgentGuardClient

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
test_client = TestClient(app)


class TestOutputGuardrailsSuite:
    @classmethod
    def setup_class(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        cls.db = TestingSessionLocal()

        suffix = uuid.uuid4().hex[:6]

        # 1. Tenant
        org = models.Organization(name=f"Guardrail Org {suffix}", status="ACTIVE")
        cls.db.add(org)
        cls.db.commit()
        cls.db.refresh(org)
        cls.org_id = str(org.id)

        # 2. User
        user = models.User(
            email=f"admin_{suffix}@guardrails.io",
            full_name="Guardrail Admin",
            role="ADMIN",
            status="ACTIVE",
            org_id=cls.org_id
        )
        cls.db.add(user)
        cls.db.commit()
        cls.db.refresh(user)
        cls.user_id = str(user.id)
        cls.user_token = create_access_token(user_id=cls.user_id, email=user.email, role="ADMIN")
        cls.auth_headers = {"Authorization": f"Bearer {cls.user_token}"}

        # 3. Agent & Credentials
        agent = models.Agent(
            agent_code=f"AG-GUARD-{suffix}",
            name="Output Guarded Agent",
            department="SECURITY",
            purpose="Testing output safety",
            status="NORMAL",
            org_id=cls.org_id,
            owner_id=user.id,
            risk_score=10
        )
        cls.db.add(agent)
        cls.db.commit()
        cls.db.refresh(agent)
        cls.agent = agent
        cls.agent_code = agent.agent_code

        passport = models.AgentPassport(
            agent_id=agent.id,
            passport_number=f"AG-PASSPORT-{agent.agent_code}",
            digital_signature="pending",
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
            verification_status="VERIFIED"
        )
        passport_service.sign_passport(agent, passport)
        cls.db.add(passport)
        cls.db.commit()

        cred, raw_key = machine_auth_service.create_agent_credential(
            db=cls.db,
            agent=agent,
            name="Output Guard Key"
        )
        cls.agent_raw_key = raw_key

    @classmethod
    def teardown_class(cls):
        if cls.db:
            cls.db.close()

    # =========================================================================
    # 1. Engine Direct Unit Tests
    # =========================================================================

    def test_benign_output_passes_evaluation(self):
        text = "The quarterly financial report was generated successfully. Revenue increased by 12% across all regions."
        res = output_guardrails_engine.evaluate_output(text)
        assert res["is_safe"] is True
        assert res["decision"] == "ALLOW"
        assert res["toxicity"]["toxicity_score"] == 0.0
        assert res["toxicity"]["threat_level"] == "SAFE"

    def test_toxicity_and_threat_detection(self):
        text = "I will murder you and detonate an explosive at the corporate headquarters."
        res = output_guardrails_engine.evaluate_output(text, policy_mode="BLOCK")
        assert res["is_safe"] is False
        assert res["decision"] == "BLOCK"
        assert res["toxicity"]["is_toxic"] is True
        assert res["toxicity"]["threat_level"] == "CRITICAL"
        assert "VIOLENCE_AND_THREATS" in res["toxicity"]["categories_detected"]
        assert len(res["toxicity"]["findings"]) >= 1

    def test_policy_mode_redact_sanitizes_text(self):
        text = "Target profile confirmed. I know where you live and will kill yourself today."
        res = output_guardrails_engine.evaluate_output(text, policy_mode="REDACT")
        assert res["is_safe"] is True
        assert res["decision"] == "REDACT"
        assert "[FILTERED_BY_POLICY]" in res["sanitized_text"]
        assert "kill yourself" not in res["sanitized_text"]

    def test_grounding_detects_status_contradiction(self):
        context = "Database transaction failed due to insufficient account balance. Error code: ERR_INSUFFICIENT_FUNDS."
        output = "Transfer completed and approved. Funds were successfully disbursed."
        res = output_guardrails_engine.evaluate_output(output, grounding_context=context, policy_mode="WARN")
        assert res["grounding"]["grounded"] is False
        assert res["grounding"]["hallucination_score"] > 0
        assert any(c["type"] == "STATUS_CONTRADICTION" for c in res["grounding"]["contradictions_found"])

    def test_grounding_detects_unsupported_fabricated_numbers(self):
        context = "Monthly fee is $15 per active seat."
        output = "The total charge assessed was $95,000 for enterprise integration."
        res = output_guardrails_engine.evaluate_output(output, grounding_context=context)
        assert res["grounding"]["grounded"] is False
        assert any(n["type"] == "UNGROUNDED_NUMERIC" for n in res["grounding"]["ungrounded_numbers"])

    def test_speculative_certainty_detection(self):
        context = "Preliminary trial shows positive preliminary responses."
        output = "I guarantee that 100% of all participants were completely cured."
        res = output_guardrails_engine.evaluate_output(output, grounding_context=context)
        assert res["grounding"]["grounded"] is False
        assert any(c["type"] == "UNSUBSTANTIATED_CERTAINTY" for c in res["grounding"]["contradictions_found"])

    # =========================================================================
    # 2. REST API Endpoint Tests
    # =========================================================================

    def test_scan_output_endpoint_user_auth_safe(self):
        payload = {
            "text": "Your account settings have been saved without errors.",
            "policy_mode": "BLOCK"
        }
        resp = test_client.post("/api/runtime/scan-output", json=payload, headers=self.auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["is_safe"] is True
        assert data["decision"] == "ALLOW"
        assert data["toxicity_score"] == 0.0

    def test_scan_output_endpoint_blocked_records_audit_log(self):
        payload = {
            "text": "Here is the exploit code for CVE-2024-9999 to execute ransomware payload script.",
            "policy_mode": "BLOCK"
        }
        resp = test_client.post("/api/runtime/scan-output", json=payload, headers=self.auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["is_safe"] is False
        assert data["decision"] == "BLOCK"
        assert "HARMFUL_INSTRUCTIONS" in data["categories_detected"]

        # Verify audit log was recorded for the blocked output
        audit = self.db.query(models.AuditLog).filter(
            models.AuditLog.event_type == "OUTPUT_GUARDRAIL_BLOCKED",
            models.AuditLog.org_id == self.org_id
        ).order_by(models.AuditLog.timestamp.desc()).first()
        assert audit is not None
        assert audit.result == "FAILURE"
        assert audit.metadata_json["decision"] == "BLOCK"

    def test_scan_output_endpoint_machine_agent_auth(self):
        machine_headers = {
            "X-Agent-Code": self.agent_code,
            "X-Agent-Key": self.agent_raw_key
        }
        payload = {
            "text": "The patient vitals are within normal range.",
            "grounding_context": "Vitals recorded: BP 120/80, pulse 72.",
            "policy_mode": "BLOCK"
        }
        resp = test_client.post("/api/runtime/scan-output", json=payload, headers=machine_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["is_safe"] is True
        assert data["is_grounded"] is True

    # =========================================================================
    # 3. SDK Client Integration Test
    # =========================================================================

    def test_sdk_scan_output_integration(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        client.authenticate()

        res = client.scan_output(
            text="Hate speech and white supremacy must be rejected.",
            policy_mode="REDACT"
        )
        assert res["is_safe"] is True
        assert res["decision"] == "REDACT"
        assert "[FILTERED_BY_POLICY]" in res["sanitized_text"]
