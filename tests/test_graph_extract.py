"""Entity/relation extraction tests.

A fake chat_fn returns canned JSON based on the system prompt (entity vs
relation pass), so the parsing, normalization, dedup, and endpoint-filtering
logic are all exercised without a live LLM.
"""
from app.graph import extract, normalize
from app.graph.schema import Entity


def make_fake(entities_json: str, relations_json: str):
    async def fake(messages):
        system = messages[0]["content"].lower()
        return relations_json if "relationship" in system else entities_json

    return fake


# --- pure helpers ---

def test_normalize_name_collapses_whitespace():
    assert normalize.normalize_name("  Ada   Lovelace \n") == "Ada Lovelace"
    assert normalize.normalize_name("") == ""


def test_parse_json_array_handles_garbage():
    assert normalize.parse_json_array("not json") == []
    assert normalize.parse_json_array('[{"name": "X"}]') == [{"name": "X"}]
    # ignores non-dict members
    assert normalize.parse_json_array('["x", {"a": 1}]') == [{"a": 1}]


def test_dedup_prefers_specific_type():
    ents = [
        Entity(name="OpenAI", type="Entity"),
        Entity(name="openai", type="Organization"),
    ]
    out = normalize.dedup_entities(ents)
    assert len(out) == 1
    assert out[0].type == "Organization"


# --- entity extraction ---

async def test_extract_entities_normalizes_and_dedupes():
    ents_json = """[
        {"name": "  Ada  Lovelace ", "type": "Person"},
        {"name": "Ada Lovelace", "type": "Person"},
        {"name": "", "type": "Person"},
        {"name": "Analytical Engine", "type": "Product"}
    ]"""
    fn = make_fake(ents_json, "[]")
    ents = await extract.extract_entities("some text", chat_fn=fn)
    names = sorted(e.name for e in ents)
    assert names == ["Ada Lovelace", "Analytical Engine"]  # deduped, blank dropped


# --- relation extraction ---

async def test_extract_relations_filters_unknown_endpoints():
    entities = [Entity(name="Ada Lovelace"), Entity(name="Analytical Engine")]
    rels_json = """[
        {"subject": "Ada Lovelace", "predicate": "worked on", "object": "Analytical Engine"},
        {"subject": "Ada Lovelace", "predicate": "knew", "object": "Charles Babbage"},
        {"subject": "Ada Lovelace", "predicate": "", "object": "Analytical Engine"}
    ]"""
    fn = make_fake("[]", rels_json)
    rels = await extract.extract_relations("text", entities, chat_fn=fn)
    assert len(rels) == 1  # unknown endpoint + empty predicate dropped
    assert rels[0].object == "Analytical Engine"


async def test_extract_relations_empty_when_no_entities():
    fn = make_fake("[]", '[{"subject":"a","predicate":"b","object":"c"}]')
    assert await extract.extract_relations("t", [], chat_fn=fn) == []


# --- end to end ---

async def test_extract_graph_end_to_end():
    ents_json = (
        '[{"name": "Ada Lovelace", "type": "Person"}, '
        '{"name": "Analytical Engine", "type": "Product"}]'
    )
    rels_json = (
        '[{"subject": "Ada Lovelace", "predicate": "worked on", '
        '"object": "Analytical Engine"}]'
    )
    fn = make_fake(ents_json, rels_json)
    graph = await extract.extract_graph("text about Ada", chat_fn=fn)
    assert {e.name for e in graph.entities} == {"Ada Lovelace", "Analytical Engine"}
    assert len(graph.relations) == 1
    assert graph.relations[0].predicate == "worked on"
