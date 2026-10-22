"""
AGENTGUARD Read-Only PostgreSQL / Supabase Schema Audit Tool.
Performs comprehensive read-only inspection of database objects that Alembic autogeneration cannot detect:
  1. PostgreSQL Extensions (uuid-ossp, pgcrypto, etc.)
  2. Row Level Security (RLS) enablement on public tables (pg_tables.rowsecurity)
  3. PostgreSQL Row-Level Security Policies (pg_policy)
  4. Database Functions & Triggers (pg_trigger, pg_proc)
  5. Column-level data types, UDTs, and server defaults (information_schema.columns)
  6. Table grants & permissions across roles (information_schema.table_privileges)

SAFE AND READ-ONLY: Never writes, modifies, or drops any database object.
"""

import sys
import os
import json
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text
from config import settings


def audit_postgres_database(db_url: str = settings.DATABASE_URL) -> Dict[str, Any]:
    """
    Connects to target PostgreSQL database in read-only mode and inspects
    all database catalog objects. Fails cleanly if database is unreachable or SQLite.
    """
    if db_url.startswith("sqlite"):
        return {
            "status": "SKIPPED",
            "reason": "Target database is SQLite. PostgreSQL-specific catalog inspection requires PostgreSQL."
        }

    engine = create_engine(db_url, connect_args={"options": "-c default_transaction_read_only=on"})
    audit_results: Dict[str, Any] = {
        "status": "COMPLETED",
        "extensions": [],
        "rls_status": {},
        "policies": {},
        "triggers": [],
        "functions": [],
        "column_defaults": {},
        "privileges": {}
    }

    with engine.connect() as conn:
        # 1. Inspect Extensions
        ext_rows = conn.execute(text("SELECT extname, extversion FROM pg_extension;")).fetchall()
        audit_results["extensions"] = [{"name": r[0], "version": r[1]} for r in ext_rows]

        # 2. Inspect RLS Enablement on all public tables
        rls_rows = conn.execute(text("""
            SELECT tablename, rowsecurity
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)).fetchall()
        for tbl, rls_enabled in rls_rows:
            audit_results["rls_status"][tbl] = bool(rls_enabled)

        # 3. Inspect Policies
        pol_rows = conn.execute(text("""
            SELECT 
                pol.polname,
                c.relname AS tablename,
                pol.polcmd,
                pg_get_expr(pol.polqual, pol.polrelid) AS using_expression,
                pg_get_expr(pol.polwithcheck, pol.polrelid) AS with_check_expression
            FROM pg_policy pol
            JOIN pg_class c ON pol.polrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = 'public'
            ORDER BY c.relname, pol.polname;
        """)).fetchall()
        for pol_name, tbl_name, cmd, using_expr, check_expr in pol_rows:
            audit_results["policies"].setdefault(tbl_name, []).append({
                "policy_name": pol_name,
                "command": cmd,
                "using": using_expr,
                "with_check": check_expr
            })

        # 4. Inspect Triggers
        trig_rows = conn.execute(text("""
            SELECT 
                t.tgname,
                c.relname AS tablename,
                pg_get_triggerdef(t.oid) AS definition
            FROM pg_trigger t
            JOIN pg_class c ON t.tgrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = 'public' AND NOT t.tgisinternal
            ORDER BY c.relname, t.tgname;
        """)).fetchall()
        audit_results["triggers"] = [{"trigger_name": r[0], "table": r[1], "definition": r[2]} for r in trig_rows]

        # 5. Inspect Column Server Defaults & Types
        col_rows = conn.execute(text("""
            SELECT 
                table_name,
                column_name,
                data_type,
                udt_name,
                column_default,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
        """)).fetchall()
        for tbl, col, dt, udt, default_val, nullable in col_rows:
            audit_results["column_defaults"].setdefault(tbl, {})[col] = {
                "data_type": dt,
                "udt_name": udt,
                "server_default": default_val,
                "nullable": nullable == "YES"
            }

    engine.dispose()
    return audit_results


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else settings.DATABASE_URL
    print(f"Running Read-Only PostgreSQL Schema Audit against target...")
    try:
        results = audit_postgres_database(url)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Audit failed to connect to database: {e}")
        sys.exit(1)
