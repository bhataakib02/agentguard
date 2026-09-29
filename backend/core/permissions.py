"""
AgentGuard Phase 5: Enterprise Role-Based Access Control (RBAC) & Permission Matrix
Authoritative centralized definition of roles, permissions, and hierarchical evaluation.
"""

from typing import List, Set, Dict

# ============================================================================
# 1. HIERARCHICAL HUMAN ROLES & LEVELS
# ============================================================================
ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_ADMIN = "ADMIN"
ROLE_DEVELOPER = "DEVELOPER"
ROLE_MANAGER = "MANAGER"
ROLE_SECURITY_ANALYST = "SECURITY_ANALYST"
ROLE_OPERATOR = "OPERATOR"
ROLE_ANALYST = "ANALYST"
ROLE_VIEWER = "VIEWER"
ROLE_USER = "USER"

ROLE_AGENT = "AGENT"  # Machine identity

MACHINE_ROLES = [
    ROLE_AGENT,
]

HUMAN_ROLES = [
    ROLE_USER,
    ROLE_VIEWER,
    ROLE_ANALYST,
    ROLE_OPERATOR,
    ROLE_SECURITY_ANALYST,
    ROLE_MANAGER,
    ROLE_DEVELOPER,
    ROLE_ADMIN,
    ROLE_SUPER_ADMIN,
]

ROLE_LEVELS: Dict[str, int] = {
    ROLE_SUPER_ADMIN: 9,
    ROLE_ADMIN: 8,
    ROLE_DEVELOPER: 7,
    ROLE_MANAGER: 6,
    ROLE_SECURITY_ANALYST: 5,
    ROLE_OPERATOR: 4,
    ROLE_ANALYST: 3,
    ROLE_VIEWER: 2,
    ROLE_USER: 1,
}

# ============================================================================
# 2. FORMAL ENTERPRISE PERMISSION CONSTANTS
# ============================================================================

# Organization
PERM_ORGANIZATION_VIEW = "ORGANIZATION_VIEW"
PERM_ORGANIZATION_UPDATE = "ORGANIZATION_UPDATE"
PERM_ORGANIZATION_SECURITY_UPDATE = "ORGANIZATION_SECURITY_UPDATE"

# User Management & Lifecycle
PERM_USER_VIEW = "USER_VIEW"
PERM_USER_CREATE = "USER_CREATE"
PERM_USER_UPDATE = "USER_UPDATE"
PERM_USER_SUSPEND = "USER_SUSPEND"
PERM_USER_DELETE = "USER_DELETE"
PERM_USER_ROLE_ASSIGN = "USER_ROLE_ASSIGN"
PERM_USER_INVITE = "USER_INVITE"

# Agent Governance
PERM_AGENT_VIEW = "AGENT_VIEW"
PERM_AGENT_CREATE = "AGENT_CREATE"
PERM_AGENT_UPDATE = "AGENT_UPDATE"
PERM_AGENT_SUSPEND = "AGENT_SUSPEND"
PERM_AGENT_RESUME = "AGENT_RESUME"
PERM_AGENT_DELETE = "AGENT_DELETE"
PERM_AGENT_BUDGET_UPDATE = "AGENT_BUDGET_UPDATE"
PERM_AGENT_POLICY_UPDATE = "AGENT_POLICY_UPDATE"

# Policy Engine
PERM_POLICY_VIEW = "POLICY_VIEW"
PERM_POLICY_CREATE = "POLICY_CREATE"
PERM_POLICY_UPDATE = "POLICY_UPDATE"
PERM_POLICY_DELETE = "POLICY_DELETE"
PERM_POLICY_ENABLE = "POLICY_ENABLE"
PERM_POLICY_DISABLE = "POLICY_DISABLE"

