import os
import sys

# Set test environment before any application modules are loaded
test_db_path = os.path.join(os.path.dirname(__file__), "test_agentguard_global.db")
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
os.environ["SECRET_KEY"] = "agentguard-test-secret-key-32charactersmin"

sys.path.insert(0, os.path.dirname(__file__))

import pytest
from database import Base, engine

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=engine)
    yield
