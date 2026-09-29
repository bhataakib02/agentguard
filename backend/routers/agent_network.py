from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/agent-network", tags=["Multi-Agent Ecosystem"])

@router.get("/relationships")
def get_relationships(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.AgentRelationship)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent, models.AgentRelationship.parent_agent_id == models.Agent.id).filter(models.Agent.org_id == current_user.org_id)
    return query.all()

@router.get("/graph")
def get_network_graph(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent_query = db.query(models.Agent)
    if current_user.role != "SUPER_ADMIN":
        agent_query = agent_query.filter(models.Agent.org_id == current_user.org_id)
    agents = agent_query.all()
    agent_ids = {a.id for a in agents}

    rel_query = db.query(models.AgentRelationship)
    rels = rel_query.all()
    rel_list = [r for r in rels if r.parent_agent_id in agent_ids or r.child_agent_id in agent_ids] if current_user.role != "SUPER_ADMIN" else rels

    nodes = [{"id": a.id, "label": f"{a.agent_code} ({a.name})", "type": "AGENT", "status": a.status} for a in agents]
    edges = [
        {
            "source": r.parent_agent_id,
            "target": r.child_agent_id,
            "label": f"Trust: {r.trust_status}"
        }
        for r in rel_list
    ]

    return {"nodes": nodes, "edges": edges}
