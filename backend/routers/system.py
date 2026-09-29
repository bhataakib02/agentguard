from fastapi import APIRouter, Depends
from core.deps import get_current_user
import models

router = APIRouter(prefix="/system", tags=["System Health & Monitoring"])

@router.get("/health")
def get_system_health(
    current_user: models.User = Depends(get_current_user)
):
    return {
        "status": "HEALTHY",
        "services": {
            "api_server": "ONLINE",
            "database": "ONLINE",
            "websocket_server": "ONLINE",
            "policy_engine": "ONLINE",
            "risk_engine": "ONLINE",
            "circuit_breaker": "ONLINE"
        },
        "version": "1.0.0",
        "uptime_seconds": 86400
    }
