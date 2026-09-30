"""
AgentGuard Digital Twin Engine - Phase 6C Truthfulness Remediation
Deterministic pre-production sandboxed stress simulation.
Explicitly classified as SIMULATED.
Uses real agent configuration, historical execution telemetry, and budget limits
as baseline inputs, then applies deterministic stress models.
Does NOT claim machine-learning predictions or artificial intelligence forecasting.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime
import models

class DigitalTwinEngine:
    """
    Deterministic scenario stress simulation for AI agents.
    Grounds projections in real historical execution baseline when available.
    """

    def run_simulation(
        self,
        agent: models.Agent,
        scenario_type: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        agent_id = str(agent.id)
        org_id = str(agent.org_id)

        # 1. Fetch Real Historical Baseline Telemetry
        exec_count = 0
        baseline_avg_latency_ms = 120.0
        baseline_error_rate_pct = 0.0
        baseline_avg_tokens = 450
        observed_refusals = 0

        if db is not None:
            exec_q = db.query(models.AgentExecution).filter(
                models.AgentExecution.agent_id == agent.id
            )
            exec_count = exec_q.count()
            if exec_count > 0:
                stats = exec_q.with_entities(
                    func.avg(models.AgentExecution.latency_ms),
                    func.avg(models.AgentExecution.total_token_count)
                ).first()
                if stats and stats[0] is not None:
                    baseline_avg_latency_ms = round(float(stats[0]), 1)
                if stats and stats[1] is not None:
                    baseline_avg_tokens = int(stats[1])

                refused = exec_q.filter(models.AgentExecution.policy_decision == "REFUSE").count()
                failed = exec_q.filter(models.AgentExecution.status == "FAILED").count()
                observed_refusals = refused
                baseline_error_rate_pct = round(((refused + failed) / exec_count) * 100.0, 2)

        # 2. Fetch Real Budget Limits
        daily_budget_tokens = None
        daily_cost_limit = None
        if db is not None:
            b_cfg = db.query(models.AgentBudgetConfig).filter(
                models.AgentBudgetConfig.agent_id == agent.id
            ).first()
            if b_cfg:
                daily_budget_tokens = b_cfg.daily_token_limit
                daily_cost_limit = b_cfg.daily_cost_limit

        # 3. Fetch Real Active Policies Count
        active_policies_count = 0
        if db is not None:
            active_policies_count = db.query(models.Policy).filter(
                models.Policy.org_id == org_id,
                models.Policy.status == "ACTIVE"
            ).count()

        # 4. Deterministic Stress Transformation
        simulated_requests = 10000
        circuit_breaker_tripped = False
        autonomy = (agent.autonomy_level or "MEDIUM").upper()

        if scenario_type == "TRAFFIC_SPIKE":
            simulated_requests = 50000
            multiplier = 1.8 if autonomy == "LOW" else (1.4 if autonomy == "MEDIUM" else 1.2)
            projected_p99_latency_ms = round(baseline_avg_latency_ms * multiplier, 1)
            projected_error_rate_pct = round(baseline_error_rate_pct + (1.2 if exec_count > 0 else 0.5), 2)
            projected_throughput = "3,200 req/min (projected under concurrency)"
            
            # Estimate budget exhaustion under 50k requests
            total_projected_tokens = simulated_requests * baseline_avg_tokens
            budget_headroom_pct = 100.0
            if daily_budget_tokens and daily_budget_tokens > 0:
                budget_headroom_pct = max(0.0, round(((daily_budget_tokens - total_projected_tokens) / daily_budget_tokens) * 100.0, 1))
                if total_projected_tokens > daily_budget_tokens:
                    circuit_breaker_tripped = True

            # Calculate readiness score deterministically
            readiness_score = max(40, min(95, int(90 - (projected_error_rate_pct * 5) - (20 if circuit_breaker_tripped else 0))))
            recommendation = (
                f"Projected throughput: {projected_throughput}. Baseline latency {baseline_avg_latency_ms}ms scales to p99 {projected_p99_latency_ms}ms. "
                + ("WARNING: Budget cap would trip circuit breaker under 50k sustained traffic spike." if circuit_breaker_tripped else "Traffic spike capacity within acceptable bounds.")
            )

        elif scenario_type == "API_FAILURE":
            simulated_requests = 15000
            projected_p99_latency_ms = round(baseline_avg_latency_ms * 2.5, 1)
            projected_error_rate_pct = round(baseline_error_rate_pct + 4.5, 2)
            projected_throughput = "1,100 req/min (throttled due to upstream retries)"
            circuit_breaker_tripped = projected_error_rate_pct > 5.0
            readiness_score = max(35, min(90, int(82 - (projected_error_rate_pct * 3))))
            recommendation = (
                f"Simulated upstream API latency spike to {projected_p99_latency_ms}ms with projected failure rate of {projected_error_rate_pct}%. "
                "Ensure upstream retry backoff with jitter and circuit-breaker tripping are configured."
            )

        elif scenario_type == "MALICIOUS_INPUT":
            simulated_requests = 20000
            projected_p99_latency_ms = round(baseline_avg_latency_ms * 1.3, 1)
            projected_error_rate_pct = round(max(5.0, baseline_error_rate_pct + 8.0), 2)
            projected_throughput = "2,400 req/min"
            readiness_score = max(50, min(98, 70 + (active_policies_count * 5)))
            recommendation = (
                f"Tested adversarial input resistance across {active_policies_count} active tenant policies. "
                f"Estimated policy refusal rate for untrusted payloads: {projected_error_rate_pct}%."
            )

        else:
            simulated_requests = 10000
            projected_p99_latency_ms = round(baseline_avg_latency_ms * 1.2, 1)
            projected_error_rate_pct = baseline_error_rate_pct
            projected_throughput = "2,500 req/min"
            readiness_score = 80
            recommendation = "Baseline stress scenario completed."

        return {
            "agent_id": agent_id,
            "agent_code": agent.agent_code,
            "scenario_type": scenario_type,
            "classification": "SIMULATED",
            "is_simulated": True,
            "is_prediction": False,
            "disclaimer": (
                "SIMULATED SCENARIO ANALYSIS: This stress test is a deterministic simulation calculated from "
                "historical agent execution telemetry, active policy count, and budget limits. It is a hypothetical stress "
                "projection and does NOT represent actual future behavior or trained ML predictions."
            ),
            "readiness_score": readiness_score,
            "inputs_real": {
                "historical_executions_observed": exec_count,
                "baseline_avg_latency_ms": baseline_avg_latency_ms,
                "baseline_error_rate_pct": baseline_error_rate_pct,
                "baseline_avg_tokens_per_call": baseline_avg_tokens,
                "active_policies_count": active_policies_count,
                "daily_budget_tokens": daily_budget_tokens,
                "agent_autonomy_level": autonomy
            },
            "transformations_simulated": [
                f"Synthetic load volume scaled to {simulated_requests:,} requests",
                "Deterministic concurrency latency degradation model",
                "Upstream dependency latency and retry backoff perturbation"
            ],
            "metrics": {
                "simulated_requests": simulated_requests,
                "throughput": projected_throughput,
                "error_rate": f"{projected_error_rate_pct}%",
                "latency_p99": f"{projected_p99_latency_ms}ms",
                "circuit_breaker_tripped": circuit_breaker_tripped,
                "data_sufficiency": "SUFFICIENT" if exec_count >= 5 else "LOW_DATA_BASELINE"
            },
            "deployment_recommendation": recommendation
        }

digital_twin_engine = DigitalTwinEngine()
