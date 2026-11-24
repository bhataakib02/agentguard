"""
AGENTGUARD — Alembic Baseline Reconciliation Engine
Safely audits and reconciles pre-existing canonical PostgreSQL databases
with Alembic migration history without data loss or table recreation.

Supports:
1. --preflight (default): Read-only deep audit of 49 baseline tables against canonical manifest.
2. --adopt --confirm: Authoritatively stamps revision 0001_initial_canonical_schema
   IF AND ONLY IF the database is proven to exactly match the canonical baseline schema.
"""

import sys
import os
import argparse
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import sqlalchemy as sa
from sqlalchemy import inspect, text

# Prepend backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import settings
from database import Base, engine as default_engine
import models  # noqa: F401 - registers all 50 declarative models

logging.basicConfig(level=logging.INFO, format="%(levelname)-5.5s [%(name)s] %(message)s")
logger = logging.getLogger("agentguard.reconcile")

BASELINE_REVISION = "0001_initial_canonical_schema"
HEAD_REVISION = "0002_add_otp_challenges"
EXPECTED_BASELINE_TABLE_COUNT = 49
TOTAL_MODEL_TABLE_COUNT = 50  # 49 baseline tables + 1 otp_challenges


def sanitize_db_url(url: str) -> str:
    """Redacts credentials from database URL for safe audit logging."""
    if not url:
        return "<EMPTY_URL>"
    try:
        from urllib.parse import urlsplit, urlunsplit
        parts = urlsplit(url)
        if parts.username or parts.password:
            hostname = parts.hostname or ""
            port_str = f":{parts.port}" if parts.port else ""
            netloc = f"***:***@{hostname}{port_str}"
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        pass
    return "postgresql://***:***@[REDACTED]"


