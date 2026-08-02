"""GraphRAG fusion + tool + endpoint-mode tests (all with fakes, no live DB)."""
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import llm
from app.graph import fusion, retrieval
from app.rag import retriever, vectorstore
from app.rag.vectorstore import SearchHit

client = TestClient(app)


def _hit(source, score, text="passage"):
    return SearchHit(id=source, score=score, payload={"source": source, "text": text})


# --- fusion (pure RRF over sources) ---

def test_fuse_hits_boosts_shared_source():
    rag = [_hit("A", 0.9), _hit("B", 0.5), _hit("C", 0.3)]
    graph = [_hit("C", 2.0), _hit("A", 1.0)]  # C and A appear in both lists
    fused = fusion.fuse_hits(rag, graph, limit=3)
    ids = [h.id for h in fused]
    # A and C are in both lists so they rank above B (which is only in rag)
    assert ids.index("A") < ids.index("B")
    assert ids.index("C") < ids.index("B")
    # fused hit keeps the RAG payload (has text)
    assert fused[0].payload.get("text") == "passage"


def test_build_graphrag_messages_prepends_graph_facts():
    msgs = fusion.build_graphrag_messages("q?", [_hit("A", 0.9)], "X —[rel]→ Y")
    user = msgs[-1]["content"]
    assert "Knowledge-graph facts:" in user
    assert "X —[rel]→ Y" in user
    assert "Passages:" in user


def test_build_graphrag_messages_without_graph():
    msgs = fusion.build_graphrag_messages("q?", [_hit("A", 0.9)], "")
    assert "Knowledge-graph facts:" not in msgs[-1]["content"]


# --- graph_chunk_hits ---

class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def run(self, cypher, params):
        self.last = (cypher, params)

        class R:
            def __init__(s, rows):
                s._rows = rows

            def __iter__(s):
                return iter(type("Rec", (), {"data": staticmethod(lambda r=r: r)})()
                            for r in s._rows)

        return R(self._rows)

    def close(self):
        pass


class _FakeDriver:
    def __init__(self, rows):
        self._rows = rows

    def session(self, database=None):
        self.session_obj = _FakeSession(self._rows)
        return self.session_obj

    def close(self):
        pass


async def test_graph_chunk_hits_ranks_by_mentions():
    from app.graph.schema import Entity

    async def fake_extract(_q):
        return [Entity(name="Ada")]

    rows = [{"source": "bio.pdf", "mentions": 3}, {"source": "notes.md", "mentions": 1}]
    hits = await retrieval.graph_chunk_hits(
        "who is Ada?", driver=_FakeDriver(rows), extract_fn=fake_extract
    )
    assert [h.id for h in hits] == ["bio.pdf", "notes.md"]
    assert hits[0].score == 3.0


# --- graph_search tool ---

async def test_graph_search_tool_returns_facts(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: True)

    async def fake_ctx(query, hops=2):
        return retrieval.GraphContext(triples=[("A", "rel", "B")], text="A —[rel]→ B")

    monkeypatch.setattr("app.tools.graph_search.get_graph_context", fake_ctx)
    from app.tools.graph_search import graph_search

    out = await graph_search("how are A and B related?")
    assert "A —[rel]→ B" in out


# --- /ask mode switch ---

def test_ask_vector_mode_unchanged(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: True)
    monkeypatch.setattr(vectorstore, "get_client", lambda *a, **k: object())

    async def fake_retrieve(query, client, collection="documents", limit=5):
        return [_hit("geo.pdf", 0.91, "The capital is Paris.")]

    async def fake_chat(messages, temperature=0.2):
        return "Paris [1]."

    monkeypatch.setattr(retriever, "retrieve", fake_retrieve)
    monkeypatch.setattr(llm, "chat", fake_chat)

    r = client.post("/ask", json={"question": "capital?"})  # no mode -> vector
    assert r.status_code == 200
    assert "Paris" in r.json()["answer"]


def test_ask_graph_mode(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: True)

    async def fake_ctx(question):
        return retrieval.GraphContext(triples=[("Ada", "worked on", "Engine")],
                                      text="Ada —[worked on]→ Engine")

    async def fake_chat(messages, temperature=0.2):
        return "Ada worked on the Engine."

    monkeypatch.setattr("app.api.main.get_graph_context", fake_ctx)
    monkeypatch.setattr(llm, "chat", fake_chat)

    r = client.post("/ask", json={"question": "what did Ada build?", "mode": "graph"})
    assert r.status_code == 200
    assert "Engine" in r.json()["answer"]
    assert r.json()["sources"] == []
