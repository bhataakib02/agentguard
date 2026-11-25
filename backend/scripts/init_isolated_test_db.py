import os
import sys
from sqlalchemy import create_engine, text

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def setup_isolated_db(db_url: str):
    print(f"Connecting to isolated test database: {db_url}...")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        with conn.begin():
            # 1. Create Supabase standard roles if missing
            print("Creating standard roles (anon, authenticated, service_role)...")
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                        CREATE ROLE anon NOLOGIN;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                        CREATE ROLE authenticated NOLOGIN;
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                        CREATE ROLE service_role NOLOGIN;
                    END IF;
                    GRANT anon, authenticated, service_role TO postgres;
                END $$;
            """))

            # 2. Create auth schema and auth.uid() helper if missing
            print("Creating auth schema and auth.uid() helper...")
            conn.execute(text("""
                CREATE SCHEMA IF NOT EXISTS auth;
                CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
                    SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid;
                $$;
                GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;
                GRANT EXECUTE ON FUNCTION auth.uid() TO anon, authenticated, service_role;
            """))

    # 3. Create all tables from SQLAlchemy models
    print("Creating all tables via SQLAlchemy Base.metadata.create_all...")
    import models
    from database import Base
    Base.metadata.create_all(bind=engine)
    print("All SQLAlchemy tables created successfully.")

    # 4. Apply the proposed RLS migration
    print("Applying proposed RLS migration...")
    migration_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql"))
    with open(migration_path, "r", encoding="utf-8") as f:
        sql = f.read()

    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text(sql))
    print("RLS migration successfully applied to isolated test database!")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "postgresql://postgres:postgres@localhost:5435/postgres"
    setup_isolated_db(url)