class BaselineReconciler:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.DATABASE_URL
        self.sanitized_url = sanitize_db_url(self.db_url)
        self.engine = sa.create_engine(self.db_url, pool_pre_ping=True)
        self.inspector = inspect(self.engine)
        self.canonical_tables = {
            tname: table for tname, table in Base.metadata.tables.items()
            if tname != "otp_challenges"
        }

    def run_preflight(self) -> Dict[str, Any]:
        """
        Executes a non-mutating, read-only audit of the database schema.
        Classifies the database status into:
          - EMPTY: Zero tables found.
          - MATCHING_UNSTAMPED_BASELINE: Exact 49-table canonical match with no alembic_version.
          - ALREADY_ADOPTED: alembic_version contains 0001 or 0002.
          - PARTIALLY_MIGRATED: Some tables or columns exist, but incomplete.
          - SCHEMA_MISMATCH: Unexplained table or column discrepancies.
          - CONFLICTING_REVISION: alembic_version has an unexpected revision.
        """
        is_sqlite = (self.engine.dialect.name == "sqlite")
        target_schema = None if is_sqlite else "public"
        inspector = inspect(self.engine)
        
        try:
            if target_schema:
                existing_tables = set(inspector.get_table_names(schema=target_schema) or inspector.get_table_names())
            else:
                existing_tables = set(inspector.get_table_names())
        except Exception:
            existing_tables = set(inspector.get_table_names())

        has_alembic = "alembic_version" in existing_tables
        has_otp = "otp_challenges" in existing_tables

        alembic_revisions: List[str] = []
        if has_alembic:
            try:
                with self.engine.connect() as conn:
                    res = conn.execute(text("SELECT version_num FROM alembic_version;")).fetchall()
                    alembic_revisions = [str(r[0]) for r in res]
            except Exception as e:
                logger.warning(f"Failed to read alembic_version: {e}")

        # Check tables excluding migration metadata
        app_tables = existing_tables - {"alembic_version"}
        canonical_names = set(self.canonical_tables.keys())

        missing_tables = sorted(list(canonical_names - app_tables))
        extra_tables = sorted(list(app_tables - canonical_names - ({"otp_challenges"} if has_otp else set())))

        # If completely empty
        if len(existing_tables) == 0:
            return {
                "status": "EMPTY",
                "database_url": self.sanitized_url,
                "table_count": 0,
                "has_alembic_version": False,
                "current_revisions": [],
                "has_otp_challenges": False,
                "missing_tables": missing_tables,
                "extra_tables": extra_tables,
                "column_diffs": {},
                "pk_diffs": {},
                "fk_diffs": {},
                "eligible_for_adoption": False,
                "recommended_action": "Run 'alembic upgrade head' for clean greenfield migration."
            }

        # Check column-by-column across matching tables
        matching_tables = app_tables.intersection(canonical_names)
        column_diffs: Dict[str, Any] = {}
        pk_diffs: Dict[str, Any] = {}
        fk_diffs: Dict[str, Any] = {}
        columns_audited = 0

        for tname in matching_tables:
            mtable = self.canonical_tables[tname]
            db_cols = {c["name"]: c for c in inspector.get_columns(tname)}
            mcols = {c.name: c for c in mtable.columns}

            missing_cols = [c for c in mcols if c not in db_cols]
            extra_cols = [c for c in db_cols if c not in mcols]

            nullability_diffs = []
            for cname, mcol in mcols.items():
                if cname in db_cols:
                    columns_audited += 1
                    dcol = db_cols[cname]
                    if mcol.nullable != dcol.get("nullable"):
                        # Only flag if both are meaningful
                        nullability_diffs.append({
                            "column": cname,
                            "model_nullable": mcol.nullable,
                            "db_nullable": dcol.get("nullable")
                        })

            if missing_cols or extra_cols or nullability_diffs:
                column_diffs[tname] = {
                    "missing_columns": missing_cols,
                    "extra_columns": extra_cols,
                    "nullability_mismatches": nullability_diffs
                }

            # Check primary key
            db_pk = set(inspector.get_pk_constraint(tname).get("constrained_columns", []))
            m_pk = {c.name for c in mtable.primary_key.columns}
            if db_pk != m_pk:
                pk_diffs[tname] = {"expected_pk": sorted(list(m_pk)), "found_pk": sorted(list(db_pk))}

            # Check foreign keys
            db_fks = inspector.get_foreign_keys(tname)
            m_fks = mtable.foreign_keys
            if len(db_fks) != len(m_fks):
                fk_diffs[tname] = {"expected_fk_count": len(m_fks), "found_fk_count": len(db_fks)}

        # Evaluate overall classification
        is_exact_baseline = (
            len(missing_tables) == 0
            and len(extra_tables) == 0
            and len(column_diffs) == 0
            and len(pk_diffs) == 0
            and len(fk_diffs) == 0
            and len(matching_tables) == EXPECTED_BASELINE_TABLE_COUNT
        )

        status = "SCHEMA_MISMATCH"
        eligible_for_adoption = False
        recommended_action = ""

        if has_alembic and (BASELINE_REVISION in alembic_revisions or HEAD_REVISION in alembic_revisions):
            status = "ALREADY_ADOPTED"
            recommended_action = (
                f"Database already stamped at revision {alembic_revisions}. "
                "Run 'alembic upgrade head' if pending migrations exist."
            )
        elif has_alembic and len(alembic_revisions) > 0:
            status = "CONFLICTING_REVISION"
            recommended_action = f"Conflicting alembic_version found: {alembic_revisions}. Manual review required."
        elif is_exact_baseline and not has_alembic:
            status = "MATCHING_UNSTAMPED_BASELINE"
            eligible_for_adoption = True
            recommended_action = (
                "Database matches canonical baseline exactly. "
                "Authorized for baseline adoption via '--adopt --confirm'."
            )
        elif len(matching_tables) < EXPECTED_BASELINE_TABLE_COUNT:
            status = "PARTIALLY_MIGRATED"
            recommended_action = "Database is incomplete or partially migrated. Manual schema repair required."
        else:
            status = "SCHEMA_MISMATCH"
            recommended_action = "Schema differences detected. Resolve column/table diffs before adopting."

        return {
            "status": status,
            "database_url": self.sanitized_url,
            "table_count": len(existing_tables),
            "app_table_count": len(app_tables),
            "columns_audited": columns_audited,
            "has_alembic_version": has_alembic,
            "current_revisions": alembic_revisions,
            "has_otp_challenges": has_otp,
            "missing_tables": missing_tables,
            "extra_tables": extra_tables,
            "column_diffs": column_diffs,
            "pk_diffs": pk_diffs,
            "fk_diffs": fk_diffs,
            "eligible_for_adoption": eligible_for_adoption,
            "recommended_action": recommended_action
        }

    def adopt_baseline(self, confirm: bool = False) -> Dict[str, Any]:
        """
        Adopts the baseline revision 0001_initial_canonical_schema.
        Requires confirm=True and preflight status == MATCHING_UNSTAMPED_BASELINE.
        Uses Alembic's supported migration-history mechanism.
        """
        if not confirm:
            raise PermissionError(
                "Adoption refused: --confirm flag is strictly required to execute baseline adoption."
            )

        preflight = self.run_preflight()
        if not preflight["eligible_for_adoption"]:
            raise RuntimeError(
                f"Adoption refused: Database is not eligible for adoption (Status: {preflight['status']}). "
                f"Reason: {preflight['recommended_action']}"
            )

        logger.info(f"Target Database: {self.sanitized_url}")
        logger.info(f"Target Revision to Adopt: {BASELINE_REVISION}")

        # Execute adoption via Alembic command
        from alembic.config import Config
        from alembic import command

        alembic_ini_path = os.path.abspath(os.path.join(backend_dir, "alembic.ini"))
        alembic_dir = os.path.abspath(os.path.join(backend_dir, "alembic"))

        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("script_location", alembic_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)

        # Stamp the baseline revision transactional
        logger.info(f"Stamping baseline revision '{BASELINE_REVISION}' into alembic_version...")
        command.stamp(alembic_cfg, BASELINE_REVISION)

        # Verify post-adoption state
        post_inspector = inspect(self.engine)
        is_sqlite = (self.engine.dialect.name == "sqlite")
        if is_sqlite:
            post_tables = set(post_inspector.get_table_names())
        else:
            post_tables = set(post_inspector.get_table_names(schema="public") or post_inspector.get_table_names())
        assert "alembic_version" in post_tables, "alembic_version was not created during adoption!"

        with self.engine.connect() as conn:
            res = conn.execute(text("SELECT version_num FROM alembic_version;")).fetchall()
            stamped_revs = [str(r[0]) for r in res]

        assert BASELINE_REVISION in stamped_revs, f"Expected {BASELINE_REVISION} in alembic_version, found {stamped_revs}"

        logger.info(f"Successfully adopted baseline! Current revision: {stamped_revs}")

        return {
            "status": "SUCCESS",
            "adopted_revision": BASELINE_REVISION,
            "database_url": self.sanitized_url,
            "stamped_revisions": stamped_revs,
            "next_step": f"Run 'alembic upgrade head' to apply pending migration {HEAD_REVISION}."
        }


