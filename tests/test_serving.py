"""Fine-tuned serving routing/fallback tests (no torch)."""
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import llm
from app.finetune import serving

client = TestClient(app)


async def _api(_messages):
    return "api answer"


def _local(_messages):
    return "finetuned answer"


# --- routing ---

async def test_answer_uses_finetuned_when_available():
    text, label = await serving.answer(
        [{"role": "user", "content": "hi"}],
        api_chat=_api, local_generate=_local, available=True,
    )
    assert text == "finetuned answer" and label == "finetuned"


async def test_answer_uses_api_when_unavailable():
    text, label = await serving.answer(
        [{"role": "user", "content": "hi"}],
        api_chat=_api, local_generate=_local, available=False,
    )
    assert text == "api answer" and label == "api"


async def test_answer_falls_back_on_local_error():
    def boom(_messages):
        raise RuntimeError("torch missing")

    text, label = await serving.answer(
        [{"role": "user", "content": "hi"}],
        api_chat=_api, local_generate=boom, available=True,
    )
    assert text == "api answer" and label == "api"  # degraded, not crashed


# --- availability + labels ---

def test_finetuned_unavailable_by_default():
    # use_finetuned defaults to False, so it never routes to a missing model.
    assert serving.finetuned_available() is False
    assert serving.model_label() == "api"


def test_model_display_name():
    assert serving.model_display_name("finetuned").startswith("lora:")
    assert serving.model_display_name("api")  # returns the configured llm model


# --- endpoint reports which model answered ---

def test_chat_reports_model(monkeypatch):
    async def fake_chat(messages, temperature=0.2):
        return "pong"

    monkeypatch.setattr(llm, "is_configured", lambda: True)
    monkeypatch.setattr(llm, "chat", fake_chat)
    r = client.post("/chat", json={"message": "ping"})
    assert r.status_code == 200
    assert r.json()["reply"] == "pong"
    assert r.json()["model"]  # a model label is reported


def test_config_exposes_active_model():
    r = client.get("/config")
    assert "active_model" in r.json()
