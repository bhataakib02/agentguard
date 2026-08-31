from fastapi import APIRouter

router = APIRouter(prefix="/integrations", tags=["Integrations Hub"])

@router.get("")
def list_integrations():
    return [
        {"name": "OpenAI LLM API", "category": "LLM Provider", "status": "CONNECTED", "health": "HEALTHY"},
        {"name": "Anthropic Claude API", "category": "LLM Provider", "status": "CONNECTED", "health": "HEALTHY"},
        {"name": "Google Gemini API", "category": "LLM Provider", "status": "CONNECTED", "health": "HEALTHY"},
        {"name": "Razorpay Payment Gateway", "category": "Payment API", "status": "CONNECTED", "health": "HEALTHY"},
        {"name": "AWS S3 Cloud Storage", "category": "Cloud Infrastructure", "status": "CONNECTED", "health": "HEALTHY"},
        {"name": "PostgreSQL Production Database", "category": "Database", "status": "CONNECTED", "health": "HEALTHY"}
    ]
