"""
Isolated Test Suite: Destructive Maintenance Safeguards Evaluation
Validates that database wipe guards fail closed and prevent accidental production data loss.
"""

import pytest
import re
from sqlalchemy import create_engine, text

def run_guarded_purge_simulation(engine, db_name: str, session_flag: str, is_production_flag: bool):
    """
    Simulates the multi-layered guard logic:
    Layer 1: Session variable confirmation
    Layer 2: Database name inspection (disallow 'prod', 'production')
    Layer 3: Schema-level production flag check
    """
    with engine.connect() as conn:
        # Layer 1: Session configuration check
        if session_flag != "YES_DELETE_ALL_DATA":
            raise PermissionError("SAFETY ABORT: Session confirmation variable missing or invalid.")
        
        # Layer 2: Database Name check
        if re.search(r"prod(uction)?", db_name, re.IGNORECASE):
            raise PermissionError(f"SAFETY ABORT: Destructive purge strictly prohibited on production database '{db_name}'.")
        
        # Layer 3: System settings lock
        if is_production_flag:
            raise PermissionError("SAFETY ABORT: System configuration table flags this database as PRODUCTION. Wipe blocked.")
        
        # If all guards pass, simulate safe purge
        return "PURGE_EXECUTED"

def test_destructive_safeguards_block_without_session_variable():
    engine = create_engine("sqlite:///:memory:")
    with pytest.raises(PermissionError, match="Session confirmation variable missing"):
        run_guarded_purge_simulation(engine, db_name="agentguard_dev", session_flag="NO", is_production_flag=False)

def test_destructive_safeguards_block_production_database_even_with_session_variable():
    """
    Critical requirement: Even if a caller sets the confirmation variable,
    the script MUST NOT execute if connected to a production database.
    """
    engine = create_engine("sqlite:///:memory:")
    with pytest.raises(PermissionError, match="strictly prohibited on production database"):
        run_guarded_purge_simulation(engine, db_name="agentguard_production", session_flag="YES_DELETE_ALL_DATA", is_production_flag=False)

def test_destructive_safeguards_block_production_system_flag():
    engine = create_engine("sqlite:///:memory:")
    with pytest.raises(PermissionError, match="flags this database as PRODUCTION"):
        run_guarded_purge_simulation(engine, db_name="agentguard_staging", session_flag="YES_DELETE_ALL_DATA", is_production_flag=True)

def test_destructive_safeguards_allow_only_in_true_dev_environment():
    engine = create_engine("sqlite:///:memory:")
    result = run_guarded_purge_simulation(engine, db_name="agentguard_test", session_flag="YES_DELETE_ALL_DATA", is_production_flag=False)
    assert result == "PURGE_EXECUTED"
