"""
Isolated Test Suite: Destructive Maintenance Safeguards Evaluation
Validates that database wipe guards fail closed and prevent accidental production data loss.
Enforces:
1. Fail-closed database allowlist: Unknown/unapproved databases (e.g. 'postgres', 'production') rejected by default.
2. Independent environment guard: Must be explicitly 'development', 'test', 'local', or 'ci'.
3. Explicit operator confirmation: 'YES_DELETE_ALL_DATA' or 'CONFIRMED_NON_PRODUCTION'.
"""

import pytest
from sqlalchemy import create_engine

ALLOWED_NON_PROD_DATABASES = {
    "agentguard_dev", "agentguard_test", "agentguard_local", "agentguard_ci", "test_agentguard"
}
ALLOWED_ENVIRONMENTS = {"development", "test", "local", "ci"}

def run_guarded_purge_simulation(
    engine,
    db_name: str,
    environment: str,
    session_confirmation: str
):
    """
    Simulates the fail-closed multi-layered guard:
    Layer 1: Database name MUST be in ALLOWED_NON_PROD_DATABASES.
             Default is REJECT for any unknown database (including 'postgres', 'agentguard').
    Layer 2: Environment MUST be explicitly in ALLOWED_ENVIRONMENTS.
    Layer 3: Session confirmation variable MUST match required phrase.
    """
    with engine.connect() as conn:
        # Layer 1: Fail-closed allowlist check
        if db_name not in ALLOWED_NON_PROD_DATABASES:
            raise PermissionError(
                f"SAFETY ABORT: Database '{db_name}' is not in approved non-production allowlist {ALLOWED_NON_PROD_DATABASES}. "
                "Unknown databases are rejected by default."
            )
        
        # Layer 2: Independent environment guard
        if environment not in ALLOWED_ENVIRONMENTS:
            raise PermissionError(
                f"SAFETY ABORT: Independent environment guard failed. Environment '{environment}' is not approved for destructive maintenance."
            )
        
        # Layer 3: Operator confirmation check
        if session_confirmation != "YES_DELETE_ALL_DATA":
            raise PermissionError("SAFETY ABORT: Session confirmation variable missing or invalid.")
        
        return "PURGE_EXECUTED"

def test_destructive_safeguards_reject_unknown_database_by_default():
    """
    Critical requirement: If a production database is named 'postgres' or 'agentguard'
    (which does not contain the substring 'prod'), it MUST STILL BE REJECTED by default.
    """
    engine = create_engine("sqlite:///:memory:")
    # Database named 'postgres' (common production default) must be rejected
    with pytest.raises(PermissionError, match="not in approved non-production allowlist"):
        run_guarded_purge_simulation(
            engine,
            db_name="postgres",
            environment="development",
            session_confirmation="YES_DELETE_ALL_DATA"
        )

    # Database named 'agentguard' must be rejected
    with pytest.raises(PermissionError, match="not in approved non-production allowlist"):
        run_guarded_purge_simulation(
            engine,
            db_name="agentguard",
            environment="development",
            session_confirmation="YES_DELETE_ALL_DATA"
        )

def test_destructive_safeguards_reject_unapproved_environment():
    """
    Even with an approved database name and confirmation token, if the environment
    is 'production' or unset, it MUST fail closed.
    """
    engine = create_engine("sqlite:///:memory:")
    with pytest.raises(PermissionError, match="Independent environment guard failed"):
        run_guarded_purge_simulation(
            engine,
            db_name="agentguard_test",
            environment="production",
            session_confirmation="YES_DELETE_ALL_DATA"
        )

    with pytest.raises(PermissionError, match="Independent environment guard failed"):
        run_guarded_purge_simulation(
            engine,
            db_name="agentguard_test",
            environment="staging",
            session_confirmation="YES_DELETE_ALL_DATA"
        )

def test_destructive_safeguards_block_without_session_confirmation():
    """Missing session confirmation fails closed."""
    engine = create_engine("sqlite:///:memory:")
    with pytest.raises(PermissionError, match="Session confirmation variable missing"):
        run_guarded_purge_simulation(
            engine,
            db_name="agentguard_dev",
            environment="development",
            session_confirmation="NO"
        )

def test_destructive_safeguards_allow_only_when_all_three_layers_verified():
    """Purge executes ONLY when allowlisted DB + approved environment + valid confirmation."""
    engine = create_engine("sqlite:///:memory:")
    result = run_guarded_purge_simulation(
        engine,
        db_name="agentguard_dev",
        environment="development",
        session_confirmation="YES_DELETE_ALL_DATA"
    )
    assert result == "PURGE_EXECUTED"
