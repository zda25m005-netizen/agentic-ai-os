"""Backend mirror of the character registry.

Kept in sync with `frontend/app/lib/characters.ts`. The backend only needs the id / name /
accent / personality to validate `character_id`, auto-assign an available character, and
serve `GET /characters`. The visual rendering lives entirely in the frontend component.
"""

from __future__ import annotations

# (id, name, accent, personality) — 13 characters, same family as the frontend.
CHARACTERS: list[dict] = [
    {"id": "nova", "name": "Nova", "accent": "#a78bfa", "personality": "Curious"},
    {"id": "milo", "name": "Milo", "accent": "#f59e0b", "personality": "Friendly"},
    {"id": "luna", "name": "Luna", "accent": "#6366f1", "personality": "Analytical"},
    {"id": "atlas", "name": "Atlas", "accent": "#38bdf8", "personality": "Focused"},
    {"id": "coco", "name": "Coco", "accent": "#ec4899", "personality": "Friendly"},
    {"id": "theo", "name": "Theo", "accent": "#14b8a6", "personality": "Concise"},
    {"id": "nori", "name": "Nori", "accent": "#22c55e", "personality": "Creative"},
    {"id": "echo", "name": "Echo", "accent": "#06b6d4", "personality": "Analytical"},
    {"id": "momo", "name": "Momo", "accent": "#fb7185", "personality": "Creative"},
    {"id": "pip", "name": "Pip", "accent": "#84cc16", "personality": "Curious"},
    {"id": "peter", "name": "Prospect Peter", "accent": "#4f8cff", "personality": "Focused"},
    {"id": "ivy", "name": "Invoice Ivy", "accent": "#10b981", "personality": "Analytical"},
    {"id": "rory", "name": "Research Rory", "accent": "#fb923c", "personality": "Analytical"},
]

CHARACTER_IDS: list[str] = [c["id"] for c in CHARACTERS]
CHARACTER_MAP: dict[str, dict] = {c["id"]: c for c in CHARACTERS}


def is_valid_character(character_id: str | None) -> bool:
    return bool(character_id) and character_id in CHARACTER_MAP


def pick_available_character(used_ids: list[str]) -> str:
    """First unused character, else the first in the roster (reuse allowed)."""
    used = set(used_ids)
    for c in CHARACTERS:
        if c["id"] not in used:
            return c["id"]
    return CHARACTERS[0]["id"]
