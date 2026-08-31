from fastapi import APIRouter

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])

@router.get("/metrics")
def get_impact_metrics():
    return {
        "prevented_fraud_amount": "₹4,85,000.00",
        "autonomous_efficiency_gain": "94.2%",
        "human_escalation_rate": "5.8%",
        "avg_decision_latency_ms": 142
    }
