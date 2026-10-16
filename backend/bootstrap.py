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
        "id": "PRO",
        "name": "Pro Tier",
        "description": "Advanced enterprise AI governance, SOC & red-team lab (Pro)",
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

def ensure_schema_compatibility(db_engine=engine):
    """
    Safely checks and adds any missing columns to existing tables
    (SQLite and PostgreSQL compatible) to ensure backward compatibility
    without drops or destructive resets.
    """
    from sqlalchemy import inspect, text
    inspector = inspect(db_engine)
    
    # Check agent_credentials columns
    if "agent_credentials" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("agent_credentials")}
        with db_engine.connect() as conn:
            if "name" not in cols:
                conn.execute(text("ALTER TABLE agent_credentials ADD COLUMN name VARCHAR;"))
            if "key_prefix" not in cols:
                conn.execute(text("ALTER TABLE agent_credentials ADD COLUMN key_prefix VARCHAR;"))
            if "last_used_at" not in cols:
                conn.execute(text("ALTER TABLE agent_credentials ADD COLUMN last_used_at TIMESTAMP;"))
            if "revoked_at" not in cols:
                conn.execute(text("ALTER TABLE agent_credentials ADD COLUMN revoked_at TIMESTAMP;"))
            conn.commit()

    # Check agent_passports columns
    if "agent_passports" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("agent_passports")}
        with db_engine.connect() as conn:
            if "algorithm" not in cols:
                conn.execute(text("ALTER TABLE agent_passports ADD COLUMN algorithm VARCHAR DEFAULT 'Ed25519';"))
            if "key_id" not in cols:
                conn.execute(text("ALTER TABLE agent_passports ADD COLUMN key_id VARCHAR DEFAULT 'agentguard-root-1';"))
            if "passport_version" not in cols:
                conn.execute(text("ALTER TABLE agent_passports ADD COLUMN passport_version VARCHAR DEFAULT '1.0';"))
            if "claims" not in cols:
                conn.execute(text("ALTER TABLE agent_passports ADD COLUMN claims JSON;"))
            conn.commit()

    # Check organizations KMS BYOK columns
    if "organizations" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("organizations")}
        with db_engine.connect() as conn:
            if "kms_provider" not in cols:
                conn.execute(text("ALTER TABLE organizations ADD COLUMN kms_provider VARCHAR DEFAULT 'SYSTEM_MANAGED';"))
            if "kms_key_arn" not in cols:
                conn.execute(text("ALTER TABLE organizations ADD COLUMN kms_key_arn VARCHAR;"))
            if "kms_key_alias" not in cols:
                conn.execute(text("ALTER TABLE organizations ADD COLUMN kms_key_alias VARCHAR;"))
            if "kms_key_status" not in cols:
                conn.execute(text("ALTER TABLE organizations ADD COLUMN kms_key_status VARCHAR DEFAULT 'NOT_CONFIGURED';"))
            if "kms_config_json" not in cols:
                conn.execute(text("ALTER TABLE organizations ADD COLUMN kms_config_json JSON DEFAULT '{}'::json;"))
            conn.commit()

    # Check evaluation_datasets and evaluation_dataset_records table columns
    if "evaluation_datasets" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("evaluation_datasets")}
        with db_engine.connect() as conn:
            if "description" not in cols:
                conn.execute(text("ALTER TABLE evaluation_datasets ADD COLUMN description TEXT;"))
            if "tags" not in cols:
                conn.execute(text("ALTER TABLE evaluation_datasets ADD COLUMN tags JSON;"))
            if "metadata_json" not in cols:
                conn.execute(text("ALTER TABLE evaluation_datasets ADD COLUMN metadata_json JSON;"))
            conn.commit()


def bootstrap_database():
    """
    Initializes metadata schema and guarantees canonical reference data.
    Safe and idempotent across PostgreSQL and SQLite.
    """
    try:
        Base.metadata.create_all(bind=engine)
        ensure_schema_compatibility(engine)
        ensure_canonical_plans()
        logger.info("[AgentGuard] Database schema and canonical plans bootstrap complete.")
    except Exception as e:
        logger.error(
            f"[AgentGuard Bootstrap] Database initialization encountered an error: {e}\n"
            f"If using Supabase or remote PostgreSQL, please verify your DATABASE_URL in backend/.env "
            f"and check whether your database project/pooler is active and not paused."
        )
        raise

if __name__ == "__main__":
    try:
        bootstrap_database()
        print("[AgentGuard] Database schema and canonical plans bootstrap complete.")
    except Exception as e:
        print(f"[AgentGuard] Bootstrap failed: {e}")


