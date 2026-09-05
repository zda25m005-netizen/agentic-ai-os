"""Scholarship Finder — scholarship discovery with deterministic hard filtering.

Mirrors the Job Search Agent's architecture (source adapters, hard-filter-before-
rank, fresh search intent, resume personalization) but with scholarship-specific
models, an eligibility engine, and a curated catalog of REAL programs. The user's
query + explicit filters are the authoritative intent; the resume only personalizes
ranking and can never override country/degree/field/funding constraints.
"""
