from fastapi import APIRouter, Depends
from core.deps import get_current_user
import models

router = APIRouter(prefix="/developers", tags=["Developer Platform & APIs"])

@router.get("/docs-summary")
def get_api_docs_summary(
    current_user: models.User = Depends(get_current_user)
):
    return {
        "title": "AgentGuard Runtime Control Plane REST API",
        "version": "v1.0.0",
        "base_url": "http://localhost:8000/api",
        "endpoints": [
            "POST /api/auth/register",
            "POST /api/auth/login",
            "GET /api/agents",
            "POST /api/agents",
            "GET /api/agents/{id}/passport",
            "POST /api/capabilities/issue",
            "POST /api/decisions/evaluate",
            "POST /api/approvals/{id}/act",
            "POST /api/red-team/run",
            "POST /api/digital-twin/run",
            "POST /api/assistant/query"
        ]
    }
