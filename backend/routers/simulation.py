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
    current_user: models.User = Depends(get_current_user)
):
    """
    Start a bounded, reproducible simulation run comparing Baseline Policy vs PACE.
    Enforces server-side tenant scoping and caller identification.
    Never dispatches actions to external tools.
    """
    tenant_org_id = current_user.org_id or "default_org"
    caller_user_id = str(current_user.id)

    run_response = simulation_runner.execute_simulation_run(
        request=request,
        tenant_org_id=tenant_org_id,
        caller_user_id=caller_user_id
    )
    return run_response


@router.get("/runs/{run_id}", response_model=schemas.SimulationRunResponse)
def get_simulation_run(
    run_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve current status, action-by-action timeline, and comparative outcomes of a simulation run.
    """
    run_record = simulation_runner.get_run(run_id)
    if not run_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found in active simulation registry."
        )
    return run_record


@router.get("/runs/{run_id}/metrics", response_model=schemas.SimulationMetricsSummary)
def get_simulation_metrics(
    run_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieve comparative confusion matrices, lead-time stats, and detection metrics for a completed run.
    """
    run_record = simulation_runner.get_run(run_id)
    if not run_record:
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
    """
    success = simulation_runner.cancel_run(run_id)
    if not success:
        run_record = simulation_runner.get_run(run_id)
        if not run_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Simulation run '{run_id}' not found."
            )
        return {"status": run_record.status, "message": f"Run is already in state '{run_record.status}'."}

    return {"status": "CANCELLED", "message": f"Simulation run '{run_id}' was cancelled."}


# ============================================================================
# PHASE 4: AUTHORIZED EVALUATION-DATA SUPPORT ENDPOINTS
# ============================================================================

@router.post("/eval-data/import", response_model=schemas.EvaluationDataImportResponse, status_code=status.HTTP_201_CREATED)
def import_evaluation_dataset(
    request: schemas.EvaluationDataImportRequest,
    current_user: models.User = Depends(get_current_user)
):
    """
    Import authorized, labeled action-sequence evaluation data.
    Validates schema and rejects malformed records.
    Explicitly segregates evaluation data from production telemetry and models.
    """
    return simulation_runner.import_evaluation_dataset(request)


@router.get("/eval-data", response_model=List[schemas.EvaluationDatasetSummary])
def list_evaluation_datasets(
    current_user: models.User = Depends(get_current_user)
):
    """
    List imported authorized evaluation datasets with record counts and provenance disclosures.
    """
    return simulation_runner.list_evaluation_datasets()


@router.get("/eval-data/{dataset_name}")
def get_evaluation_dataset(
    dataset_name: str,
    current_user: models.User = Depends(get_current_user)
):
    """
    Inspect records and metadata of an authorized evaluation dataset.
    """
    dataset = simulation_runner.get_evaluation_dataset(dataset_name)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation dataset '{dataset_name}' not found."
        )
    return dataset

