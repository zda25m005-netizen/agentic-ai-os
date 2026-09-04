"""Resume-aware job recommendations.

Separates SEARCH INTENT (what the user asked for — a hard boundary) from the
CANDIDATE PROFILE (how well a valid job fits the person). The resume only ever
personalizes ranking; it never broadens or overrides the user's explicit query
constraints.
"""
