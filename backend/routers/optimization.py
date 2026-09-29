from fastapi import APIRouter, Depends
from core.deps import get_current_user
import models
from engines.model_router import model_router_engine

router = APIRouter(prefix="/optimization", tags=["Model & Compute Router"])

@router.get("/models")
def get_model_options(
    current_user: models.User = Depends(get_current_user)
):
    return model_router_engine.select_model(task_complexity="HIGH")

@router.get("/compute")
def get_compute_usage(
    current_user: models.User = Depends(get_current_user)
):
    return {
        "active_gpu_clusters": 2,
        "avg_cpu_utilization": "18.4%",
        "total_compute_cost_today": "₹1,420.00",
        "energy_consumption": "4.2 kWh",
        "optimization_mode": "BALANCED_SECURITY_AND_COST"
    }
