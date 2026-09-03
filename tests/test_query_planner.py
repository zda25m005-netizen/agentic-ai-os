"""Query planner: keyless decomposition + LLM acronym expansion, with safe fallback."""

from app.tools.query_planner import plan_queries


async def test_keyless_decomposition_without_llm():
    qs = await plan_queries("Evaluate LLM memory: RAG, Fine-Tuning, Structured Memory", None)
    assert qs  # never empty
    assert any("RAG" in q for q in qs)  # per-option queries produced
    assert any("Structured Memory" in q for q in qs)


async def test_llm_expands_acronyms():
    async def fake(_m):
        return (
            '["retrieval augmented generation language model", '
            '"fine tuning large language model", "structured memory llm agents"]'
        )

    qs = await plan_queries("Evaluate LLM memory: RAG, Fine-Tuning, Structured Memory", fake)
    assert "retrieval augmented generation language model" in qs
    assert len(qs) <= 5


async def test_bad_llm_falls_back_to_keyless():
    async def bad(_m):
        return "not json"

    qs = await plan_queries("Compare A and B", bad)
    assert qs and all(isinstance(q, str) for q in qs)


async def test_llm_exception_falls_back():
    async def boom(_m):
        raise RuntimeError("down")

    qs = await plan_queries("Compare A and B", boom)
    assert qs
