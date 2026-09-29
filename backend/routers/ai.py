from fastapi import APIRouter, Depends
from core.deps import get_current_user
import models
from engines.model_router import model_router_engine

router = APIRouter(prefix="/ai", tags=["AI Engine Router"])

@router.get("/models")
def get_ai_models(
    current_user: models.User = Depends(get_current_user)
):
    return model_router_engine.select_model(task_complexity="HIGH")
