"""Async, owner-scoped persistence for user-created agents.

Every method takes an `owner` and filters by it, so agents, updates and deletes are
isolated per user. Character auto-assignment prefers an unused character among the owner's
current agents. Backed by SQLAlchemy async; tests run on in-memory SQLite.
"""

from __future__ import annotations

import time

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent_registry.characters import is_valid_character, pick_available_character
from app.agent_registry.models import Agent, AgentRow


class AgentRepository:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self._sm = sessionmaker

    async def _used_characters(self, s: AsyncSession, owner: str) -> list[str]:
        rows = (
            (await s.execute(select(AgentRow.character_id).where(AgentRow.owner == owner)))
            .scalars()
            .all()
        )
        return list(rows)

    async def create(self, owner: str, **fields) -> Agent:
        async with self._sm() as s:
            character_id = fields.get("character_id")
            if not is_valid_character(character_id):
                character_id = pick_available_character(await self._used_characters(s, owner))
            row = AgentRow(
                owner=owner,
                name=fields.get("name") or "New Agent",
                description=fields.get("description", ""),
                purpose=fields.get("purpose", ""),
                instructions=fields.get("instructions", ""),
                character_id=character_id,
                tools=fields.get("tools") or [],
                memory_config=fields.get("memory_config") or {},
                knowledge_sources=fields.get("knowledge_sources") or [],
                model_cfg=fields.get("model_cfg") or {},
                schedule=fields.get("schedule") or {},
                trigger_config=fields.get("trigger_config") or {},
                approval_policy=fields.get("approval_policy") or {},
                personality=fields.get("personality") or "Friendly",
                template_id=fields.get("template_id"),
                status=fields.get("status") or "idle",
            )
            s.add(row)
            await s.commit()
            await s.refresh(row)
            return Agent.from_row(row)

    async def get(self, owner: str, agent_id: str) -> Agent | None:
        async with self._sm() as s:
            row = await s.get(AgentRow, agent_id)
            if row is None or row.owner != owner:  # owner isolation
                return None
            return Agent.from_row(row)

    async def list(self, owner: str, limit: int = 100) -> list[Agent]:
        async with self._sm() as s:
            q = (
                select(AgentRow)
                .where(AgentRow.owner == owner)
                .order_by(desc(AgentRow.created_at))
                .limit(limit)
            )
            rows = (await s.execute(q)).scalars().all()
            return [Agent.from_row(r) for r in rows]

    async def update(self, owner: str, agent_id: str, **fields) -> Agent | None:
        async with self._sm() as s:
            row = await s.get(AgentRow, agent_id)
            if row is None or row.owner != owner:
                return None
            for k, v in fields.items():
                if v is not None and hasattr(row, k):
                    if k == "character_id" and not is_valid_character(v):
                        continue
                    setattr(row, k, v)
            await s.commit()
            await s.refresh(row)
            return Agent.from_row(row)

    async def set_status(self, owner: str, agent_id: str, status: str) -> Agent | None:
        return await self.update(owner, agent_id, status=status)

    async def touch_run(self, owner: str, agent_id: str) -> Agent | None:
        return await self.update(owner, agent_id, last_run_at=time.time(), status="working")

    async def delete(self, owner: str, agent_id: str) -> bool:
        async with self._sm() as s:
            row = await s.get(AgentRow, agent_id)
            if row is None or row.owner != owner:
                return False
            await s.execute(
                delete(AgentRow).where(AgentRow.id == agent_id, AgentRow.owner == owner)
            )
            await s.commit()
            return True
