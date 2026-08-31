from typing import Dict, Any, List

class ModelRouterEngine:
    def select_model(self, task_complexity: str = "HIGH") -> List[Dict[str, Any]]:
        return [
            {
                "model_name": "gpt-4o",
                "provider": "OpenAI",
                "tier": "FLAGSHIP",
                "avg_latency": "320ms",
                "cost_index": "MEDIUM",
                "recommended_for": "Complex reasoning, high-value financial actions"
            },
            {
                "model_name": "claude-3-5-sonnet",
                "provider": "Anthropic",
                "tier": "FLAGSHIP",
                "avg_latency": "290ms",
                "cost_index": "MEDIUM",
                "recommended_for": "Code generation, complex policy analysis"
            },
            {
                "model_name": "gemini-1.5-pro",
                "provider": "Google",
                "tier": "BALANCED",
                "avg_latency": "240ms",
                "cost_index": "LOW",
                "recommended_for": "High-throughput log analysis, long-context audit"
            }
        ]

model_router_engine = ModelRouterEngine()
