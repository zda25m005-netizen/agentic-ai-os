"""Data analysis tool: run pandas operations over a CSV in the workspace.

Loads a CSV (scoped to the sandboxed workspace) and returns a summary:
shape, columns, head, describe, or a grouped aggregate. Lets the agent
answer quantitative questions about tabular data it was given.
"""
from __future__ import annotations

import pandas as pd

from app.tools.file_ops import safe_path
from app.tools.registry import tool

MAX_OUTPUT = 4000
OPERATIONS = ("shape", "columns", "head", "describe")


def _summarize(df: pd.DataFrame, operation: str) -> str:
    if operation == "shape":
        return f"{df.shape[0]} rows x {df.shape[1]} columns"
    if operation == "columns":
        return ", ".join(map(str, df.columns))
    if operation == "head":
        return df.head().to_string(index=False)
    if operation == "describe":
        return df.describe(include="all").to_string()
    raise ValueError(f"unknown operation: {operation}")


@tool(
    name="analyze_csv",
    description="Analyze a CSV in the workspace (shape, columns, head, describe).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "CSV path within workspace"},
            "operation": {
                "type": "string",
                "description": "One of: shape, columns, head, describe",
            },
        },
        "required": ["path"],
    },
)
async def analyze_csv(path: str, operation: str = "describe") -> str:
    """Tool handler: load a CSV and return the requested summary."""
    try:
        target = safe_path(path)
    except ValueError as exc:
        return f"error: {exc}"
    if not target.is_file():
        return f"error: no such file: {path}"
    try:
        df = pd.read_csv(target)
        return _summarize(df, operation)[:MAX_OUTPUT]
    except (ValueError, pd.errors.ParserError) as exc:
        return f"error: {exc}"
