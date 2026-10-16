export const HUMAN_ROLE_LEVELS: Record<string, number> = {
  USER: 1,
  AUDITOR: 2,
  VIEWER: 2,
  ANALYST: 3,
  OPERATOR: 4,
  SECURITY_OFFICER: 5,
  SECURITY_ANALYST: 5,
  MANAGER: 6,
  DEVELOPER: 7,
  ADMIN: 8,
  SUPER_ADMIN: 9,
};

export const ROUTE_PERMISSIONS: Record<string, { roles: string[]; requiredPermission: string }> = {
  "/dashboard": {
    roles: ["USER", "AUDITOR", "VIEWER", "ANALYST", "OPERATOR", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "dashboard:read",
  },
  "/profile": {
    roles: ["USER", "AUDITOR", "VIEWER", "ANALYST", "OPERATOR", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "profile:read",
  },
  "/activity": {
    roles: ["USER", "AUDITOR", "VIEWER", "ANALYST", "OPERATOR", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "activity:read",
  },
  "/notifications": {
    roles: ["USER", "AUDITOR", "VIEWER", "ANALYST", "OPERATOR", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "notifications:read",
  },
  "/agents": {
    roles: ["USER", "AUDITOR", "VIEWER", "ANALYST", "OPERATOR", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "agents:read",
  },
  "/analytics": {
    roles: ["USER", "AUDITOR", "VIEWER", "ANALYST", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "analytics:read",
  },
  "/trust": {
    roles: ["AUDITOR", "VIEWER", "ANALYST", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "trust:read",
  },
  "/risk": {
    roles: ["AUDITOR", "VIEWER", "ANALYST", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "risk:read",
  },
  "/behavior": {
    roles: ["AUDITOR", "ANALYST", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "behavior:read",
  },
  "/decisions": {
    roles: ["AUDITOR", "ANALYST", "SECURITY_OFFICER", "MANAGER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "decisions:read",
  },
  "/simulation": {
    roles: ["AUDITOR", "ANALYST", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "simulation:read",
  },
  "/provenance": {
    roles: ["AUDITOR", "ANALYST", "SECURITY_OFFICER", "SECURITY_ANALYST", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "provenance:read",
  },
  "/audit": {
    roles: ["AUDITOR", "ANALYST", "SECURITY_OFFICER", "SECURITY_ANALYST", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "audit:read",
  },
  "/capabilities": {
    roles: ["OPERATOR", "DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "capabilities:read",
  },
  "/runtime": {
    roles: ["OPERATOR", "SECURITY_OFFICER", "SECURITY_ANALYST", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "runtime:read",
  },
  "/approvals": {
    roles: ["OPERATOR", "SECURITY_OFFICER", "MANAGER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "approvals:read",
  },
  "/agent-network": {
    roles: ["OPERATOR", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "agent_network:read",
  },
  "/security": {
    roles: ["SECURITY_OFFICER", "SECURITY_ANALYST", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "security:read",
  },
  "/red-team": {
    roles: ["SECURITY_OFFICER", "SECURITY_ANALYST", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "red_team:read",
  },
  "/policies": {
    roles: ["SECURITY_OFFICER", "MANAGER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "policies:read",
  },
  "/economics": {
    roles: ["MANAGER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "economics:read",
  },
  "/developers": {
    roles: ["DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "developers:read",
  },
  "/integrations": {
    roles: ["DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "integrations:read",
  },
  "/iam": {
    roles: ["ADMIN", "SUPER_ADMIN"],
    requiredPermission: "iam:manage",
  },
  "/organization": {
    roles: ["ADMIN", "SUPER_ADMIN"],
    requiredPermission: "organization:manage",
  },
  "/reports": {
    roles: ["USER", "AUDITOR", "VIEWER", "ANALYST", "OPERATOR", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "reports:read",
  },
  "/settings": {
    roles: ["USER", "AUDITOR", "VIEWER", "ANALYST", "OPERATOR", "SECURITY_OFFICER", "SECURITY_ANALYST", "MANAGER", "DEVELOPER", "ADMIN", "SUPER_ADMIN"],
    requiredPermission: "settings:read",
  },
  "/platform": {
    roles: ["SUPER_ADMIN"],
    requiredPermission: "platform:manage",
  },
};

export function hasRoutePermission(userRole: string, pathname: string): boolean {
  if (!userRole) return false;
  if (userRole === "SUPER_ADMIN") return true;

  // Match root prefix of pathname (e.g., /iam/users -> /iam)
  const matchedRouteKey = Object.keys(ROUTE_PERMISSIONS).find(
    (key) => pathname === key || pathname.startsWith(`${key}/`)
  );

  if (!matchedRouteKey) return true; // Unrestricted default route

  const rule = ROUTE_PERMISSIONS[matchedRouteKey];
  return rule.roles.includes(userRole);
}
