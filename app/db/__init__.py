"""Async database layer (SQLAlchemy 2.0): engine, sessions, health check.

Postgres in production (asyncpg); tests use in-memory SQLite (aiosqlite), so
the persistence layer is exercised in CI without a live database.
"""
