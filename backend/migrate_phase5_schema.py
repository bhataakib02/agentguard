from database import engine, Base
from sqlalchemy import text
import models

def migrate():
    with engine.connect() as conn:
        print("Migrating Phase 5 columns...")
        # 1. audit_logs org_id
        conn.execute(text("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS org_id UUID;"))

        # 2. security_incidents columns
        conn.execute(text("ALTER TABLE security_incidents ADD COLUMN IF NOT EXISTS description TEXT;"))
        conn.execute(text("ALTER TABLE security_incidents ADD COLUMN IF NOT EXISTS affected_user_id UUID;"))
        conn.execute(text("ALTER TABLE security_incidents ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'SYSTEM';"))
        conn.execute(text("ALTER TABLE security_incidents ADD COLUMN IF NOT EXISTS assigned_to_user_id UUID;"))
        conn.execute(text("ALTER TABLE security_incidents ADD COLUMN IF NOT EXISTS resolution_notes TEXT;"))
        conn.execute(text("ALTER TABLE security_incidents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("ALTER TABLE security_incidents ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP;"))

        # 3. api_keys columns
        conn.execute(text("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS owner_id UUID;"))
        conn.execute(text("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS is_revoked BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP;"))
        conn.execute(text("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS revoked_by_id UUID;"))
        conn.execute(text("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMP;"))

        conn.commit()
        print("  [SUCCESS] Phase 5 columns added successfully!")

    print("Creating any missing Phase 5 tables (e.g. user_invitations)...")
    Base.metadata.create_all(bind=engine)
    print("  [SUCCESS] Phase 5 tables verified and created successfully!")

if __name__ == "__main__":
    migrate()
