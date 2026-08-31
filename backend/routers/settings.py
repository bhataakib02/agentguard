from fastapi import APIRouter

router = APIRouter(prefix="/settings", tags=["Platform Settings"])

@router.get("")
def get_settings():
    return {
        "organization_name": "AgentGuard Control Plane",
        "default_risk_threshold": 60,
        "max_autonomous_refund": 5000.0,
        "circuit_breaker_auto_tripping": True,
        "realtime_websockets_enabled": True,
        "audit_log_retention_days": 365
    }
