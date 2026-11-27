"""
Comprehensive Automated Test Suite: Notification & Alerting Engine & System Health Verification
Validates:
1. In-app notification creation, database persistence, and user/tenant isolation.
2. Notification listing, unread count, pagination, and category filtering.
3. Marking individual and all notifications as read.
4. Dismissing / deleting notifications with strict IDOR/cross-user protection.
5. In-app functionality remains 100% operational when external email provider is disabled.
6. Email failure graceful degradation (no crash, truthful reporting).
7. System Health engine multi-state classification:
   - OPERATIONAL when core in-app and delivery configured.
   - DEGRADED when core in-app is active but outbound email is unconfigured.
   - DOWN when database or core service fails.
8. Truthful response latencies and detailed reason strings.
"""

import uuid
import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
import models
from core.security import create_access_token
from services.notification_service import notification_service
from services.email_service import email_service
from config import settings

# In-memory SQLite for isolated unit testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_notifications.db"
test_engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    prev_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    if prev_override is not None:
        app.dependency_overrides[get_db] = prev_override
    else:
        app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)
    import os
    if os.path.exists("./test_notifications.db"):
        try:
            os.remove("./test_notifications.db")
        except Exception:
            pass


@pytest.fixture(scope="module")
def test_data():
    db = TestingSessionLocal()
    org_a_id = str(uuid.uuid4())
    org_b_id = str(uuid.uuid4())
    org_a = models.Organization(id=org_a_id, name="Tenant A Corp", slug=f"tenant-a-{org_a_id[:8]}")
    org_b = models.Organization(id=org_b_id, name="Tenant B Corp", slug=f"tenant-b-{org_b_id[:8]}")
    db.add_all([org_a, org_b])
    db.commit()

    # Create Users
    user_a = models.User(
        id=str(uuid.uuid4()),
        org_id=org_a.id,
        email=f"user_a_{org_a_id[:6]}@tenant-a.com",
        full_name="User Alpha",
        role="ADMIN",
        status="ACTIVE"
    )
    user_b = models.User(
        id=str(uuid.uuid4()),
        org_id=org_b.id,
        email=f"user_b_{org_b_id[:6]}@tenant-b.com",
        full_name="User Beta",
        role="ADMIN",
        status="ACTIVE"
    )
    super_admin = models.User(
        id=str(uuid.uuid4()),
        org_id=org_a.id,
        email=f"super_{org_a_id[:6]}@agentguard.internal",
        full_name="Platform SuperAdmin",
        role="SUPER_ADMIN",
        status="ACTIVE"
    )
    db.add_all([user_a, user_b, super_admin])
    db.commit()

    token_a = create_access_token(user_id=str(user_a.id), email=user_a.email, role=user_a.role)
    token_b = create_access_token(user_id=str(user_b.id), email=user_b.email, role=user_b.role)
    token_super = create_access_token(user_id=str(super_admin.id), email=super_admin.email, role="SUPER_ADMIN")

    data = {
        "org_a_id": str(org_a.id),
        "org_b_id": str(org_b.id),
        "user_a_id": str(user_a.id),
        "user_b_id": str(user_b.id),
        "token_a": token_a,
        "token_b": token_b,
        "token_super": token_super
    }
    db.close()
    return data


def test_01_create_in_app_notification(test_data):
    """Verifies that in-app notifications are stored in the database with accurate fields."""
    db = TestingSessionLocal()
    notif = notification_service.create_in_app_notification(
        db=db,
        user_id=test_data["user_a_id"],
        title="High Risk Transaction Flagged",
        message="Agent 007 requested ₹50,000 refund exceeding threshold.",
        severity="HIGH",
        notif_type="RISK_ALERT"
    )
    assert notif.id is not None
    assert notif.is_read is False
    assert notif.read is False
    assert notif.title == "High Risk Transaction Flagged"
    assert notif.severity == "HIGH"
    db.close()


