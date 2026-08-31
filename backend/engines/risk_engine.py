from typing import Dict, Any

class RiskEngine:
    def calculate_risk(
        self,
        agent_autonomy: str,
        action: str,
        amount: float,
        daily_budget: float,
        behavior_deviation: float = 0.0,
        historical_violations: int = 0
    ) -> Dict[str, Any]:
        identity_risk = 5
        permission_risk = 10
        financial_risk = 0
        behavior_risk = int(behavior_deviation * 10)
        data_sensitivity_risk = 0
        
        if amount > 50000:
            financial_risk = 50
        elif amount > 25000:
            financial_risk = 35
        elif amount > 5000:
            financial_risk = 25
        elif amount > 0:
            financial_risk = 10
            
        if "delete" in action or "drop" in action:
            data_sensitivity_risk = 45
            permission_risk = 30
        elif "export" in action:
            data_sensitivity_risk = 30

        if agent_autonomy == "FULL":
            identity_risk += 15
        elif agent_autonomy == "HIGH":
            identity_risk += 10

        identity_risk += historical_violations * 5

        total_score = identity_risk + permission_risk + financial_risk + behavior_risk + data_sensitivity_risk
        total_score = min(max(total_score, 0), 100)

        if total_score <= 30:
            level = "LOW"
            color = "#2E9D50"
        elif total_score <= 60:
            level = "MEDIUM"
            color = "#F59A23"
        elif total_score <= 80:
            level = "HIGH"
            color = "#E76F32"
        else:
            level = "CRITICAL"
            color = "#E53935"

        return {
            "overall_score": total_score,
            "level": level,
            "color": color,
            "breakdown": {
                "identity_risk": identity_risk,
                "permission_risk": permission_risk,
                "financial_risk": financial_risk,
                "behavior_risk": behavior_risk,
                "data_sensitivity_risk": data_sensitivity_risk
            }
        }

risk_engine = RiskEngine()
