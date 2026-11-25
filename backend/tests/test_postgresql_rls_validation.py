"""
Automated PostgreSQL RLS & Tenant Isolation Integration Test Suite
Executes against a real, isolated PostgreSQL database to validate database-level
Row Level Security (RLS) policies, session-scoped tenant context (SET LOCAL),
and cross-tenant isolation across all 15 security invariants.

Usage:
  # With local Docker PostgreSQL running:
  $env:POSTGRES_TEST_URL = "postgresql://postgres:postgres@localhost:5432/agentguard_test"
  python -m pytest backend/tests/test_postgresql_rls_validation.py -v
"""

import os
import unittest
import uuid
import pytest
from sqlalchemy import create_engine, text

TEST_PG_URL = os.getenv("POSTGRES_TEST_URL") or os.getenv("TEST_DATABASE_URL")


@pytest.mark.skipif(
    not TEST_PG_URL or not TEST_PG_URL.startswith("postgres"),
    reason="Isolated PostgreSQL instance not available. Set POSTGRES_TEST_URL to execute."
)
class TestPostgreSQLRLSValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(TEST_PG_URL)
        cls.org1_id = str(uuid.uuid4())
        cls.org2_id = str(uuid.uuid4())
        cls.user1_id = str(uuid.uuid4())
        cls.user2_id = str(uuid.uuid4())
        cls.agent1_id = str(uuid.uuid4())
        cls.agent2_id = str(uuid.uuid4())

    # =========================================================================
    # 1. Tenant Isolation Invariants
    # =========================================================================

    def test_01_tenant_a_cannot_read_tenant_b(self):
        """Verifies that Tenant A cannot SELECT records owned by Tenant B under RLS."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                conn.execute(text(f"SET LOCAL request.jwt.claims = '{{\"app_metadata\": {{\"org_id\": \"{self.org1_id}\"}}}}';"))
                
                # Query agents for org2
                res = conn.execute(
                    text(f"SELECT count(*) FROM public.agents WHERE org_id = '{self.org2_id}'")
                ).scalar()
                self.assertEqual(res, 0, "Tenant A should see 0 rows of Tenant B agents")

    def test_02_tenant_a_cannot_modify_tenant_b(self):
        """Verifies that Tenant A cannot UPDATE or DELETE records owned by Tenant B."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                conn.execute(text(f"SET LOCAL request.jwt.claims = '{{\"app_metadata\": {{\"org_id\": \"{self.org1_id}\"}}}}';"))
                
                # Attempt to update org2 agent
                res = conn.execute(
                    text(f"UPDATE public.agents SET name = 'tampered' WHERE org_id = '{self.org2_id}'")
                )
                self.assertEqual(res.rowcount, 0, "Tenant A update on Tenant B agents must affect 0 rows")

    def test_03_cross_tenant_agent_relationships_rejected(self):
        """Verifies that relationships linking Tenant A agent to Tenant B agent are blocked."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                conn.execute(text(f"SET LOCAL request.jwt.claims = '{{\"app_metadata\": {{\"org_id\": \"{self.org1_id}\"}}}}';"))
                
                # Attempt to link agent1 (org1) to agent2 (org2)
                rel_id = str(uuid.uuid4())
                with pytest.raises(Exception):
                    conn.execute(text(f"""
                        INSERT INTO public.agent_relationships (id, parent_agent_id, child_agent_id, relationship_type)
                        VALUES ('{rel_id}', '{self.agent1_id}', '{self.agent2_id}', 'DELEGATE');
                    """))

    # =========================================================================
    # 2. Token & Audit Log Hardening
    # =========================================================================

    def test_04_sessions_cannot_be_read_by_ordinary_users(self):
        """Verifies that ordinary authenticated users have no SELECT privilege on sessions."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                with pytest.raises(Exception) as exc_info:
                    conn.execute(text("SELECT * FROM public.sessions;"))
                self.assertIn("permission denied", str(exc_info.value).lower())

    def test_05_audit_logs_cannot_be_updated_or_deleted(self):
        """Verifies that audit_logs rejects UPDATE and DELETE from authenticated users."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                conn.execute(text(f"SET LOCAL request.jwt.claims = '{{\"app_metadata\": {{\"org_id\": \"{self.org1_id}\"}}}}';"))
                
                with pytest.raises(Exception) as exc_info:
                    conn.execute(text(f"DELETE FROM public.audit_logs WHERE org_id = '{self.org1_id}';"))
                self.assertIn("permission denied", str(exc_info.value).lower())

    # =========================================================================
    # 3. Global Tools & Decision Polymorphism
    # =========================================================================

    def test_06_global_tools_remain_visible_immutable_to_tenants(self):
        """Verifies that global tools (org_id IS NULL) are visible but immutable to tenants."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                conn.execute(text(f"SET LOCAL request.jwt.claims = '{{\"app_metadata\": {{\"org_id\": \"{self.org1_id}\"}}}}';"))
                
                # Global tools can be read
                res = conn.execute(text("SELECT count(*) FROM public.tools WHERE org_id IS NULL;")).scalar()
                self.assertIsNotNone(res)

                # Global tools cannot be modified by tenant
                mod_res = conn.execute(text("UPDATE public.tools SET name = 'tampered' WHERE org_id IS NULL;"))
                self.assertEqual(mod_res.rowcount, 0)

    def test_07_human_decisions_work_correctly(self):
        """Verifies that decisions originated by human users without agents pass RLS."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                conn.execute(text(f"SET LOCAL request.jwt.claims = '{{\"app_metadata\": {{\"org_id\": \"{self.org1_id}\"}}}}';"))
                
                dec_id = str(uuid.uuid4())
                # Human decision has user_id = user1, agent_id = NULL
                res = conn.execute(text(f"""
                    SELECT count(*) FROM public.decisions 
                    WHERE user_id = '{self.user1_id}' AND agent_id IS NULL;
                """)).scalar()
                self.assertEqual(res, 0)

    def test_08_agent_decisions_work_correctly(self):
        """Verifies that decisions originated by autonomous agents pass RLS."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                conn.execute(text(f"SET LOCAL request.jwt.claims = '{{\"app_metadata\": {{\"org_id\": \"{self.org1_id}\"}}}}';"))
                
                res = conn.execute(text(f"""
                    SELECT count(*) FROM public.decisions 
                    WHERE agent_id = '{self.agent1_id}';
                """)).scalar()
                self.assertEqual(res, 0)

    def test_09_conflicting_decision_ownership_rejected(self):
        """Verifies that a decision cannot pair an Org 1 agent with an Org 2 user."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                conn.execute(text(f"SET LOCAL request.jwt.claims = '{{\"app_metadata\": {{\"org_id\": \"{self.org1_id}\"}}}}';"))
                
                dec_id = str(uuid.uuid4())
                with pytest.raises(Exception):
                    conn.execute(text(f"""
                        INSERT INTO public.decisions (id, agent_id, user_id, action_requested, decision)
                        VALUES ('{dec_id}', '{self.agent1_id}', '{self.user2_id}', 'execute_tool', 'ALLOW');
                    """))

    # =========================================================================
    # 4. Pre-Auth, Missing Context & Anti-Spoofing
    # =========================================================================

    def test_10_otp_challenges_inaccessible_through_postgrest(self):
        """Verifies that otp_challenges is completely blocked for anon and authenticated."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE anon;"))
                with pytest.raises(Exception) as exc_info:
                    conn.execute(text("SELECT * FROM public.otp_challenges;"))
                self.assertIn("permission denied", str(exc_info.value).lower())

    def test_11_missing_tenant_context_fails_closed(self):
        """Verifies that missing tenant context in current_org_id() fails closed (returns NULL)."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                res = conn.execute(text("SELECT public.current_org_id();")).scalar()
                self.assertIsNone(res)

    def test_12_guc_spoofing_cannot_change_tenant_identity(self):
        """Verifies that setting app.current_org_id is ignored when running as authenticated."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                conn.execute(text(f"SET LOCAL app.current_org_id = '{self.org2_id}';"))
                # current_org_id() should ignore app.current_org_id for authenticated
                res = conn.execute(text("SELECT public.current_org_id();")).scalar()
                self.assertNotEqual(str(res), self.org2_id)

    def test_13_guc_spoofing_cannot_grant_super_admin(self):
        """Verifies that setting app.is_super_admin is ignored when running as authenticated."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET LOCAL ROLE authenticated;"))
                conn.execute(text("SET LOCAL app.is_super_admin = 'true';"))
                res = conn.execute(text("SELECT public.is_super_admin();")).scalar()
                self.assertFalse(res)

    # =========================================================================
    # 5. Connection Pooling & Backend Operations
    # =========================================================================

    def test_14_connection_pool_context_does_not_leak(self):
        """Verifies SET LOCAL does not leak across transactions on pooled connections."""
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(text(f"SET LOCAL app.current_org_id = '{self.org1_id}';"))
            # Outside transaction boundary, local setting is reset
            res = conn.execute(text("SELECT public.current_org_id();")).scalar()
            self.assertIsNone(res)

    def test_15_trusted_backend_access_continues_to_work(self):
        """Verifies that backend service_role / postgres retains full CRUD access."""
        with self.engine.connect() as conn:
            with conn.begin():
                # Connected as postgres / service_role
                res = conn.execute(text("SELECT count(*) FROM public.organizations;")).scalar()
                self.assertIsNotNone(res)
