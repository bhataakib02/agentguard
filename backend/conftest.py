import os
import sys

# Set test environment before any application modules are loaded
test_db_path = os.path.join(os.path.dirname(__file__), "test_agentguard_global.db")
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
os.environ["SECRET_KEY"] = "agentguard-test-secret-key-32charactersmin"
os.environ["ALLOW_DEMO_SEED"] = "true"
os.environ["AGENTGUARD_ALLOW_LOCAL_TOOLS"] = "false"

sys.path.insert(0, os.path.dirname(__file__))

import pytest
from database import Base, engine

@pytest.fixture(autouse=True)
def setup_test_database():
    from database import Base, engine
    Base.metadata.create_all(bind=engine)
    yield
