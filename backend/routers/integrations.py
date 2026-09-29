import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from core.deps import get_current_user
from core.supabase_admin import supabase_admin
import models

router = APIRouter(prefix="/integrations", tags=["Integrations Hub"])

@router.get("")
def list_integrations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Database live check
    db_connected = False
    try:
        db.execute(text("SELECT 1;"))
        db_connected = True
    except Exception:
        db_connected = False

    # 2. Supabase Auth
    supabase_configured = bool(getattr(supabase_admin, "is_configured", False))

    # 3. LLM Providers
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))
    anthropic_configured = bool(os.getenv("ANTHROPIC_API_KEY"))
    gemini_configured = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

    # 4. Payment & Cloud
    razorpay_configured = bool(os.getenv("RAZORPAY_KEY_ID"))
    aws_configured = bool(os.getenv("AWS_ACCESS_KEY_ID"))

    # 5. Webhooks count
    wh_query = db.query(models.WebhookEndpoint)
    if current_user.role != "SUPER_ADMIN":
        wh_query = wh_query.filter(models.WebhookEndpoint.org_id == current_user.org_id)
    wh_count = wh_query.filter(models.WebhookEndpoint.is_active == True).count()

    return [
        {
            "id": "db",
            "name": "PostgreSQL Production Database",
            "category": "Database",
            "status": "CONNECTED" if db_connected else "ERROR",
            "health": "HEALTHY" if db_connected else "DEGRADED",
            "details": "Primary PostgreSQL Relational Ledger"
        },
        {
            "id": "supabase_auth",
            "name": "Supabase Identity & Auth Core",
            "category": "Identity Provider",
            "status": "CONFIGURED" if supabase_configured else "NOT CONFIGURED",
            "health": "HEALTHY" if supabase_configured else "INACTIVE",
            "details": "Service Role JWT verification"
        },
        {
            "id": "webhooks",
            "name": "Enterprise Webhook Engine",
            "category": "Notifications & Dispatch",
            "status": "CONNECTED" if wh_count > 0 else "CONFIGURED",
            "health": "HEALTHY",
            "details": f"{wh_count} active webhook endpoint(s) registered"
        },
        {
            "id": "openai",
            "name": "OpenAI LLM API",
            "category": "LLM Provider",
            "status": "CONFIGURED" if openai_configured else "NOT CONFIGURED",
            "health": "STANDBY" if openai_configured else "NOT AVAILABLE",
            "details": "API Key configuration in environment"
        },
        {
            "id": "anthropic",
            "name": "Anthropic Claude API",
            "category": "LLM Provider",
            "status": "CONFIGURED" if anthropic_configured else "NOT CONFIGURED",
            "health": "STANDBY" if anthropic_configured else "NOT AVAILABLE",
            "details": "API Key configuration in environment"
        },
        {
            "id": "gemini",
            "name": "Google Gemini API",
            "category": "LLM Provider",
            "status": "CONFIGURED" if gemini_configured else "NOT CONFIGURED",
            "health": "STANDBY" if gemini_configured else "NOT AVAILABLE",
            "details": "API Key configuration in environment"
        },
        {
            "id": "razorpay",
            "name": "Razorpay Payment Gateway",
            "category": "Payment API",
            "status": "CONFIGURED" if razorpay_configured else "NOT CONFIGURED",
            "health": "STANDBY" if razorpay_configured else "NOT AVAILABLE",
            "details": "Payment webhook & intent handler"
        },
        {
            "id": "aws_s3",
            "name": "AWS S3 Cloud Storage",
            "category": "Cloud Infrastructure",
            "status": "CONFIGURED" if aws_configured else "NOT CONFIGURED",
            "health": "STANDBY" if aws_configured else "NOT AVAILABLE",
            "details": "Report PDF & audit archive bucket"
        }
    ]