def test_02_list_notifications_and_user_isolation(test_data):
    """Verifies that User A cannot see User B's notifications (strict tenant/user isolation)."""
    db = TestingSessionLocal()
    # Create notification for User B
    notification_service.create_in_app_notification(
        db=db,
        user_id=test_data["user_b_id"],
        title="Tenant B Secret Notification",
        message="Sensitive Tenant B event.",
        severity="CRITICAL",
        notif_type="SECURITY"
    )
    db.close()

    # User A requests notifications
    headers_a = {"Authorization": f"Bearer {test_data['token_a']}"}
    resp_a = client.get("/api/v1/notifications", headers=headers_a)
    assert resp_a.status_code == 200
    notifs_a = resp_a.json()
    assert len(notifs_a) >= 1
    # Ensure none of User B's notifications leak to User A
    for n in notifs_a:
        assert n["user_id"] == test_data["user_a_id"]
        assert "Tenant B" not in n["title"]
        # Both is_read and read fields are provided for frontend compatibility
        assert "is_read" in n
        assert "read" in n


def test_03_unread_count_endpoint(test_data):
    """Verifies real database-backed unread notification count."""
    headers_a = {"Authorization": f"Bearer {test_data['token_a']}"}
    resp = client.get("/api/v1/notifications/unread-count", headers=headers_a)
    assert resp.status_code == 200
    data = resp.json()
    assert "unread_count" in data
    assert data["unread_count"] >= 1


def test_04_mark_single_notification_read(test_data):
    """Verifies marking a single notification as read and rejecting cross-user tampering."""
    db = TestingSessionLocal()
    notif = db.query(models.Notification).filter(
        models.Notification.user_id == test_data["user_a_id"],
        models.Notification.is_read == False
    ).first()
    assert notif is not None
    notif_id = str(notif.id)
    db.close()

    # User B attempts to mark User A's notification as read (IDOR check -> 403 Forbidden)
    headers_b = {"Authorization": f"Bearer {test_data['token_b']}"}
    forbidden_resp = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=headers_b)
    assert forbidden_resp.status_code == 403

    # Legitimate User A marks it read
    headers_a = {"Authorization": f"Bearer {test_data['token_a']}"}
    resp = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True

    # Confirm database state updated
    db = TestingSessionLocal()
    updated = db.query(models.Notification).filter(models.Notification.id == notif_id).first()
    assert updated.is_read is True
    db.close()


