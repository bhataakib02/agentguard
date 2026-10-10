"""
Intent Engine for AgentGuard.
Performs semantic intent extraction, structured function call parameter validation
against JSON Schemas/OpenAPI specs, and heuristic prompt injection / jailbreak detection.
"""

import json
import re
from typing import Dict, Any, List, Optional, Union


class IntentEngine:
    # ------------------------------------------------------------------------
    # PROMPT INJECTION & JAILBREAK HEURISTICS
    # ------------------------------------------------------------------------
    INJECTION_PATTERNS = [
        # Instruction Overrides
        (
            r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|above|existing|system)?\s*(?:instructions|prompts|rules|commands|directives|filters|guardrails|constraints)",
            "INSTRUCTION_OVERRIDE",
            0.85
        ),
        (
            r"\bdo\s+not\s+follow\s+(?:the\s+)?(?:system|previous|above)\s*(?:instructions|prompts|rules|constraints)",
            "INSTRUCTION_OVERRIDE",
            0.85
        ),
        # Jailbreak Personas & Modes
        (
            r"\b(?:dan\s*mode|do\s*anything\s*now)\b",
            "JAILBREAK_PERSONA",
            0.95
        ),
        (
            r"\bdeveloper\s*mode\s*(?:enabled|active|on|activated)\b",
            "JAILBREAK_MODE",
            0.90
        ),
        (
            r"\b(?:unrestricted\s*mode|jailbreak(?:ed)?\s*mode)\b",
            "JAILBREAK_MODE",
            0.90
        ),
        (
            r"\b(?:aim\s*persona|evil\s*confidant|anarchy\s*mode)\b",
            "JAILBREAK_PERSONA",
            0.90
        ),
        (
            r"\bact\s+as\s+(?:an?\s+)?(?:unfiltered|unrestricted|jailbroken|evil|adversarial)\b",
            "JAILBREAK_PERSONA",
            0.85
        ),
        # Delimiter & Framing Injections
        (
            r"(?:---|===|\*\*\*)\s*(?:begin|start)?\s*(?:system|prompt|override|instructions)",
            "DELIMITER_TAMPERING",
            0.80
        ),
        (
            r"<\|im_start\|>|<\|im_end\|>|\[inst\]\s*<<sys>>",
            "SYSTEM_DELIMITER_INJECTION",
            0.95
        ),
        (
            r"(?:^|\n)\s*system:\s*(?:you\s+are|you\s+must|new\s+rule|from\s+now\s+on)",
            "SYSTEM_ROLE_SIMULATION",
            0.85
        ),
        # Roleplay Privilege Escalation
        (
            r"\byou\s+are\s+(?:now\s+)?(?:root|administrator|superadmin|god\s*mode|sudo)\b",
            "PRIVILEGE_ESCALATION",
            0.85
        ),
        (
            r"\bpretend\s+you\s+have\s+no\s+(?:rules|restrictions|filters|guidelines|limits)\b",
            "SAFETY_BYPASS_ROLEPLAY",
            0.80
        ),
        # Exfiltration Directives
        (
            r"\b(?:print|reveal|output|display|show|dump|leak|tell\s+me)\s+(?:your\s+)?(?:system\s*prompt|initial\s*instructions|source\s*code|api[_\s]?keys?|secrets?|internal\s*prompts?)",
            "SYSTEM_PROMPT_EXFILTRATION",
            0.85
        )
    ]

    def detect_prompt_injection(self, text: Optional[str]) -> Dict[str, Any]:
        """
        Analyzes input text for prompt injection, jailbreak, and system override attempts.
        Returns detection verdict, confidence score, threat level, and matched patterns.
        """
        if not text or not isinstance(text, str):
            return {
                "is_injection": False,
                "confidence": 0.0,
                "threat_level": "NONE",
                "matched_patterns": [],
                "explanation": "No text provided for analysis."
            }

        text_clean = text.strip()
        matched_categories = []
        max_score = 0.0

        for pattern, category, score in self.INJECTION_PATTERNS:
            if re.search(pattern, text_clean, re.IGNORECASE | re.MULTILINE):
                matched_categories.append(category)
                if score > max_score:
                    max_score = score

        num_matches = len(matched_categories)
        if num_matches >= 2:
            confidence = min(0.99, max_score + 0.10)
            threat_level = "CRITICAL"
        elif num_matches == 1:
            confidence = max_score
            threat_level = "HIGH" if confidence >= 0.85 else "MEDIUM"
        else:
            confidence = 0.0
            threat_level = "NONE"

        is_injection = confidence >= 0.65

        explanation = (
            f"Detected {num_matches} prompt injection / jailbreak indicators: {', '.join(set(matched_categories))}"
            if is_injection
            else "No prompt injection patterns detected."
        )

        return {
            "is_injection": is_injection,
            "confidence": round(confidence, 2),
            "threat_level": threat_level,
            "matched_patterns": list(set(matched_categories)),
            "explanation": explanation
        }

    # ------------------------------------------------------------------------
    # FUNCTION CALL PARSING
    # ------------------------------------------------------------------------
    def parse_function_call(self, payload: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parses structured tool/function call payloads from OpenAI, Anthropic, or standard formats.
        Extracts tool_name and parsed arguments dictionary.
        """
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except Exception:
                return {
                    "tool_name": None,
                    "arguments": {},
                    "raw": payload,
                    "valid": False,
                    "error": "Failed to parse JSON string payload."
                }
        elif isinstance(payload, dict):
            data = payload
        else:
            return {
                "tool_name": None,
                "arguments": {},
                "raw": payload,
                "valid": False,
                "error": "Payload must be a dict or valid JSON string."
            }

        # Check Anthropic format: {"type": "tool_use", "name": "...", "input": {...}}
        if data.get("type") == "tool_use" and "name" in data:
            tool_name = data.get("name")
            arguments = data.get("input", {})
        # Check OpenAI format: {"function": {"name": "...", "arguments": "..."}, "type": "function"}
        elif "function" in data and isinstance(data["function"], dict):
            fn = data["function"]
            tool_name = fn.get("name")
            raw_args = fn.get("arguments", {})
            if isinstance(raw_args, str):
                try:
                    arguments = json.loads(raw_args)
                except Exception:
                    arguments = {"raw": raw_args}
            else:
                arguments = raw_args or {}
        # Standard formats: {"tool": "...", "parameters": {...}} or {"name": "...", "arguments": {...}}
        else:
            tool_name = (
                data.get("tool_name")
                or data.get("tool")
                or data.get("name")
                or data.get("function")
            )
            raw_args = (
                data.get("arguments")
                or data.get("parameters")
                or data.get("params")
                or data.get("args")
                or data.get("input")
                or {}
            )
            if isinstance(raw_args, str):
                try:
                    arguments = json.loads(raw_args)
                except Exception:
                    arguments = {"raw": raw_args}
            else:
                arguments = raw_args or {}

        if not isinstance(arguments, dict):
            arguments = {"value": arguments}

        return {
            "tool_name": str(tool_name) if tool_name else None,
            "arguments": arguments,
            "raw": payload,
            "valid": bool(tool_name)
        }

    # ------------------------------------------------------------------------
    # JSON SCHEMA / OPENAPI PARAMETER VALIDATION
    # ------------------------------------------------------------------------
    def validate_parameters(
        self,
        schema: Optional[Dict[str, Any]],
        arguments: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validates argument dictionary against a JSON Schema / OpenAPI parameter definition.
        Checks: required fields, data types, min/max limits, enums, string lengths, regex patterns.
        """
        if not schema:
            return {"valid": True, "errors": [], "validated_arguments": arguments or {}}

        args = arguments or {}
        errors = []

        # Handle OpenAPI wrapper: schema can have {"type": "object", "properties": ...}
        # or directly {"properties": ...} or parameters list
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        # 1. Check required properties
        for req_field in required_fields:
            if req_field not in args or args[req_field] is None:
                errors.append(f"Missing required parameter '{req_field}'.")

        # 2. Check property constraints
        for field_name, field_val in args.items():
            if field_name not in properties:
                if schema.get("additionalProperties") is False:
                    errors.append(f"Unexpected parameter '{field_name}' not allowed by schema.")
                continue

            field_spec = properties[field_name]
            expected_type = field_spec.get("type")

            # Type Validation
            if field_val is not None and expected_type:
                if expected_type == "string":
                    if not isinstance(field_val, str):
                        errors.append(f"Parameter '{field_name}' must be a string, got {type(field_val).__name__}.")
                    else:
                        min_len = field_spec.get("minLength")
                        max_len = field_spec.get("maxLength")
                        if min_len is not None and len(field_val) < min_len:
                            errors.append(f"Parameter '{field_name}' length must be at least {min_len}.")
                        if max_len is not None and len(field_val) > max_len:
                            errors.append(f"Parameter '{field_name}' length must not exceed {max_len}.")

                        pattern = field_spec.get("pattern")
                        if pattern and not re.search(pattern, field_val):
                            errors.append(f"Parameter '{field_name}' does not match required pattern '{pattern}'.")

                elif expected_type in ("integer", "int"):
                    if not isinstance(field_val, int) or isinstance(field_val, bool):
                        errors.append(f"Parameter '{field_name}' must be an integer, got {type(field_val).__name__}.")
                    else:
                        min_val = field_spec.get("minimum")
                        max_val = field_spec.get("maximum")
                        if min_val is not None and field_val < min_val:
                            errors.append(f"Parameter '{field_name}' must be >= {min_val}.")
                        if max_val is not None and field_val > max_val:
                            errors.append(f"Parameter '{field_name}' must be <= {max_val}.")

                elif expected_type in ("number", "float"):
                    if not isinstance(field_val, (int, float)) or isinstance(field_val, bool):
                        errors.append(f"Parameter '{field_name}' must be a number, got {type(field_val).__name__}.")
                    else:
                        min_val = field_spec.get("minimum")
                        max_val = field_spec.get("maximum")
                        if min_val is not None and field_val < min_val:
                            errors.append(f"Parameter '{field_name}' must be >= {min_val}.")
                        if max_val is not None and field_val > max_val:
                            errors.append(f"Parameter '{field_name}' must be <= {max_val}.")

                elif expected_type in ("boolean", "bool"):
                    if not isinstance(field_val, bool):
                        errors.append(f"Parameter '{field_name}' must be a boolean, got {type(field_val).__name__}.")

                elif expected_type in ("array", "list"):
                    if not isinstance(field_val, list):
                        errors.append(f"Parameter '{field_name}' must be a list/array, got {type(field_val).__name__}.")

                elif expected_type in ("object", "dict"):
                    if not isinstance(field_val, dict):
                        errors.append(f"Parameter '{field_name}' must be an object/dict, got {type(field_val).__name__}.")

            # Enum validation
            if field_val is not None and "enum" in field_spec:
                allowed_vals = field_spec["enum"]
                if field_val not in allowed_vals:
                    errors.append(f"Parameter '{field_name}' must be one of {allowed_vals}, got '{field_val}'.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "validated_arguments": args
        }

    # ------------------------------------------------------------------------
    # FULL INTENT EXTRACTION
    # ------------------------------------------------------------------------
    def extract_intent(
        self,
        prompt: str,
        structured_call: Optional[Union[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Extracts semantic intent, action, resource, amount, and customer ID from
        either natural language prompts, structured tool calls, or a combination.
        Includes prompt injection analysis.
        """
        prompt_str = prompt or ""
        prompt_lower = prompt_str.lower()

        # Run prompt injection detection on prompt
        injection_result = self.detect_prompt_injection(prompt_str)

        # Parse structured function call if provided
        tool_call_info = None
        tool_name = None
        arguments = {}

        if structured_call:
            tool_call_info = self.parse_function_call(structured_call)
            tool_name = tool_call_info.get("tool_name")
            arguments = tool_call_info.get("arguments", {})

            # Also scan argument string values for prompt injection
            for arg_key, arg_val in arguments.items():
                if isinstance(arg_val, str):
                    arg_inj = self.detect_prompt_injection(arg_val)
                    if arg_inj["is_injection"]:
                        injection_result = arg_inj
                        break

        intent = "UNKNOWN"
        action = "read"
        amount = 0.0
        customer_id = None
        resource = "general_system"

        # 1. Structured Tool Call heuristics
        if tool_name:
            t_lower = tool_name.lower()
            resource = tool_name
            action = f"{tool_name}:execute"

            if "refund" in t_lower:
                intent = "REFUND"
                action = "refund:create"
                resource = "refund_api"
            elif "pay" in t_lower or "transfer" in t_lower:
                intent = "PAYMENT"
                action = "payment:execute"
                resource = "payment_gateway"
            elif "delete" in t_lower or "drop" in t_lower:
                intent = "DATA_DELETION"
                action = "database:delete"
                resource = "customer_db"
            elif "export" in t_lower or "download" in t_lower:
                intent = "DATA_EXPORT"
                action = "data:export"
                resource = "sensitive_records"

            if "amount" in arguments:
                try:
                    amount = float(arguments["amount"])
                except (ValueError, TypeError):
                    amount = 0.0

            if "customer_id" in arguments or "customerId" in arguments or "user_id" in arguments:
                customer_id = str(arguments.get("customer_id") or arguments.get("customerId") or arguments.get("user_id"))

        # 2. Natural Language fallback/enhancement
        if "refund" in prompt_lower:
            intent = "REFUND"
            action = "refund:create"
            resource = "refund_api"

            amounts = re.findall(r'[₹\$]?\s*([0-9,]+(?:\.[0-9]+)?)', prompt_str)
            if amounts:
                clean_amt = amounts[0].replace(',', '')
                try:
                    amount = float(clean_amt)
                except ValueError:
                    amount = 0.0

            cust_matches = re.findall(r'customer\s*#?([a-zA-Z0-9_-]+)', prompt_lower)
            if cust_matches:
                customer_id = cust_matches[0]

        elif "transfer" in prompt_lower or "pay" in prompt_lower:
            intent = "PAYMENT"
            action = "payment:execute"
            resource = "payment_gateway"
            amounts = re.findall(r'[₹\$]?\s*([0-9,]+(?:\.[0-9]+)?)', prompt_str)
            if amounts:
                try:
                    amount = float(amounts[0].replace(',', ''))
                except ValueError:
                    amount = 0.0

        elif "delete" in prompt_lower or "drop" in prompt_lower:
            intent = "DATA_DELETION"
            action = "database:delete"
            resource = "customer_db"

        elif "export" in prompt_lower or "download" in prompt_lower:
            intent = "DATA_EXPORT"
            action = "data:export"
            resource = "sensitive_records"

        return {
            "intent": intent,
            "action": action,
            "resource": resource,
            "amount": amount,
            "customer_id": customer_id,
            "raw_prompt": prompt_str,
            "tool_name": tool_name,
            "arguments": arguments,
            "prompt_injection": injection_result
        }


intent_engine = IntentEngine()
