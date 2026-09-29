from database import engine, Base
from sqlalchemy import text
import models

def migrate():
    with engine.connect() as conn:
        # 1. Add new columns to webhook_deliveries
        print("Migrating webhook_deliveries columns...")
        conn.execute(text("ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS response_body_preview TEXT;"))
        conn.execute(text("ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMP;"))
        conn.commit()
        print("  [SUCCESS] webhook_deliveries columns migrated!")

    # 2. Create any missing Phase 4 tables (agent_executions, model_pricing, agent_budget_configs, agent_risk_signals)
    print("Creating any missing Phase 4 tables...")
    Base.metadata.create_all(bind=engine)
    print("  [SUCCESS] Phase 4 tables verified and created successfully!")

if __name__ == "__main__":
    migrate()
