from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/risk", tags=["Risk Intelligence"])

@router.get("/agents")
def get_agent_risk_scores(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agents = query.all()
    return [
        {
            "id": a.id,
            "agent_code": a.agent_code,
            "name": a.name,
            "department": a.department,
            "risk_score": a.risk_score,
            "status": a.status,
            "autonomy": a.autonomy_level
        }
        for a in agents
    ]

@router.get("/trends")
def get_risk_trends(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import datetime

    now = datetime.datetime.utcnow()
    seven_days_ago = now - datetime.timedelta(days=7)

    # Base decision query scoped to tenant
    dec_query = db.query(models.Decision).filter(models.Decision.timestamp >= seven_days_ago)
    agent_query = db.query(models.Agent)
    if current_user.role != "SUPER_ADMIN":
        dec_query = dec_query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
        agent_query = agent_query.filter(models.Agent.org_id == current_user.org_id)

    decisions = dec_query.all()
    agents = agent_query.all()
    current_high_risk_agents = len([a for a in agents if a.risk_score > 60])

    # Build daily buckets for the past 7 days
    daily_stats = {}
    day_order = []
    for i in range(6, -1, -1):
        d = now - datetime.timedelta(days=i)
        day_str = d.strftime("%a")
        date_key = d.strftime("%Y-%m-%d")
        day_order.append(date_key)
        daily_stats[date_key] = {
            "day": day_str,
            "date": date_key,
            "total_risk": 0,
            "count": 0,
            "high_risk_decisions": 0
        }

    for dec in decisions:
        if dec.timestamp:
            date_key = dec.timestamp.strftime("%Y-%m-%d")
            if date_key in daily_stats:
                daily_stats[date_key]["count"] += 1
                daily_stats[date_key]["total_risk"] += (dec.risk_score or 0)
                if (dec.risk_score or 0) > 60:
                    daily_stats[date_key]["high_risk_decisions"] += 1

    return [
        {
            "day": daily_stats[dk]["day"],
            "date": daily_stats[dk]["date"],
            "avg_risk": round(daily_stats[dk]["total_risk"] / daily_stats[dk]["count"], 1) if daily_stats[dk]["count"] > 0 else 0.0,
            "decision_count": daily_stats[dk]["count"],
            "high_risk_agents": current_high_risk_agents
        }
        for dk in day_order
    ]
