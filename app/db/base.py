"""Declarative base for all ORM models.

Models import `Base` and register on its metadata, so `init_models` can create
every table in one call. Kept in its own module to avoid circular imports
between the session factory and the models.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base."""
