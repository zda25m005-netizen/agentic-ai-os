"""Query planner — turn a research objective into focused, acronym-expanded searches.

A single combined query ("RAG Fine-Tuning Structured Memory") makes web search
return generic glossary pages, so the relevance gate drops everything and the
report ends up with no real sources. This planner asks the LLM to expand acronyms
to their full technical term (RAG -> retrieval-augmented generation) and to emit
one focused query per option plus an overview, so search finds the *specific*
authoritative pages. It always falls back to a keyless keyword decomposition, so
it degrades to the previous behaviour when no LLM is available or the call fails.
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable

ChatFn = Callable[[list[dict]], Awaitable[str]]
_ARR = re.compile(r"\[.*\]", re.DOTALL)

_SYS = (
    "You turn a research objective into web-search queries that find AUTHORITATIVE, "
    "on-topic sources. Rules: EXPAND every acronym to its full technical term "
    "(e.g. RAG -> retrieval augmented generation; LLM -> large language model); "
    "write ONE focused query per key option/technology named in the objective, PLUS "
    "one overview query; each query is 3-8 plain keywords — no punctuation, no quotes, "
    "no boolean operators. Return ONLY a JSON array of 3-6 short query strings."
)


def _keyword_queries(query: str, max_queries: int) -> list[str]:
    """Keyless fallback: the combined query + one per comma/and/vs-separated option."""
    from app.tools.deep_search import clean_query

    q = query.strip()
    tail = q.split(":", 1)[-1] if ":" in q else q
    parts = re.split(r",|\band\b|\bvs\.?\b|\bversus\b", tail, flags=re.I)
    candidates = [clean_query(q)]
    for p in parts:
        c = clean_query(p)
        if c and len(c.split()) <= 6:
            candidates.append(c)
    out: list[str] = []
    seen: set[str] = set()
    for x in candidates:
        if x and x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
    return out[:max_queries]


async def plan_queries(
    query: str, chat_fn: ChatFn | None = None, max_queries: int = 5
) -> list[str]:
    """Return focused search queries (LLM-planned when available, else keyless)."""
    base = _keyword_queries(query, max_queries)
    if chat_fn is None:
        return base
    try:
        raw = await chat_fn(
            [
                {"role": "system", "content": _SYS},
                {"role": "user", "content": query[:600]},
            ]
        )
        m = _ARR.search(raw or "")
        arr = json.loads(m.group(0)) if m else []
        planned = [
            str(x).strip() for x in arr if isinstance(x, str) and 2 <= len(str(x).split()) <= 10
        ]
        if planned:
            out: list[str] = []
            seen: set[str] = set()
            for x in planned + base:  # LLM queries first, keyless as safety net
                if x.lower() not in seen:
                    seen.add(x.lower())
                    out.append(x)
            return out[:max_queries]
    except Exception:
        pass
    return base
