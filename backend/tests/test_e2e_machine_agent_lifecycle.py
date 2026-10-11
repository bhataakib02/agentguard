"""
End-to-End Test Suite: Complete Machine Agent Lifecycle Integration Flow
Tests Section 37:
  Machine Agent -> Auth -> Passport -> Permission -> Capability -> Runtime Gate -> Tool Execution -> Audit Trail

Stages tested in full contiguous succession:
1. Tenant Provisioning & BYOK Encryption Setup
2. Agent Registration & Autonomy Configuration
3. Machine Credential Issuance & Secure SHA-256 Hashing
4. Ed25519 Cryptographic Passport Issuance & Signature Verification
5. Machine Agent Authentication (POST /api/runtime/auth) -> Machine JWT Token
6. Agent Runtime Session Tracking & Heartbeat (POST /api/runtime/heartbeat)
7. Action Permission Grant with Scoped Parameter Constraints
8. Single-Use Capability Token Issuance
9. Pre-Flight Runtime Authorization Kernel (POST /api/runtime/authorize) -> Single-Use Gate Token
10. Forward Tool Proxy Execution (POST /api/runtime/execute) with Replay Protection
11. Output Guardrail Safety Verification
12. Immutable Causal Audit Trail & Telemetry Verification
"""

import os
import sys
import uuid
import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///test_e2e_machine_lifecycle.db"
os.environ["SECRET_KEY"] = "test-e2e-machine-lifecycle-secret-key-12345678"
os.environ["ENVIRONMENT"] = "test"

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sdks", "python")))

from main import app
from database import Base, engine, get_db
import models
from core import security
from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service
from services.byok_service import byok_service
from services.tool_proxy_service import tool_proxy_service
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


