"""Python execution tool: run code in an isolated subprocess.

Untrusted code runs in a *separate* Python process (never in-process), in
isolated mode (`-I`, so it ignores the user's env and site-packages), with
a hard wall-clock timeout. On timeout the process is killed. This is a
pragmatic sandbox — good for a single-user dev tool. Production hardening
(containers, seccomp, no network, memory caps) is noted in DESIGN.md.
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

from app.tools.registry import tool

DEFAULT_TIMEOUT = 5.0
MAX_OUTPUT = 4000  # chars, to keep tool output bounded


@dataclass
class ExecResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


async def run_python(code: str, timeout: float = DEFAULT_TIMEOUT) -> ExecResult:
    """Run `code` in an isolated subprocess and capture its output."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",  # isolated mode
        "-c",
        code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except (TimeoutError, asyncio.TimeoutError):  # noqa: UP041  (3.10 alias differs)
        proc.kill()
        await proc.wait()
        return ExecResult(False, "", f"timeout after {timeout}s", -1)

    return ExecResult(
        ok=proc.returncode == 0,
        stdout=out.decode(errors="replace")[:MAX_OUTPUT],
        stderr=err.decode(errors="replace")[:MAX_OUTPUT],
        returncode=proc.returncode or 0,
    )


@tool(
    name="python_exec",
    description="Execute Python code in an isolated sandbox and return its output.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source to run"},
            "timeout": {"type": "number", "description": "Seconds (default 5)"},
        },
        "required": ["code"],
    },
)
async def python_exec(code: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Tool handler: run code, return stdout (and stderr on failure)."""
    result = await run_python(code, timeout=timeout)
    if result.ok:
        return result.stdout.strip() or "(no output)"
    return f"error (exit {result.returncode}):\n{result.stderr.strip()}"
