import asyncio

import app.core.llm as llm_mod
from app.obs import tracing


def _reset():
    tracing.clear_trace()


def test_estimate_cost_known_model():
    cost = tracing.estimate_cost("gpt-4o-mini", 1000, 1000)
    assert round(cost, 6) == round((0.15 + 0.60) / 1000, 6)


def test_estimate_cost_unknown_model_is_zero():
    assert tracing.estimate_cost("mystery", 1000, 1000) == 0.0


def test_record_span_without_trace_is_noop():
    _reset()
    tracing.record_span("x", 5.0)
    assert tracing.current_trace() is None


def test_trace_summary_aggregates():
    _reset()
    trace = tracing.start_trace()
    tracing.record_span("llm.chat", 10.0, model="gpt-4o-mini",
                        prompt_tokens=100, completion_tokens=50)
    tracing.record_span("llm.chat", 20.0, model="gpt-4o-mini",
                        prompt_tokens=200, completion_tokens=25)
    s = trace.summary()
    assert s["spans"] == 2
    assert s["total_ms"] == 30.0
    assert s["prompt_tokens"] == 300
    assert s["completion_tokens"] == 75
    assert s["by_name"] == {"llm.chat": 2}
    assert s["est_cost_usd"] > 0
    _reset()


async def test_traced_records_span():
    _reset()
    tracing.start_trace()

    async def work():
        await asyncio.sleep(0)
        return 42

    result = await tracing.traced("unit", work())
    assert result == 42
    assert tracing.current_trace().summary()["by_name"] == {"unit": 1}
    _reset()


async def test_chat_raw_records_llm_span(monkeypatch):
    _reset()
    monkeypatch.setattr(llm_mod, "is_configured", lambda: True)

    async def fake_post(payload):
        return {
            "choices": [{"message": {"content": "hi"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3},
        }

    monkeypatch.setattr(llm_mod, "_post", fake_post)

    trace = tracing.start_trace()
    msg = await llm_mod.chat_raw([{"role": "user", "content": "hello"}])
    assert msg["content"] == "hi"

    s = trace.summary()
    assert s["by_name"].get("llm.chat") == 1
    assert s["prompt_tokens"] == 12
    assert s["completion_tokens"] == 3
    _reset()
