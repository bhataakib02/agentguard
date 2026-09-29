import sys, os, datetime
sys.path.append(os.path.dirname(__file__))

from database import engine, SessionLocal, Base
from sqlalchemy import text
import models
from clean_demo_data import clean_all_demo_data

def migrate_columns():
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'ACTIVE';"))
        db.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS admin_email VARCHAR;"))
        db.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS display_name VARCHAR;"))
        db.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS logo_url VARCHAR;"))
        db.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS logo_path VARCHAR;"))
        db.commit()
    except Exception as e:
        print(f"Migration note: {e}")
    finally:
        db.close()

def seed_plans():
    migrate_columns()
    db = SessionLocal()
    plans_data = [
        {"id": "FREE", "name": "Free Community", "description": "Basic community plan for evaluation", "price_monthly": 0.0, "max_users": 3, "max_ai_agents": 2, "max_api_keys": 1, "max_monthly_api_requests": 10000, "max_storage_gb": 5.0},
        {"id": "STARTER", "name": "Starter Plan", "description": "Small team AI agent governance & oversight", "price_monthly": 299.0, "max_users": 10, "max_ai_agents": 5, "max_api_keys": 5, "max_monthly_api_requests": 100000, "max_storage_gb": 20.0},
        {"id": "PROFESSIONAL", "name": "Professional Enterprise", "description": "Advanced enterprise AI governance, SOC & red-team lab", "price_monthly": 999.0, "max_users": 50, "max_ai_agents": 25, "max_api_keys": 20, "max_monthly_api_requests": 1000000, "max_storage_gb": 100.0},
        {"id": "ENTERPRISE", "name": "Custom Enterprise", "description": "Full-scale multi-tenant enterprise control plane with dedicated SLA", "price_monthly": 4999.0, "max_users": 1000, "max_ai_agents": 500, "max_api_keys": 100, "max_monthly_api_requests": 10000000, "max_storage_gb": 1000.0}
    ]

    for p in plans_data:
        existing = db.query(models.Plan).filter(models.Plan.id == p["id"]).first()
        if not existing:
            plan = models.Plan(**p)
            db.add(plan)
    db.commit()

    orgs = db.query(models.Organization).all()
    for o in orgs:
        lic = db.query(models.License).filter(models.License.org_id == o.id).first()
        if not lic:
            lic = models.License(
                org_id=o.id,
                plan_id="ENTERPRISE",
                status="ACTIVE",
                start_date=datetime.datetime.utcnow(),
                expiry_date=datetime.datetime.utcnow() + datetime.timedelta(days=365),
                max_users=1000,
                max_ai_agents=500,
                max_api_keys=100,
                max_monthly_api_requests=10000000
            )
            db.add(lic)
        usage = db.query(models.LicenseUsage).filter(models.LicenseUsage.org_id == o.id).first()
        if not usage:
            usage = models.LicenseUsage(org_id=o.id, api_requests_count=0, storage_used_gb=0.0)
            db.add(usage)
    db.commit()
    db.close()

def seed_data():
    print("Initializing AGENTGUARD production database schema...")
    Base.metadata.create_all(bind=engine)
    seed_plans()
    print("SaaS plans and tenant licenses seeded successfully.")

if __name__ == "__main__":
    seed_data()
