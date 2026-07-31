"""LLM-based extraction of entities and relations from text.

Two passes over a chunk: first pull typed entities, then ask for
subject–predicate–object relations *between those entities*. Names are
normalized and deduped so the same real-world thing doesn't become three nodes.

Parsing is defensive (mirrors the reranker): a malformed LLM response yields an
empty list rather than crashing, so ingest degrades gracefully. The `chat_fn`
is injectable, so extraction is unit-tested with a fake LLM — no network in CI.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.core import llm
from app.graph.normalize import dedup_entities, normalize_name, parse_json_array
from app.graph.schema import Entity, GraphExtraction, Relation

ChatFn = Callable[[list[dict]], Awaitable[str]]

_ENTITY_SYSTEM = (
    "You extract named entities from text. Return ONLY a JSON array of objects "
    'with keys "name" and "type" (e.g. Person, Organization, Product, Concept, '
    'Place). Example: [{"name": "Ada Lovelace", "type": "Person"}].'
)
_RELATION_SYSTEM = (
    "You extract relationships between entities. Given the text and a list of "
    "known entities, return ONLY a JSON array of objects with keys "
    '"subject", "predicate", "object". Use entity names exactly as given, and '
    "only emit a relation when both subject and object are in the entity list."
)

async def extract_entities(text: str, chat_fn: ChatFn | None = None) -> list[Entity]:
    """Extract normalized, deduped entities from `text`."""
    chat_fn = chat_fn or llm.chat
    messages = [
        {"role": "system", "content": _ENTITY_SYSTEM},
        {"role": "user", "content": text},
    ]
    entities: list[Entity] = []
    for item in parse_json_array(await chat_fn(messages)):
        name = normalize_name(item.get("name", ""))
        if not name:
            continue
        etype = (item.get("type") or "Entity").strip() or "Entity"
        entities.append(Entity(name=name, type=etype))
    return dedup_entities(entities)


async def extract_relations(
    text: str, entities: list[Entity], chat_fn: ChatFn | None = None
) -> list[Relation]:
    """Extract relations whose subject and object are both known entities."""
    if not entities:
        return []
    chat_fn = chat_fn or llm.chat
    known = {e.name.casefold() for e in entities}
    entity_list = ", ".join(e.name for e in entities)
    messages = [
        {"role": "system", "content": _RELATION_SYSTEM},
        {"role": "user", "content": f"Entities: {entity_list}\n\nText:\n{text}"},
    ]
    relations: list[Relation] = []
    for item in parse_json_array(await chat_fn(messages)):
        subj = normalize_name(item.get("subject", ""))
        pred = normalize_name(item.get("predicate", ""))
        obj = normalize_name(item.get("object", ""))
        if not (subj and pred and obj):
            continue
        if subj.casefold() in known and obj.casefold() in known:
            relations.append(Relation(subject=subj, predicate=pred, object=obj))
    return relations


async def extract_graph(text: str, chat_fn: ChatFn | None = None) -> GraphExtraction:
    """Full extraction: entities then the relations among them."""
    entities = await extract_entities(text, chat_fn)
    relations = await extract_relations(text, entities, chat_fn)
    return GraphExtraction(entities=entities, relations=relations)
