from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import schemas, models
from engines.assistant_engine import assistant_engine

router = APIRouter(prefix="/assistant", tags=["AI Admin Assistant"])

@router.post("/query", response_model=schemas.AssistantQueryResponse)
def query_assistant(
    req: schemas.AssistantQueryRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return assistant_engine.process_query(req.question, db)
