from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import schemas
from engines.assistant_engine import assistant_engine

router = APIRouter(prefix="/assistant", tags=["AI Admin Assistant"])

@router.post("/query", response_model=schemas.AssistantQueryResponse)
def query_assistant(req: schemas.AssistantQueryRequest, db: Session = Depends(get_db)):
    return assistant_engine.process_query(req.question, db)
