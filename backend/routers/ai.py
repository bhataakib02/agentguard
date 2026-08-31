from fastapi import APIRouter
from engines.model_router import model_router_engine

router = APIRouter(prefix="/ai", tags=["AI Engine Router"])

@router.get("/models")
def get_ai_models():
    return model_router_engine.select_model(task_complexity="HIGH")
