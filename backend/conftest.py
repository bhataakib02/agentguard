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

@pytest.fixture(autouse=True)
def inject_test_mock_transport():
    import httpx
    import json
    from services.tool_proxy_service import tool_proxy_service

    def test_mock_handler(request: httpx.Request):
        try:
            body = json.loads(request.content.decode("utf-8")) if request.content else {}
        except Exception:
            body = {}
        return httpx.Response(200, json={
            "status": "APPROVED",
            "refund_id": "ref_test_mock_12345",
            "tool": "mock_tool",
            "parameters": body,
            "message": "Tool endpoint executed successfully."
        })

    mock_transport = httpx.MockTransport(test_mock_handler)
    tool_proxy_service.set_mock_transport(mock_transport)
    yield
    tool_proxy_service.set_mock_transport(None)
