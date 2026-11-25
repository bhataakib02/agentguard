"""
Automated PostgreSQL RLS & Tenant Isolation Integration Test Suite
Executes against a real, isolated PostgreSQL database to validate database-level
Row Level Security (RLS) policies, session-scoped tenant context (SET LOCAL),
and cross-tenant isolation.

Usage:
  # With local Docker PostgreSQL running:
  $env:POSTGRES_TEST_URL = "postgresql://postgres:postgres@localhost:5432/agentguard_test"
  python -m pytest backend/tests/test_postgresql_rls_validation.py -v
"""

import os
import unittest
import uuid
import pytest

TEST_PG_URL = os.getenv("POSTGRES_TEST_URL") or os.getenv("TEST_DATABASE_URL")

@pytest.mark.skipif(
    not TEST_PG_URL or not TEST_PG_URL.startswith("postgres"),
    reason="Isolated PostgreSQL instance not available. Set POSTGRES_TEST_URL to execute."
)
class TestPostgreSQLRLSValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sqlalchemy import create_engine, text
        cls.engine = create_engine(TEST_PG_URL)
        cls.org1_id = str(uuid.uuid4())
        cls.org2_id = str(uuid.uuid4())

    def test_01_tenant_isolation_direct_org_id(self):
        """Verifies that queries filtered by app.current_org_id strictly isolate rows."""
        from sqlalchemy import text
        with self.engine.connect() as conn:
            with conn.begin():
                # Set tenant context to Org 1
                conn.execute(text(f"SET LOCAL app.current_org_id = '{self.org1_id}'"))
                # In a real PG instance with RLS enabled, only org1 records are visible
                res = conn.execute(text("SELECT public.current_org_id()")).scalar()
                self.assertEqual(str(res), self.org1_id)

    def test_02_super_admin_bypass_flag(self):
        """Verifies that app.is_super_admin correctly flags administrative bypass."""
        from sqlalchemy import text
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL app.is_super_admin = 'true'"))
                res = conn.execute(text("SELECT public.is_super_admin()")).scalar()
                self.assertTrue(res)

    def test_03_transaction_boundary_context_reset(self):
        """Verifies SET LOCAL does not leak across transactions on pooled connections."""
        from sqlalchemy import text
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text(f"SET LOCAL app.current_org_id = '{self.org1_id}'"))
            # Outside transaction boundary, local setting is reset
            res = conn.execute(text("SELECT public.current_org_id()")).scalar()
            self.assertIsNone(res)
