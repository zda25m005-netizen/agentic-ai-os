"""Multi-agent execution: role-specialized workers + a critic with a replan loop.

Each task carries a role (`meta["roles"]`), and different roles deserve different
behavior — a Researcher gathers facts, an Analyst reasons over tradeoffs, an
Executor just does the thing. `MultiAgentExecutor` runs the task with the role's
system prompt, then a **Critic** judges the output; if it's rejected the task is
regenerated with the critic's feedback (a bounded replan loop). It's a
`TaskExecutor` (`async (Task) -> str`), so it drops into the runtime/worker with
no other change — the same tick that budgets, routes, and recovers now also runs
a self-critiquing multi-agent step.
"""
from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.core import llm
from app.core.config import get_settings
from app.missions.executor import TaskExecutor, chat_executor
from app.missions.models import Task
from app.missions.repository import MissionRepository

ChatFn = Callable[[list[dict]], Awaitable[str]]

ROLE_PROMPTS: dict[str, str] = {
    "researcher": (
        "You are a Researcher agent. Gather the relevant facts, options, and "
        "sources needed for the task. Be thorough and specific; return concise, "
        "well-organized findings."
    ),
    "analyst": (
        "You are an Analyst agent. Reason carefully over the inputs, weigh the "
        "tradeoffs, and produce a clear, well-justified analysis or recommendation."
    ),
    "executor": (
        "You are an Executor agent. Carry out the task directly and return a "
        "concise result describing what you did or produced."
    ),
}
DEFAULT_ROLE = "executor"

_UNSET = object()  # sentinel: distinguish "no critic given" from "critic disabled"

_CRITIC_SYSTEM = (
    "You are a strict Critic/Judge. Given a task and a candidate answer, decide "
    "whether the answer adequately completes the task. Respond with ONLY a JSON "
    'object: {"accepted": true|false, "score": 0.0-1.0, "feedback": "concrete '
    'improvements if not accepted"}.'
)
_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Verdict:
    accepted: bool
    score: float
    feedback: str


def _parse_obj(raw: str) -> dict | None:
    m = _OBJ_RE.search(raw or "")
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


class Critic:
    """LLM judge that accepts or rejects a candidate answer, with feedback."""

    def __init__(self, chat_fn: ChatFn | None = None, threshold: float = 0.6):
        self._chat = chat_fn or llm.chat
        self.threshold = threshold

    async def review(self, description: str, output: str) -> Verdict:
        raw = await self._chat([
            {"role": "system", "content": _CRITIC_SYSTEM},
            {"role": "user", "content": f"Task: {description}\n\nAnswer:\n{output}"},
        ])
        data = _parse_obj(raw)
        if data is None:  # never block progress on a malformed judge response
            return Verdict(accepted=True, score=1.0, feedback="")
        score = float(data.get("score", 1.0))
        accepted = bool(data.get("accepted", True)) and score >= self.threshold
        return Verdict(accepted=accepted, score=score, feedback=str(data.get("feedback", "")))


class MultiAgentExecutor:
    """A role-specialized, self-critiquing `TaskExecutor`."""

    def __init__(
        self,
        repo: MissionRepository,
        chat_fn: ChatFn | None = None,
        critic: Critic | None | object = _UNSET,
        max_replans: int = 1,
    ):
        self._repo = repo
        self._chat = chat_fn or llm.chat
        # _UNSET -> default critic; explicit None -> critic disabled
        self._critic = Critic(self._chat) if critic is _UNSET else critic
        self._max_replans = max_replans

    async def _generate(self, role: str, description: str, feedback: str = "") -> str:
        system = ROLE_PROMPTS.get(role, ROLE_PROMPTS[DEFAULT_ROLE])
        user = description
        if feedback:
            user = f"{description}\n\nReviewer feedback to address:\n{feedback}"
        return (await self._chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])).strip()

    async def _role_of(self, task: Task) -> str:
        mission = await self._repo.get(task.mission_id)
        roles = (mission.meta.get("roles") if mission else None) or {}
        return roles.get(str(task.id), DEFAULT_ROLE)

    async def __call__(self, task: Task) -> str:
        role = await self._role_of(task)
        output = await self._generate(role, task.description)
        for _ in range(self._max_replans):
            if self._critic is None:
                break
            verdict = await self._critic.review(task.description, output)
            if verdict.accepted:
                break
            output = await self._generate(role, task.description, feedback=verdict.feedback)
        return output


def build_executor(repo: MissionRepository, chat_fn: ChatFn | None = None) -> TaskExecutor:
    """Pick the executor per config: multi-agent (role + critic) or plain chat."""
    s = get_settings()
    if s.multi_agent_enabled:
        return MultiAgentExecutor(
            repo,
            chat_fn=chat_fn,
            critic=Critic(chat_fn or llm.chat, threshold=s.critic_threshold),
            max_replans=s.max_replans,
        )
    return chat_executor(chat_fn)
