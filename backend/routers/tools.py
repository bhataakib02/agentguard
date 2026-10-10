"""
Tools & Semantic Function Schemas Router for AgentGuard.
Manages registered downstream tools, OpenAPI/JSON schema definitions, risk levels, and endpoints.
"""

import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database import get_db
from core.deps import get_current_user, get_authenticated_entity, AuthenticatedAgent
import models
import schemas

router = APIRouter(prefix="/tools", tags=["Tools & Schemas"])


@router.post("", response_model=schemas.ToolResponse, status_code=status.HTTP_201_CREATED)
def create_tool(
    req: schemas.ToolCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registers a new downstream tool/API with semantic JSON Schema/OpenAPI parameter definitions.
    """
    existing = db.query(models.Tool).filter(
        models.Tool.name == req.name,
        (models.Tool.org_id == current_user.org_id) | (models.Tool.org_id == None)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A tool with name '{req.name}' already exists."
        )

    tool = models.Tool(
        org_id=current_user.org_id,
        name=req.name,
        category=req.category,
        endpoint=req.endpoint,
        description=req.description,
        risk_level=req.risk_level,
        status="ACTIVE",
        schema_definition=req.schema_definition or {},
        headers_json=req.headers_json or {},
        timeout_seconds=req.timeout_seconds or 30,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


@router.get("", response_model=List[schemas.ToolResponse])
def list_tools(
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    entity: Any = Depends(get_authenticated_entity),
    db: Session = Depends(get_db)
):
    """
    Lists registered tools available to the calling organization or machine agent.
    """
    org_id = None
    if isinstance(entity, AuthenticatedAgent):
        org_id = entity.org_id
    elif isinstance(entity, models.User):
        org_id = entity.org_id

    query = db.query(models.Tool)
    if org_id:
        query = query.filter((models.Tool.org_id == org_id) | (models.Tool.org_id == None))

    if category:
        query = query.filter(models.Tool.category == category.upper())
    if risk_level:
        query = query.filter(models.Tool.risk_level == risk_level.upper())
    if status_filter:
        query = query.filter(models.Tool.status == status_filter.upper())

    return query.order_by(models.Tool.name.asc()).all()


@router.get("/{tool_id}", response_model=schemas.ToolResponse)
def get_tool(
    tool_id: str,
    entity: Any = Depends(get_authenticated_entity),
    db: Session = Depends(get_db)
):
    """
    Retrieves tool details by ID or unique name.
    """
    org_id = entity.org_id if hasattr(entity, "org_id") else None

    query = db.query(models.Tool).filter(
        (models.Tool.id == tool_id) | (models.Tool.name == tool_id)
    )
    if org_id:
        query = query.filter((models.Tool.org_id == org_id) | (models.Tool.org_id == None))

    tool = query.first()
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found.")
    return tool


@router.put("/{tool_id}", response_model=schemas.ToolResponse)
def update_tool(
    tool_id: str,
    req: schemas.ToolUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates tool configuration, schema definition, or status.
    """
    query = db.query(models.Tool).filter(
        (models.Tool.id == tool_id) | (models.Tool.name == tool_id)
    )
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Tool.org_id == current_user.org_id)

    tool = query.first()
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found or unauthorized.")

    if req.name is not None:
        tool.name = req.name
    if req.category is not None:
        tool.category = req.category
    if req.endpoint is not None:
        tool.endpoint = req.endpoint
    if req.description is not None:
        tool.description = req.description
    if req.risk_level is not None:
        tool.risk_level = req.risk_level
    if req.status is not None:
        tool.status = req.status
    if req.schema_definition is not None:
        tool.schema_definition = req.schema_definition
    if req.headers_json is not None:
        tool.headers_json = req.headers_json
    if req.timeout_seconds is not None:
        tool.timeout_seconds = req.timeout_seconds

    tool.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(tool)
    return tool


@router.delete("/{tool_id}")
def delete_tool(
    tool_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deactivates or removes a tool from the registry.
    """
    query = db.query(models.Tool).filter(
        (models.Tool.id == tool_id) | (models.Tool.name == tool_id)
    )
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Tool.org_id == current_user.org_id)

    tool = query.first()
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found or unauthorized.")

    db.delete(tool)
    db.commit()
    return {"status": "SUCCESS", "message": f"Tool '{tool.name}' deleted successfully."}
