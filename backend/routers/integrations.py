from fastapi import APIRouter, Depends
from core.deps import get_current_user
import models

router = APIRouter(prefix="/integrations", tags=["Integrations Hub"])

@router.get("")
def list_integrations(
    current_user: models.User = Depends(get_current_user)
):
    return [
        {"name": "OpenAI LLM API", "category": "LLM Provider", "status": "CONNECTED", "health": "HEALTHY"},
        {"name": "Anthropic Claude API", "category": "LLM Provider", "status": "CONNECTED", "health": "HEALTHY"},
        {"name": "Google Gemini API", "category": "LLM Provider", "status": "CONNECTED", "health": "HEALTHY"},
        {"name": "Razorpay Payment Gateway", "category": "Payment API", "status": "CONNECTED", "health": "HEALTHY"},
        {"name": "AWS S3 Cloud Storage", "category": "Cloud Infrastructure", "status": "CONNECTED", "health": "HEALTHY"},
        {"name": "PostgreSQL Production Database", "category": "Database", "status": "CONNECTED", "health": "HEALTHY"}
    ]