# Decisions & Approvals
PERM_DECISION_VIEW = "DECISION_VIEW"
PERM_DECISION_CREATE = "DECISION_CREATE"
PERM_DECISION_REVIEW = "DECISION_REVIEW"
PERM_DECISION_APPROVE = "DECISION_APPROVE"
PERM_DECISION_REJECT = "DECISION_REJECT"

# Audit & Compliance
PERM_AUDIT_VIEW = "AUDIT_VIEW"
PERM_AUDIT_EXPORT = "AUDIT_EXPORT"

# Security Operations & Incidents
PERM_SECURITY_VIEW = "SECURITY_VIEW"
PERM_SECURITY_INCIDENT_CREATE = "SECURITY_INCIDENT_CREATE"
PERM_SECURITY_INCIDENT_UPDATE = "SECURITY_INCIDENT_UPDATE"
PERM_SECURITY_INCIDENT_RESOLVE = "SECURITY_INCIDENT_RESOLVE"

# Reports
PERM_REPORT_VIEW = "REPORT_VIEW"
PERM_REPORT_GENERATE = "REPORT_GENERATE"
PERM_REPORT_DOWNLOAD = "REPORT_DOWNLOAD"

# Webhooks
PERM_WEBHOOK_VIEW = "WEBHOOK_VIEW"
PERM_WEBHOOK_CREATE = "WEBHOOK_CREATE"
PERM_WEBHOOK_UPDATE = "WEBHOOK_UPDATE"
PERM_WEBHOOK_DELETE = "WEBHOOK_DELETE"
PERM_WEBHOOK_RETRY = "WEBHOOK_RETRY"

# Telemetry
PERM_TELEMETRY_VIEW = "TELEMETRY_VIEW"
PERM_TELEMETRY_EXPORT = "TELEMETRY_EXPORT"

# API Keys
PERM_API_KEY_VIEW = "API_KEY_VIEW"
PERM_API_KEY_CREATE = "API_KEY_CREATE"
PERM_API_KEY_REVOKE = "API_KEY_REVOKE"

# Platform Control Plane (SUPER_ADMIN only)
PERM_PLATFORM_VIEW = "PLATFORM_VIEW"
PERM_PLATFORM_ADMIN = "PLATFORM_ADMIN"

# ============================================================================
# 3. AUTHORITATIVE ROLE-PERMISSION MAPPINGS
# ============================================================================

