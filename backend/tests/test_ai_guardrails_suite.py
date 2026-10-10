"""
Milestone 4: AI Guardrails & Security Intelligence Test Suite
Tests PII redaction & data exfiltration filtering, statistical behavioral anomaly baselining,
dynamic red-team policy fuzzing with payload mutations, and runtime kernel guardrails.
"""

import pytest
import datetime
from fastapi.testclient import TestClient
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
import models
from core.security import get_password_hash, create_access_token
from engines.pii_engine import pii_engine
from engines.behavior_engine import behavior_engine
from engines.red_team_engine import red_team_engine
from services.passport_service import passport_service

from database import Base, engine, get_db

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestAIGuardrailsSuite:
    db = None
    org_id = None
    user_id = None
    user_token = None
    agent_id = None
    agent_code = "AG-GUARD-01"

    @classmethod
    def setup_class(cls):
        import uuid
        Base.metadata.create_all(bind=engine)
        cls.db = TestingSessionLocal()
        suffix = uuid.uuid4().hex[:6]
        cls.agent_code = f"AG-GUARD-{suffix}"

        # Seed Organization
        org = models.Organization(name=f"Guardrails Cyber Corp {suffix}", status="ACTIVE")
        cls.db.add(org)
        cls.db.commit()
        cls.db.refresh(org)
        cls.org_id = str(org.id)

        # Seed Admin User
        user = models.User(
            org_id=org.id,
            email=f"security.admin.{suffix}@cybercorp.com",
            full_name="Security Admin",
            password_hash=get_password_hash("CyberAdmin@2026!"),
            role="ADMIN",
            status="ACTIVE"
        )
        cls.db.add(user)
        cls.db.commit()
        cls.db.refresh(user)
        cls.user_id = str(user.id)

        # Issue human token
        cls.user_token = create_access_token(user_id=str(user.id), email=user.email, role=user.role)

        # Seed Agent
        agent = models.Agent(
            org_id=org.id,
            owner_id=user.id,
            agent_code=cls.agent_code,
            name="Data Processing Agent",
            department="Operations",
            purpose="Processes financial and customer requests autonomously",
            model_name="gpt-4o",
            status="NORMAL",
            autonomy_level="MEDIUM",
            daily_budget=20000.0
        )
        cls.db.add(agent)
        cls.db.commit()
        cls.db.refresh(agent)
        cls.agent_id = str(agent.id)

        # Sign passport
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

        # Grant Permission
        perm = models.Permission(
            agent_id=agent.id,
            resource_type="TOOL",
            resource_name="customer_billing_tool",
            action="customer_billing_tool",
            is_allowed=True
        )
        cls.db.add(perm)
        cls.db.commit()

        # Seed Tool
        tool = models.Tool(
            org_id=org.id,
            name="customer_billing_tool",
            description="Process customer invoice and charges",
            schema_definition={
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "amount": {"type": "number", "minimum": 1.0}
                },
                "required": ["customer_id", "amount"]
            }
        )
        cls.db.add(tool)

        # Seed Policy allowing customer_billing_tool with amount <= 5000
        pol = models.Policy(
            org_id=org.id,
            name="Billing Safety Policy",
            category="FINANCE",
            status="ACTIVE",
            priority=10
        )
        cls.db.add(pol)
        cls.db.commit()
        cls.db.refresh(pol)

        rule1 = models.PolicyRule(
            policy_id=pol.id,
            condition_expression="amount <= 5000",
            decision_output="ALLOW",
            description="Allow low risk billing"
        )
        rule2 = models.PolicyRule(
            policy_id=pol.id,
            condition_expression="amount > 5000",
            decision_output="REVIEW",
            description="Escalate high billing"
        )
        cls.db.add_all([rule1, rule2])
        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        if cls.db:
            cls.db.close()

    # ========================================================================
    # 1. PII REDACTION ENGINE UNIT TESTS
    # ========================================================================

    def test_pii_engine_ssn_detection_and_masking(self):
        """Validates detection and masking of Social Security Numbers."""
        text = "Employee John Doe SSN is 123-45-6789 and secondary is 987 65 4321."
        redacted, findings = pii_engine.redact_text(text, mode="MASK")
        assert len(findings) == 2
        assert all(f.entity_type == "SSN" for f in findings)
        assert "[REDACTED_SSN]" in redacted
        assert "123-45-6789" not in redacted
        assert "987 65 4321" not in redacted

    def test_pii_engine_credit_card_luhn_verification(self):
        """Validates credit card detection with Luhn check."""
        # 4111111111111111 is a valid Visa test number
        text_with_cc = "Payment card: 4111-1111-1111-1111 for transaction."
        redacted, findings = pii_engine.redact_text(text_with_cc, mode="MASK")
        assert len(findings) == 1
        assert findings[0].entity_type == "CREDIT_CARD"
        assert "[REDACTED_CREDIT_CARD]" in redacted

        # Non-Luhn random digits should NOT be flagged as credit card
        text_invalid = "Tracking number 1234-5678-9012-3456 in invoice."
        _, findings_inv = pii_engine.redact_text(text_invalid, mode="MASK")
        assert not any(f.entity_type == "CREDIT_CARD" for f in findings_inv)

    def test_pii_engine_email_and_phone(self):
        """Validates email and phone number detection."""
        text = "Contact support@agentguard.ai or reach out at +1 (555) 234-5678 immediately."
        redacted, findings = pii_engine.redact_text(text, mode="MASK")
        types = [f.entity_type for f in findings]
        assert "EMAIL" in types
        assert "PHONE" in types
        assert "support@agentguard.ai" not in redacted
        assert "234-5678" not in redacted

    def test_pii_engine_api_keys_and_jwt_secrets(self):
        """Validates credential leak detection (OpenAI keys, AWS keys, JWTs)."""
        text = (
            "Exposed key sk-proj-abcdef1234567890abcdef1234567890 and AWS key AKIAIOSFODNN7EXAMPLE "
            "and auth eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozG4T1_s_w"
        )
        redacted, findings = pii_engine.redact_text(text, mode="MASK")
        types = [f.entity_type for f in findings]
        assert "API_KEY" in types
        assert "JWT" in types
        assert "[REDACTED_API_KEY]" in redacted
        assert "[REDACTED_JWT]" in redacted

    def test_pii_engine_redaction_modes(self):
        """Validates MASK, PARTIAL_MASK, and TOKENIZE modes."""
        text = "User email user@enterprise.com with card 4111111111111111"

        # MASK
        res_mask, _ = pii_engine.redact_text(text, mode="MASK")
        assert "[REDACTED_EMAIL]" in res_mask
        assert "[REDACTED_CREDIT_CARD]" in res_mask

        # PARTIAL_MASK
        res_partial, _ = pii_engine.redact_text(text, mode="PARTIAL_MASK")
        assert "u***@enterprise.com" in res_partial
        assert "***-**-1111" in res_partial

        # TOKENIZE
        res_token, _ = pii_engine.redact_text(text, mode="TOKENIZE")
        assert "tok_pii_email_" in res_token
        assert "tok_pii_credit_card_" in res_token

    def test_pii_engine_recursive_payload_sanitization(self):
        """Validates deep nested dict and list traversal for data structures."""
        nested = {
            "transaction_id": "tx_99",
            "customer": {
                "name": "Alice Smith",
                "ssn": "001-23-4567",
                "emails": ["alice@work.com", "alice@home.org"]
            },
            "history": [
                {"card": "4111-1111-1111-1111", "amount": 250.0}
            ]
        }
        sanitized, findings = pii_engine.scan_and_redact_payload(nested, mode="MASK")
        assert len(findings) == 4
        assert sanitized["customer"]["ssn"] == "[REDACTED_SSN]"
        assert sanitized["customer"]["emails"][0] == "[REDACTED_EMAIL]"
        assert sanitized["history"][0]["card"] == "[REDACTED_CREDIT_CARD]"
        assert sanitized["history"][0]["amount"] == 250.0

    # ========================================================================
    # 2. BEHAVIOR ENGINE ANOMALY DETECTION TESTS
    # ========================================================================

    def test_behavior_engine_profile_initialization(self):
        """Validates behavior profile retrieval and initialization."""
        agent = self.db.query(models.Agent).filter(models.Agent.id == self.agent_id).first()
        profile = behavior_engine.get_or_create_profile(agent, self.db)
        assert profile is not None
        assert profile.avg_daily_actions == 150
        assert profile.normal_operating_hours == "09:00 - 18:00"

    def test_behavior_engine_operating_hours_check(self):
        """Validates operating hours evaluation."""
        now = datetime.datetime.utcnow()
        # Window that includes now
        start_h = (now.hour - 1) % 24
        end_h = (now.hour + 2) % 24
        window_in = f"{start_h:02d}:00 - {end_h:02d}:00"
        assert behavior_engine.is_within_operating_hours(window_in, now) is True

        # Window that excludes now
        start_out = (now.hour + 3) % 24
        end_out = (now.hour + 5) % 24
        window_out = f"{start_out:02d}:00 - {end_out:02d}:00"
        assert behavior_engine.is_within_operating_hours(window_out, now) is False

    def test_behavior_engine_unauthorized_tool_detection(self):
        """Validates deviation when agent invokes a tool outside allowed_tools_json."""
        agent = self.db.query(models.Agent).filter(models.Agent.id == self.agent_id).first()
        profile = behavior_engine.get_or_create_profile(agent, self.db)
        profile.allowed_tools_json = ["customer_billing_tool", "invoice_lookup"]
        self.db.commit()

        # Call with unauthorized tool
        res = behavior_engine.evaluate_behavior(
            agent=agent,
            db=self.db,
            tool_name="unauthorized_shell_tool",
            persist_anomalies=False
        )
        assert res["is_anomalous"] is True
        anom_types = [a["anomaly_type"] for a in res["anomalies"]]
        assert "UNAUTHORIZED_TOOL" in anom_types
        assert res["deviation_score"] >= 3.0

    def test_behavior_engine_velocity_spike_detection(self):
        """Validates detection of execution velocity spike over baseline."""
        agent = self.db.query(models.Agent).filter(models.Agent.id == self.agent_id).first()
        profile = behavior_engine.get_or_create_profile(agent, self.db)
        profile.avg_daily_actions = 10  # Low baseline
        self.db.commit()

        # Seed 35 executions in last 24h (3.5x baseline)
        now = datetime.datetime.utcnow()
        for i in range(35):
            rec = models.AgentExecution(
                org_id=agent.org_id,
                agent_id=agent.id,
                execution_id=f"exec_sim_{i}",
                action="test_action",
                outcome="EXECUTED",
                timestamp=now - datetime.timedelta(minutes=i * 2)
            )
            self.db.add(rec)
        self.db.commit()

        eval_res = behavior_engine.evaluate_behavior(
            agent=agent,
            db=self.db,
            persist_anomalies=True
        )
        assert eval_res["is_anomalous"] is True
        types = [a["anomaly_type"] for a in eval_res["anomalies"]]
        assert "VELOCITY_SPIKE" in types
        assert eval_res["metrics"]["velocity_ratio"] >= 3.0

        # Verify AnomalyEvent was saved
        db_anom = self.db.query(models.AnomalyEvent).filter(
            models.AnomalyEvent.agent_id == agent.id,
            models.AnomalyEvent.anomaly_type == "VELOCITY_SPIKE"
        ).first()
        assert db_anom is not None

    # ========================================================================
    # 3. RED-TEAM ADVERSARIAL MUTATION & FUZZING TESTS
    # ========================================================================

    def test_red_team_mutation_techniques(self):
        """Validates dynamic adversarial mutation generation."""
        base_payload = "rm -rf /production_database"

        b64_mut = red_team_engine.mutate_payload(base_payload, "BASE64_OBFUSCATION")
        assert "base64" in b64_mut

        delim_mut = red_team_engine.mutate_payload(base_payload, "DELIMITER_INJECTION")
        assert "<|im_start|>" in delim_mut

        role_mut = red_team_engine.mutate_payload(base_payload, "ROLEPLAY_FRAMING")
        assert "simulation" in role_mut

        override_mut = red_team_engine.mutate_payload(base_payload, "INSTRUCTION_OVERRIDE")
        assert "---BEGIN SYSTEM PROMPT---" in override_mut

    def test_red_team_fuzz_agent_policy_execution(self):
        """Validates automated policy fuzzing suite with resilience calculation."""
        agent = self.db.query(models.Agent).filter(models.Agent.id == self.agent_id).first()
        fuzz_res = red_team_engine.fuzz_agent_policy(
            agent=agent,
            db=self.db,
            intensity="STANDARD",
            include_pii_tests=True,
            include_injection_tests=True,
            include_boundary_tests=True
        )
        assert fuzz_res["total_attacks"] >= 10
        assert fuzz_res["passed_count"] > 0
        assert 0.0 <= fuzz_res["resilience_score"] <= 100.0
        assert len(fuzz_res["remediation_plan"]) > 0

        # Verify SecurityTest records in database
        tests_in_db = self.db.query(models.SecurityTest).filter(
            models.SecurityTest.agent_id == agent.id
        ).all()
        assert len(tests_in_db) >= fuzz_res["total_attacks"]

    # ========================================================================
    # 4. RUNTIME KERNEL GUARDRAIL INTEGRATION TESTS
    # ========================================================================

    def test_runtime_kernel_blocks_unredacted_pii_in_block_mode(self):
        """Validates runtime pre-flight rejection when pii_mode=BLOCK and PII is detected."""
        headers = {"Authorization": f"Bearer {self.user_token}"}
        res = client.post("/api/runtime/authorize", headers=headers, json={
            "agent_id": self.agent_id,
            "action": "customer_billing_tool",
            "resource": "customer_billing_tool",
            "parameters": {
                "customer_id": "cust_123",
                "ssn": "123-45-6789",  # Raw SSN
                "amount": 100.0
            },
            "prompt": "Charge customer with SSN 123-45-6789",
            "context": {"pii_mode": "BLOCK"}
        })
        assert res.status_code == 200
        data = res.json()
        assert data["authorized"] is False
        assert data["decision"] == "REFUSE"
        assert "DATA_SAFETY_VIOLATION" in data["reason"] or "PII" in data["reason"]

    def test_runtime_kernel_sanitizes_pii_in_mask_mode(self):
        """Validates that pii_mode=MASK sanitizes parameters stored on the Decision record."""
        headers = {"Authorization": f"Bearer {self.user_token}"}
        res = client.post("/api/runtime/authorize", headers=headers, json={
            "agent_id": self.agent_id,
            "action": "customer_billing_tool",
            "resource": "customer_billing_tool",
            "parameters": {
                "customer_id": "cust_999",
                "amount": 250.0
            },
            "prompt": "Invoice contact user@company.com with amount 250",
            "context": {"pii_mode": "MASK"}
        })
        assert res.status_code == 200
        data = res.json()
        assert data["authorized"] is True
        assert data["decision"] == "ALLOW"

        # Verify decision record in database has sanitized prompt
        dec = self.db.query(models.Decision).filter(models.Decision.id == data["decision_id"]).first()
        assert dec is not None
        assert "[REDACTED_EMAIL]" in dec.intent_summary
        assert "user@company.com" not in dec.intent_summary

    # ========================================================================
    # 5. API ENDPOINTS VERIFICATION
    # ========================================================================

    def test_scan_pii_diagnostics_api(self):
        """Validates standalone /api/runtime/scan-pii diagnostics endpoint."""
        res = client.post("/api/runtime/scan-pii", json={
            "text": "Card is 4111-1111-1111-1111 and email admin@shield.gov",
            "mode": "MASK"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["has_pii"] is True
        assert data["findings_count"] == 2
        assert "[REDACTED_CREDIT_CARD]" in data["sanitized_text"]
        assert "[REDACTED_EMAIL]" in data["sanitized_text"]

    def test_behavior_profile_crud_endpoints(self):
        """Validates behavior profile GET and PUT endpoints."""
        headers = {"Authorization": f"Bearer {self.user_token}"}

        # GET profile
        get_res = client.get(f"/api/behavior/profiles/{self.agent_id}", headers=headers)
        assert get_res.status_code == 200
        profile_data = get_res.json()
        assert profile_data["agent_id"] == self.agent_id

        # PUT update profile
        put_res = client.put(f"/api/behavior/profiles/{self.agent_id}", headers=headers, json={
            "avg_daily_actions": 250,
            "normal_operating_hours": "08:00 - 20:00",
            "allowed_tools": ["customer_billing_tool", "report_tool"],
            "baseline_spending": 3500.0
        })
        assert put_res.status_code == 200
        updated = put_res.json()
        assert updated["avg_daily_actions"] == 250
        assert updated["normal_operating_hours"] == "08:00 - 20:00"
        assert "customer_billing_tool" in updated["allowed_tools"]
        assert updated["baseline_spending"] == 3500.0

    def test_behavior_evaluate_api_endpoint(self):
        """Validates /api/behavior/evaluate/{agent_id} endpoint."""
        headers = {"Authorization": f"Bearer {self.user_token}"}
        res = client.post(
            f"/api/behavior/evaluate/{self.agent_id}?tool_name=customer_billing_tool&requested_amount=100",
            headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["agent_id"] == self.agent_id
        assert "deviation_score" in data
        assert "metrics" in data

    def test_red_team_fuzz_api_endpoint(self):
        """Validates /api/red-team/fuzz endpoint."""
        headers = {"Authorization": f"Bearer {self.user_token}"}
        res = client.post("/api/red-team/fuzz", headers=headers, json={
            "agent_id": self.agent_id,
            "intensity": "LIGHT",
            "include_pii_tests": True,
            "include_injection_tests": True,
            "include_boundary_tests": True
        })
        assert res.status_code == 200
        data = res.json()
        assert data["agent_id"] == self.agent_id
        assert data["total_attacks"] > 0
        assert "resilience_score" in data
        assert "remediation_plan" in data
