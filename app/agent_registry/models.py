"""ORM table + domain dataclass for user-created agents.

Mirrors the missions package style: `AgentRow` persists state, `Agent` is the clean
domain object the API returns. Every row is owner-scoped (`owner`) — the repository
always filters by owner so one user's agents never leak to another.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy import JSON, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Agent lifecycle states (mirror the frontend AgentState + mission/task machine).
AGENT_STATES = (
    "idle",
    "thinking",
    "planning",
    "working",
    "waiting",
    "needs_approval",
    "completed",
    "failed",
    "paused",
)


def _new_id() -> str:
    return f"agent-{uuid.uuid4().hex[:12]}"


class AgentRow(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    owner: Mapped[str] = mapped_column(String(64), default="me", index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    purpose: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    character_id: Mapped[str] = mapped_column(String(32), default="nova")
    tools: Mapped[list] = mapped_column(JSON, default=list)
    memory_config: Mapped[dict] = mapped_column(JSON, default=dict)
    knowledge_sources: Mapped[list] = mapped_column(JSON, default=list)
    model_cfg: Mapped[dict] = mapped_column(JSON, default=dict)  # 'model' in the API
    schedule: Mapped[dict] = mapped_column(JSON, default=dict)
    trigger_config: Mapped[dict] = mapped_column(JSON, default=dict)
    approval_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    personality: Mapped[str] = mapped_column(String(32), default="Friendly")
    template_id: Mapped[str | None] = mapped_column(String(48), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="idle")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time, onupdate=time.time)
    last_run_at: Mapped[float | None] = mapped_column(Float, nullable=True)


@dataclass
class Agent:
    id: str
    owner: str
    name: str
    description: str
    purpose: str
    instructions: str
    character_id: str
    tools: list
    memory_config: dict
    knowledge_sources: list
    model_cfg: dict
    schedule: dict
    trigger_config: dict
    approval_policy: dict
    personality: str
    template_id: str | None
    status: str
    created_at: float
    updated_at: float
    last_run_at: float | None = field(default=None)

    @classmethod
    def from_row(cls, r: AgentRow) -> Agent:
        return cls(
            id=r.id,
            owner=r.owner,
            name=r.name,
            description=r.description or "",
            purpose=r.purpose or "",
            instructions=r.instructions or "",
            character_id=r.character_id,
            tools=list(r.tools or []),
            memory_config=dict(r.memory_config or {}),
            knowledge_sources=list(r.knowledge_sources or []),
            model_cfg=dict(r.model_cfg or {}),
            schedule=dict(r.schedule or {}),
            trigger_config=dict(r.trigger_config or {}),
            approval_policy=dict(r.approval_policy or {}),
            personality=r.personality or "Friendly",
            template_id=r.template_id,
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at,
            last_run_at=r.last_run_at,
        )
