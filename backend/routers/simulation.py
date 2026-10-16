"""
Simulation and Evaluation Lab Router for AGENTGUARD PACE Phase 3.
Provides endpoints for inspecting versioned simulation scenarios,
triggering bounded reproducible simulation runs, retrieving comparative
Baseline vs. PACE metrics, and managing execution states.

All simulations execute within bounded in-memory isolation, never dispatching
to external tools or writing synthetic events to production audit logs.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from core.deps import get_current_user
from engines.simulation_engine import simulation_runner

router = APIRouter(prefix="/simulation", tags=["PACE Simulation Lab"])


@router.get("/scenarios", response_model=List[schemas.SimulationScenario])
def list_scenarios(
    category: Optional[str] = Query(None, description="Optional category filter"),
    current_user: models.User = Depends(get_current_user)
):
    """
    List all versioned scenarios available in the Simulation Scenario Library.
    Categorized into 10 deterministic test suites probing safe and adversarial behaviors.
    """
    scenarios = simulation_runner.get_scenarios(category=category)
    return scenarios


@router.post("/runs", response_model=schemas.SimulationRunResponse, status_code=status.HTTP_201_CREATED)
def start_simulation_run(
    request: schemas.SimulationRunRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a bounded, reproducible simulation run comparing Baseline Policy vs PACE.
    Supports predefined scenario libraries and persisted evaluation datasets.
    Enforces server-side tenant scoping and 5-role enterprise IAM.
    Never dispatches actions to external tools.
    """
    if current_user.role == "AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: AGENT represents an AI machine identity and cannot launch simulations"
        )

    if current_user.role == "AUDITOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: AUDITOR role has read-only access and cannot launch simulations"
        )

    if current_user.role not in ENTERPRISE_EVAL_IMPORT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Insufficient privileges to launch simulations. Role '{current_user.role}' is not authorized."
        )

    tenant_org_id = str(current_user.org_id) if current_user.org_id else "default_org"
    caller_user_id = str(current_user.id)

    run_response = simulation_runner.execute_simulation_run(
        request=request,
        tenant_org_id=tenant_org_id,
        caller_user_id=caller_user_id,
        db=db
    )
    return run_response


@router.get("/runs/{run_id}", response_model=schemas.SimulationRunResponse)
def get_simulation_run(
    run_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve current status, action-by-action timeline, and comparative outcomes of a simulation run.
    Enforces server-side tenant isolation and 5-role enterprise IAM.
    """
    if current_user.role == "AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: AGENT represents an AI machine identity and cannot access simulation runs"
        )

    if current_user.role not in ENTERPRISE_EVAL_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Role '{current_user.role}' is not authorized to access simulation runs."
        )

    run_record = simulation_runner.get_run(run_id)
    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found in active simulation registry."
        )

    run_org = simulation_runner.get_run_org(run_id)
    caller_org = str(current_user.org_id) if current_user.org_id else "default_org"
    if run_org and caller_org and run_org != caller_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found."
        )

    return run_record


@router.get("/runs/{run_id}/metrics", response_model=schemas.SimulationMetricsSummary)
def get_simulation_metrics(
    run_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve comparative confusion matrices, lead-time stats, and detection metrics for a completed run.
    Enforces server-side tenant isolation and 5-role enterprise IAM.
    """
    if current_user.role == "AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: AGENT represents an AI machine identity and cannot access simulation runs"
        )

    if current_user.role not in ENTERPRISE_EVAL_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Role '{current_user.role}' is not authorized to access simulation runs."
        )

    run_record = simulation_runner.get_run(run_id)
    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found."
        )

    run_org = simulation_runner.get_run_org(run_id)
    caller_org = str(current_user.org_id) if current_user.org_id else "default_org"
    if run_org and caller_org and run_org != caller_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found."
        )

    if not run_record.metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Simulation run '{run_id}' does not have calculated metrics yet (Status: {run_record.status})."
        )
    return run_record.metrics


