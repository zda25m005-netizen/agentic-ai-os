"""A safe arithmetic calculator tool.

Evaluates a math expression by walking a parsed AST — never `eval()` — so
untrusted input can't execute arbitrary code. Supports + - * / % ** and
parentheses over numbers. This is the first concrete tool; web/SQL/Python
tools follow in the next days using the same registry.
"""
from __future__ import annotations

import ast
import operator

from app.tools.registry import tool

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


def safe_eval(expression: str) -> float:
    """Evaluate a basic arithmetic expression safely."""
    tree = ast.parse(expression, mode="eval")
    return _eval(tree.body)


@tool(
    name="calculator",
    description="Evaluate a basic arithmetic expression (+, -, *, /, %, **).",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression, e.g. '2 + 2 * 3'",
            }
        },
        "required": ["expression"],
    },
)
async def calculator(expression: str) -> str:
    """Tool handler: compute the expression, or return an error string."""
    try:
        return str(safe_eval(expression))
    except (ValueError, SyntaxError, KeyError, ZeroDivisionError) as exc:
        return f"error: {exc}"
