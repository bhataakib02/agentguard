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
    settings as settings_router, notifications, platform, organization, reports
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

# Mount all domain routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(profile.router, prefix=settings.API_V1_STR)
app.include_router(platform.router, prefix=settings.API_V1_STR)
app.include_router(organization.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(agents.router, prefix=settings.API_V1_STR)
app.include_router(iam.router, prefix=settings.API_V1_STR)
app.include_router(permissions.router, prefix=settings.API_V1_STR)
app.include_router(capabilities.router, prefix=settings.API_V1_STR)
app.include_router(policies.router, prefix=settings.API_V1_STR)
app.include_router(ai.router, prefix=settings.API_V1_STR)
app.include_router(decisions.router, prefix=settings.API_V1_STR)
app.include_router(risk.router, prefix=settings.API_V1_STR)
app.include_router(trust.router, prefix=settings.API_V1_STR)
app.include_router(behavior.router, prefix=settings.API_V1_STR)
app.include_router(security.router, prefix=settings.API_V1_STR)
app.include_router(runtime.router, prefix=settings.API_V1_STR)
app.include_router(approvals.router, prefix=settings.API_V1_STR)
app.include_router(agent_network.router, prefix=settings.API_V1_STR)
app.include_router(provenance.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(red_team.router, prefix=settings.API_V1_STR)
app.include_router(digital_twin.router, prefix=settings.API_V1_STR)
app.include_router(economics.router, prefix=settings.API_V1_STR)
app.include_router(impact.router, prefix=settings.API_V1_STR)
app.include_router(optimization.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)
app.include_router(assistant.router, prefix=settings.API_V1_STR)
app.include_router(developers.router, prefix=settings.API_V1_STR)
app.include_router(integrations.router, prefix=settings.API_V1_STR)
app.include_router(system.router, prefix=settings.API_V1_STR)
app.include_router(settings_router.router, prefix=settings.API_V1_STR)
app.include_router(notifications.router, prefix=settings.API_V1_STR)

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
    await ws_manager.connect(websocket)
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
