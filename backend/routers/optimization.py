from fastapi import APIRouter
from engines.model_router import model_router_engine

router = APIRouter(prefix="/optimization", tags=["Model & Compute Router"])

@router.get("/models")
def get_model_options():
    return model_router_engine.select_model(task_complexity="HIGH")

@router.get("/compute")
def get_compute_usage():
    return {
        "active_gpu_clusters": 2,
        "avg_cpu_utilization": "18.4%",
        "total_compute_cost_today": "₹1,420.00",
        "energy_consumption": "4.2 kWh",
        "optimization_mode": "BALANCED_SECURITY_AND_COST"
    }