class TestE2EMachineAgentLifecycle:
    @classmethod
    def setup_class(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        cls.db = TestingSessionLocal()

    @classmethod
    def teardown_class(cls):
        cls.db.close()

    def test_full_machine_agent_lifecycle_flow(self):
        suffix = uuid.uuid4().hex[:6]

        # ----------------------------------------------------------------------
        # STAGE 1: Tenant Provisioning & BYOK Encryption Setup
        # ----------------------------------------------------------------------
        org = models.Organization(
            id=str(uuid.uuid4()),
            name=f"E2E Enterprise Corp {suffix}",
            slug=f"e2e-corp-{suffix}",
            status="ACTIVE"
        )
        self.db.add(org)
        self.db.commit()

        # Admin user to configure tenant
        admin = models.User(
            id=str(uuid.uuid4()),
            org_id=org.id,
            email=f"admin-{suffix}@e2ecorp.com",
            full_name="E2E Admin",
            role="ADMIN",
            status="ACTIVE",
            password_hash=security.get_password_hash("AdminPass123!")
        )
        self.db.add(admin)
        self.db.commit()

        admin_token = security.create_access_token(
            user_id=admin.id, email=admin.email, role="ADMIN"
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Configure BYOK for tenant
        byok_res = test_client.post(
            "/api/organization/byok",
            headers=admin_headers,
            json={
                "provider": "AWS_KMS",
                "key_arn": f"arn:aws:kms:us-east-1:123456789012:key/e2e-key-{suffix}",
                "key_alias": f"alias/e2e-key-{suffix}"
            }
        )
        assert byok_res.status_code == 200
        assert byok_res.json()["status"] == "ACTIVE"
        assert byok_res.json()["is_custom_key"] is True

        # ----------------------------------------------------------------------
        # STAGE 2: Agent Registration & Autonomy Configuration
        # ----------------------------------------------------------------------
        agent = models.Agent(
            id=str(uuid.uuid4()),
            org_id=org.id,
            owner_id=admin.id,
            name=f"Autonomous Settlement Agent {suffix}",
            agent_code=f"AG-SETTLE-{suffix}".upper(),
            purpose="Autonomous treasury and wire settlement agent",
            department="Treasury",
            autonomy_level="HIGH",
            status="NORMAL",
            daily_budget=100000.0
        )
        self.db.add(agent)
        self.db.commit()

        # ----------------------------------------------------------------------
        # STAGE 3: Machine Credential Issuance & SHA-256 Hashing
        # ----------------------------------------------------------------------
        cred_res = test_client.post(
            f"/api/agents/{agent.id}/credentials",
            headers=admin_headers,
            json={"name": "Production E2E Pipeline Credential", "expires_in_days": 30}
        )
        assert cred_res.status_code == 200
        cred_data = cred_res.json()
        raw_api_key = cred_data.get("plaintext_token") or cred_data.get("api_key")
        assert raw_api_key is not None
        assert raw_api_key.startswith("ag_agent_")
        credential_id = cred_data.get("credential", {}).get("id") or cred_data.get("id")

        # Verify plaintext is not stored in DB
        db_cred = self.db.query(models.AgentCredential).filter(
            models.AgentCredential.id == credential_id
        ).first()
        assert db_cred is not None
        assert db_cred.key_hash != raw_api_key
        assert db_cred.status == "ACTIVE"

        # ----------------------------------------------------------------------
        # STAGE 4: Cryptographic Passport Issuance & Ed25519 Verification
        # ----------------------------------------------------------------------
        passport = models.AgentPassport(
            id=str(uuid.uuid4()),
            agent_id=agent.id,
            passport_number=f"AG-PASSPORT-{uuid.uuid4().hex[:6].upper()}",
            verification_status="ACTIVE",
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=90),
            passport_version="1.0"
        )
        sig = passport_service.sign_passport(
            agent=agent,
            passport=passport,
            capabilities=["TRANSFER", "SETTLE", "AUDIT_QUERY"]
        )
        assert sig.startswith("ed25519:")
        assert passport.digital_signature is not None
        self.db.add(passport)
        self.db.commit()

        # Cryptographically verify the passport signature
        verification = passport_service.verify_passport(passport, agent)
        assert verification["valid"] is True
        assert verification["status"] == "VERIFIED"

        # ----------------------------------------------------------------------
        # STAGE 5: Machine Authentication (POST /api/runtime/auth)
        # ----------------------------------------------------------------------
        auth_res = test_client.post(
            "/api/runtime/auth",
            json={"agent_code": agent.agent_code, "credential": raw_api_key}
        )
        assert auth_res.status_code == 200
        auth_data = auth_res.json()
        assert "access_token" in auth_data
        machine_jwt = auth_data["access_token"]
        assert auth_data["agent_code"] == agent.agent_code
        assert auth_data["org_id"] == str(org.id)
        assert auth_data["token_type"].lower() == "bearer"

        machine_headers = {"Authorization": f"Bearer {machine_jwt}"}

        # ----------------------------------------------------------------------
        # STAGE 6: Agent Runtime Session Management & Heartbeat
        # ----------------------------------------------------------------------
        heartbeat_res = test_client.post(
            "/api/runtime/heartbeat",
            headers=machine_headers,
            json={"status": "HEALTHY", "metrics": {"queue_depth": 0, "cpu_usage": 12.5}}
        )
        assert heartbeat_res.status_code == 200
        assert heartbeat_res.json()["status"] in ("HEALTHY", "PONG")
        assert heartbeat_res.json()["agent_code"] == agent.agent_code

        # ----------------------------------------------------------------------
        # STAGE 7: Action Permission Grant
        # ----------------------------------------------------------------------
        grant_res = test_client.post(
            f"/api/agents/{agent.id}/permissions",
            headers=admin_headers,
            json={
                "resource_type": "TOOL",
                "resource_name": "treasury_wire_transfer",
                "action": "EXECUTE",
                "is_allowed": True
            }
        )
        assert grant_res.status_code == 201
        perm_data = grant_res.json()
        assert perm_data["action"] == "EXECUTE"

        # ----------------------------------------------------------------------
        # STAGE 8: Capability Token Issuance
        # ----------------------------------------------------------------------
        from engines.capability_engine import capability_engine
        token_data = capability_engine.issue_token(
            agent_id=agent.id,
            capability_name="treasury_wire_transfer.EXECUTE",
            scope="*",
            amount_limit=25000.0,
            ttl_seconds=3600
        )
        cap_token = models.CapabilityToken(
            id=str(uuid.uuid4()),
            token_code=token_data["token_code"],
            agent_id=token_data["agent_id"],
            capability_name=token_data["capability_name"],
            scope=token_data["scope"],
            amount_limit=token_data["amount_limit"],
            issued_at=token_data["issued_at"],
            expires_at=token_data["expires_at"],
            status="ACTIVE"
        )
        self.db.add(cap_token)
        self.db.commit()

        # ----------------------------------------------------------------------
        # STAGE 9: Pre-Flight Runtime Authorization Kernel (POST /api/runtime/authorize)
        # ----------------------------------------------------------------------
        authz_payload = {
            "action": "EXECUTE",
            "resource": "treasury_wire_transfer",
            "parameters": {
                "recipient_account": "ACC-998877",
                "amount": 15000.0,
                "memo": "Vendor payment for cloud infrastructure"
            },
            "capability_token": cap_token.token_code
        }

        authz_res = test_client.post(
            "/api/runtime/authorize",
            headers=machine_headers,
            json=authz_payload
        )
        assert authz_res.status_code == 200
        authz_data = authz_res.json()
        assert authz_data["decision"] in ("ALLOW", "PERMITTED")
        gate_token = authz_data.get("execution_gate_token") or authz_data.get("gate_token")
        assert gate_token is not None
        assert gate_token.startswith("gate_")

        # ----------------------------------------------------------------------
        # STAGE 10: Register Mock Tool & Execute via Tool Proxy (POST /api/runtime/execute)
        # ----------------------------------------------------------------------
        tool = models.Tool(
            id=str(uuid.uuid4()),
            org_id=org.id,
            name="treasury_wire_transfer",
            category="PAYMENT",
            endpoint="https://api.example.com/treasury/wire",
            schema_definition={
                "type": "object",
                "properties": {
                    "recipient_account": {"type": "string"},
                    "amount": {"type": "number"},
                    "memo": {"type": "string"}
                },
                "required": ["recipient_account", "amount"]
            },
            status="ACTIVE"
        )
        self.db.add(tool)
        self.db.commit()

        exec_res = test_client.post(
            "/api/runtime/execute",
            headers=machine_headers,
            json={
                "tool_name": "treasury_wire_transfer",
                "parameters": {
                    "recipient_account": "ACC-998877",
                    "amount": 15000.0,
                    "memo": "Vendor payment for cloud infrastructure"
                },
                "execution_gate_token": gate_token
            }
        )
        assert exec_res.status_code == 200
        exec_data = exec_res.json()
        assert exec_data["success"] is True
        assert exec_data["status"] == "EXECUTED"
        assert exec_data["tool_name"] == "treasury_wire_transfer"
        assert "execution_id" in exec_data

        # Verify Replay Protection: reusing the same gate_token MUST fail
        replay_res = test_client.post(
            "/api/runtime/execute",
            headers=machine_headers,
            json={
                "tool_name": "treasury_wire_transfer",
                "parameters": {"recipient_account": "ACC-998877", "amount": 15000.0},
                "execution_gate_token": gate_token
            }
        )
        assert replay_res.status_code == 400
        assert "replay" in replay_res.json()["detail"].lower()

        # ----------------------------------------------------------------------
        # STAGE 11: Output Safety Guardrail Scan (POST /api/runtime/scan-output)
        # ----------------------------------------------------------------------
        settlement_output = (
            "Wire transfer of $15,000 to ACC-998877 completed successfully with reference TX-9921."
        )
        scan_res = test_client.post(
            "/api/runtime/scan-output",
            headers=machine_headers,
            json={
                "text": settlement_output,
                "grounding_context": "Transfer of $15,000 for vendor cloud infrastructure account ACC-998877 with reference TX-9921.",
                "policy_mode": "BLOCK"
            }
        )
        assert scan_res.status_code == 200
        scan_data = scan_res.json()
        assert scan_data["is_safe"] is True
        assert scan_data["decision"] == "ALLOW"
        assert scan_data["is_grounded"] is True

        # ----------------------------------------------------------------------
        # STAGE 12: Python SDK Integration & Verification
        # ----------------------------------------------------------------------
        sdk = AgentGuardClient(
            agent_code=agent.agent_code,
            agent_key=raw_api_key,
            base_url="",
            session=test_client
        )
        token = sdk.authenticate()
        assert token is not None

        # SDK heartbeat
        sdk_hb = sdk.heartbeat(status="HEALTHY")
        assert sdk_hb.get("status") in ("HEALTHY", "PONG")

        # SDK output scan
        sdk_scan = sdk.scan_output(
            text="Clean operation status report",
            policy_mode="BLOCK"
        )
        assert sdk_scan["is_safe"] is True
        assert sdk_scan["decision"] == "ALLOW"

        # ----------------------------------------------------------------------
        # STAGE 13: Immutable Audit Trail & Telemetry Provenance Check
        # ----------------------------------------------------------------------
        audits = self.db.query(models.AuditLog).filter(
            models.AuditLog.org_id == org.id
        ).all()
        assert len(audits) >= 3
        event_types = [a.event_type for a in audits]
        assert "BYOK_KEY_CONFIGURED" in event_types
        assert "AGENT_CREDENTIAL_CREATED" in event_types

        # Verify Decision & Execution Record exists
        decision_record = self.db.query(models.Decision).filter(
            models.Decision.agent_id == agent.id
        ).first()
        assert decision_record is not None
        assert decision_record.execution_status == "EXECUTED"
        assert decision_record.gate_token_used is True

        # Verify Causal Provenance Event recorded
        prov_record = self.db.query(models.ProvenanceEvent).filter(
            models.ProvenanceEvent.agent_id == agent.id
        ).first()
        assert prov_record is not None
        assert prov_record.tool_used == "treasury_wire_transfer"
