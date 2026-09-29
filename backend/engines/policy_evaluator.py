"""
Safe Policy Rule Condition Evaluator for AgentGuard
Evaluates boolean condition expressions against decision context without using eval().
Uses an Abstract Syntax Tree (AST) walker with a strict allowlist of node types,
operators, context fields, and value types.
"""

import ast
import re
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("agentguard.policy_evaluator")

# Allowed fields in decision context
ALLOWED_CONTEXT_FIELDS = {
    "amount",
    "risk_score",
    "action",
    "intent",
    "resource",
    "agent_status",
    "agent_name",
    "agent_code",
    "agent_department",
    "agent_autonomy",
    "department",
    "status",
    "user_role",
}

# Allowed AST node types
ALLOWED_AST_NODES = (
    ast.Expression,
    ast.Constant,
    ast.Name,
    ast.UnaryOp,
    ast.UAdd,
    ast.USub,
    ast.Not,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.Compare,
    ast.Gt,
    ast.Lt,
    ast.GtE,
    ast.LtE,
    ast.Eq,
    ast.NotEq,
    ast.In,
    ast.NotIn,
    ast.List,
    ast.Tuple,
    ast.Load,
)


def normalize_expression(expr: str) -> str:
    """
    Normalizes common expressions, e.g.:
    - 'resource contains "production"' -> '"production" in resource'
    - 'action contains "delete"' -> '"delete" in action'
    - '₹5,000' -> '5000'
    """
    cleaned = expr.strip()
    # Remove currency symbols and commas in numbers (e.g. ₹5,000 -> 5000)
    cleaned = re.sub(r'[₹$€£](\d[\d,]*)', lambda m: m.group(1).replace(',', ''), cleaned)
    
    # Handle natural "field contains 'value'" syntax
    contains_match = re.match(r'^(\w+)\s+contains\s+(.+)$', cleaned, re.IGNORECASE)
    if contains_match:
        field, val = contains_match.groups()
        return f"{val.strip()} in {field.strip()}"
        
    return cleaned


def validate_rule_syntax(condition_expr: str) -> Tuple[bool, Optional[str]]:
    """
    Validates that a condition expression is syntactically valid and uses only allowlisted constructs.
    Returns (is_valid, error_message).
    """
    if not condition_expr or not condition_expr.strip():
        return False, "Condition expression cannot be empty."

    norm_expr = normalize_expression(condition_expr)
    try:
        tree = ast.parse(norm_expr, mode="eval")
    except SyntaxError as e:
        return False, f"Syntax error in expression: {str(e)}"

    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST_NODES):
            return False, f"Disallowed expression element: {type(node).__name__}"
        if isinstance(node, ast.Name):
            var_name = node.id.lower()
            if var_name not in ALLOWED_CONTEXT_FIELDS and var_name not in ("true", "false", "none"):
                return False, f"Unknown or unauthorized field '{node.id}' in rule condition. Allowed fields: {sorted(list(ALLOWED_CONTEXT_FIELDS))}"

    return True, None


def evaluate_condition(condition_expr: str, context: Dict[str, Any]) -> Tuple[bool, bool, Optional[str]]:
    """
    Safely evaluates condition_expr against context.
    Returns (matched: bool, is_valid: bool, error_message: Optional[str]).
    If the rule is invalid, matched will ALWAYS be False to prevent accidental ALLOWs.
    """
    is_valid, err = validate_rule_syntax(condition_expr)
    if not is_valid:
        logger.warning(f"Invalid policy rule condition '{condition_expr}': {err}")
        return False, False, err

    norm_expr = normalize_expression(condition_expr)
    try:
        tree = ast.parse(norm_expr, mode="eval")
    except Exception as e:
        logger.warning(f"Failed to parse condition '{condition_expr}': {e}")
        return False, False, str(e)

    # Prepare lowercased context lookup
    ctx = {k.lower(): v for k, v in context.items()}

    def _eval_node(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)

        elif isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Name):
            name_lower = node.id.lower()
            if name_lower == "true":
                return True
            if name_lower == "false":
                return False
            if name_lower == "none":
                return None
            if name_lower in ctx:
                return ctx[name_lower]
            raise ValueError(f"Context variable '{node.id}' not provided")

        elif isinstance(node, ast.UnaryOp):
            operand = _eval_node(node.operand)
            if isinstance(node.op, ast.Not):
                return not bool(operand)
            elif isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.UAdd):
                return +operand
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")

        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for val in node.values:
                    if not _eval_node(val):
                        return False
                return True
            elif isinstance(node.op, ast.Or):
                for val in node.values:
                    if _eval_node(val):
                        return True
                return False
            raise ValueError(f"Unsupported boolean operator: {type(node.op).__name__}")

        elif isinstance(node, ast.Compare):
            left = _eval_node(node.left)
            for op, comparator_node in zip(node.ops, node.comparators):
                right = _eval_node(comparator_node)

                # Type coercion for comparisons if numeric
                if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    l_val, r_val = float(left), float(right)
                else:
                    l_val, r_val = left, right

                if isinstance(op, ast.Gt):
                    res = l_val > r_val
                elif isinstance(op, ast.Lt):
                    res = l_val < r_val
                elif isinstance(op, ast.GtE):
                    res = l_val >= r_val
                elif isinstance(op, ast.LtE):
                    res = l_val <= r_val
                elif isinstance(op, ast.Eq):
                    if isinstance(l_val, str) and isinstance(r_val, str):
                        res = l_val.strip().lower() == r_val.strip().lower()
                    else:
                        res = l_val == r_val
                elif isinstance(op, ast.NotEq):
                    if isinstance(l_val, str) and isinstance(r_val, str):
                        res = l_val.strip().lower() != r_val.strip().lower()
                    else:
                        res = l_val != r_val
                elif isinstance(op, ast.In):
                    if isinstance(r_val, str) and isinstance(l_val, str):
                        res = l_val.strip().lower() in r_val.strip().lower()
                    elif isinstance(r_val, (list, tuple, set)):
                        res = any(
                            (l_val.strip().lower() == str(item).strip().lower() if isinstance(l_val, str) else l_val == item)
                            for item in r_val
                        )
                    else:
                        res = l_val in r_val
                elif isinstance(op, ast.NotIn):
                    if isinstance(r_val, str) and isinstance(l_val, str):
                        res = l_val.strip().lower() not in r_val.strip().lower()
                    elif isinstance(r_val, (list, tuple, set)):
                        res = not any(
                            (l_val.strip().lower() == str(item).strip().lower() if isinstance(l_val, str) else l_val == item)
                            for item in r_val
                        )
                    else:
                        res = l_val not in r_val
                else:
                    raise ValueError(f"Unsupported comparator operator: {type(op).__name__}")

                if not res:
                    return False
                left = right
            return True

        elif isinstance(node, (ast.List, ast.Tuple)):
            return [_eval_node(elem) for elem in node.elts]

        raise ValueError(f"Disallowed expression node: {type(node).__name__}")

    try:
        matched = bool(_eval_node(tree))
        return matched, True, None
    except Exception as e:
        logger.warning(f"Error evaluating rule '{condition_expr}': {e}")
        return False, False, str(e)