def main():
    parser = argparse.ArgumentParser(description="AGENTGUARD Alembic Baseline Reconciler")
    parser.add_argument("--preflight", action="store_true", default=True, help="Run read-only schema audit")
    parser.add_argument("--adopt", action="store_true", help="Execute authorized baseline adoption")
    parser.add_argument("--confirm", action="store_true", help="Explicit confirmation for baseline adoption")
    parser.add_argument("--db-url", type=str, default=None, help="Optional database URL override")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    reconciler = BaselineReconciler(db_url=args.db_url)

    if args.adopt:
        try:
            res = reconciler.adopt_baseline(confirm=args.confirm)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print("\n" + "=" * 70)
                print("BASELINE ADOPTION COMPLETED SUCCESSFULLY")
                print("=" * 70)
                print(f"Database: {res['database_url']}")
                print(f"Adopted Revision: {res['adopted_revision']}")
                print(f"Current Revisions: {res['stamped_revisions']}")
                print(f"Next Action: {res['next_step']}")
        except Exception as e:
            logger.error(f"Adoption failed: {e}")
            sys.exit(1)
    else:
        res = reconciler.run_preflight()
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print("\n" + "=" * 70)
            print("AGENTGUARD — ALEMBIC BASELINE PREFLIGHT AUDIT REPORT")
            print("=" * 70)
            print(f"Target Database:       {res['database_url']}")
            print(f"Audit Status:          {res['status']}")
            print(f"Total Tables in DB:    {res['table_count']}")
            print(f"Columns Audited:       {res['columns_audited']}")
            print(f"Has alembic_version:   {res['has_alembic_version']}")
            print(f"Current Revisions:     {res['current_revisions']}")
            print(f"Has otp_challenges:    {res['has_otp_challenges']}")
            print(f"Missing Baseline Tabs: {res['missing_tables']}")
            print(f"Extra Tables:          {res['extra_tables']}")
            print(f"Column Diffs:          {len(res['column_diffs'])}")
            print(f"PK Diffs:              {len(res['pk_diffs'])}")
            print(f"FK Diffs:              {len(res['fk_diffs'])}")
            print(f"Eligible for Adoption: {res['eligible_for_adoption']}")
            print(f"Recommended Action:    {res['recommended_action']}")
            print("=" * 70)


if __name__ == "__main__":
    main()
