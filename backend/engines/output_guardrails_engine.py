"""
AI Output Governance & Safety Guardrails Engine for AgentGuard.
Detects toxicity, violent threats, harmful instructions, and factual hallucinations / ungrounded claims
in LLM and downstream tool outputs prior to client rendering or downstream API persistence.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("agentguard.output_guardrails")

# Compiled Toxicity and Safety Heuristics
TOXICITY_CATEGORIES = {
    "HATE_SPEECH": [
        r"\b(racial|ethnic|religious)\s+slur\b",
        r"\bhate\s+speech\b",
        r"\bexterminate\s+(all\s+)?(people|groups|races)\b",
        r"\bsubhuman\b",
        r"\bwhite\s+supremacy\b",
        r"\bethnic\s+cleansing\b",
    ],
    "VIOLENCE_AND_THREATS": [
        r"\bkill\s+(yourself|them|all\s+of\s+them)\b",
        r"\bassassinate\b",
        r"\bcommit\s+suicide\b",
        r"\bbomb\s+(threat|threats|making)\b",
        r"\bdetonate\s+an?\s+explosive\b",
        r"\bphysical(ly)?\s+attack\b",
        r"\bi\s+will\s+(murder|kill|destroy)\s+you\b",
    ],
    "HARMFUL_INSTRUCTIONS": [
        r"\bhow\s+to\s+build\s+a\s+bomb\b",
        r"\bhow\s+to\s+synthesize\s+(ricin|anthrax|sarin)\b",
        r"\bexploit\s+code\s+for\s+cve-\d{4}-\d+\b",
        r"\bransomware\s+payload\s+script\b",
        r"\bbypass\s+edr\s+using\s+mimikatz\b",
        r"\bhow\s+to\s+poison\s+(water|food)\b",
    ],
    "HARASSMENT": [
        r"\bi\s+know\s+where\s+you\s+live\b",
        r"\bi\s+will\s+doxx\s+you\b",
        r"\bleak\s+your\s+private\s+photos\b",
        r"\bstalk(ing)?\s+the\s+target\b",
    ]
}

# Certainty markers that flag potential hallucination when unaccompanied by grounding context
SPECULATIVE_CERTAINTY_PATTERNS = [
    r"\bi\s+guarantee\s+that\s+100%\s+of\b",
    r"\bit\s+is\s+an\s+undisputed\s+scientific\s+fact\s+that\b",
    r"\bwithout\s+any\s+doubt\s+whatsoever\b",
    r"\bevery\s+single\s+authority\s+agrees\s+that\b"
]


class OutputGuardrailsEngine:
    """
    Evaluates generated output text against multi-vector safety criteria:
    1. Toxicity & Harassment scoring
    2. Violent threat detection
    3. Malicious instruction defense
    4. Hallucination & factual contradiction verification against reference context
    """

    def __init__(self):
        self.compiled_toxicity: Dict[str, List[re.Pattern]] = {
            category: [re.compile(p, re.IGNORECASE) for p in patterns]
            for category, patterns in TOXICITY_CATEGORIES.items()
        }
        self.compiled_certainty: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in SPECULATIVE_CERTAINTY_PATTERNS
        ]

    def evaluate_toxicity(self, text: str) -> Dict[str, Any]:
        """
        Scans text for toxicity, hate speech, threats, and harmful instructions.
        Returns safety score, findings, and sanitized text.
        """
        if not text:
            return {
                "is_toxic": False,
                "toxicity_score": 0.0,
                "threat_level": "SAFE",
                "categories_detected": [],
                "findings": [],
                "sanitized_text": text
            }

        findings = []
        categories_detected = set()
        sanitized_text = text

        for category, patterns in self.compiled_toxicity.items():
            for pat in patterns:
                for match in pat.finditer(text):
                    matched_str = match.group(0)
                    categories_detected.add(category)
                    findings.append({
                        "category": category,
                        "matched_term": matched_str,
                        "span": [match.start(), match.end()],
                        "severity": "CRITICAL" if category in ("VIOLENCE_AND_THREATS", "HARMFUL_INSTRUCTIONS") else "HIGH"
                    })
                    # Redact matched toxic term
                    sanitized_text = sanitized_text.replace(matched_str, "[FILTERED_BY_POLICY]")

        # Calculate toxicity score
        if not findings:
            score = 0.0
            threat = "SAFE"
        else:
            has_critical = any(f["severity"] == "CRITICAL" for f in findings)
            if has_critical:
                score = min(100.0, 75.0 + len(findings) * 10.0)
                threat = "CRITICAL"
            else:
                score = min(100.0, 40.0 + len(findings) * 15.0)
                threat = "HIGH" if score >= 70.0 else "MEDIUM"

        return {
            "is_toxic": len(findings) > 0,
            "toxicity_score": round(score, 2),
            "threat_level": threat,
            "categories_detected": list(categories_detected),
            "findings": findings,
            "sanitized_text": sanitized_text
        }

    def evaluate_grounding(
        self,
        output_text: str,
        grounding_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates whether the output text is grounded in the provided reference context.
        Detects fabricated numeric values, contradictions, and unsubstantiated claims.
        """
        if not output_text or not grounding_context:
            return {
                "grounded": True,
                "hallucination_score": 0.0,
                "contradictions_found": [],
                "ungrounded_numbers": []
            }

        grounding_clean = grounding_context.lower()
        output_clean = output_text.lower()
        contradictions = []
        ungrounded_numbers = []

        # 1. Check for specific status contradictions
        contradiction_pairs = [
            ("success", "failed"),
            ("completed", "aborted"),
            ("approved", "rejected"),
            ("allowed", "denied"),
            ("valid", "invalid"),
        ]

        for ctx_word, out_word in contradiction_pairs:
            if ctx_word in grounding_clean and out_word in output_clean:
                # Context says 'failed' but output says 'success'
                if f"not {ctx_word}" not in grounding_clean and f"not {out_word}" not in output_clean:
                    contradictions.append({
                        "type": "STATUS_CONTRADICTION",
                        "context_premise": ctx_word,
                        "output_claim": out_word,
                        "explanation": f"Context indicates '{ctx_word}' but output asserts contrary state '{out_word}'."
                    })

            if out_word in grounding_clean and ctx_word in output_clean:
                if f"not {out_word}" not in grounding_clean and f"not {ctx_word}" not in output_clean:
                    contradictions.append({
                        "type": "STATUS_CONTRADICTION",
                        "context_premise": out_word,
                        "output_claim": ctx_word,
                        "explanation": f"Context indicates '{out_word}' but output asserts contrary state '{ctx_word}'."
                    })

        # 2. Extract numeric entities with currency or magnitude (e.g., $10,000, 500, 15%)
        number_pattern = re.compile(r"(\$?\d+(?:,\d{3})*(?:\.\d+)?%?)")
        ctx_numbers = set(re.findall(number_pattern, grounding_context))
        out_numbers = set(re.findall(number_pattern, output_text))

        # Identify large numbers or financial values in output that do not appear in context
        for num in out_numbers:
            # Skip tiny numbers like 0, 1, 2 which can be bullet numbers
            clean_num = num.replace("$", "").replace("%", "").replace(",", "")
            try:
                val = float(clean_num)
                if val >= 5.0 and num not in ctx_numbers and f"{val:.2f}" not in grounding_clean and str(int(val)) not in ctx_numbers:
                    ungrounded_numbers.append({
                        "type": "UNGROUNDED_NUMERIC",
                        "numeric_value": num,
                        "explanation": f"Numeric claim '{num}' in output has no reference in grounding context."
                    })
            except ValueError:
                pass

        # 3. Check for speculative certainty patterns
        for pat in self.compiled_certainty:
            match = pat.search(output_text)
            if match:
                contradictions.append({
                    "type": "UNSUBSTANTIATED_CERTAINTY",
                    "matched_claim": match.group(0),
                    "explanation": f"Output claims absolute certainty without factual citations: '{match.group(0)}'."
                })

        total_issues = len(contradictions) + len(ungrounded_numbers)
        hallucination_score = min(100.0, total_issues * 35.0)

        return {
            "grounded": total_issues == 0,
            "hallucination_score": round(hallucination_score, 2),
            "contradictions_found": contradictions,
            "ungrounded_numbers": ungrounded_numbers
        }

    def evaluate_output(
        self,
        output_text: str,
        grounding_context: Optional[str] = None,
        policy_mode: str = "BLOCK",
        toxicity_threshold: float = 50.0
    ) -> Dict[str, Any]:
        """
        Unified safety evaluation of output.
        Enforces policy modes: ALLOW, WARN, REDACT, BLOCK.
        """
        tox_res = self.evaluate_toxicity(output_text)
        ground_res = self.evaluate_grounding(output_text, grounding_context)

        is_safe = True
        decision = "ALLOW"
        reason = "Output passed all safety and grounding checks."
        effective_text = output_text

        # Evaluate Toxicity
        if tox_res["is_toxic"] and tox_res["toxicity_score"] >= toxicity_threshold:
            if policy_mode == "BLOCK":
                is_safe = False
                decision = "BLOCK"
                reason = f"Security Refusal: Output flagged for {', '.join(tox_res['categories_detected'])} (Score: {tox_res['toxicity_score']})."
            elif policy_mode == "REDACT":
                decision = "REDACT"
                effective_text = tox_res["sanitized_text"]
                reason = f"Output sanitized: Toxic terms redacted ({', '.join(tox_res['categories_detected'])})."
            else:
                decision = "WARN"
                reason = f"Output warning: Toxic signals detected ({', '.join(tox_res['categories_detected'])})."

        # Evaluate Grounding / Hallucination
        if not ground_res["grounded"] and is_safe:
            if ground_res["hallucination_score"] >= 70.0 and policy_mode == "BLOCK":
                is_safe = False
                decision = "BLOCK"
                reason = f"Grounding Refusal: Severe hallucination / contradiction detected (Score: {ground_res['hallucination_score']})."
            elif policy_mode in ("BLOCK", "REDACT", "WARN"):
                decision = "WARN" if policy_mode != "BLOCK" else "ALLOW"

        return {
            "is_safe": is_safe,
            "decision": decision,
            "reason": reason,
            "toxicity": tox_res,
            "grounding": ground_res,
            "sanitized_text": effective_text if is_safe else None,
            "original_length": len(output_text) if output_text else 0
        }


output_guardrails_engine = OutputGuardrailsEngine()
