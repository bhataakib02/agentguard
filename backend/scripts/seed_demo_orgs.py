import sys
import os
import re
import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database import SessionLocal, engine, Base
from core import security
import models

def slugify(text_val: str) -> str:
    if not text_val:
        return "unnamed-org"
    clean = re.sub(r'[^a-zA-Z0-9]+', '-', text_val.strip()).lower().strip('-')
    return clean or "unnamed-org"

def seed_five_demo_organizations():
    db = SessionLocal()
    print("Starting provisioning of 5 real Multi-Tenant Demo Organizations...")

    pwd_hash = security.get_password_hash("Blackbird@12.")

    demo_orgs_data = [
        {
            "name": "Acme Financial Technologies",
            "display_name": "ACME FINTECH",
            "domain": "acmefintech.com",
            "industry": "Financial Services / FinTech",
            "admin_email": "admin@acmefintech.com",
            "plan_id": "ENTERPRISE",
            "max_users": 100,
            "max_agents": 20,
            "expiry_days": 365,
            "logo_url": "https://img.icons8.com/color/96/bank-building.png",
            "users": [
                {"email": "admin@acmefintech.com", "full_name": "Acme Admin", "role": "ADMIN", "dept": "Executive Management"},
                {"email": "finance.manager@acmefintech.com", "full_name": "Finance Manager", "role": "MANAGER", "dept": "Finance"},
                {"email": "sec.analyst@acmefintech.com", "full_name": "Security Officer", "role": "SECURITY_ANALYST", "dept": "InfoSec"},
                {"email": "compliance@acmefintech.com", "full_name": "Compliance Auditor", "role": "VIEWER", "dept": "Compliance"},
                {"email": "fin.analyst@acmefintech.com", "full_name": "Financial Analyst", "role": "ANALYST", "dept": "Analytics"},
                {"email": "operator@acmefintech.com", "full_name": "Operations Member", "role": "OPERATOR", "dept": "Operations"},
                {"email": "developer@acmefintech.com", "full_name": "Dev Member", "role": "DEVELOPER", "dept": "Engineering"},
                {"email": "user@acmefintech.com", "full_name": "Employee Member", "role": "USER", "dept": "General"},
            ],
            "agents": [
                {"name": "RefundAgent", "purpose": "Handle customer refund requests", "autonomy": "MEDIUM", "risk": 35},
                {"name": "FraudMonitorAgent", "purpose": "Detect suspicious financial transactions", "autonomy": "HIGH", "risk": 68},
                {"name": "FinanceAssistant", "purpose": "Financial operations assistance", "autonomy": "LOW", "risk": 15},
                {"name": "CustomerSupportAgent", "purpose": "Customer support response agent", "autonomy": "MEDIUM", "risk": 25},
            ],
            "policies": [
                {"name": "Refund Auto Approval Limit", "type": "RESOURCE", "rule": "Refund requests under ₹5,000 auto-approved; over ₹50,000 refused"},
                {"name": "High Value Transaction Review", "type": "ACTION", "rule": "Transactions over ₹40,000 require human manager approval"},
                {"name": "Sensitive Financial Data Access", "type": "DATA", "rule": "Restrict account number disclosure"},
            ]
        },
        {
            "name": "NovaCare Health Systems",
            "display_name": "NOVACARE",
            "domain": "novacarehealth.org",
            "industry": "Healthcare Technology",
            "admin_email": "admin@novacarehealth.org",
            "plan_id": "PROFESSIONAL",
            "max_users": 50,
            "max_agents": 15,
            "expiry_days": 270,
            "logo_url": "https://img.icons8.com/color/96/caduceus.png",
            "users": [
                {"email": "admin@novacarehealth.org", "full_name": "Healthcare Administrator", "role": "ADMIN", "dept": "Hospital Admin"},
                {"email": "ops.manager@novacarehealth.org", "full_name": "Operations Manager", "role": "MANAGER", "dept": "Operations"},
                {"email": "sec.analyst@novacarehealth.org", "full_name": "HIPAA Security Officer", "role": "SECURITY_ANALYST", "dept": "Cybersecurity"},
                {"email": "compliance@novacarehealth.org", "full_name": "Compliance Auditor", "role": "VIEWER", "dept": "Regulatory Affairs"},
                {"email": "data.analyst@novacarehealth.org", "full_name": "Clinical Data Analyst", "role": "ANALYST", "dept": "Health Informatics"},
                {"email": "dev@novacarehealth.org", "full_name": "EHR Software Developer", "role": "DEVELOPER", "dept": "Software Engineering"},
                {"email": "operator@novacarehealth.org", "full_name": "Healthcare Operator", "role": "OPERATOR", "dept": "Clinical Ops"},
                {"email": "user@novacarehealth.org", "full_name": "Staff User", "role": "USER", "dept": "General Staff"},
            ],
            "agents": [
                {"name": "AppointmentAgent", "purpose": "Manage patient appointment scheduling", "autonomy": "MEDIUM", "risk": 20},
                {"name": "PatientSupportAgent", "purpose": "Answer general patient-support questions", "autonomy": "LOW", "risk": 12},
                {"name": "OperationsAgent", "purpose": "Assist hospital operational planning", "autonomy": "MEDIUM", "risk": 30},
                {"name": "SecurityMonitorAgent", "purpose": "Detect abnormal patient record access", "autonomy": "HIGH", "risk": 55},
            ],
            "policies": [
                {"name": "Patient Data Privacy Policy", "type": "DATA", "rule": "Enforce strict HIPAA data access controls"},
                {"name": "Appointment Reschedule Guard", "type": "ACTION", "rule": "Prevent double-booking patient slots"},
            ]
        },
        {
            "name": "Vertex Manufacturing Industries",
            "display_name": "VERTEX INDUSTRIES",
            "domain": "vertexmfg.com",
            "industry": "Manufacturing",
            "admin_email": "admin@vertexmfg.com",
            "plan_id": "ENTERPRISE",
            "max_users": 200,
            "max_agents": 30,
            "expiry_days": 540,
            "logo_url": "https://img.icons8.com/color/96/factory.png",
            "users": [
                {"email": "admin@vertexmfg.com", "full_name": "Plant Administrator", "role": "ADMIN", "dept": "Plant Operations"},
                {"email": "prod.manager@vertexmfg.com", "full_name": "Production Manager", "role": "MANAGER", "dept": "Manufacturing"},
                {"email": "sec.officer@vertexmfg.com", "full_name": "Industrial Security Officer", "role": "SECURITY_ANALYST", "dept": "Safety & Sec"},
                {"email": "compliance@vertexmfg.com", "full_name": "Compliance Auditor", "role": "VIEWER", "dept": "Quality Control"},
                {"email": "prod.analyst@vertexmfg.com", "full_name": "Production Analyst", "role": "ANALYST", "dept": "Supply Chain Analytics"},
                {"email": "operator@vertexmfg.com", "full_name": "Runtime Machine Operator", "role": "OPERATOR", "dept": "Assembly Operations"},
                {"email": "dev@vertexmfg.com", "full_name": "IoT Platform Developer", "role": "DEVELOPER", "dept": "Automation Tech"},
                {"email": "user@vertexmfg.com", "full_name": "Factory Staff Employee", "role": "USER", "dept": "General Ops"},
            ],
            "agents": [
                {"name": "InventoryAgent", "purpose": "Track raw material inventory levels", "autonomy": "HIGH", "risk": 40},
                {"name": "ProductionPlannerAgent", "purpose": "Optimize factory line throughput", "autonomy": "MEDIUM", "risk": 30},
                {"name": "EquipmentMonitorAgent", "purpose": "Detect machine breakdown alerts", "autonomy": "HIGH", "risk": 45},
                {"name": "SupplyChainAgent", "purpose": "Reorder depleted production stock", "autonomy": "MEDIUM", "risk": 35},
                {"name": "MaintenanceAssistant", "purpose": "Assist assembly line maintenance", "autonomy": "LOW", "risk": 15},
            ],
            "policies": [
                {"name": "Equipment Thermal Override Limit", "type": "RESOURCE", "rule": "Refuse motor operation over 85°C"},
                {"name": "Automated Stock Order Approval", "type": "ACTION", "rule": "Reorders under $10,000 auto-approved"},
            ]
        },
        {
            "name": "Orbit Retail & Commerce",
            "display_name": "ORBIT RETAIL",
            "domain": "orbitretail.com",
            "industry": "Retail / E-Commerce",
            "admin_email": "admin@orbitretail.com",
            "plan_id": "STARTER",
            "max_users": 75,
            "max_agents": 15,
            "expiry_days": 180,
            "logo_url": "https://img.icons8.com/color/96/shopping-bag.png",
            "users": [
                {"email": "admin@orbitretail.com", "full_name": "Retail Administrator", "role": "ADMIN", "dept": "Executive Office"},
                {"email": "store.manager@orbitretail.com", "full_name": "Store Operations Manager", "role": "MANAGER", "dept": "Retail Operations"},
                {"email": "sec.analyst@orbitretail.com", "full_name": "E-Commerce Security Analyst", "role": "SECURITY_ANALYST", "dept": "Fraud & Security"},
                {"email": "compliance@orbitretail.com", "full_name": "Compliance Auditor", "role": "VIEWER", "dept": "Audit & Risk"},
                {"email": "biz.analyst@orbitretail.com", "full_name": "Retail Business Analyst", "role": "ANALYST", "dept": "Merchandising"},
                {"email": "operator@orbitretail.com", "full_name": "Fulfillment Operator", "role": "OPERATOR", "dept": "Fulfillment Center"},
                {"email": "dev@orbitretail.com", "full_name": "Store Frontend Developer", "role": "DEVELOPER", "dept": "Tech Team"},
                {"email": "user@orbitretail.com", "full_name": "Store Associate", "role": "USER", "dept": "Sales Operations"},
            ],
            "agents": [
                {"name": "OrderAgent", "purpose": "Process customer checkout orders", "autonomy": "HIGH", "risk": 25},
                {"name": "RecommendationAgent", "purpose": "Serve personalized shopping offers", "autonomy": "FULL", "risk": 10},
                {"name": "InventoryAgent", "purpose": "Manage regional catalog stock", "autonomy": "HIGH", "risk": 30},
                {"name": "CustomerSupportAgent", "purpose": "Handle customer order inquiries", "autonomy": "MEDIUM", "risk": 20},
                {"name": "FraudDetectionAgent", "purpose": "Flag stolen card checkout attempts", "autonomy": "HIGH", "risk": 60},
            ],
            "policies": [
                {"name": "Chargeback Protection Guard", "type": "SECURITY", "rule": "Refuse orders with high velocity risk score"},
                {"name": "Promotional Discount Limit", "type": "RESOURCE", "rule": "Limit coupon application to 25% max"},
            ]
        },
        {
            "name": "Skyline Logistics & Mobility",
            "display_name": "SKYLINE LOGISTICS",
            "domain": "skylinelogistics.io",
            "industry": "Logistics / Transportation",
            "admin_email": "admin@skylinelogistics.io",
            "plan_id": "STARTER",
            "max_users": 30,
            "max_agents": 10,
            "expiry_days": 90,
            "logo_url": "https://img.icons8.com/color/96/delivery-truck.png",
            "users": [
                {"email": "admin@skylinelogistics.io", "full_name": "Logistics Administrator", "role": "ADMIN", "dept": "Fleet Leadership"},
                {"email": "ops.manager@skylinelogistics.io", "full_name": "Operations Manager", "role": "MANAGER", "dept": "Dispatch Center"},
                {"email": "sec.analyst@skylinelogistics.io", "full_name": "Fleet Security Analyst", "role": "SECURITY_ANALYST", "dept": "Safety & Sec"},
                {"email": "compliance@skylinelogistics.io", "full_name": "Compliance Auditor", "role": "VIEWER", "dept": "DOT Compliance"},
                {"email": "log.analyst@skylinelogistics.io", "full_name": "Logistics Analyst", "role": "ANALYST", "dept": "Route Analytics"},
                {"email": "operator@skylinelogistics.io", "full_name": "Fleet Dispatch Operator", "role": "OPERATOR", "dept": "Fleet Dispatch"},
                {"email": "dev@skylinelogistics.io", "full_name": "Telematics Developer", "role": "DEVELOPER", "dept": "IoT Dev"},
                {"email": "user@skylinelogistics.io", "full_name": "Logistics Employee", "role": "USER", "dept": "General Fleet"},
            ],
            "agents": [
                {"name": "RoutePlannerAgent", "purpose": "Optimize long-haul delivery routes", "autonomy": "HIGH", "risk": 35},
                {"name": "FleetMonitorAgent", "purpose": "Monitor truck speed and fuel efficiency", "autonomy": "HIGH", "risk": 40},
                {"name": "DeliveryAgent", "purpose": "Coordinate last-mile parcel drops", "autonomy": "MEDIUM", "risk": 20},
                {"name": "DemandForecastAgent", "purpose": "Predict weekly freight demand", "autonomy": "MEDIUM", "risk": 15},
            ],
            "policies": [
                {"name": "Driver Rest Hour Compliance Policy", "type": "ACTION", "rule": "Enforce mandatory 8-hour rest intervals"},
                {"name": "Hazardous Material Route Exclusion", "type": "DATA", "rule": "Reroute hazmat trucks away from urban tunnels"},
            ]
        }
    ]

    for item in demo_orgs_data:
        # 1. Create Organization
        target_slug = slugify(item["name"])
        org = db.query(models.Organization).filter(
            (models.Organization.slug == target_slug) | (models.Organization.name == item["name"])
        ).first()
        if not org:
            org = models.Organization(
                name=item["name"],
                slug=target_slug,
                display_name=item["display_name"],
                domain=item["domain"],
                status="ACTIVE",
                admin_email=item["admin_email"],
                logo_url=item["logo_url"]
            )
            db.add(org)
            db.commit()
            db.refresh(org)
        else:
            org.slug = target_slug
            org.display_name = item["display_name"]
            org.logo_url = item["logo_url"]
            db.commit()

        # 2. License Setup
        lic = db.query(models.License).filter(models.License.org_id == org.id).first()
        if not lic:
            lic = models.License(
                org_id=org.id,
                plan_id=item["plan_id"],
                status="ACTIVE",
                start_date=datetime.datetime.utcnow(),
                expiry_date=datetime.datetime.utcnow() + datetime.timedelta(days=item["expiry_days"]),
                max_users=item["max_users"],
                max_ai_agents=item["max_agents"],
                max_api_keys=10,
                max_monthly_api_requests=1000000
            )
            db.add(lic)

            lic_usage = models.LicenseUsage(
                org_id=org.id,
                api_requests_count=1240,
                storage_used_gb=1.2
            )
            db.add(lic_usage)
            db.commit()

        # 3. Seed Human Users (8 per organization)
        admin_user = None
        for udata in item["users"]:
            existing_user = db.query(models.User).filter(models.User.email == udata["email"]).first()
            if not existing_user:
                existing_user = models.User(
                    org_id=org.id,
                    email=udata["email"],
                    full_name=udata["full_name"],
                    role=udata["role"],
                    department=udata["dept"],
                    password_hash=pwd_hash,
                    status="ACTIVE"
                )
                db.add(existing_user)
                db.commit()
                db.refresh(existing_user)

            if udata["role"] == "ADMIN":
                admin_user = existing_user

        # 4. Seed AI Agents, Passports, and Capability Tokens
        for idx, adata in enumerate(item["agents"]):
            existing_agent = db.query(models.Agent).filter(
                models.Agent.org_id == org.id,
                models.Agent.name == adata["name"]
            ).first()

            passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == existing_agent.id).first()
            if not passport:
                passport = models.AgentPassport(
                    agent_id=existing_agent.id,
                    passport_number=f"PSP-{str(existing_agent.id)[:8].upper()}",
                    digital_signature=f"SIG-{str(existing_agent.id)[:12]}",
                    expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
                    verification_status="VERIFIED"
                )
                db.add(passport)

            token = db.query(models.CapabilityToken).filter(models.CapabilityToken.agent_id == existing_agent.id).first()
            if not token:
                token = models.CapabilityToken(
                    token_code=f"CAP-{str(existing_agent.id)[:8].upper()}",
                    agent_id=existing_agent.id,
                    capability_name="read_and_execute",
                    scope=f"org={org.name[:10]}",
                    amount_limit=10000.0,
                    expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=180),
                    status="ACTIVE"
                )
                db.add(token)

                # Demo Decision Records
                dec = models.Decision(
                    agent_id=existing_agent.id,
                    intent_summary=f"Automated action by {existing_agent.name}",
                    action_requested="EXECUTE_ACTION",
                    resource_target=adata["purpose"],
                    amount=5000.0,
                    decision="ALLOW" if existing_agent.risk_score < 40 else ("REVIEW" if existing_agent.risk_score < 60 else "REFUSE"),
                    risk_score=existing_agent.risk_score,
                    explanation=f"Risk evaluation score {existing_agent.risk_score} under tenant policy",
                    execution_status="EXECUTED"
                )
                db.add(dec)
        db.commit()

        # 5. Seed Policies
        for pdata in item["policies"]:
            pol = db.query(models.Policy).filter(
                models.Policy.org_id == org.id,
                models.Policy.name == pdata["name"]
            ).first()
            if not pol:
                pol = models.Policy(
                    org_id=org.id,
                    name=pdata["name"],
                    category=pdata["type"],
                    status="ACTIVE"
                )
                db.add(pol)
                db.commit()
                db.refresh(pol)

                rule = models.PolicyRule(
                    policy_id=pol.id,
                    condition_expression=pdata["rule"],
                    decision_output="ALLOW" if "approved" in pdata["rule"] else "REVIEW",
                    risk_delta=15,
                    description=pdata["rule"]
                )
                db.add(rule)
        db.commit()

        # 6. Audit Log Entry
        audit = models.AuditLog(
            event_type="DEMO_TENANT_PROVISIONED",
            actor_type="SYSTEM",
            actor_id="SUPER_ADMIN",
            action=f"Provisioned demo multi-tenant organization {org.name} ({item['display_name']})",
            resource="organizations",
            result="SUCCESS",
            metadata_json={"org_id": str(org.id), "users_count": 8, "agents_count": len(item["agents"])}
        )
        db.add(audit)
        db.commit()

    db.close()
    print("SUCCESS: Provisioned 5 real Multi-Tenant Demo Organizations in PostgreSQL database!")

if __name__ == "__main__":
    seed_five_demo_organizations()
