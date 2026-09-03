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
from app.tools import wikipedia
from app.tools.deep_search import deep_research
from app.tools.fetch_extract import enrich_sources
from app.tools.query_planner import plan_queries

ChatFn = Callable[[list[dict]], Awaitable[str]]
SearchFn = Callable[[str], Awaitable[list[dict]]]


async def default_search(query: str, max_results: int = 4) -> list[dict]:
    """Keyless deep research: full Wikipedia extracts + arXiv papers.

    Fetches paragraph-length article content (not one-line snippets) and adds real
    arXiv papers so the researcher has substantial, citable evidence — all free and
    keyless. Falls back to plain Wikipedia search if the richer path yields nothing.
    """
    results = await deep_research(query, max_results=max_results)
    results = results or await wikipedia.search(query, max_results=max_results)
    # Deepen evidence: replace shallow snippets with full page text (best-effort).
    if results and get_settings().research_fetch_fulltext:
        try:
            results = await enrich_sources(results, limit=8)
        except Exception:
            pass  # enrichment must never break a research step
    return results


ROLE_PROMPTS: dict[str, str] = {
    "researcher": (
        "You are a Researcher agent. Gather the relevant facts, options, and "
        "sources needed for the task. When web search results are provided, ground "
        "your findings in them and cite the exact source URLs you rely on. Never "
        "invent URLs or statistics. Return concise, well-organized findings."
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
    "You are a strict Critic/Judge. Given the mission objective, a task and a "
    "candidate answer, decide whether the answer adequately completes the task AND "
    "stays on-topic for the mission objective. Respond with ONLY a JSON object: "
    '{"accepted": true|false, "score": 0.0-1.0, "feedback": "concrete improvements '
    'if not accepted"}.'
)
_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)

# --- topic-drift detection (deterministic, LLM-free) ---
_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "for",
    "nor",
    "of",
    "to",
    "in",
    "on",
    "at",
    "by",
    "with",
    "from",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "their",
    "our",
    "your",
    "you",
    "we",
    "they",
    "he",
    "she",
    "them",
    "his",
    "her",
    "which",
    "who",
    "whom",
    "what",
    "how",
    "why",
    "when",
    "where",
    "into",
    "over",
    "under",
    "than",
    "then",
    "also",
    "can",
    "could",
    "should",
    "would",
    "will",
    "may",
    "might",
    "must",
    "do",
    "does",
    "did",
    "not",
    "no",
    "yes",
    "all",
    "any",
    "each",
    "more",
    "most",
    "some",
    "such",
    "using",
    "use",
    "used",
    "via",
    "per",
    "about",
    "across",
    "between",
    "given",
}
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+_-]{2,}")


@dataclass
class Verdict:
    accepted: bool
    score: float
    feedback: str


@dataclass
class DriftVerdict:
    drifted: bool
    overlap: float
    note: str


def _salient(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text or "") if w.lower() not in _STOP}