@router.post("/runs/{run_id}/cancel")
def cancel_simulation_run(
    run_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """
    Cancel a running simulation safely.
    Enforces server-side tenant isolation and 5-role enterprise IAM.
    """
    if current_user.role == "AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: AGENT represents an AI machine identity and cannot cancel simulations"
        )

    if current_user.role not in ENTERPRISE_EVAL_IMPORT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Insufficient privileges to cancel simulations. Role '{current_user.role}' is not authorized."
        )

    run_record = simulation_runner.get_run(run_id)
    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found."
        )

    run_org = simulation_runner.get_run_org(run_id)
    caller_org = str(current_user.org_id) if current_user.org_id else "default_org"
    if run_org and caller_org and run_org != caller_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found."
        )

    success = simulation_runner.cancel_run(run_id)
    if not success:
        return {"status": run_record.status, "message": f"Run is already in state '{run_record.status}'."}

    return {"status": "CANCELLED", "message": f"Simulation run '{run_id}' was cancelled."}


# ============================================================================
# PHASE 4 & PHASE 5.1/5.2: AUTHORIZED EVALUATION-DATA SUPPORT ENDPOINTS
# Enterprise IAM 5-Role Alignment: ADMIN, MANAGER, SECURITY_OFFICER, AUDITOR, AGENT
# ============================================================================

ENTERPRISE_EVAL_IMPORT_ROLES = {"ADMIN", "SECURITY_OFFICER", "MANAGER"}
ENTERPRISE_EVAL_READ_ROLES = {"ADMIN", "SECURITY_OFFICER", "MANAGER", "AUDITOR"}

@router.post("/eval-data/import", response_model=schemas.EvaluationDataImportResponse, status_code=status.HTTP_201_CREATED)
def import_evaluation_dataset(
    request: schemas.EvaluationDataImportRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import authorized, labeled action-sequence evaluation data.
    Validates schema, provenance, and payload limits, rejecting malformed records.
    Persists evaluation datasets and records into tenant-isolated database storage.
    Enforces enterprise five-role IAM:
      - ADMIN, SECURITY_OFFICER, MANAGER: Authorized to import.
      - AUDITOR: Read-only access; cannot import.
      - AGENT: Machine identity; blocked from human UI management.
    """
    if current_user.role == "AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: AGENT represents an AI machine identity and cannot manage evaluation datasets"
        )

    if current_user.role == "AUDITOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: AUDITOR role has read-only access and cannot import evaluation datasets"
        )

    if current_user.role not in ENTERPRISE_EVAL_IMPORT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Insufficient privileges to import evaluation datasets. Role '{current_user.role}' is not authorized."
        )

    org_id = str(current_user.org_id) if current_user.org_id else None
    return simulation_runner.import_evaluation_dataset(request, db=db, org_id=org_id)


@router.get("/eval-data", response_model=List[schemas.EvaluationDatasetSummary])
def list_evaluation_datasets(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List imported authorized evaluation datasets with record counts and provenance disclosures.
    Enforces server-side tenant scoping from authenticated identity.
    Accessible to authorized human roles (ADMIN, SECURITY_OFFICER, MANAGER, AUDITOR).
    Machine identities (AGENT) are blocked.
    """
    if current_user.role == "AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: AGENT represents an AI machine identity and cannot manage evaluation datasets"
        )

    if current_user.role not in ENTERPRISE_EVAL_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Role '{current_user.role}' is not authorized to access evaluation datasets."
        )

    org_id = str(current_user.org_id) if current_user.org_id else None
    return simulation_runner.list_evaluation_datasets(db=db, org_id=org_id)


@router.get("/eval-data/{dataset_name}")
def get_evaluation_dataset(
    dataset_name: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inspect records and metadata of an authorized evaluation dataset.
    Enforces server-side tenant scoping from authenticated identity.
    Accessible to authorized human roles (ADMIN, SECURITY_OFFICER, MANAGER, AUDITOR).
    Machine identities (AGENT) are blocked.
    """
    if current_user.role == "AGENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: AGENT represents an AI machine identity and cannot manage evaluation datasets"
        )

    if current_user.role not in ENTERPRISE_EVAL_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Role '{current_user.role}' is not authorized to access evaluation datasets."
        )

    org_id = str(current_user.org_id) if current_user.org_id else None
    dataset = simulation_runner.get_evaluation_dataset(dataset_name, db=db, org_id=org_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation dataset '{dataset_name}' not found."
        )
    return dataset