ROLE_PERMISSIONS_MATRIX: Dict[str, Set[str]] = {
    ROLE_USER: {
        PERM_ORGANIZATION_VIEW,
        PERM_USER_VIEW,
        PERM_DECISION_CREATE,
        # Legacy mappings
        "dashboard:read",
        "profile:read",
        "profile:write",
    },
    ROLE_VIEWER: {
        PERM_ORGANIZATION_VIEW,
        PERM_USER_VIEW,
        PERM_AGENT_VIEW,
        PERM_POLICY_VIEW,
        PERM_DECISION_VIEW,
        PERM_AUDIT_VIEW,
        PERM_REPORT_VIEW,
        PERM_TELEMETRY_VIEW,
        # Legacy
        "dashboard:read",
        "profile:read",
        "agents:read",
        "analytics:read",
    },
    ROLE_ANALYST: {
        PERM_ORGANIZATION_VIEW,
        PERM_USER_VIEW,
        PERM_AGENT_VIEW,
        PERM_POLICY_VIEW,
        PERM_DECISION_VIEW,
        PERM_AUDIT_VIEW,
        PERM_AUDIT_EXPORT,
        PERM_REPORT_VIEW,
        PERM_REPORT_GENERATE,
        PERM_REPORT_DOWNLOAD,
        PERM_TELEMETRY_VIEW,
        PERM_TELEMETRY_EXPORT,
        PERM_SECURITY_VIEW,
        # Legacy
        "dashboard:read",
        "profile:read",
        "agents:read",
        "decisions:read",
        "risk:read",
        "audit:read",
        "provenance:read",
        "analytics:read",
    },
    ROLE_OPERATOR: {
        PERM_ORGANIZATION_VIEW,
        PERM_USER_VIEW,
        PERM_AGENT_VIEW,
        PERM_AGENT_SUSPEND,
        PERM_AGENT_RESUME,
        PERM_DECISION_VIEW,
        PERM_DECISION_CREATE,
        PERM_DECISION_REVIEW,
        PERM_TELEMETRY_VIEW,
        PERM_TELEMETRY_EXPORT,
        # Legacy
        "dashboard:read",
        "profile:read",
        "agents:read",
        "agents:manage",
        "capabilities:read",
        "capabilities:execute",
        "runtime:read",
    },
    ROLE_SECURITY_ANALYST: {
        PERM_ORGANIZATION_VIEW,
        PERM_USER_VIEW,
        PERM_AGENT_VIEW,
        PERM_AGENT_SUSPEND,
        PERM_AGENT_RESUME,
        PERM_POLICY_VIEW,
        PERM_DECISION_VIEW,
        PERM_AUDIT_VIEW,
        PERM_AUDIT_EXPORT,
        PERM_SECURITY_VIEW,
        PERM_SECURITY_INCIDENT_CREATE,
        PERM_SECURITY_INCIDENT_UPDATE,
        PERM_SECURITY_INCIDENT_RESOLVE,
        PERM_REPORT_VIEW,
        PERM_REPORT_GENERATE,
        PERM_REPORT_DOWNLOAD,
        PERM_TELEMETRY_VIEW,
        PERM_TELEMETRY_EXPORT,
        # Legacy
        "dashboard:read",
        "profile:read",
        "agents:read",
        "security:read",
        "security:write",
        "circuit_breaker:manage",
        "red_team:execute",
        "incidents:manage",
    },
    ROLE_MANAGER: {
        PERM_ORGANIZATION_VIEW,
        PERM_USER_VIEW,
        PERM_AGENT_VIEW,
        PERM_AGENT_BUDGET_UPDATE,
        PERM_POLICY_VIEW,
        PERM_DECISION_VIEW,
        PERM_DECISION_REVIEW,
        PERM_DECISION_APPROVE,
        PERM_DECISION_REJECT,
        PERM_REPORT_VIEW,
        PERM_REPORT_GENERATE,
        PERM_REPORT_DOWNLOAD,
        PERM_TELEMETRY_VIEW,
        # Legacy
        "dashboard:read",
        "profile:read",
        "agents:read",
        "approvals:read",
        "approvals:write",
        "budgets:read",
        "policies:read",
    },
    ROLE_DEVELOPER: {
        PERM_ORGANIZATION_VIEW,
        PERM_USER_VIEW,
        PERM_AGENT_VIEW,
        PERM_AGENT_CREATE,
        PERM_AGENT_UPDATE,
        PERM_AGENT_POLICY_UPDATE,
        PERM_POLICY_VIEW,
        PERM_POLICY_CREATE,
        PERM_POLICY_UPDATE,
        PERM_DECISION_VIEW,
        PERM_DECISION_CREATE,
        PERM_API_KEY_VIEW,
        PERM_API_KEY_CREATE,
        PERM_API_KEY_REVOKE,
        PERM_WEBHOOK_VIEW,
        PERM_WEBHOOK_CREATE,
        PERM_WEBHOOK_UPDATE,
        PERM_WEBHOOK_RETRY,
        PERM_TELEMETRY_VIEW,
        # Legacy
        "dashboard:read",
        "profile:read",
        "agents:read",
        "api_keys:read",
        "api_keys:write",
        "integrations:manage",
        "assistant:use",
    },
    ROLE_ADMIN: {
        # Tenant administrator with full org permissions
        PERM_ORGANIZATION_VIEW,
        PERM_ORGANIZATION_UPDATE,
        PERM_ORGANIZATION_SECURITY_UPDATE,
        PERM_USER_VIEW,
        PERM_USER_CREATE,
        PERM_USER_UPDATE,
        PERM_USER_SUSPEND,
        PERM_USER_DELETE,
        PERM_USER_ROLE_ASSIGN,
        PERM_USER_INVITE,
        PERM_AGENT_VIEW,
        PERM_AGENT_CREATE,
        PERM_AGENT_UPDATE,
        PERM_AGENT_SUSPEND,
        PERM_AGENT_RESUME,
        PERM_AGENT_DELETE,
        PERM_AGENT_BUDGET_UPDATE,
        PERM_AGENT_POLICY_UPDATE,
        PERM_POLICY_VIEW,
        PERM_POLICY_CREATE,
        PERM_POLICY_UPDATE,
        PERM_POLICY_DELETE,
        PERM_POLICY_ENABLE,
        PERM_POLICY_DISABLE,
        PERM_DECISION_VIEW,
        PERM_DECISION_CREATE,
        PERM_DECISION_REVIEW,
        PERM_DECISION_APPROVE,
        PERM_DECISION_REJECT,
        PERM_AUDIT_VIEW,
        PERM_AUDIT_EXPORT,
        PERM_SECURITY_VIEW,
        PERM_SECURITY_INCIDENT_CREATE,
        PERM_SECURITY_INCIDENT_UPDATE,
        PERM_SECURITY_INCIDENT_RESOLVE,
        PERM_REPORT_VIEW,
        PERM_REPORT_GENERATE,
        PERM_REPORT_DOWNLOAD,
        PERM_WEBHOOK_VIEW,
        PERM_WEBHOOK_CREATE,
        PERM_WEBHOOK_UPDATE,
        PERM_WEBHOOK_DELETE,
        PERM_WEBHOOK_RETRY,
        PERM_TELEMETRY_VIEW,
        PERM_TELEMETRY_EXPORT,
        PERM_API_KEY_VIEW,
        PERM_API_KEY_CREATE,
        PERM_API_KEY_REVOKE,
    },
    ROLE_SUPER_ADMIN: {
        "*",
        PERM_PLATFORM_VIEW,
        PERM_PLATFORM_ADMIN,
    },
    ROLE_AGENT: {
        PERM_DECISION_CREATE,
        PERM_TELEMETRY_VIEW,
    }
}

