"""Langfuse export tests — a fake client records calls; no SDK/server needed."""
from app.obs import langfuse_export
from app.obs.tracing import Span, Trace, estimate_cost


class FakeTrace:
    def __init__(self, sink):
        self.sink = sink

    def span(self, **kw):
        self.sink.append(("span", kw))

    def generation(self, **kw):
        self.sink.append(("generation", kw))


class FakeClient:
    def __init__(self):
        self.calls = []
        self.trace_kw = None
        self.flushed = False

    def trace(self, **kw):
        self.trace_kw = kw
        return FakeTrace(self.calls)

    def flush(self):
        self.flushed = True


def _trace_with_spans() -> Trace:
    t = Trace()
    t.spans.append(Span("planner", 12.0))
    t.spans.append(Span("llm.chat", 300.0,
                        {"model": "gpt-4o-mini", "prompt_tokens": 100, "completion_tokens": 20}))
    return t


def test_export_maps_spans_and_generations():
    client = FakeClient()
    ok = langfuse_export.export_trace(_trace_with_spans(), name="agent-run",
                                      metadata={"goal": "hi"}, client=client)
    assert ok is True
    kinds = [c[0] for c in client.calls]
    assert kinds == ["span", "generation"]  # planner -> span, llm.chat -> generation
    gen = next(kw for kind, kw in client.calls if kind == "generation")
    assert gen["model"] == "gpt-4o-mini"
    assert gen["usage"] == {"input": 100, "output": 20}
    assert client.flushed is True


def test_metadata_includes_cost_and_tokens():
    client = FakeClient()
    langfuse_export.export_trace(_trace_with_spans(), metadata={"goal": "hi"}, client=client)
    meta = client.trace_kw["metadata"]
    assert meta["goal"] == "hi"
    assert meta["prompt_tokens"] == 100
    assert meta["completion_tokens"] == 20
    # cost matches the tracing estimate for this usage
    assert meta["est_cost_usd"] == round(estimate_cost("gpt-4o-mini", 100, 20), 6)


def test_export_is_noop_without_client(monkeypatch):
    monkeypatch.setattr(langfuse_export, "build_client", lambda: None)
    assert langfuse_export.export_trace(_trace_with_spans()) is False


def test_is_enabled_reflects_config(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config, "get_settings", lambda: type(
        "S", (), {"langfuse_public_key": "pk", "langfuse_secret_key": "sk",
                  "langfuse_host": "h"})())
    # is_enabled reads via the module's get_settings import
    monkeypatch.setattr(langfuse_export, "get_settings", config.get_settings)
    assert langfuse_export.is_enabled() is True
