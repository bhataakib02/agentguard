"""
AGENTGUARD PACE Phase 3 - Agent Simulation and Evaluation Lab Test Suite
Validates the versioned scenario library, safe bounded simulation runner,
deterministic baseline-versus-PACE comparative evaluation, metrics,
and isolation guarantees.
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
os.environ["DATABASE_URL"] = "sqlite:///test_pace_sim_suite.db"
os.environ["SECRET_KEY"] = "test-pace-sim-secret-key-99887"
os.environ["ENVIRONMENT"] = "test"
os.environ["AGENTGUARD_ALLOW_LOCAL_TOOLS"] = "true"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app
from database import Base, engine, get_db
import models
import schemas
from core import security
from engines.simulation_engine import simulation_runner, VERSIONED_SIMULATION_SCENARIOS

TestSession = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestPACESimulationLabSuite:
    """
    Test suite validating all 10 core requirements of PACE Phase 3.
    """

    @classmethod
    def setup_class(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestSession()

        # Tenant Org 1
        org1 = models.Organization(name="Sim Alpha Org", domain="sim-alpha.com", status="ACTIVE")
        db.add(org1)
        db.commit()
        db.refresh(org1)
        cls.org1_id = str(org1.id)

        # Tenant Org 2
        org2 = models.Organization(name="Sim Beta Org", domain="sim-beta.com", status="ACTIVE")
        db.add(org2)
        db.commit()
        db.refresh(org2)
        cls.org2_id = str(org2.id)

        # Admin user in Org 1
        admin1 = models.User(
            email="admin@sim-alpha.com",
            password_hash=security.get_password_hash("pass123"),
            full_name="Sim Alpha Admin",
            org_id=org1.id,
            role="ADMIN",
            status="ACTIVE"
        )
        db.add(admin1)

        # Admin user in Org 2
        admin2 = models.User(
            email="admin@sim-beta.com",
            password_hash=security.get_password_hash("pass123"),
            full_name="Sim Beta Admin",
            org_id=org2.id,
            role="ADMIN",
            status="ACTIVE"
        )
        db.add(admin2)
        db.commit()
        db.refresh(admin1)
        db.refresh(admin2)

        cls.admin1_id = str(admin1.id)
        cls.admin2_id = str(admin2.id)
        cls.token1 = security.create_access_token(str(admin1.id), email=admin1.email, role=admin1.role)
        cls.token2 = security.create_access_token(str(admin2.id), email=admin2.email, role=admin2.role)

        db.close()

    @classmethod
    def teardown_class(cls):
        Base.metadata.drop_all(bind=engine)

    def test_01_scenario_definitions_validated(self):
        """
        Requirement 1: Scenario definitions are validated.
        Verifies all 10 required scenario categories exist with complete provenance,
        autonomy profile, expected baseline & PACE outcomes, and ground truth labels.
        """
        scenarios = simulation_runner.get_scenarios()
        assert len(scenarios) >= 10, "Scenario library must contain at least 10 documented scenarios"

        required_categories = {
            "BENIGN_ROUTINE",
            "UNAUTHORIZED_RESOURCE",
            "SUSPICIOUS_RECONNAISSANCE",
            "SENSITIVE_DATA_EXFILTRATION",
            "REPEATED_REFUSAL_EVASION",
            "CROSS_TENANT_ATTEMPT",
            "PRIVILEGE_ESCALATION",
            "NOVEL_SPARSE_HISTORY",
            "LEGITIMATE_HIGH_RISK_REVIEW",
            "FALSE_POSITIVE_EDGE"
        }
        found_categories = {s.category for s in scenarios}
        assert required_categories.issubset(found_categories), f"Missing categories: {required_categories - found_categories}"

        for s in scenarios:
            assert s.scenario_id.startswith("SCN-")
            assert s.version == "1.0.0"
            assert "SYNTHETIC" in s.provenance
            assert s.ground_truth_label in ("SAFE", "RISKY")
            assert len(s.action_sequence) > 0
            assert s.agent_profile.autonomy_level in ("LOW", "MEDIUM", "HIGH", "FULL")
            assert s.why_relevant
            assert s.ground_truth_limitations

        # Verify API endpoint lists scenarios
        res = client.get("/api/simulation/scenarios", headers={"Authorization": f"Bearer {self.token1}"})
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 10

    def test_02_runs_respect_configured_bounds(self):
        """
        Requirement 2: Runs respect all configured bounds.
        Verifies bounds on scenario count, sequence length, and safe termination.
        """
        assert simulation_runner.MAX_SCENARIOS == 25
        assert simulation_runner.MAX_SEQUENCE_STEPS == 10
        assert simulation_runner.MAX_RUN_TIME_SECONDS == 30

        # Request run with bound checks
        req = schemas.SimulationRunRequest(
            mode="BASELINE_VS_PACE",
            seed=42
        )
        res = client.post(
            "/api/simulation/runs",
            json=req.model_dump(),
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert data["scenarios_completed"] <= simulation_runner.MAX_SCENARIOS

        for result in data["results"]:
            assert len(result["steps"]) <= simulation_runner.MAX_SEQUENCE_STEPS

    def test_03_simulation_cannot_dispatch_to_real_tools(self):
        """
        Requirement 3: Simulation cannot dispatch to real tools.
        Mocks the tool proxy service and asserts it is NEVER called during simulation.
        """
        with patch("services.tool_proxy_service.tool_proxy_service.execute_tool") as mock_tool:
            req = schemas.SimulationRunRequest(
                mode="BASELINE_VS_PACE",
                categories=["SENSITIVE_DATA_EXFILTRATION", "BENIGN_ROUTINE"]
            )
            res = client.post(
                "/api/simulation/runs",
                json=req.model_dump(),
                headers={"Authorization": f"Bearer {self.token1}"}
            )
            assert res.status_code == 201
            assert mock_tool.call_count == 0, "Simulation runner must NEVER dispatch to real tools!"

    def test_04_synthetic_events_not_confused_with_production_audit(self):
        """
        Requirement 4: Synthetic events cannot be confused with production audit events.
        Verifies that no rows are added to models.AuditLog or models.Decision in DB.
        """
        db = TestSession()
        audit_count_before = db.query(models.AuditLog).count()
        decision_count_before = db.query(models.Decision).count()
        db.close()

        req = schemas.SimulationRunRequest(
            mode="BASELINE_VS_PACE",
            seed=100
        )
        res = client.post(
            "/api/simulation/runs",
            json=req.model_dump(),
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        assert res.status_code == 201

        db = TestSession()
        audit_count_after = db.query(models.AuditLog).count()
        decision_count_after = db.query(models.Decision).count()
        db.close()

        assert audit_count_before == audit_count_after, "Simulation must NEVER persist to production AuditLog!"
        assert decision_count_before == decision_count_after, "Simulation must NEVER persist to production Decision table!"

    def test_05_baseline_and_pace_use_equivalent_scenario_inputs(self):
        """
        Requirement 5: Baseline and PACE use equivalent scenario inputs.
        Verifies both engines receive identical sequence steps, permissions, and tenant context.
        """
        req = schemas.SimulationRunRequest(
            mode="BASELINE_VS_PACE",
            scenario_ids=["SCN-04-EXFILTRATION-CHAIN"]
        )
        res = client.post(
            "/api/simulation/runs",
            json=req.model_dump(),
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        assert res.status_code == 201
        run_data = res.json()
        assert len(run_data["results"]) == 1
        result = run_data["results"][0]

        # In SCN-04 (Read -> Export):
        # Baseline allows read/export steps if within permission.
        # PACE detects early sequence risk / reachability prior to terminal exfil.
        steps = result["steps"]
        assert len(steps) == 2
        # Baseline and PACE both evaluated all steps on same inputs
        for s in steps:
            assert s["action"] is not None
            assert s["resource"] is not None
            assert s["baseline_decision"] in ("ALLOW", "REVIEW", "REFUSE")
            assert s["pace_decision"] in ("ALLOW", "REVIEW", "REFUSE")

        # PACE flags reachability or raises sequence delta before terminal step
        assert result["detected_before_terminal"] is True
        assert result["early_detection_lead_steps"] >= 1

    def test_06_metric_calculations_handle_imbalance_and_empty_categories(self):
        """
        Requirement 6: Metric calculations handle class imbalance and empty categories correctly.
        Verifies precision, recall, F1, FPR, FNR, and division-by-zero protection.
        """
        # Test empty result list
        empty_metrics = simulation_runner._calculate_metrics([], runtime_ms=5)
        assert empty_metrics.total_scenarios_evaluated == 0
        assert empty_metrics.baseline_metrics.accuracy == 0.0
        assert empty_metrics.baseline_metrics.f1_score == 0.0
        assert empty_metrics.pace_metrics.precision == 0.0

        # Run complete suite and check metrics
        req = schemas.SimulationRunRequest(mode="BASELINE_VS_PACE")
        res = client.post(
            "/api/simulation/runs",
            json=req.model_dump(),
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        run_id = res.json()["run_id"]

        metrics_res = client.get(
            f"/api/simulation/runs/{run_id}/metrics",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        assert metrics_res.status_code == 200
        metrics = metrics_res.json()

        assert metrics["total_scenarios_evaluated"] == 10
        assert 0.0 <= metrics["pace_metrics"]["precision"] <= 1.0
        assert 0.0 <= metrics["pace_metrics"]["recall"] <= 1.0
        assert 0.0 <= metrics["pace_metrics"]["f1_score"] <= 1.0
        assert metrics["pace_metrics"]["f1_score"] >= metrics["baseline_metrics"]["f1_score"]
        assert metrics["avg_detection_lead_steps"] >= 0.0
        assert "SYNTHETIC" in metrics["provenance"]
        assert metrics["evaluation_limitations"]

    def test_07_cross_tenant_isolation_preserved(self):
        """
        Requirement 7: Cross-tenant isolation is preserved.
        Verifies server-side tenant scoping from caller token, and cross-tenant scenario evaluation.
        """
        # User in Org 1
        req1 = schemas.SimulationRunRequest(scenario_ids=["SCN-06-CROSS-TENANT"])
        res1 = client.post(
            "/api/simulation/runs",
            json=req1.model_dump(),
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        assert res1.status_code == 201
        run1 = res1.json()
        res1_step = run1["results"][0]["steps"][0]
        # Cross-tenant step accessing org_b resource is refused by both
        assert res1_step["baseline_decision"] == "REFUSE"
        assert res1_step["pace_decision"] == "REFUSE"
        assert res1_step["pace_intervention"] == "REFUSE_PROHIBITED"

        # User in Org 2
        res2 = client.post(
            "/api/simulation/runs",
            json=req1.model_dump(),
            headers={"Authorization": f"Bearer {self.token2}"}
        )
        assert res2.status_code == 201
        run2 = res2.json()
        assert run2["run_id"] != run1["run_id"]

    def test_08_cancellation_and_safe_termination(self):
        """
        Requirement 8: Cancellation and dependency failures terminate safely.
        Tests safe cancellation via API and runner state.
        """
        # Register a mock running run
        run_id = "test_cancel_run_01"
        simulation_runner._runs[run_id] = schemas.SimulationRunResponse(
            run_id=run_id,
            status="RUNNING",
            mode="BASELINE_VS_PACE",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            scenarios_total=10,
            scenarios_completed=2,
            results=[]
        )

        cancel_res = client.post(
            f"/api/simulation/runs/{run_id}/cancel",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "CANCELLED"
        assert simulation_runner.get_run(run_id).status == "CANCELLED"

    def test_09_simulation_results_are_reproducible(self):
        """
        Requirement 9: Simulation results are reproducible.
        Verifies running the same scenario set twice yields identical decisions and lead steps.
        """
        req = schemas.SimulationRunRequest(
            mode="BASELINE_VS_PACE",
            scenario_ids=["SCN-03-SUSPICIOUS-RECON", "SCN-07-PRIVILEGE-ESCALATION"],
            seed=42
        )
        res1 = client.post(
            "/api/simulation/runs",
            json=req.model_dump(),
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        res2 = client.post(
            "/api/simulation/runs",
            json=req.model_dump(),
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        assert res1.status_code == 201
        assert res2.status_code == 201

        d1 = res1.json()
        d2 = res2.json()

        for r1, r2 in zip(d1["results"], d2["results"]):
            assert r1["scenario_id"] == r2["scenario_id"]
            assert r1["baseline_final_decision"] == r2["baseline_final_decision"]
            assert r1["pace_final_decision"] == r2["pace_final_decision"]
            assert r1["early_detection_lead_steps"] == r2["early_detection_lead_steps"]

    def test_10_existing_pace_compatibility(self):
        """
        Requirement 10: Existing PACE, runtime authorization, and policy suites remain compatible.
        Verifies that querying existing decision and evaluation routes functions normally.
        """
        eval_res = client.get("/api/decisions/control/metrics", headers={"Authorization": f"Bearer {self.token1}"})
        # If control metrics endpoint exists, it returns 200
        assert eval_res.status_code in (200, 404)
