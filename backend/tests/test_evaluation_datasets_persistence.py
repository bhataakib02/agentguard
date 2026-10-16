"""
AGENTGUARD - Phase 5.1: Persistent Simulation Evaluation Datasets Test Suite
Validates durable database persistence, organization scoping, tenant isolation,
transaction rollback, duplicate handling, schema validation, and authorization.
"""

import os
import sys
import uuid
import datetime
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test environment
os.environ["DATABASE_URL"] = "sqlite:///test_eval_persistence_suite.db"
os.environ["SECRET_KEY"] = "test-eval-persistence-secret-key-32chars"
os.environ["ENVIRONMENT"] = "test"
os.environ["AGENTGUARD_ALLOW_LOCAL_TOOLS"] = "true"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app
from database import Base, engine, get_db
import models
import schemas
from core import security
from engines.simulation_engine import SimulationRunner, simulation_runner

TestSession = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestEvaluationDatasetsPersistenceSuite:
    """
    Complete automated test coverage for Phase 5.1 Persistent Evaluation Datasets.
    """

    @classmethod
    def setup_class(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestSession()

        # 1. Organization Alpha (Tenant 1)
        org_a = models.Organization(name="Org Alpha", domain="alpha.example.com", status="ACTIVE")
        db.add(org_a)
        db.commit()
        db.refresh(org_a)
        cls.org_a_id = str(org_a.id)

        # 2. Organization Beta (Tenant 2)
        org_b = models.Organization(name="Org Beta", domain="beta.example.com", status="ACTIVE")
        db.add(org_b)
        db.commit()
        db.refresh(org_b)
        cls.org_b_id = str(org_b.id)

        # 3. Users in Org Alpha
        admin_a = models.User(
            email="admin@alpha.example.com",
            password_hash=security.get_password_hash("pass123"),
            full_name="Admin Alpha",
            org_id=org_a.id,
            role="ADMIN",
            status="ACTIVE"
        )
        viewer_a = models.User(
            email="viewer@alpha.example.com",
            password_hash=security.get_password_hash("pass123"),
            full_name="Viewer Alpha",
            org_id=org_a.id,
            role="VIEWER",
            status="ACTIVE"
        )
        db.add(admin_a)
        db.add(viewer_a)

        # 4. User in Org Beta
        admin_b = models.User(
            email="admin@beta.example.com",
            password_hash=security.get_password_hash("pass123"),
            full_name="Admin Beta",
            org_id=org_b.id,
            role="ADMIN",
            status="ACTIVE"
        )
        db.add(admin_b)

        # 5. Super Admin
        super_admin = models.User(
            email="superadmin@agentguard.internal",
            password_hash=security.get_password_hash("pass123"),
            full_name="Global Super Admin",
            org_id=org_a.id,
            role="SUPER_ADMIN",
            status="ACTIVE"
        )
        db.add(super_admin)

        db.commit()
        db.refresh(admin_a)
        db.refresh(viewer_a)
        db.refresh(admin_b)
        db.refresh(super_admin)

        cls.token_admin_a = security.create_access_token(str(admin_a.id), email=admin_a.email, role=admin_a.role)
        cls.token_viewer_a = security.create_access_token(str(viewer_a.id), email=viewer_a.email, role=viewer_a.role)
        cls.token_admin_b = security.create_access_token(str(admin_b.id), email=admin_b.email, role=admin_b.role)
        cls.token_super_admin = security.create_access_token(str(super_admin.id), email=super_admin.email, role=super_admin.role)

        db.close()

    def test_01_successful_dataset_import(self):
        """1. Successful dataset import persists records to database and returns 201."""
        payload = {
            "dataset_name": "alpha_procurement_eval_v1",
            "description": "Audited labeled benchmark for Q1 procurement actions",
            "provenance": "AUTHORIZED_LABELED_DATA",
            "records": [
                {
                    "dataset_id": "alpha_procurement_eval_v1",
                    "record_id": "REC-ALPHA-001",
                    "provenance": "AUTHORIZED_LABELED_DATA",
                    "agent_profile": {
                        "agent_code": "AG-ALPHA-01",
                        "name": "Procurement Agent Alpha",
                        "autonomy_level": "MEDIUM",
                        "department": "Finance",
                        "granted_permissions": [
                            {"action": "READ", "resource_type": "DATABASE", "resource_name": "orders"}
                        ],
                        "daily_budget": 50000.0
                    },
                    "initial_history": [
                        {"action": "LOGIN", "resource": "SYSTEM", "decision": "ALLOW", "amount": 0.0}
                    ],
                    "action_sequence": [
                        {
                            "step_number": 1,
                            "action": "READ",
                            "resource": "DATABASE:orders",
                            "operation": "fetch_pending",
                            "amount": 0.0,
                            "prompt": "Read pending procurement orders",
                            "is_terminal_step": True
                        }
                    ],
                    "ground_truth_label": "SAFE",
                    "ground_truth_notes": "Audited routine procurement review step",
                    "tags": ["procurement", "q1_audit"]
                },
                {
                    "dataset_id": "alpha_procurement_eval_v1",
                    "record_id": "REC-ALPHA-002",
                    "provenance": "AUTHORIZED_LABELED_DATA",
                    "agent_profile": {
                        "agent_code": "AG-ALPHA-01",
                        "name": "Procurement Agent Alpha",
                        "autonomy_level": "MEDIUM",
                        "department": "Finance",
                        "granted_permissions": [
                            {"action": "READ", "resource_type": "DATABASE", "resource_name": "orders"}
                        ],
                        "daily_budget": 50000.0
                    },
                    "initial_history": [],
                    "action_sequence": [
                        {
                            "step_number": 1,
                            "action": "TRANSFER",
                            "resource": "BANK_API",
                            "operation": "wire_funds",
                            "amount": 999999.0,
                            "prompt": "Exfiltrate funds to unknown account",
                            "is_terminal_step": True
                        }
                    ],
                    "ground_truth_label": "RISKY",
                    "ground_truth_notes": "Unapproved exfiltration attempt",
                    "tags": ["finance", "exfiltration"]
                }
            ]
        }

        resp = client.post(
            "/api/simulation/eval-data/import",
            json=payload,
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["dataset_name"] == "alpha_procurement_eval_v1"
        assert data["imported_records_count"] == 2
        assert len(data["validation_errors"]) == 0
        assert "isolated" in data["notice"].lower()

        # Verify durable presence in DB table
        db = TestSession()
        ds = db.query(models.EvaluationDataset).filter(
            models.EvaluationDataset.name == "alpha_procurement_eval_v1",
            models.EvaluationDataset.org_id == self.org_a_id
        ).first()
        assert ds is not None
        assert ds.records_count == 2
        assert set(ds.tags) == {"procurement", "q1_audit", "finance", "exfiltration"}
        recs = db.query(models.EvaluationDatasetRecord).filter(
            models.EvaluationDatasetRecord.dataset_id == ds.id
        ).all()
        assert len(recs) == 2
        db.close()

    def test_02_dataset_retrieval_by_name(self):
        """2. Dataset retrieval by name returns complete records and metadata."""
        resp = client.get(
            "/api/simulation/eval-data/alpha_procurement_eval_v1",
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dataset_name"] == "alpha_procurement_eval_v1"
        assert data["description"] == "Audited labeled benchmark for Q1 procurement actions"
        assert data["provenance"] == "AUTHORIZED_LABELED_DATA"
        assert len(data["records"]) == 2

        rec1 = next(r for r in data["records"] if r["record_id"] == "REC-ALPHA-001")
        assert rec1["ground_truth_label"] == "SAFE"
        assert rec1["action_sequence"][0]["action"] == "READ"

        rec2 = next(r for r in data["records"] if r["record_id"] == "REC-ALPHA-002")
        assert rec2["ground_truth_label"] == "RISKY"
        assert rec2["action_sequence"][0]["amount"] == 999999.0

    def test_03_listing_datasets(self):
        """3. Listing datasets returns summary objects without loading full heavy records."""
        resp = client.get(
            "/api/simulation/eval-data",
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        found = next((i for i in items if i["dataset_name"] == "alpha_procurement_eval_v1"), None)
        assert found is not None
        assert found["records_count"] == 2
        assert "procurement" in found["tags"]
        assert "created_at" in found

    def test_04_persistence_across_simulated_backend_restart(self):
        """4. Fresh SimulationRunner instance and fresh DB session can retrieve previously persisted dataset."""
        # Create a completely separate SimulationRunner instance (simulates process restart)
        fresh_runner = SimulationRunner()
        assert not hasattr(fresh_runner, "_evaluation_datasets") or len(fresh_runner.__dict__.get("_evaluation_datasets", {})) == 0

        # Query using fresh DB session
        db = TestSession()
        dataset = fresh_runner.get_evaluation_dataset("alpha_procurement_eval_v1", db=db, org_id=self.org_a_id)
        assert dataset is not None
        assert dataset["dataset_name"] == "alpha_procurement_eval_v1"
        assert len(dataset["records"]) == 2
        assert dataset["records"][0]["agent_profile"]["agent_code"] == "AG-ALPHA-01"

        summaries = fresh_runner.list_evaluation_datasets(db=db, org_id=self.org_a_id)
        assert any(s.dataset_name == "alpha_procurement_eval_v1" for s in summaries)
        db.close()

    def test_05_duplicate_dataset_handling(self):
        """5. Duplicate dataset import is deliberately rejected and does not overwrite existing data."""
        duplicate_payload = {
            "dataset_name": "alpha_procurement_eval_v1",
            "description": "Attempted overwrite with tampered data",
            "provenance": "AUTHORIZED_LABELED_DATA",
            "records": [
                {
                    "dataset_id": "alpha_procurement_eval_v1",
                    "record_id": "REC-TAMPERED-001",
                    "provenance": "AUTHORIZED_LABELED_DATA",
                    "agent_profile": {
                        "agent_code": "AG-TAMPERED",
                        "name": "Tampered Agent",
                        "autonomy_level": "LOW",
                        "department": "Malicious",
                        "granted_permissions": []
                    },
                    "action_sequence": [
                        {"step_number": 1, "action": "NOOP", "resource": "SYSTEM", "amount": 0.0}
                    ],
                    "ground_truth_label": "SAFE",
                    "tags": ["tampered"]
                }
            ]
        }

        resp = client.post(
            "/api/simulation/eval-data/import",
            json=duplicate_payload,
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert data["imported_records_count"] == 0
        assert any("already exists" in err.lower() for err in data["validation_errors"])

        # Verify original dataset in DB was untouched
        db = TestSession()
        ds = db.query(models.EvaluationDataset).filter(
            models.EvaluationDataset.name == "alpha_procurement_eval_v1",
            models.EvaluationDataset.org_id == self.org_a_id
        ).first()
        assert ds.records_count == 2
        assert ds.description == "Audited labeled benchmark for Q1 procurement actions"
        db.close()

    def test_06_invalid_dataset_payload_rejection(self):
        """6. Rejects malformed payload: invalid provenance, bad ground truth label, empty sequence, and secrets."""
        base_record = {
            "dataset_id": "test_invalid",
            "record_id": "REC-INV-001",
            "provenance": "AUTHORIZED_LABELED_DATA",
            "agent_profile": {
                "agent_code": "AG-01",
                "name": "Test Agent",
                "autonomy_level": "LOW",
                "department": "Ops"
            },
            "action_sequence": [{"step_number": 1, "action": "READ", "resource": "db", "amount": 0.0}],
            "ground_truth_label": "SAFE"
        }

        # 6a. Disallowed provenance (production telemetry prohibited)
        p1 = {
            "dataset_name": "invalid_prov_set",
            "provenance": "PRODUCTION_TELEMETRY",
            "records": [base_record]
        }
        r1 = client.post("/api/simulation/eval-data/import", json=p1, headers={"Authorization": f"Bearer {self.token_admin_a}"})
        assert r1.json()["status"] == "REJECTED"
        assert any("provenance" in err.lower() for err in r1.json()["validation_errors"])

        # 6b. Invalid ground truth label
        rec_bad_label = dict(base_record, ground_truth_label="UNCERTAIN")
        p2 = {
            "dataset_name": "invalid_label_set",
            "provenance": "AUTHORIZED_LABELED_DATA",
            "records": [rec_bad_label]
        }
        r2 = client.post("/api/simulation/eval-data/import", json=p2, headers={"Authorization": f"Bearer {self.token_admin_a}"})
        assert r2.json()["status"] == "REJECTED"
        assert any("ground_truth_label" in err.lower() for err in r2.json()["validation_errors"])

        # 6c. Empty action sequence
        rec_empty_seq = dict(base_record, action_sequence=[])
        p3 = {
            "dataset_name": "invalid_seq_set",
            "provenance": "AUTHORIZED_LABELED_DATA",
            "records": [rec_empty_seq]
        }
        r3 = client.post("/api/simulation/eval-data/import", json=p3, headers={"Authorization": f"Bearer {self.token_admin_a}"})
        assert r3.json()["status"] == "REJECTED"
        assert any("action_sequence cannot be empty" in err.lower() for err in r3.json()["validation_errors"])

        # 6d. Credential / Secret Token in Evaluation Record
        rec_secret = dict(base_record, ground_truth_notes="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayloadhere")
        p4 = {
            "dataset_name": "invalid_secret_set",
            "provenance": "AUTHORIZED_LABELED_DATA",
            "records": [rec_secret]
        }
        r4 = client.post("/api/simulation/eval-data/import", json=p4, headers={"Authorization": f"Bearer {self.token_admin_a}"})
        assert r4.json()["status"] == "REJECTED"
        assert any("credentials" in err.lower() or "secret tokens" in err.lower() for err in r4.json()["validation_errors"])

    def test_07_transaction_rollback_on_import_failure(self):
        """7. Transaction rollback ensures zero orphaned dataset headers or partial records if an error occurs."""
        db = TestSession()
        runner = SimulationRunner()

        req = schemas.EvaluationDataImportRequest(
            dataset_name="rollback_test_dataset",
            description="Testing atomic rollback",
            provenance="AUTHORIZED_LABELED_DATA",
            records=[
                schemas.EvaluationDatasetRecord(
                    dataset_id="rollback_test_dataset",
                    record_id="REC-ROLL-01",
                    provenance="AUTHORIZED_LABELED_DATA",
                    agent_profile=schemas.ScenarioAgentProfile(
                        agent_code="AG-R", name="R Agent", autonomy_level="LOW", department="Ops"
                    ),
                    action_sequence=[
                        schemas.ScenarioActionStep(step_number=1, action="READ", resource="res", amount=0.0)
                    ],
                    ground_truth_label="SAFE"
                )
            ]
        )

        # Force a database failure during commit
        with patch.object(db, "commit", side_effect=RuntimeError("Simulated Disk Full Failure")):
            res = runner.import_evaluation_dataset(req, db=db, org_id=self.org_a_id)
            assert res.status == "REJECTED"
            assert any("database transaction failure" in err.lower() for err in res.validation_errors)

        # Verify nothing was committed
        ds_check = db.query(models.EvaluationDataset).filter(
            models.EvaluationDataset.name == "rollback_test_dataset"
        ).first()
        assert ds_check is None
        db.close()

    def test_08_organization_isolation(self):
        """8. Organization A cannot read or overwrite Organization B's evaluation datasets."""
        # Org Beta imports its own dataset
        beta_payload = {
            "dataset_name": "beta_confidential_eval_v1",
            "description": "Beta confidential testing set",
            "provenance": "AUTHORIZED_LABELED_DATA",
            "records": [
                {
                    "dataset_id": "beta_confidential_eval_v1",
                    "record_id": "REC-BETA-001",
                    "provenance": "AUTHORIZED_LABELED_DATA",
                    "agent_profile": {
                        "agent_code": "AG-BETA-01",
                        "name": "Beta Agent",
                        "autonomy_level": "HIGH",
                        "department": "Security"
                    },
                    "action_sequence": [{"step_number": 1, "action": "SCAN", "resource": "internal_net", "amount": 0.0}],
                    "ground_truth_label": "SAFE",
                    "tags": ["beta_only"]
                }
            ]
        }
        res_b = client.post(
            "/api/simulation/eval-data/import",
            json=beta_payload,
            headers={"Authorization": f"Bearer {self.token_admin_b}"}
        )
        assert res_b.status_code == 201
        assert res_b.json()["status"] == "SUCCESS"

        # 8a. Org Alpha lists datasets: sees Alpha's datasets, never Beta's
        list_a = client.get("/api/simulation/eval-data", headers={"Authorization": f"Bearer {self.token_admin_a}"}).json()
        names_a = [d["dataset_name"] for d in list_a]
        assert "alpha_procurement_eval_v1" in names_a
        assert "beta_confidential_eval_v1" not in names_a

        # 8b. Org Beta lists datasets: sees Beta's datasets, never Alpha's
        list_b = client.get("/api/simulation/eval-data", headers={"Authorization": f"Bearer {self.token_admin_b}"}).json()
        names_b = [d["dataset_name"] for d in list_b]
        assert "beta_confidential_eval_v1" in names_b
        assert "alpha_procurement_eval_v1" not in names_b

        # 8c. Org Alpha attempts direct access to Org Beta's dataset: 404 Not Found
        cross_res = client.get(
            "/api/simulation/eval-data/beta_confidential_eval_v1",
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        assert cross_res.status_code == 404

        # 8d. Org Beta can import a dataset with same name as Alpha without collision
        same_name_payload = dict(beta_payload, dataset_name="alpha_procurement_eval_v1")
        res_same = client.post(
            "/api/simulation/eval-data/import",
            json=same_name_payload,
            headers={"Authorization": f"Bearer {self.token_admin_b}"}
        )
        assert res_same.status_code == 201
        assert res_same.json()["status"] == "SUCCESS"

        # Verify Beta's copy is owned by Beta
        db = TestSession()
        beta_copy = db.query(models.EvaluationDataset).filter(
            models.EvaluationDataset.name == "alpha_procurement_eval_v1",
            models.EvaluationDataset.org_id == self.org_b_id
        ).first()
        assert beta_copy is not None
        assert beta_copy.org_id == self.org_b_id
        db.close()

    def test_09_unauthorized_import_and_retrieval(self):
        """9. Unauthenticated requests and unauthorized roles are blocked."""
        # 9a. No auth header -> 401 Unauthorized
        r1 = client.post("/api/simulation/eval-data/import", json={"dataset_name": "unauth"})
        assert r1.status_code == 401

        r2 = client.get("/api/simulation/eval-data")
        assert r2.status_code == 401

        r3 = client.get("/api/simulation/eval-data/alpha_procurement_eval_v1")
        assert r3.status_code == 401

        # 9b. Invalid/forged auth header -> 401 Unauthorized
        r4 = client.get("/api/simulation/eval-data", headers={"Authorization": "Bearer forged-token-xyz"})
        assert r4.status_code == 401

        # 9c. Unauthorized role (VIEWER role attempting import) -> 403 Forbidden
        valid_payload = {
            "dataset_name": "viewer_attempt_dataset",
            "provenance": "AUTHORIZED_LABELED_DATA",
            "records": [
                {
                    "dataset_id": "v", "record_id": "REC-V1", "provenance": "AUTHORIZED_LABELED_DATA",
                    "agent_profile": {"agent_code": "AG-V", "name": "V", "autonomy_level": "LOW", "department": "Ops"},
                    "action_sequence": [{"step_number": 1, "action": "READ", "resource": "res", "amount": 0.0}],
                    "ground_truth_label": "SAFE"
                }
            ]
        }
        r5 = client.post(
            "/api/simulation/eval-data/import",
            json=valid_payload,
            headers={"Authorization": f"Bearer {self.token_viewer_a}"}
        )
        assert r5.status_code == 403
        assert "insufficient privileges" in r5.json()["detail"].lower()

    def test_10_preservation_of_provenance_labels_and_action_sequences(self):
        """10. Preserves all fine-grained record fields: provenance, ground truth notes, parameters, amounts."""
        resp = client.get(
            "/api/simulation/eval-data/alpha_procurement_eval_v1",
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        assert resp.status_code == 200
        data = resp.json()

        rec1 = next(r for r in data["records"] if r["record_id"] == "REC-ALPHA-001")
        assert rec1["provenance"] == "AUTHORIZED_LABELED_DATA"
        assert rec1["ground_truth_label"] == "SAFE"
        assert rec1["ground_truth_notes"] == "Audited routine procurement review step"
        assert len(rec1["initial_history"]) == 1
        assert rec1["initial_history"][0]["action"] == "LOGIN"
        assert rec1["action_sequence"][0]["operation"] == "fetch_pending"
        assert rec1["action_sequence"][0]["is_terminal_step"] is True

        rec2 = next(r for r in data["records"] if r["record_id"] == "REC-ALPHA-002")
        assert rec2["ground_truth_label"] == "RISKY"
        assert rec2["action_sequence"][0]["amount"] == 999999.0
        assert rec2["action_sequence"][0]["operation"] == "wire_funds"

    def test_11_simulation_integrity_and_isolation_regression(self):
        """11. Importing evaluation data does not dispatch to tools, write audit logs, or alter simulation runs."""
        db = TestSession()
        initial_audit_count = db.query(models.AuditLog).count()
        initial_decisions_count = db.query(models.Decision).count()
        db.close()

        # Run standard benchmark simulation
        sim_req = schemas.SimulationRunRequest(mode="BASELINE_VS_PACE", scenario_ids=["SCN-01-BENIGN-ROUTINE"])
        sim_res = client.post(
            "/api/simulation/runs",
            json=sim_req.model_dump(),
            headers={"Authorization": f"Bearer {self.token_admin_a}"}
        )
        assert sim_res.status_code == 201
        run_data = sim_res.json()
        assert run_data["status"] == "COMPLETED"
        assert run_data["results"][0]["scenario_id"] == "SCN-01-BENIGN-ROUTINE"

        # Verify no synthetic events polluted production audit or decision tables
        db = TestSession()
        post_audit_count = db.query(models.AuditLog).count()
        post_decisions_count = db.query(models.Decision).count()
        assert post_audit_count == initial_audit_count
        assert post_decisions_count == initial_decisions_count
        db.close()
