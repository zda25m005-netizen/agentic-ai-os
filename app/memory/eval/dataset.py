"""Local memory-evaluation FIXTURES (not a benchmark; no external numbers claimed).

Each scenario seeds some memories, optionally applies follow-up writes (updates/
corrections), then issues a query and asserts what should / should not surface.
Categories mirror LongMemEval capability areas so we can track regressions.
"""

from __future__ import annotations

# category ∈ retrieval | temporal_update | contradiction | stale_resistance |
#            irrelevant_resistance | multi_session
SCENARIOS: list[dict] = [
    {
        "id": "retrieval_basic",
        "category": "retrieval",
        "seed": [
            {
                "content": "User is interested in reinforcement learning for robotics.",
                "layer": "semantic",
                "key": "research_interest",
                "confidence": 0.8,
            },
            {
                "content": "User's favourite coffee is a flat white.",
                "layer": "semantic",
                "key": "coffee",
                "confidence": 0.6,
            },
        ],
        "query": "what research is the user interested in",
        "relevant": ["reinforcement learning"],
        "irrelevant": ["coffee"],
        "stale": [],
    },
    {
        "id": "temporal_update",
        "category": "temporal_update",
        "seed": [
            {
                "content": "First-choice country is Switzerland.",
                "layer": "semantic",
                "key": "country_pref",
                "confidence": 0.7,
            },
        ],
        "ops": [
            {
                "content": "First-choice country is now Germany.",
                "layer": "semantic",
                "key": "country_pref",
                "confidence": 0.9,
            },
        ],
        "query": "which country does the user prefer",
        "relevant": ["Germany"],
        "irrelevant": [],
        "stale": ["Switzerland"],  # must NOT surface as current
    },
    {
        "id": "additive_preferences",
        "category": "contradiction",
        "seed": [
            {
                "content": "Prefers Switzerland for a PhD.",
                "layer": "semantic",
                "key": "phd_pref",
                "confidence": 0.7,
            },
        ],
        "ops": [
            {
                "content": "Also considering Norway for a PhD.",
                "layer": "semantic",
                "key": "phd_pref",
                "confidence": 0.5,
            },
        ],
        "query": "phd country options",
        "relevant": ["Switzerland", "Norway"],  # both kept (no blind overwrite)
        "irrelevant": [],
        "stale": [],
    },
    {
        "id": "irrelevant_resistance",
        "category": "irrelevant_resistance",
        "seed": [
            {"content": "User studies computer vision.", "layer": "semantic", "confidence": 0.8},
            {"content": "User owns a cat named Pixel.", "layer": "semantic", "confidence": 0.5},
            {"content": "User dislikes early meetings.", "layer": "semantic", "confidence": 0.5},
        ],
        "query": "computer vision research background",
        "relevant": ["computer vision"],
        "irrelevant": ["cat", "meetings"],
        "stale": [],
    },
]
