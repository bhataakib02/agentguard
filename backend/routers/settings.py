from fastapi import APIRouter, Depends
from core.deps import get_current_user
import models

router = APIRouter(prefix="/settings", tags=["Platform Settings"])

@router.get("")
def get_settings(
    current_user: models.User = Depends(get_current_user)
):
    return {
        "organization_name": current_user.organization.name if current_user.organization else "AgentGuard Control Plane",
        "default_risk_threshold": 60,
        "max_autonomous_refund": 5000.0,
        "circuit_breaker_auto_tripping": True,
        "realtime_websockets_enabled": True,
        "audit_log_retention_days": 365
    }
