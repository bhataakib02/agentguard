"""
AgentGuard Behavioral Anomaly Detection Engine
Tracks autonomous agent execution velocity, operating hours compliance,
allowed tool constraints, and financial spending baselines to detect statistical deviations.
"""

import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import models

class BehaviorEngine:
    """
    Statistical Behavioral Anomaly Detector.
    Evaluates real runtime telemetry against agent behavior baselines.
    """

    @staticmethod
    def get_or_create_profile(agent: models.Agent, db: Session) -> models.BehaviorProfile:
        """Retrieves or initializes baseline behavior profile for an agent."""
        profile = db.query(models.BehaviorProfile).filter(
            models.BehaviorProfile.agent_id == agent.id
        ).first()

        if not profile:
            profile = models.BehaviorProfile(
                agent_id=agent.id,
                avg_daily_actions=150,
                normal_operating_hours="09:00 - 18:00",
                allowed_tools_json=[],
                baseline_spending=2500.0,
                updated_at=datetime.datetime.utcnow()
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)

        return profile

    @staticmethod
    def is_within_operating_hours(
        operating_hours_str: Optional[str],
        check_time: Optional[datetime.datetime] = None
    ) -> bool:
        """
        Parses operating hours string e.g. '09:00 - 18:00' and verifies if check_time
        (default UTC now) falls within the window.
        """
        if not operating_hours_str or "-" not in operating_hours_str:
            return True  # 24/7 or unrestricted if not specified

        try:
            parts = operating_hours_str.split("-")
            start_str = parts[0].strip()
            end_str = parts[1].strip()

            start_h, start_m = [int(x) for x in start_str.split(":")]
            end_h, end_m = [int(x) for x in end_str.split(":")]

            now = check_time or datetime.datetime.utcnow()
            curr_minutes = now.hour * 60 + now.minute
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m

            if start_minutes <= end_minutes:
                return start_minutes <= curr_minutes <= end_minutes
            else:
                # Spans midnight e.g. 22:00 - 06:00
                return curr_minutes >= start_minutes or curr_minutes <= end_minutes
        except Exception:
            return True

    def evaluate_behavior(
        self,
        agent: models.Agent,
        db: Session,
        tool_name: Optional[str] = None,
        requested_amount: float = 0.0,
        persist_anomalies: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluates real agent telemetry and current invocation against historical baseline.
        Returns aggregate deviation score, list of anomalies, and telemetry metrics.
        """
        profile = self.get_or_create_profile(agent, db)
        now = datetime.datetime.utcnow()
        twenty_four_hours_ago = now - datetime.timedelta(hours=24)

        anomalies_detected: List[Dict[str, Any]] = []
        deviation_score = 0.0

        # 1. Action Velocity Check (Last 24 Hours)
        exec_count = db.query(models.AgentExecution).filter(
            models.AgentExecution.agent_id == agent.id,
            models.AgentExecution.timestamp >= twenty_four_hours_ago
        ).count()

        avg_actions = max(profile.avg_daily_actions or 150, 1)
        velocity_ratio = exec_count / avg_actions

        if velocity_ratio >= 3.0:
            severity = "CRITICAL" if velocity_ratio >= 5.0 else "HIGH"
            dev = min(4.0, (velocity_ratio - 1.0) * 1.0)
            deviation_score += dev
            anomalies_detected.append({
                "anomaly_type": "VELOCITY_SPIKE",
                "severity": severity,
                "description": f"Execution velocity exceeded baseline by {velocity_ratio:.1f}x ({exec_count} executions in 24h vs baseline {avg_actions}).",
                "deviation_score": round(dev, 2)
            })
        elif velocity_ratio >= 1.75:
            dev = 1.5
            deviation_score += dev
            anomalies_detected.append({
                "anomaly_type": "VELOCITY_SPIKE",
                "severity": "MEDIUM",
                "description": f"Elevated execution velocity ({exec_count} executions in 24h vs baseline {avg_actions}).",
                "deviation_score": dev
            })

        # 2. Operating Hours Compliance Check
        within_hours = self.is_within_operating_hours(profile.normal_operating_hours, now)
        if not within_hours:
            dev = 2.0
            deviation_score += dev
            anomalies_detected.append({
                "anomaly_type": "OFF_HOURS_ACTIVITY",
                "severity": "MEDIUM",
                "description": f"Agent activity detected outside normal operating hours ({profile.normal_operating_hours}). Current UTC time: {now.strftime('%H:%M')}.",
                "deviation_score": dev
            })

        # 3. Tool Usage Compliance Check
        allowed_tools = profile.allowed_tools_json or []
        tool_allowed = True
        if allowed_tools and tool_name:
            if tool_name not in allowed_tools:
                tool_allowed = False
                dev = 3.5
                deviation_score += dev
                anomalies_detected.append({
                    "anomaly_type": "UNAUTHORIZED_TOOL",
                    "severity": "HIGH",
                    "description": f"Target tool '{tool_name}' is not in agent's allowed behavior profile: {allowed_tools}.",
                    "deviation_score": dev
                })

        # 4. Spending Baseline Spike Check
        # Query total spend today from AgentExecution
        daily_executions = db.query(models.AgentExecution).filter(
            models.AgentExecution.agent_id == agent.id,
            models.AgentExecution.timestamp >= twenty_four_hours_ago
        ).all()
        current_spend = sum(e.estimated_cost or 0.0 for e in daily_executions) + requested_amount
        baseline_spending = profile.baseline_spending or 2500.0

        if baseline_spending > 0 and current_spend > (baseline_spending * 2.5):
            dev = 3.0
            deviation_score += dev
            anomalies_detected.append({
                "anomaly_type": "SPENDING_ANOMALY",
                "severity": "HIGH",
                "description": f"Daily expenditure ({current_spend:.2f}) significantly exceeds baseline spending ({baseline_spending:.2f}).",
                "deviation_score": dev
            })

        # 5. Error / Failure Rate Spike Check
        recent_executions = db.query(models.AgentExecution).filter(
            models.AgentExecution.agent_id == agent.id
        ).order_by(models.AgentExecution.timestamp.desc()).limit(15).all()

        if len(recent_executions) >= 5:
            failures = sum(1 for e in recent_executions if e.outcome in ("BLOCKED", "ERROR", "REFUSE"))
            fail_rate = failures / len(recent_executions)
            if fail_rate >= 0.5:
                dev = 2.5
                deviation_score += dev
                anomalies_detected.append({
                    "anomaly_type": "HIGH_REFUSAL_RATE",
                    "severity": "HIGH",
                    "description": f"Recent execution failure/refusal rate reached {fail_rate * 100:.0f}% ({failures}/{len(recent_executions)}).",
                    "deviation_score": dev
                })

        # Final capped deviation score [0.0, 10.0]
        final_deviation = min(round(deviation_score, 2), 10.0)

        # Persist anomalies to database if requested
        if persist_anomalies and anomalies_detected:
            for anom in anomalies_detected:
                event = models.AnomalyEvent(
                    agent_id=agent.id,
                    anomaly_type=anom["anomaly_type"],
                    severity=anom["severity"],
                    description=anom["description"],
                    deviation_score=anom["deviation_score"],
                    timestamp=now
                )
                db.add(event)

            # If high or critical severity, record a RuntimeRiskSignal
            has_high_or_crit = any(a["severity"] in ("HIGH", "CRITICAL") for a in anomalies_detected)
            if has_high_or_crit:
                signal = models.RuntimeRiskSignal(
                    org_id=agent.org_id,
                    agent_id=agent.id,
                    signal_type="BEHAVIORAL_ANOMALY",
                    severity="HIGH",
                    title=f"Behavioral Anomaly Detected for {agent.agent_code}",
                    description=anomalies_detected[0]["description"],
                    evidence_json={
                        "anomalies": anomalies_detected,
                        "deviation_score": final_deviation,
                        "velocity_ratio": round(velocity_ratio, 2)
                    },
                    status="ACTIVE",
                    timestamp=now
                )
                db.add(signal)

            db.commit()

        return {
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "deviation_score": final_deviation,
            "is_anomalous": len(anomalies_detected) > 0,
            "anomalies_count": len(anomalies_detected),
            "anomalies": anomalies_detected,
            "metrics": {
                "executions_24h": exec_count,
                "avg_daily_actions": avg_actions,
                "velocity_ratio": round(velocity_ratio, 2),
                "is_within_operating_hours": within_hours,
                "operating_hours": profile.normal_operating_hours,
                "tool_allowed": tool_allowed,
                "allowed_tools": allowed_tools,
                "current_spend": round(current_spend, 2),
                "baseline_spending": baseline_spending
            }
        }


behavior_engine = BehaviorEngine()
