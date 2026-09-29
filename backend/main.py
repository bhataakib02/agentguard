from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from ws_manager import manager as ws_manager
from config import settings

# Import routers
from routers import (
    auth, profile, admin, agents, iam, permissions, capabilities, policies, ai, decisions,
    risk, trust, behavior, security, runtime, approvals, agent_network,
    provenance, audit, red_team, digital_twin, economics, impact,
    optimization, analytics, assistant, developers, integrations, system,
    settings as settings_router, notifications, platform, organization, reports, webhooks,
    telemetry
)

# Initialize DB Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.TAGLINE,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for Next.js frontend with restricted trusted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount all domain routers with both /api and /api/v1
DOMAIN_ROUTERS = [
    auth.router, profile.router, platform.router, organization.router,
    reports.router, admin.router, agents.router, iam.router,
    permissions.router, capabilities.router, policies.router, ai.router,
    decisions.router, risk.router, trust.router, behavior.router,
    security.router, runtime.router, approvals.router, agent_network.router,
    provenance.router, audit.router, red_team.router, digital_twin.router,
    economics.router, impact.router, optimization.router, analytics.router,
    assistant.router, developers.router, integrations.router, system.router,
    settings_router.router, notifications.router, webhooks.router,
    telemetry.router
]

for r in DOMAIN_ROUTERS:
    app.include_router(r, prefix=settings.API_V1_STR)
    if settings.API_V1_STR != "/api/v1":
        app.include_router(r, prefix="/api/v1")

import logging
from core.supabase_admin import supabase_admin
from database import SessionLocal
import models

logger = logging.getLogger("agentguard.startup")

@app.on_event("startup")
def validate_auth_and_config():
    if supabase_admin.is_configured:
        logger.info("[AgentGuard] Supabase Admin Auth: ACTIVE (Service Role Key configured)")
    else:
        logger.warning(
            "[AgentGuard] Supabase Admin Auth: SUPABASE_SERVICE_ROLE_KEY not configured. "
            "New org/invite users will have local password fallback only."
        )

    try:
        db = SessionLocal()
        users_count = db.query(models.User).count()
        users_with_supabase = db.query(models.User).filter(models.User.auth_user_id != None).count()
        users_with_local_hash = db.query(models.User).filter(models.User.password_hash != None).count()
        logger.info(
            f"[AgentGuard] Auth Audit: {users_count} total users | "
            f"{users_with_supabase} linked to Supabase Auth | "
            f"{users_with_local_hash} with local password hash"
        )
        db.close()
    except Exception as e:
        logger.warning(f"[AgentGuard] Startup user audit notice: {e}")

@app.get("/")
@app.get("/health")
@app.get(f"{settings.API_V1_STR}/health")
def root():
    return {
        "platform": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "status": "RUNNING",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Accept org_id and role from query params for tenant-isolated streaming
    org_id = websocket.query_params.get("org_id")
    role = websocket.query_params.get("role", "USER")
    await ws_manager.connect(websocket, org_id=org_id, role=role)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "PING":
                await websocket.send_text("PONG")
            else:
                await websocket.send_json({"type": "PONG", "received": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

