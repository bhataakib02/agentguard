import datetime
import logging
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
import models

logger = logging.getLogger("agentguard.bootstrap")

CANONICAL_PLANS = [
    {
        "id": "FREE",
        "name": "Free Community",
        "description": "Basic community plan for evaluation",
        "price_monthly": 0.0,
        "max_users": 3,
        "max_ai_agents": 2,
        "max_api_keys": 1,
        "max_monthly_api_requests": 10000,
        "max_storage_gb": 5.0,
        "feature_flags": {}
    },
    {
        "id": "STARTER",
        "name": "Starter Plan",
        "description": "Small team AI agent governance & oversight",
        "price_monthly": 299.0,
        "max_users": 10,
        "max_ai_agents": 5,
        "max_api_keys": 5,
        "max_monthly_api_requests": 100000,
        "max_storage_gb": 20.0,
        "feature_flags": {}
    },
    {
        "id": "PROFESSIONAL",
        "name": "Professional Enterprise",
        "description": "Advanced enterprise AI governance, SOC & red-team lab",
        "price_monthly": 999.0,
        "max_users": 50,
        "max_ai_agents": 25,
        "max_api_keys": 20,
        "max_monthly_api_requests": 1000000,
        "max_storage_gb": 100.0,
        "feature_flags": {}
    },
    {
        "id": "ENTERPRISE",
        "name": "Custom Enterprise",
        "description": "Full-scale multi-tenant enterprise control plane with dedicated SLA",
        "price_monthly": 4999.0,
        "max_users": 1000,
        "max_ai_agents": 500,
        "max_api_keys": 100,
        "max_monthly_api_requests": 10000000,
        "max_storage_gb": 1000.0,
        "feature_flags": {}
    }
]

def ensure_canonical_plans(db: Session = None):
    """
    Deterministically and idempotently ensures all canonical plans
    (FREE, STARTER, PROFESSIONAL, ENTERPRISE) exist in the database.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        for plan_spec in CANONICAL_PLANS:
            existing = db.query(models.Plan).filter(models.Plan.id == plan_spec["id"]).first()
            if not existing:
                new_plan = models.Plan(**plan_spec)
                db.add(new_plan)
                logger.info(f"[Bootstrap] Created canonical plan: {plan_spec['id']} ({plan_spec['name']})")
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[Bootstrap] Error ensuring canonical plans: {e}")
        raise e
    finally:
        if close_db:
            db.close()

def bootstrap_database():
    """
    Initializes metadata schema and guarantees canonical reference data.
    Safe and idempotent across PostgreSQL and SQLite.
    """
    Base.metadata.create_all(bind=engine)
    ensure_canonical_plans()

if __name__ == "__main__":
    bootstrap_database()
    print("[AgentGuard] Database schema and canonical plans bootstrap complete.")
