"""
AgentGuard PII & Sensitive Data Redaction Engine
Detects, redacts, tokenizes, and blocks Personally Identifiable Information (PII)
and credentials across agent prompts, tool parameters, and response payloads.
"""

import re
import hashlib
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict

@dataclass
class PIIDetectionResult:
    entity_type: str
    raw_value: str
    redacted_value: str
    start: int
    end: int
    confidence: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PIIEngine:
    """
    Enterprise PII & Secret Redaction Engine.
    Provides rule-based regex detection, Luhn validation for payment cards,
    and multiple remediation modes (MASK, PARTIAL_MASK, TOKENIZE, BLOCK).
    """

    # --- PII Regex Patterns ---
    SSN_PATTERN = re.compile(
        r"\b(?!000|666)\d{3}[- ]?(?!00)\d{2}[- ]?(?!0000)\d{4}\b"
    )

    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b",
        re.IGNORECASE
    )

    PHONE_PATTERN = re.compile(
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b"
    )

    CREDIT_CARD_PATTERN = re.compile(
        r"\b(?:\d{4}[- ]?){3}\d{4}\b|\b\d{13,19}\b"
    )

    API_KEY_PATTERNS = [
        ("OPENAI_KEY", re.compile(r"\b(?:sk-proj-|sk-)[a-zA-Z0-9_\-]{20,}\b")),
        ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
        ("GITHUB_KEY", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b")),
        ("AGENTGUARD_KEY", re.compile(r"\bag_(?:agent|live)_[a-zA-Z0-9_\-]{16,}\b")),
        ("BEARER_TOKEN", re.compile(r"\bBearer\s+[A-Za-z0-9_\-\.]{25,}\b", re.IGNORECASE)),
        ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----[^-]+-----END (?:RSA |EC )?PRIVATE KEY-----", re.DOTALL)),
    ]

    JWT_PATTERN = re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
    )

    IPV4_PATTERN = re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    )

    @staticmethod
    def _is_luhn_valid(number_str: str) -> bool:
        """Validate credit card number using the Luhn checksum algorithm."""
        digits = [int(c) for c in number_str if c.isdigit()]
        if len(digits) < 13 or len(digits) > 19:
            return False
        total = 0
        reverse_digits = digits[::-1]
        for idx, digit in enumerate(reverse_digits):
            if idx % 2 == 1:
                doubled = digit * 2
                total += doubled - 9 if doubled > 9 else doubled
            else:
                total += digit
        return total % 10 == 0

    @staticmethod
    def _generate_token(entity_type: str, value: str) -> str:
        """Deterministically tokenize sensitive value into a non-reversible pseudonymous token."""
        h = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
        return f"tok_pii_{entity_type.lower()}_{h}"

    def scan_text(self, text: str) -> List[PIIDetectionResult]:
        """
        Scans a text string for all recognizable PII and secret patterns.
        Returns a sorted list of detection results.
        """
        if not text or not isinstance(text, str):
            return []

        results: List[PIIDetectionResult] = []

        # 1. API Keys & Secrets
        for key_type, pattern in self.API_KEY_PATTERNS:
            for match in pattern.finditer(text):
                val = match.group(0)
                results.append(PIIDetectionResult(
                    entity_type="API_KEY",
                    raw_value=val,
                    redacted_value="[REDACTED_API_KEY]",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.99,
                    description=f"Secret credentials ({key_type})"
                ))

        # 2. JWTs
        for match in self.JWT_PATTERN.finditer(text):
            val = match.group(0)
            results.append(PIIDetectionResult(
                entity_type="JWT",
                raw_value=val,
                redacted_value="[REDACTED_JWT]",
                start=match.start(),
                end=match.end(),
                confidence=0.99,
                description="JSON Web Token authentication secret"
            ))

        # 3. Social Security Numbers
        for match in self.SSN_PATTERN.finditer(text):
            val = match.group(0)
            results.append(PIIDetectionResult(
                entity_type="SSN",
                raw_value=val,
                redacted_value="[REDACTED_SSN]",
                start=match.start(),
                end=match.end(),
                confidence=0.95,
                description="Government Social Security Number"
            ))

        # 4. Credit Cards (Luhn verified)
        for match in self.CREDIT_CARD_PATTERN.finditer(text):
            val = match.group(0)
            cleaned = re.sub(r"[- ]", "", val)
            if self._is_luhn_valid(cleaned):
                results.append(PIIDetectionResult(
                    entity_type="CREDIT_CARD",
                    raw_value=val,
                    redacted_value="[REDACTED_CREDIT_CARD]",
                    start=match.start(),
                    end=match.end(),
                    confidence=0.98,
                    description="Payment card number"
                ))

        # 5. Email Addresses
        for match in self.EMAIL_PATTERN.finditer(text):
            val = match.group(0)
            results.append(PIIDetectionResult(
                entity_type="EMAIL",
                raw_value=val,
                redacted_value="[REDACTED_EMAIL]",
                start=match.start(),
                end=match.end(),
                confidence=0.95,
                description="Personal email address"
            ))

        # 6. Phone Numbers
        for match in self.PHONE_PATTERN.finditer(text):
            val = match.group(0)
            digits_only = re.sub(r"\D", "", val)
            # Filter out non-phone digit sequences (must be 10-15 digits)
            if 10 <= len(digits_only) <= 15:
                # Avoid overlapping with already detected SSN or Credit Card
                start, end = match.start(), match.end()
                overlap = any(r.start <= start and r.end >= end for r in results if r.entity_type in ("SSN", "CREDIT_CARD"))
                if not overlap:
                    results.append(PIIDetectionResult(
                        entity_type="PHONE",
                        raw_value=val,
                        redacted_value="[REDACTED_PHONE]",
                        start=match.start(),
                        end=match.end(),
                        confidence=0.90,
                        description="Telephone contact number"
                    ))

        # 7. IP Addresses
        for match in self.IPV4_PATTERN.finditer(text):
            val = match.group(0)
            # Exclude loopback or local testing addresses if needed, or flag as IP
            results.append(PIIDetectionResult(
                entity_type="IP_ADDRESS",
                raw_value=val,
                redacted_value="[REDACTED_IP_ADDRESS]",
                start=match.start(),
                end=match.end(),
                confidence=0.90,
                description="Network IP address"
            ))

        # Sort results by position (descending for safe in-place replacement)
        results.sort(key=lambda r: r.start)
        return results

    def redact_text(
        self,
        text: str,
        mode: str = "MASK"
    ) -> Tuple[str, List[PIIDetectionResult]]:
        """
        Redacts PII occurrences from text.
        Modes:
          - MASK: Replaces with [REDACTED_<TYPE>]
          - PARTIAL_MASK: Masks keeping minimal safe characters (e.g. ***-**-1234)
          - TOKENIZE: Replaces with tok_pii_<type>_<hash>
          - BLOCK: Does not change text, returns findings for blocking
        """
        findings = self.scan_text(text)
        if not findings or mode == "BLOCK":
            return text, findings

        # Deduplicate overlaps: remove findings that fall inside another finding's span
        non_overlapping: List[PIIDetectionResult] = []
        for f in findings:
            if not any(f.start >= ex.start and f.end <= ex.end for ex in non_overlapping):
                non_overlapping.append(f)

        # Work right-to-left so slice replacements don't invalidate indices
        sorted_rev = sorted(non_overlapping, key=lambda f: f.start, reverse=True)
        redacted = text

        for item in sorted_rev:
            replacement = item.redacted_value

            if mode == "TOKENIZE":
                replacement = self._generate_token(item.entity_type, item.raw_value)
            elif mode == "PARTIAL_MASK":
                if item.entity_type == "EMAIL" and "@" in item.raw_value:
                    user, dom = item.raw_value.split("@", 1)
                    replacement = f"{user[0]}***@{dom}" if user else f"***@{dom}"
                elif item.entity_type in ("CREDIT_CARD", "SSN"):
                    clean = re.sub(r"\D", "", item.raw_value)
                    last4 = clean[-4:] if len(clean) >= 4 else "xxxx"
                    replacement = f"***-**-{last4}"
                elif item.entity_type == "PHONE":
                    clean = re.sub(r"\D", "", item.raw_value)
                    last4 = clean[-4:] if len(clean) >= 4 else "xxxx"
                    replacement = f"***-***-{last4}"
                elif item.entity_type in ("API_KEY", "JWT"):
                    replacement = f"{item.raw_value[:6]}...[REDACTED]"
                else:
                    replacement = f"[REDACTED_{item.entity_type}]"

            redacted = redacted[:item.start] + replacement + redacted[item.end:]
            item.redacted_value = replacement

        return redacted, non_overlapping

    def scan_and_redact_payload(
        self,
        data: Any,
        mode: str = "MASK"
    ) -> Tuple[Any, List[PIIDetectionResult]]:
        """
        Recursively traverses arbitrary data structures (dicts, lists, strings)
        to identify and redact PII.
        """
        all_findings: List[PIIDetectionResult] = []

        if isinstance(data, str):
            redacted_str, findings = self.redact_text(data, mode=mode)
            all_findings.extend(findings)
            return redacted_str, all_findings

        elif isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                # Also check key if string
                redacted_v, findings = self.scan_and_redact_payload(v, mode=mode)
                all_findings.extend(findings)
                new_dict[k] = redacted_v
            return new_dict, all_findings

        elif isinstance(data, list):
            new_list = []
            for item in data:
                redacted_item, findings = self.scan_and_redact_payload(item, mode=mode)
                all_findings.extend(findings)
                new_list.append(redacted_item)
            return new_list, all_findings

        else:
            return data, all_findings

    def evaluate_guardrail(
        self,
        prompt: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        policy_mode: str = "MASK"
    ) -> Dict[str, Any]:
        """
        Comprehensive guardrail check for agent invocation payloads.
        Returns whether violations occurred, whether action should be blocked,
        sanitized prompt, sanitized parameters, and itemized findings.
        """
        findings: List[PIIDetectionResult] = []

        sanitized_prompt = prompt
        if prompt:
            redacted_p, p_findings = self.redact_text(prompt, mode=policy_mode)
            findings.extend(p_findings)
            sanitized_prompt = redacted_p

        sanitized_params = parameters
        if parameters:
            redacted_params, param_findings = self.scan_and_redact_payload(parameters, mode=policy_mode)
            findings.extend(param_findings)
            sanitized_params = redacted_params

        has_pii = len(findings) > 0
        should_block = has_pii and policy_mode.upper() == "BLOCK"

        return {
            "has_pii": has_pii,
            "blocked": should_block,
            "policy_mode": policy_mode.upper(),
            "findings_count": len(findings),
            "findings": [f.to_dict() for f in findings],
            "sanitized_prompt": sanitized_prompt,
            "sanitized_parameters": sanitized_params,
        }


pii_engine = PIIEngine()
