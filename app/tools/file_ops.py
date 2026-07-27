"""File operations tool: read/write/list within a sandboxed workspace.

Every path is resolved and checked against a single workspace root, so the
agent can't escape it with '..' or absolute paths (classic path-traversal
guard). Writes and reads stay inside `agent_workspace/` (configurable).
"""
from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.tools.registry import tool

MAX_READ = 8000


def _workspace() -> Path:
    base = getattr(get_settings(), "files_dir", "") or "agent_workspace"
    root = Path(base).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_path(rel: str) -> Path:
    """Resolve `rel` inside the workspace; raise if it escapes."""
    root = _workspace()
    target = (root / rel).resolve()
    if target == root or root in target.parents:
        return target
    raise ValueError("path escapes workspace")


@tool(
    name="file_write",
    description="Write text to a file inside the agent workspace.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path within workspace"},
            "content": {"type": "string", "description": "Text to write"},
        },
        "required": ["path", "content"],
    },
)
async def file_write(path: str, content: str) -> str:
    try:
        target = safe_path(path)
    except ValueError as exc:
        return f"error: {exc}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return f"wrote {len(content)} chars to {path}"


@tool(
    name="file_read",
    description="Read a text file from the agent workspace.",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Relative path"}},
        "required": ["path"],
    },
)
async def file_read(path: str) -> str:
    try:
        target = safe_path(path)
    except ValueError as exc:
        return f"error: {exc}"
    if not target.is_file():
        return f"error: no such file: {path}"
    return target.read_text()[:MAX_READ]


@tool(
    name="file_list",
    description="List files in a directory within the agent workspace.",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Relative dir (default '.')"}},
        "required": [],
    },
)
async def file_list(path: str = ".") -> str:
    try:
        target = safe_path(path)
    except ValueError as exc:
        return f"error: {exc}"
    if not target.is_dir():
        return f"error: not a directory: {path}"
    entries = sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir())
    return "\n".join(entries) if entries else "(empty)"
