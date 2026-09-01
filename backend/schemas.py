from pydantic import BaseModel
from typing import Optional, List, Any
import datetime

class RegisterRequest(BaseModel):
    org_name: str
    full_name: str
    email: str
    password: Optional[str] = None
    auth_user_id: Optional[str] = None
    role: Optional[str] = "USER"

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None
    auth_user_id: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    auth_user_id: Optional[str] = None
    role: str
    full_name: str
    email: str
    org_name: str

class UserSchema(BaseModel):
    id: str
    auth_user_id: Optional[str] = None
    org_id: Optional[str] = None
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    status: str
    created_at: datetime.datetime
    org_name: Optional[str] = None

    class Config:
        from_attributes = True

class AgentCreateRequest(BaseModel):
    name: str
    department: str = "Operations"
    purpose: str = "Autonomous AI Agent Workflow"
    model_name: str = "gpt-4o"
    model_version: str = "1.0.0"
    environment: str = "PRODUCTION"
    autonomy_level: str = "MEDIUM"
    daily_budget: float = 10000.0
    org_id: Optional[str] = None
    owner_id: Optional[str] = None

class AgentSchema(BaseModel):
    id: str
    agent_code: str
    org_id: str
    owner_id: str
    name: str
    department: str
    purpose: str
    model_name: str
    model_version: str
    environment: str
    autonomy_level: str
    status: str
    risk_score: int
    trust_score: int
    daily_budget: float
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class CapabilityTokenRequest(BaseModel):
    agent_id: str
    capability_name: str
    scope: str
    amount_limit: float = 0.0
    ttl_seconds: int = 60

class CapabilityTokenSchema(BaseModel):
    id: str
    token_code: str
    agent_id: str
    capability_name: str
    scope: str
    amount_limit: float
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    status: str

    class Config:
        from_attributes = True

class ActionEvaluateRequest(BaseModel):
    prompt: str
    agent_id: Optional[str] = None
    amount: float = 0.0

class DecisionSchema(BaseModel):
    id: str
    agent_id: str
    user_id: Optional[str] = None
    intent_summary: str
    action_requested: str
    resource_target: str
    amount: float
    decision: str
    risk_score: int
    policy_name: Optional[str] = None
    explanation: str
    execution_status: str
    timestamp: datetime.datetime

    class Config:
        from_attributes = True

class ApprovalActionRequest(BaseModel):
    action: str  # APPROVE, REJECT

class RedTeamRunRequest(BaseModel):
    agent_id: str
    attack_type: str

class DigitalTwinRunRequest(BaseModel):
    agent_id: str
    scenario_type: str

class AssistantQueryRequest(BaseModel):
    question: str

class AssistantQueryResponse(BaseModel):
    question: str
    answer: str
    data: Optional[Any] = None
    recommendations: Optional[List[str]] = None
