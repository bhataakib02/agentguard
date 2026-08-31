from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/agent-network", tags=["Multi-Agent Ecosystem"])

@router.get("/relationships")
def get_relationships(db: Session = Depends(get_db)):
    return db.query(models.AgentRelationship).all()

@router.get("/graph")
def get_network_graph(db: Session = Depends(get_db)):
    agents = db.query(models.Agent).all()
    rel_list = db.query(models.AgentRelationship).all()

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
