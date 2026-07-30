"""Graph client tests.

No live Neo4j: we monkeypatch GraphDatabase.driver with fakes so the wrapper's
config wiring, session lifecycle, and row mapping are all verified in CI.
"""
from app.graph import client as gc


class FakeRecord:
    def __init__(self, d: dict):
        self._d = d

    def data(self) -> dict:
        return self._d


class FakeResult:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def __iter__(self):
        return iter(FakeRecord(r) for r in self._rows)


class FakeSession:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.ran: tuple | None = None
        self.closed = False

    def run(self, cypher: str, params: dict):
        self.ran = (cypher, params)
        return FakeResult(self._rows)

    def close(self):
        self.closed = True


class FakeDriver:
    def __init__(self, rows: list[dict] | None = None):
        self._rows = rows or []
        self.session_obj: FakeSession | None = None
        self.closed = False

    def session(self, database=None):
        self.session_obj = FakeSession(self._rows)
        return self.session_obj

    def close(self):
        self.closed = True


def test_get_graph_driver_passes_config(monkeypatch):
    captured = {}

    def fake_driver(uri, auth=None, **kw):
        captured["uri"] = uri
        captured["auth"] = auth
        return FakeDriver()

    monkeypatch.setattr(gc.GraphDatabase, "driver", fake_driver)
    gc.close_driver()

    d = gc.get_graph_driver(uri="bolt://x:7687", user="u", password="p")
    assert captured["uri"] == "bolt://x:7687"
    assert captured["auth"] == ("u", "p")
    assert isinstance(d, FakeDriver)


def test_default_driver_is_cached(monkeypatch):
    calls = {"n": 0}

    def fake_driver(uri, auth=None, **kw):
        calls["n"] += 1
        return FakeDriver()

    monkeypatch.setattr(gc.GraphDatabase, "driver", fake_driver)
    gc.close_driver()

    a = gc.get_graph_driver()
    b = gc.get_graph_driver()
    assert a is b
    assert calls["n"] == 1  # built once, reused
    gc.close_driver()


def test_run_query_returns_dicts_and_closes_session():
    fake = FakeDriver(rows=[{"name": "A"}, {"name": "B"}])
    out = gc.run_query("MATCH (n) RETURN n", {"x": 1}, driver=fake)
    assert out == [{"name": "A"}, {"name": "B"}]
    assert fake.session_obj.ran == ("MATCH (n) RETURN n", {"x": 1})
    assert fake.session_obj.closed is True


def test_verify_connectivity_true():
    fake = FakeDriver(rows=[{"ok": 1}])
    assert gc.verify_connectivity(driver=fake) is True


def test_verify_connectivity_false_on_error():
    class Boom(FakeDriver):
        def session(self, database=None):
            raise RuntimeError("down")

    assert gc.verify_connectivity(driver=Boom()) is False
