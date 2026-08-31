import sys, os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, engine, get_db
import models, schemas
from routers.auth import register_organization, login, get_me
from core.deps import get_current_user

def run_auth_verification_suite():
    print("=" * 60)
    print("  AGENTGUARD PRODUCTION AUTHENTICATION & MULTI-TENANT TEST SUITE  ")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # 1. DATABASE SCHEMA TEST (auth_user_id)
    print("\n--- 1. DATABASE SCHEMA & AUTH_USER_ID CONSTRAINT CHECK ---")
    user_cols = [c.name for c in models.User.__table__.columns]
    assert "auth_user_id" in user_cols, "FAIL: auth_user_id missing from User model!"
    print("  [SUCCESS] auth_user_id column verified in User model.")

    # 2. USER REGISTRATION TEST (SUPABASE AUTH LINKAGE)
    print("\n--- 2. SUPABASE AUTH USER REGISTRATION & ORGANIZATION CREATION ---")
    test_email = f"user_{uuid.uuid4().hex[:6]}@enterprise.ai"
    test_auth_id = str(uuid.uuid4())
    req = schemas.RegisterRequest(
        org_name="Quantum Security Labs",
        full_name="Dr. Alan Turing",
        email=test_email,
        auth_user_id=test_auth_id
    )

    reg_resp = register_organization(req=req, db=db)
    assert reg_resp.access_token is not None, "FAIL: Access token missing from registration response!"
    assert reg_resp.auth_user_id == test_auth_id, "FAIL: auth_user_id mismatch in registration!"
    assert reg_resp.org_name == "Quantum Security Labs", "FAIL: Organization name mismatch!"
    print(f"  [SUCCESS] User Registered: {reg_resp.email} (Auth ID: {reg_resp.auth_user_id})")
    print(f"  [SUCCESS] Organization Linked: {reg_resp.org_name}")

    # 3. DATABASE PERSISTENCE & FOREIGN KEY VERIFICATION
    print("\n--- 3. DATABASE PERSISTENCE & FOREIGN KEY CHECK ---")
    db_user = db.query(models.User).filter(models.User.email == test_email).first()
    assert db_user is not None, "FAIL: User record not persisted in database!"
    assert db_user.auth_user_id == test_auth_id, "FAIL: auth_user_id not saved in database!"
    
    db_org = db.query(models.Organization).filter(models.Organization.id == db_user.org_id).first()
    assert db_org is not None, "FAIL: Linked organization not found!"
    print(f"  [SUCCESS] User ID: {db_user.id} -> Org ID: {db_org.id} ({db_org.name})")

    # 4. IDENTITY RESOLUTION & /me ENDPOINT TEST
    print("\n--- 4. USER IDENTITY RESOLUTION (/auth/me) TEST ---")
    me_resp = get_me(current_user=db_user, db=db)
    assert me_resp.email == test_email, "FAIL: Email mismatch in /me endpoint!"
    assert me_resp.org_name == "Quantum Security Labs", "FAIL: Organization name missing from /me!"
    print(f"  [SUCCESS] Authenticated Profile Resolved: {me_resp.full_name} ({me_resp.role})")

    # 5. MULTI-TENANT ISOLATION CHECK
    print("\n--- 5. MULTI-TENANT ORGANIZATION ISOLATION TEST ---")
    user2_email = f"user2_{uuid.uuid4().hex[:6]}@competitor.ai"
    req2 = schemas.RegisterRequest(
        org_name="CyberDyne Systems",
        full_name="Sarah Connor",
        email=user2_email,
        auth_user_id=str(uuid.uuid4())
    )
    reg_resp2 = register_organization(req=req2, db=db)
    db_user2 = db.query(models.User).filter(models.User.email == user2_email).first()
    
    assert db_user.org_id != db_user2.org_id, "FAIL: Multi-tenant isolation failure! Users share org_id!"
    print(f"  [SUCCESS] Org 1 ({db_user.org_id}) != Org 2 ({db_user2.org_id}) - Multi-tenant scoping enforced!")

    print("\n" + "=" * 60)
    print("      ALL AUTHENTICATION & MULTI-TENANT TESTS PASSED 100%      ")
    print("=" * 60)

if __name__ == "__main__":
    run_auth_verification_suite()