def detect_topic_drift(
    objective: str,
    description: str,
    output: str,
    min_overlap: float = 0.12,
) -> DriftVerdict:
    """Flag output that shares almost none of the mission's key terms (off-topic).

    Deterministic and LLM-free: compares the salient vocabulary of the objective +
    task against the output. Only substantial outputs are judged, so short or empty
    answers are never spuriously flagged.
    """
    key = _salient(objective) | _salient(description)
    if not key or len((output or "").strip()) < 80:
        return DriftVerdict(False, 1.0, "")
    overlap = len(key & _salient(output)) / len(key)
    if overlap < min_overlap:
        top = ", ".join(sorted(key, key=len, reverse=True)[:6])
        return DriftVerdict(
            True,
            overlap,
            f"Output shares only {overlap:.0%} of the mission's key terms; expected "
            f"content about: {top}.",
        )
    return DriftVerdict(False, overlap, "")


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

    async def review(self, description: str, output: str, objective: str = "") -> Verdict:
        ctx = f"Mission objective: {objective}\n\n" if objective else ""
        raw = await self._chat(
            [
                {"role": "system", "content": _CRITIC_SYSTEM},
                {"role": "user", "content": f"{ctx}Task: {description}\n\nAnswer:\n{output}"},
            ]
        )
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
        search_fn: SearchFn | None = None,
    ):
        self._repo = repo
        self._chat = chat_fn or llm.chat
        # _UNSET -> default critic; explicit None -> critic disabled
        self._critic = Critic(self._chat) if critic is _UNSET else critic
        self._max_replans = max_replans
        self._search = search_fn  # None -> no live search (offline/CI default)

    async def _generate(
        self,
        role: str,
        description: str,
        feedback: str = "",
        context: str = "",
    ) -> str:
        system = ROLE_PROMPTS.get(role, ROLE_PROMPTS[DEFAULT_ROLE])
        user = description
        if context:
            user = (
                f"{description}\n\nWeb search results (ground your answer in these "
                f"and cite the URLs you use):\n{context}"
            )
        if feedback:
            user = f"{user}\n\nReviewer feedback to address:\n{feedback}"
        return (
            await self._chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]
            )
        ).strip()

    async def _research(self, query: str) -> tuple[str, list[str], list[dict]]:
        """Plan focused queries, search each, merge; return (context, urls, raw dicts)."""
        if self._search is None:
            return "", [], []
        s = get_settings()
        chat = self._chat if s.research_query_planner else None
        queries = await plan_queries(query, chat, max_queries=s.research_max_queries)
        results: list[dict] = []
        seen: set[str] = set()
        for q in queries:
            for r in await self._search(q):
                url = (r.get("url") or "").strip()
                if url and url not in seen:
                    seen.add(url)
                    results.append(r)
        results = results[: s.research_max_sources]
        ctx, urls = [], []
        for r in results:
            url = (r.get("url") or "").strip()
            snippet = (r.get("snippet") or r.get("title") or "").strip()
            if url and snippet:
                ctx.append(f"- {snippet} ({url})")
                urls.append(url)
        return "\n".join(ctx), urls, results

    async def _persist_sources(self, mission_id: int, results: list[dict]) -> None:
        """Store gathered source metadata on the mission for rich references."""
        if not results:
            return
        try:
            fresh = await self._repo.get(mission_id)
            meta = dict(fresh.meta or {}) if fresh else {}
            by_url = {s.get("url"): s for s in (meta.get("sources") or []) if s.get("url")}
            for r in results:
                u = (r.get("url") or "").strip()
                if u:
                    by_url[u] = {
                        "url": u,
                        "title": r.get("title", ""),
                        "authors": r.get("authors") or [],
                        "year": r.get("year"),
                        "venue": r.get("venue") or "",
                        "snippet": (r.get("snippet") or "")[:1500],
                    }
            meta["sources"] = list(by_url.values())
            await self._repo.update_meta(mission_id, meta)
        except Exception:
            pass  # telemetry must never break execution

    async def _record_flag(self, mission_id: int, task_id: int, note: str) -> None:
        """Persist a critic flag onto the mission meta (best-effort, race-tolerant)."""
        try:
            fresh = await self._repo.get(mission_id)
            meta = dict(fresh.meta or {}) if fresh else {}
            flags = list(meta.get("critic_flags", []))
            flags.append({"task_id": task_id, "type": "topic_drift", "note": note})
            meta["critic_flags"] = flags
            await self._repo.update_meta(mission_id, meta)
        except Exception:
            pass  # telemetry must never break execution

    async def __call__(self, task: Task) -> str:
        mission = await self._repo.get(task.mission_id)
        objective = mission.objective if mission else ""
        roles = (mission.meta.get("roles") if mission else None) or {}
        role = roles.get(str(task.id), DEFAULT_ROLE)

        # Researcher tasks gather real sources via web search before answering.
        context, urls = ("", [])
        if role == "researcher":
            context, urls, results = await self._research(f"{objective} {task.description}".strip())
            await self._persist_sources(task.mission_id, results)

        output = await self._generate(role, task.description, context=context)

        # Topic-drift guard: if the answer is off-topic vs the objective, flag it and
        # regenerate once with a corrective instruction (separate from critic replans).
        drift = detect_topic_drift(objective, task.description, output)
        if drift.drifted:
            await self._record_flag(task.mission_id, task.id, drift.note)
            output = await self._generate(
                role,
                task.description,
                context=context,
                feedback=(
                    f"Your previous answer drifted off-topic. It MUST directly "
                    f"address the mission objective: {objective}. {drift.note} "
                    f"Rewrite it to focus only on the objective."
                ),
            )

        # Quality critic loop (bounded replans).
        for _ in range(self._max_replans):
            if self._critic is None:
                break
            verdict = await self._critic.review(task.description, output, objective)
            if verdict.accepted:
                break
            output = await self._generate(
                role, task.description, context=context, feedback=verdict.feedback
            )

        # Guarantee the real sources are present for the report's evidence ledger.
        if urls:
            have = {u for u in urls if u in output}
            missing = [u for u in urls if u not in have]
            if missing:
                output = f"{output}\n\nSources:\n" + "\n".join(missing)
        return output


def build_executor(repo: MissionRepository, chat_fn: ChatFn | None = None) -> TaskExecutor:
    """Pick the executor per config: multi-agent (role + critic) or plain chat."""
    s = get_settings()
    if s.multi_agent_enabled:
        search_fn = None
        if s.research_enabled:

            async def search_fn(q: str) -> list[dict]:
                return await default_search(q, max_results=s.research_max_results)

        return MultiAgentExecutor(
            repo,
            chat_fn=chat_fn,
            critic=Critic(chat_fn or llm.chat, threshold=s.critic_threshold),
            max_replans=s.max_replans,
            search_fn=search_fn,
        )
    return chat_executor(chat_fn)