# ============================================================================
# 4. HIERARCHY & AUTHORIZATION UTILITIES
# ============================================================================

def get_role_level(role: str) -> int:
    """Returns the integer hierarchy level for a role (1 to 9). Unknown roles return 0."""
    return ROLE_LEVELS.get(role, 0)


def can_manage_role(actor_role: str, target_role: str) -> bool:
    """
    Checks if an actor is authorized to assign or modify target_role:
    1. SUPER_ADMIN can assign any role up to SUPER_ADMIN.
    2. Tenant ADMIN can assign roles up to ADMIN (levels 1-8), but NEVER SUPER_ADMIN.
    3. Actors below ADMIN cannot assign or manage roles.
    4. A user cannot assign a role higher than their own.
    """
    if actor_role == ROLE_SUPER_ADMIN:
        return True
    if target_role == ROLE_SUPER_ADMIN:
        return False
    actor_level = get_role_level(actor_role)
    target_level = get_role_level(target_role)
    if actor_level < ROLE_LEVELS[ROLE_ADMIN]:
        return False
    return actor_level >= target_level


def has_permission(user_role: str, permission: str) -> bool:
    """Evaluates whether user_role grants the specified permission."""
    if user_role == ROLE_SUPER_ADMIN:
        return True
    perms = ROLE_PERMISSIONS_MATRIX.get(user_role, set())
    return "*" in perms or permission in perms


def get_user_permissions(user_role: str) -> List[str]:
    """Returns the sorted list of permissions for a role."""
    return sorted(list(ROLE_PERMISSIONS_MATRIX.get(user_role, set())))
