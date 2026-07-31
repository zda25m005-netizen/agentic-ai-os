"""Graph extraction schemas.

Typed containers for what we pull out of a chunk before it goes into Neo4j:
`Entity` nodes and `Relation` (subject–predicate–object) edges between them.
Kept deliberately small — the LLM returns loose JSON, and these models are the
validation boundary that turns it into something safe to MERGE.
"""
from __future__ import annotations

from pydantic import BaseModel


class Entity(BaseModel):
    """A named node in the knowledge graph."""

    name: str
    type: str = "Entity"


class Relation(BaseModel):
    """A directed, typed edge: (subject) -[predicate]-> (object)."""

    subject: str
    predicate: str
    object: str


class GraphExtraction(BaseModel):
    """Everything extracted from a single chunk of text."""

    entities: list[Entity] = []
    relations: list[Relation] = []