def test_05_mark_all_notifications_read(test_data):
    """Verifies bulk marking all notifications as read for current user."""
    db = TestingSessionLocal()
    # Add two new unread notifications for User A
    notification_service.create_in_app_notification(
        db=db,
        user_id=test_data["user_a_id"],
        title="Alert 1",
        message="Msg 1"
    )
    notification_service.create_in_app_notification(
        db=db,
        user_id=test_data["user_a_id"],
        title="Alert 2",
        message="Msg 2"
    )
    db.close()

    headers_a = {"Authorization": f"Bearer {test_data['token_a']}"}
    resp = client.post("/api/v1/notifications/read-all", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"

    # Verify unread count is now 0 for User A
    count_resp = client.get("/api/v1/notifications/unread-count", headers=headers_a)
    assert count_resp.json()["unread_count"] == 0


def test_06_delete_notification_and_idor_protection(test_data):
    """Verifies notification deletion/dismissal with strict ownership checks."""
    db = TestingSessionLocal()
    notif = notification_service.create_in_app_notification(
        db=db,
        user_id=test_data["user_a_id"],
        title="To be deleted",
        message="Dismiss me"
    )
    notif_id = str(notif.id)
    db.close()

    # User B attempts to delete User A's notification -> 403 Forbidden
    headers_b = {"Authorization": f"Bearer {test_data['token_b']}"}
    forbid = client.delete(f"/api/v1/notifications/{notif_id}", headers=headers_b)
    assert forbid.status_code == 403

    # User A deletes their notification -> 200 OK
    headers_a = {"Authorization": f"Bearer {test_data['token_a']}"}
    resp = client.delete(f"/api/v1/notifications/{notif_id}", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"

    # Confirm deleted from DB
    db = TestingSessionLocal()
    deleted = db.query(models.Notification).filter(models.Notification.id == notif_id).first()
    assert deleted is None
    db.close()


def test_07_in_app_notifications_work_when_email_disabled(test_data):
    """Verifies that in-app notification creation and governance dispatch succeed even with email disabled."""
    original_provider = settings.EMAIL_PROVIDER
    settings.EMAIL_PROVIDER = "DISABLED"

    db = TestingSessionLocal()
    res = notification_service.notify_governance_event(
        db=db,
        org_id=test_data["org_a_id"],
        event_type="agent.quarantine",
        resource_type="agent",
        resource_id=str(uuid.uuid4()),
        title="Agent Quarantined",
        message="Agent breached maximum token budget.",
        data={"reason": "budget_breach"},
        user_id=test_data["user_a_id"],
        severity="CRITICAL"
    )
    assert res["notification_id"] is not None
    assert res["email_dispatched"] is False

    # Confirm notification is present in database
    created = db.query(models.Notification).filter(models.Notification.id == res["notification_id"]).first()
    assert created is not None
    assert created.title == "Agent Quarantined"
    db.close()

    settings.EMAIL_PROVIDER = original_provider
    assert created is not None
    assert created.title == "Agent Quarantined"
    db.close()

    settings.EMAIL_PROVIDER = original_provider


def test_08_system_health_degraded_when_email_not_configured(test_data):
    """
    Verifies that when database notifications are active but email provider is not configured,
    the Notification & Alerting Engine reports DEGRADED (amber), NOT red 'Not Configured'.
    """
    original_provider = settings.EMAIL_PROVIDER
    settings.EMAIL_PROVIDER = "DISABLED"

    headers_super = {"Authorization": f"Bearer {test_data['token_super']}"}
    resp = client.get("/api/v1/platform/health", headers=headers_super)
    assert resp.status_code == 200
    data = resp.json()

    notif_card = next((s for s in data["services"] if s["id"] == "s8"), None)
    assert notif_card is not None
    assert data["overall_status"] == "Degraded"
    assert notif_card["status"] == "Degraded"
    assert "In-App Active" in notif_card["telemetry"]
    assert "In-app notifications active" in notif_card["details"]
    assert notif_card["latency_ms"] is not None
    assert notif_card["latency_ms"] >= 0

    settings.EMAIL_PROVIDER = original_provider


def test_09_system_health_operational_when_email_configured(test_data):
    """
    Verifies that when both in-app notifications and email provider are active,
    the Notification & Alerting Engine reports OPERATIONAL.
    """
    original_provider = settings.EMAIL_PROVIDER
    settings.EMAIL_PROVIDER = "MOCK"

    headers_super = {"Authorization": f"Bearer {test_data['token_super']}"}
    resp = client.get("/api/v1/platform/health", headers=headers_super)
    assert resp.status_code == 200
    data = resp.json()

    notif_card = next((s for s in data["services"] if s["id"] == "s8"), None)
    assert notif_card is not None
    assert data["overall_status"] == "Operational"
    assert notif_card["status"] == "Operational"
    assert notif_card["telemetry"] == "Active"
    assert "operational" in notif_card["details"].lower()
    assert notif_card["latency_ms"] is not None

    settings.EMAIL_PROVIDER = original_provider


def test_10_unauthorized_access_rejected():
    """Verifies that unauthenticated access to notification endpoints is rejected with 401."""
    resp = client.get("/api/v1/notifications")
    assert resp.status_code == 401
    resp_count = client.get("/api/v1/notifications/unread-count")
    assert resp_count.status_code == 401


def test_11_system_health_down_when_db_unavailable(test_data):
    """
    Verifies that when DB/notification query fails, /api/v1/platform/health reports DOWN
    (never hardcoded OPERATIONAL).
    """
    headers_super = {"Authorization": f"Bearer {test_data['token_super']}"}

    class BrokenHealthSession:
        def __init__(self):
            self._real = TestingSessionLocal()

        def execute(self, *args, **kwargs):
            raise RuntimeError("Simulated database outage")

        def query(self, *entities, **kwargs):
            if any((e is models.Notification or getattr(e, "class_", None) is models.Notification) for e in entities):
                raise RuntimeError("Simulated notification query failure")
            return self._real.query(*entities, **kwargs)

        def close(self):
            self._real.close()

    def broken_get_db():
        db = BrokenHealthSession()
        try:
            yield db
        finally:
            db.close()

    prev = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = broken_get_db
    try:
        resp = client.get("/api/v1/platform/health", headers=headers_super)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"].upper() == "DOWN"
        notif_card = next((s for s in data["services"] if s["id"] == "s8"), None)
        assert notif_card is not None
        assert notif_card["status"] == "Down"
    finally:
        if prev is not None:
            app.dependency_overrides[get_db] = prev


def test_12_super_admin_read_all_does_not_clobber_tenant_unread(test_data):
    """
    Verifies that SUPER_ADMIN calling POST /notifications/read-all only marks
    SUPER_ADMIN's own or system-level alerts and never clears tenant users' unread alerts.
    """
    db = TestingSessionLocal()
    tenant_notif = notification_service.create_in_app_notification(
        db=db,
        user_id=test_data["user_a_id"],
        title="Tenant Must Stay Unread",
        message="Do not clear across tenants",
        severity="HIGH",
        notif_type="SECURITY"
    )
    tenant_notif_id = str(tenant_notif.id)
    db.close()

    headers_super = {"Authorization": f"Bearer {test_data['token_super']}"}
    resp = client.post("/api/v1/notifications/read-all", headers=headers_super)
    assert resp.status_code == 200

    db = TestingSessionLocal()
    refreshed = db.query(models.Notification).filter(models.Notification.id == tenant_notif_id).first()
    assert refreshed is not None
    assert refreshed.is_read is False
    db.close()


def test_13_pagination_and_filtering(test_data):
    """Verifies limit, offset, severity, type, and unread_only query filters."""
    db = TestingSessionLocal()
    for i in range(4):
        notification_service.create_in_app_notification(
            db=db,
            user_id=test_data["user_b_id"],
            title=f"Paginated Alert {i}",
            message=f"Msg {i}",
            severity="WARNING" if i % 2 == 0 else "INFO",
            notif_type="WEBHOOK_TEST"
        )
    db.close()

    headers_b = {"Authorization": f"Bearer {test_data['token_b']}"}
    p1 = client.get("/api/v1/notifications?limit=2&offset=0&type=WEBHOOK_TEST", headers=headers_b)
    p2 = client.get("/api/v1/notifications?limit=2&offset=2&type=WEBHOOK_TEST", headers=headers_b)
    assert p1.status_code == 200
    assert p2.status_code == 200
    ids_1 = {item["id"] for item in p1.json()}
    ids_2 = {item["id"] for item in p2.json()}
    assert len(ids_1) == 2
    assert len(ids_2) == 2
    assert ids_1.isdisjoint(ids_2)

    sev_resp = client.get("/api/v1/notifications?severity=WARNING&type=WEBHOOK_TEST", headers=headers_b)
    assert sev_resp.status_code == 200
    assert all(n["severity"] == "WARNING" for n in sev_resp.json())


def test_14_agent_suspend_restore_and_incident_update_notifications(test_data):
    """Verifies suspend_agent, restore_agent, and update_incident emit accurate event notifications."""
    original_provider = settings.EMAIL_PROVIDER
    settings.EMAIL_PROVIDER = "DISABLED"
    try:
        db = TestingSessionLocal()
        agent = models.Agent(
            id=str(uuid.uuid4()),
            org_id=test_data["org_a_id"],
            owner_id=test_data["user_a_id"],
            name="Notif Agent",
            agent_code=f"AG-NOTIF-{uuid.uuid4().hex[:6]}",
            purpose="Notification lifecycle test",
            status="NORMAL",
            autonomy_level="MEDIUM"
        )
        inc = models.SecurityIncident(
            id=str(uuid.uuid4()),
            org_id=test_data["org_a_id"],
            title="Suspicious Probe",
            severity="HIGH",
            source="TEST",
            status="OPEN"
        )
        db.add_all([agent, inc])
        db.commit()
        agent_id = str(agent.id)
        inc_id = str(inc.id)
        db.close()

        headers_a = {"Authorization": f"Bearer {test_data['token_a']}"}
        assert client.post(f"/api/v1/agents/{agent_id}/suspend", headers=headers_a).status_code == 200
        assert client.post(f"/api/v1/agents/{agent_id}/restore", headers=headers_a).status_code == 200
        assert client.patch(f"/api/v1/security/incidents/{inc_id}", json={"status": "RESOLVED"}, headers=headers_a).status_code == 200

        db = TestingSessionLocal()
        notifs = db.query(models.Notification).filter(models.Notification.user_id == test_data["user_a_id"]).all()
        types = {n.type for n in notifs}
        titles = " | ".join(n.title for n in notifs)
        assert "AGENT.SUSPENDED" in types
        assert "AGENT.RESTORED" in types
        assert "Agent Restored: Notif Agent" in titles
        assert "SECURITY.INCIDENT_RESOLVED" in types
        db.close()
    finally:
        settings.EMAIL_PROVIDER = original_provider


def test_15_webhook_dead_letter_tenant_notification_and_retry_dedupe(test_data, monkeypatch):
    """
    Verifies webhook permanent failure notifies org admins (user_id populated) and retries skip
    already DEAD_LETTER deliveries without duplicate notifications.
    """
    from tasks import webhook_tasks

    original_provider = settings.EMAIL_PROVIDER
    settings.EMAIL_PROVIDER = "DISABLED"
    try:
        db = TestingSessionLocal()
        ep = models.WebhookEndpoint(
            id=str(uuid.uuid4()),
            org_id=test_data["org_a_id"],
            name="Test Webhook",
            url="https://example.invalid/webhook",
            secret_hash="testhash",
            secret_key="test-secret",
            event_types=["decision.refused"],
            is_active=True
        )
        db.add(ep)
        db.flush()
        delivery = models.WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=ep.id,
            event_type="decision.refused",
            payload_json={"event": "test"},
            status="RETRYING",
            attempt_count=2  # Next failure (3rd) hits MAX_RETRIES=3 -> DEAD_LETTER
        )
        db.add(delivery)
        db.commit()
        delivery_id = str(delivery.id)
        db.close()

        monkeypatch.setattr(webhook_tasks, "SessionLocal", TestingSessionLocal)
        monkeypatch.setattr(
            webhook_tasks.tool_proxy_service,
            "safe_dispatch_request",
            lambda *args, **kwargs: {
                "success": False,
                "status_code": 500,
                "error": "Simulated HTTP 500 timeout",
            },
        )

        res1 = webhook_tasks.dispatch_webhook_task(delivery_id)
        assert res1["status"] == "DEAD_LETTER"

        db = TestingSessionLocal()
        wh_notifs = db.query(models.Notification).filter(
            models.Notification.user_id == test_data["user_a_id"],
            models.Notification.type == "WEBHOOK.DELIVERY_FAILED"
        ).all()
        assert len(wh_notifs) == 1
        db.close()

        # Re-running dispatch on DEAD_LETTER must be idempotent and NOT create duplicate notifications
        res2 = webhook_tasks.dispatch_webhook_task(delivery_id)
        assert res2["status"] == "ALREADY_COMPLETED"

        db = TestingSessionLocal()
        wh_notifs_after = db.query(models.Notification).filter(
            models.Notification.user_id == test_data["user_a_id"],
            models.Notification.type == "WEBHOOK.DELIVERY_FAILED"
        ).all()
        assert len(wh_notifs_after) == 1
        db.close()
    finally:
        settings.EMAIL_PROVIDER = original_provider
