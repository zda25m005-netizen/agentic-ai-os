from fastapi.testclient import TestClient

from app.api.main import app
from app.core.config import get_settings

client = TestClient(app)


def test_settings_defaults():
    s = get_settings()
    assert s.llm_model
    assert s.qdrant_url.startswith("http")


def test_config_endpoint():
    r = client.get("/config")
    assert r.status_code == 200
    body = r.json()
    assert "app_env" in body
    assert "llm_key_configured" in body
