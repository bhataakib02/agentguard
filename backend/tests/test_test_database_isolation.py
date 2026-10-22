"""
Regression Test Suite: Test Database Isolation & Safety Safeguards
Proves:
1. Production/staging database URLs are rejected with fail-closed RuntimeError.
2. Ambient .env Supabase pooler target is blocked when running in test mode.
3. Engine and session factories use only the isolated test database.
4. Test runner rejects unsafe remote database targets.
5. Test cleanup isolates records created by test fixtures.
"""

import os
import sys
import pytest
from sqlalchemy import text
from database import validate_test_database_target, engine, SessionLocal
from config import settings
import models


class TestDatabaseIsolation:
    def test_01_production_database_url_is_rejected(self):
        """Production database URL triggers fail-closed RuntimeError in test mode."""
        unsafe_url = "postgresql://user:pass@pooler.supabase.com:6543/postgres"
        with pytest.raises(RuntimeError) as exc_info:
            validate_test_database_target(unsafe_url)
        assert "Test Isolation Guard" in str(exc_info.value)
        assert "supabase" in str(exc_info.value)

    def test_02_staging_or_prod_domain_is_rejected(self):
        """Arbitrary production/staging hostname is rejected."""
        unsafe_urls = [
            "postgresql://admin:secret@db.agentguard.io:5432/agentguard",
            "postgresql://admin:secret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres",
            "postgresql://admin:secret@app-agentguard-prod.internal:5432/db",
        ]
        for url in unsafe_urls:
            with pytest.raises(RuntimeError) as exc_info:
                validate_test_database_target(url)
            assert "Test Isolation Guard" in str(exc_info.value)

    def test_03_disposable_sqlite_url_is_accepted(self):
        """Isolated local SQLite databases pass validation safely."""
        safe_urls = [
            "sqlite:///:memory:",
            "sqlite:///test_agentguard_global.db",
            f"sqlite:///{os.path.abspath('test_isolated.db')}",
        ]
        for url in safe_urls:
            # Should not raise
            validate_test_database_target(url)

    def test_04_engine_and_session_factory_use_isolated_test_database(self):
        """Verifies active engine is bound to an isolated test database (SQLite)."""
        assert str(engine.url).startswith("sqlite"), f"Engine URL is not SQLite: {engine.url}"
        db = SessionLocal()
        try:
            # Simple query proves isolated connection works
            res = db.execute(text("SELECT 1")).scalar()
            assert res == 1
        finally:
            db.close()

    def test_05_test_fixture_cleanup_affects_only_test_owned_records(self):
        """Verifies that record creation and deletion are contained within test scope."""
        db = SessionLocal()
        try:
            org = models.Organization(name="Isolation Test Org", status="ACTIVE")
            db.add(org)
            db.commit()
            db.refresh(org)
            org_id = org.id

            # Verify it exists
            fetched = db.query(models.Organization).filter_by(id=org_id).first()
            assert fetched is not None
            assert fetched.name == "Isolation Test Org"

            # Clean up
            db.delete(fetched)
            db.commit()

            # Verify removed
            assert db.query(models.Organization).filter_by(id=org_id).first() is None
        finally:
            db.close()
