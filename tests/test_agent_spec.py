"""Agent spec generation (Phase 5) — deterministic template matching + cue detection."""

from app.agent_registry.spec import deterministic_spec, generate_spec


def test_matches_job_search_and_schedule_and_approval():
    s = deterministic_spec(
        "Find AI/ML jobs every morning, dedupe them and ask me before sending applications."
    )
    assert s["template_id"] == "job-search"
    assert "job_search" in s["tools"]
    assert s["schedule"] == {"cadence": "daily", "time": "08:00"}
    assert s["approval_policy"] == {"require_approval": True}
    assert s["suggested_character_id"] == "peter"
    assert s["generated_by"] == "deterministic"


def test_matches_phd_and_weekly():
    s = deterministic_spec("Find funded PhD positions in Norway every monday")
    assert s["template_id"] == "phd-finder"
    assert s["schedule"] == {"cadence": "weekly", "day": "monday"}


def test_defaults_to_research():
    s = deterministic_spec("Summarize these three papers for me")
    assert s["template_id"] == "research"
    assert s["name"]  # always names the agent


async def test_generate_spec_without_llm_is_deterministic():
    s = await generate_spec("find scholarships for AI masters", chat_fn=None, use_llm=False)
    assert s["template_id"] == "scholarship-finder"
    assert s["generated_by"] == "deterministic"


async def test_generate_spec_llm_falls_back_on_bad_output():
    async def bad_chat(_messages):
        return "not json at all"

    s = await generate_spec("optimize my resume", chat_fn=bad_chat, use_llm=True)
    # unusable LLM output -> deterministic draft preserved
    assert s["template_id"] == "resume-optimizer"
    assert s["generated_by"] == "deterministic"
