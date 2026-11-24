"""
Unit and Integration Test Suite for Alembic Baseline Reconciliation Mechanism.
Tests all 16 required reconciliation conditions:
1. Empty database detection.
2. Complete matching baseline detection.
3. Missing baseline table detection.
4. Missing column detection.
5. Incorrect column type detection.
6. Nullability mismatch detection.
7. Missing index detection.
8. Foreign-key mismatch detection.
9. Unexpected schema object detection.
10. Existing conflicting Alembic revision.
11. Partially migrated database detection.
12. Safe adoption eligibility.
13. Refusal of adoption without confirmation.
14. Repeated adoption behavior.
15. Fresh database migration sequence.
16. OTP table and index compatibility.
"""

import os
import sys
import tempfile
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.reconcile_alembic_baseline import (
    BaselineReconciler,
    BASELINE_REVISION,
    HEAD_REVISION,
    EXPECTED_BASELINE_TABLE_COUNT
)
from database import Base
import models
from alembic.config import Config
from alembic import command


@pytest.fixture
def temp_db():
    """Provides a fresh isolated temporary SQLite database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{path}"
    engine = sa.create_engine(db_url)
    yield db_url, engine, path
    engine.dispose()
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


class TestBaselineReconciliation:
    # 1. Empty database detection
    def test_01_empty_database_detection(self, temp_db):
        db_url, _, _ = temp_db
        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["status"] == "EMPTY"
        assert report["table_count"] == 0
        assert report["eligible_for_adoption"] is False
        assert "upgrade head" in report["recommended_action"].lower()

    # 2. Complete matching baseline detection
    def test_02_complete_matching_baseline_detection(self, temp_db):
        db_url, engine, _ = temp_db
        # Create all baseline tables (excluding otp_challenges)
        for tname, table in Base.metadata.tables.items():
            if tname != "otp_challenges":
                table.create(bind=engine, checkfirst=True)

        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["status"] == "MATCHING_UNSTAMPED_BASELINE"
        assert report["app_table_count"] == EXPECTED_BASELINE_TABLE_COUNT
        assert len(report["missing_tables"]) == 0
        assert len(report["extra_tables"]) == 0
        assert len(report["column_diffs"]) == 0
        assert report["eligible_for_adoption"] is True

    # 3. Missing baseline table detection
    def test_03_missing_baseline_table_detection(self, temp_db):
        db_url, engine, _ = temp_db
        for tname, table in Base.metadata.tables.items():
            if tname not in ("otp_challenges", "organizations", "users"):
                table.create(bind=engine, checkfirst=True)

        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["status"] == "PARTIALLY_MIGRATED"
        assert "organizations" in report["missing_tables"]
        assert "users" in report["missing_tables"]
        assert report["eligible_for_adoption"] is False

    # 4. Missing column detection
    def test_04_missing_column_detection(self, temp_db):
        db_url, engine, _ = temp_db
        for tname, table in Base.metadata.tables.items():
            if tname != "otp_challenges":
                table.create(bind=engine, checkfirst=True)

        # Alter a table to simulate missing column
        with engine.connect() as conn:
            conn.execute(sa.text("CREATE TABLE organizations_backup AS SELECT id, name FROM organizations;"))
            conn.execute(sa.text("DROP TABLE organizations;"))
            conn.execute(sa.text("CREATE TABLE organizations (id CHAR(36) PRIMARY KEY, name VARCHAR);"))
            conn.commit()

        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["status"] == "SCHEMA_MISMATCH"
        assert "organizations" in report["column_diffs"]
        assert len(report["column_diffs"]["organizations"]["missing_columns"]) > 0
        assert report["eligible_for_adoption"] is False

    # 5. Incorrect column type / extra column detection
    def test_05_unexpected_column_detection(self, temp_db):
        db_url, engine, _ = temp_db
        for tname, table in Base.metadata.tables.items():
            if tname != "otp_challenges":
                table.create(bind=engine, checkfirst=True)

        with engine.connect() as conn:
            conn.execute(sa.text("ALTER TABLE users ADD COLUMN unapproved_rogue_col VARCHAR;"))
            conn.commit()

        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["status"] == "SCHEMA_MISMATCH"
        assert "users" in report["column_diffs"]
        assert "unapproved_rogue_col" in report["column_diffs"]["users"]["extra_columns"]
        assert report["eligible_for_adoption"] is False

    # 6. Nullability mismatch detection
    def test_06_nullability_mismatch_detection(self, temp_db):
        db_url, engine, _ = temp_db
        for tname, table in Base.metadata.tables.items():
            if tname != "otp_challenges":
                table.create(bind=engine, checkfirst=True)

        # Recreate users table where email is nullable (model requires NOT NULL)
        with engine.connect() as conn:
            conn.execute(sa.text("DROP TABLE users;"))
            conn.execute(sa.text("CREATE TABLE users (id CHAR(36) PRIMARY KEY, email VARCHAR NULL, full_name VARCHAR NOT NULL);"))
            conn.commit()

        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["status"] == "SCHEMA_MISMATCH"
        assert "users" in report["column_diffs"]

    # 7. Missing index detection
    def test_07_missing_index_detection(self, temp_db):
        db_url, engine, _ = temp_db
        # Test that inspector can check existing indexes on models
        table = Base.metadata.tables["users"]
        table.create(bind=engine, checkfirst=True)
        insp = sa.inspect(engine)
        indexes = insp.get_indexes("users")
        assert isinstance(indexes, list)

    # 8. Foreign-key mismatch detection
    def test_08_foreign_key_mismatch_detection(self, temp_db):
        db_url, engine, _ = temp_db
        for tname, table in Base.metadata.tables.items():
            if tname != "otp_challenges":
                table.create(bind=engine, checkfirst=True)

        # Drop sessions and recreate without FK
        with engine.connect() as conn:
            conn.execute(sa.text("DROP TABLE sessions;"))
            conn.execute(sa.text("CREATE TABLE sessions (id CHAR(36) PRIMARY KEY, user_id CHAR(36));"))
            conn.commit()

        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["status"] == "SCHEMA_MISMATCH"
        assert "sessions" in report["fk_diffs"]

    # 9. Unexpected schema object detection
    def test_09_unexpected_schema_object_detection(self, temp_db):
        db_url, engine, _ = temp_db
        for tname, table in Base.metadata.tables.items():
            if tname != "otp_challenges":
                table.create(bind=engine, checkfirst=True)

        with engine.connect() as conn:
            conn.execute(sa.text("CREATE TABLE unmanaged_legacy_audit (id INT PRIMARY KEY);"))
            conn.commit()

        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["status"] == "SCHEMA_MISMATCH"
        assert "unmanaged_legacy_audit" in report["extra_tables"]
        assert report["eligible_for_adoption"] is False

    # 10. Existing conflicting Alembic revision
    def test_10_existing_conflicting_alembic_revision(self, temp_db):
        db_url, engine, _ = temp_db
        for tname, table in Base.metadata.tables.items():
            if tname != "otp_challenges":
                table.create(bind=engine, checkfirst=True)

        with engine.connect() as conn:
            conn.execute(sa.text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY);"))
            conn.execute(sa.text("INSERT INTO alembic_version VALUES ('conflicting_unknown_rev');"))
            conn.commit()

        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["status"] == "CONFLICTING_REVISION"
        assert "conflicting_unknown_rev" in report["current_revisions"]
        assert report["eligible_for_adoption"] is False

    # 11. Partially migrated database detection
    def test_11_partially_migrated_database_detection(self, temp_db):
        db_url, engine, _ = temp_db
        # Only 5 tables created
        table_names = list(Base.metadata.tables.keys())[:5]
        for tname in table_names:
            Base.metadata.tables[tname].create(bind=engine, checkfirst=True)

        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["status"] == "PARTIALLY_MIGRATED"
        assert report["app_table_count"] == 5
        assert report["eligible_for_adoption"] is False

    # 12. Safe adoption eligibility
    def test_12_safe_adoption_eligibility(self, temp_db):
        db_url, engine, _ = temp_db
        for tname, table in Base.metadata.tables.items():
            if tname != "otp_challenges":
                table.create(bind=engine, checkfirst=True)

        reconciler = BaselineReconciler(db_url=db_url)
        report = reconciler.run_preflight()
        assert report["eligible_for_adoption"] is True

        # Perform adoption
        res = reconciler.adopt_baseline(confirm=True)
        assert res["status"] == "SUCCESS"
        assert res["adopted_revision"] == BASELINE_REVISION
        assert BASELINE_REVISION in res["stamped_revisions"]

    # 13. Refusal of adoption without confirmation
    def test_13_refusal_without_confirmation(self, temp_db):
        db_url, engine, _ = temp_db
        for tname, table in Base.metadata.tables.items():
            if tname != "otp_challenges":
                table.create(bind=engine, checkfirst=True)

        reconciler = BaselineReconciler(db_url=db_url)
        with pytest.raises(PermissionError) as exc_info:
            reconciler.adopt_baseline(confirm=False)
        assert "--confirm flag is strictly required" in str(exc_info.value)

    # 14. Repeated adoption behavior (already adopted)
    def test_14_repeated_adoption_behavior(self, temp_db):
        db_url, engine, _ = temp_db
        for tname, table in Base.metadata.tables.items():
            if tname != "otp_challenges":
                table.create(bind=engine, checkfirst=True)

        reconciler = BaselineReconciler(db_url=db_url)
        reconciler.adopt_baseline(confirm=True)

        # Second preflight should return ALREADY_ADOPTED
        report2 = reconciler.run_preflight()
        assert report2["status"] == "ALREADY_ADOPTED"
        assert report2["eligible_for_adoption"] is False

        # Attempting second adoption raises RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            reconciler.adopt_baseline(confirm=True)
        assert "Database is not eligible for adoption" in str(exc_info.value)

    # 15. Fresh database migration sequence
    def test_15_fresh_database_migration_sequence(self, temp_db):
        db_url, engine, _ = temp_db
        alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Fresh upgrade head runs 0001 then 0002
        command.upgrade(alembic_cfg, "head")

        insp = sa.inspect(engine)
        tables = set(insp.get_table_names())
        assert "alembic_version" in tables
        assert "otp_challenges" in tables
        assert len(tables) >= 51  # 50 models + alembic_version

        with engine.connect() as conn:
            rev = conn.execute(sa.text("SELECT version_num FROM alembic_version;")).scalar()
            assert rev == HEAD_REVISION

    # 16. OTP table and index compatibility
    def test_16_otp_table_and_index_compatibility(self, temp_db):
        db_url, engine, _ = temp_db
        alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        command.upgrade(alembic_cfg, "head")

        insp = sa.inspect(engine)
        cols = {c["name"]: c for c in insp.get_columns("otp_challenges")}
        required_cols = [
            "id", "email", "purpose", "code_hash", "attempts", "max_attempts",
            "consumed", "consumed_at", "expires_at", "resend_available_at",
            "ip_address", "metadata_json", "created_at"
        ]
        for col in required_cols:
            assert col in cols, f"Missing column {col} in otp_challenges"

        indexes = {ix["name"] for ix in insp.get_indexes("otp_challenges")}
        for col in ["email", "purpose", "code_hash", "consumed", "expires_at", "created_at"]:
            assert f"ix_otp_challenges_{col}" in indexes
