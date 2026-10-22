"""
AGENTGUARD Existing Database Reconciliation Bridge Tool.
Safe, idempotent, non-destructive reconciliation of existing PostgreSQL / SQLite databases.

PROTOCOL:
1. Inspects target database schema for existing vs missing tables and columns.
2. Creates any missing application tables using Base.metadata without modifying existing tables.
3. Adds any missing columns idempotently using ADD COLUMN.
4. Uses Alembic produce_migrations to verify zero schema diff against Base.metadata.
5. Stamps the database with 0001_initial_canonical_schema ONLY after parity is verified.
6. Preserves 100% of existing organizations, users, agents, audit logs, and operational data.
"""

import sys
import os
from typing import Dict, List, Set, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, inspect, text
from alembic.config import Config
from alembic import command
from alembic.migration import MigrationContext
from alembic.autogenerate import produce_migrations
import models
from config import settings


def reconcile_database(db_url: str = settings.DATABASE_URL, auto_stamp: bool = False) -> Dict[str, Any]:
    print(f"=== RECONCILING DATABASE: {db_url.split('@')[-1] if '@' in db_url else db_url} ===")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    canonical_tables = set(models.Base.metadata.tables.keys())

    missing_tables = canonical_tables - existing_tables
    print(f"Existing tables in DB: {len(existing_tables)}")
    print(f"Canonical tables required: {len(canonical_tables)}")
    print(f"Missing tables to create: {len(missing_tables)}")

    # 1. Idempotently create any missing tables (preserves existing tables completely)
    if missing_tables:
        print(f"Creating {len(missing_tables)} missing tables...")
        tables_to_create = [models.Base.metadata.tables[t] for t in missing_tables]
        models.Base.metadata.create_all(bind=engine, tables=tables_to_create)
        print("Missing tables created successfully.")

    # 2. Idempotently check and add missing columns on key existing tables
    inspector = inspect(engine)
    with engine.connect() as conn:
        # organizations
        if "organizations" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("organizations")}
            col_defs = [
                ("slug", "VARCHAR"),
                ("display_name", "VARCHAR"),
                ("status", "VARCHAR DEFAULT 'ACTIVE'"),
                ("admin_email", "VARCHAR"),
                ("logo_url", "VARCHAR"),
                ("logo_path", "VARCHAR"),
                ("kms_provider", "VARCHAR DEFAULT 'SYSTEM_MANAGED'"),
                ("kms_key_arn", "VARCHAR"),
                ("kms_key_alias", "VARCHAR"),
                ("kms_key_status", "VARCHAR DEFAULT 'NOT_CONFIGURED'"),
                ("kms_config_json", "JSON")
            ]
            for col_name, col_type in col_defs:
                if col_name not in cols:
                    print(f"Adding missing column organizations.{col_name}...")
                    conn.execute(text(f"ALTER TABLE organizations ADD COLUMN {col_name} {col_type};"))

        # users
        if "users" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("users")}
            col_defs = [
                ("job_title", "VARCHAR"),
                ("phone", "VARCHAR"),
                ("updated_at", "TIMESTAMP"),
                ("last_login_at", "TIMESTAMP")
            ]
            for col_name, col_type in col_defs:
                if col_name not in cols:
                    print(f"Adding missing column users.{col_name}...")
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"))

        # decisions
        if "decisions" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("decisions")}
            col_defs = [
                ("authorized_endpoint", "VARCHAR"),
                ("execution_gate_token", "VARCHAR"),
                ("gate_token_used", "BOOLEAN DEFAULT FALSE"),
                ("executed_at", "TIMESTAMP"),
                ("tool_id", "CHAR(36)" if db_url.startswith("sqlite") else "UUID"),
                ("execution_parameters", "JSON")
            ]
            for col_name, col_type in col_defs:
                if col_name not in cols:
                    print(f"Adding missing column decisions.{col_name}...")
                    conn.execute(text(f"ALTER TABLE decisions ADD COLUMN {col_name} {col_type};"))

        # audit_logs
        if "audit_logs" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("audit_logs")}
            if "org_id" not in cols:
                print("Adding missing column audit_logs.org_id...")
                col_type = "CHAR(36)" if db_url.startswith("sqlite") else "UUID"
                conn.execute(text(f"ALTER TABLE audit_logs ADD COLUMN org_id {col_type};"))

        # agent_passports
        if "agent_passports" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("agent_passports")}
            col_defs = [
                ("algorithm", "VARCHAR DEFAULT 'Ed25519'"),
                ("key_id", "VARCHAR DEFAULT 'agentguard-root-1'"),
                ("passport_version", "VARCHAR DEFAULT '1.0'"),
                ("claims", "JSON")
            ]
            for col_name, col_type in col_defs:
                if col_name not in cols:
                    print(f"Adding missing column agent_passports.{col_name}...")
                    conn.execute(text(f"ALTER TABLE agent_passports ADD COLUMN {col_name} {col_type};"))

        conn.commit()

    # 3. Direct schema comparison via produce_migrations
    print("\nVerifying schema equivalence against canonical models...")
    diff_detected = False
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"target_metadata": models.Base.metadata})
        diff = produce_migrations(ctx, models.Base.metadata)
        upgrade_ops = diff.upgrade_ops
        if upgrade_ops is not None and upgrade_ops.is_empty():
            print("[SUCCESS] Schema equivalence verified: 0 migration differences detected!")
        else:
            diff_detected = True
            ops_list = upgrade_ops.ops if upgrade_ops is not None else []
            diff_ops = [str(getattr(op, "table_name", op)) for op in ops_list]
            print(f"[NOTICE] Remaining migration operations detected: {len(ops_list)} operations across tables {diff_ops}")

    engine.dispose()
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))

    # 4. Stamp if requested and verified
    stamped = False
    if auto_stamp and not diff_detected:
        print("\nStamping database with 0001_initial_canonical_schema...")
        command.stamp(cfg, "0001_initial_canonical_schema")
        print("[SUCCESS] Stamped database at 0001_initial_canonical_schema (head).")
        stamped = True

        # Now that it's stamped, alembic check can verify version alignment
        try:
            command.check(cfg)
            print("[SUCCESS] alembic check confirmed database is at head with zero diff.")
        except Exception as exc:
            print(f"[NOTICE] Post-stamp check notice: {exc}")

    return {
        "existing_before": len(existing_tables),
        "missing_created": len(missing_tables),
        "diff_detected": diff_detected,
        "stamped": stamped
    }


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else settings.DATABASE_URL
    should_stamp = "--stamp" in sys.argv
    res = reconcile_database(target_url, auto_stamp=should_stamp)
    print("\nReconciliation Result Summary:", res)
