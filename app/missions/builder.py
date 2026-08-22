"""Bridge: a raw goal -> a persisted mission with a wired task DAG.

Interprets the goal, plans subgoals, creates the mission, and materializes each
subgoal as a Task — translating subgoal *indices* into real task ids so the
persisted `depends_on` edges point at actual tasks.
"""
from __future__ import annotations

import time

from app.missions.goal_interpreter import ChatFn, interpret_goal
from app.missions.mission_planner import plan_objective
from app.missions.models import Mission
from app.missions.repository import MissionRepository


async def build_mission(
    repo: MissionRepository, goal: str, chat_fn: ChatFn | None = None, priority: int = 0
) -> Mission:
    """Interpret + plan + persist a mission with its task DAG. Returns the Mission."""
    objective = await interpret_goal(goal, chat_fn)
    specs = await plan_objective(objective, chat_fn)

    deadline = None
    if objective.deadline_days:
        deadline = time.time() + objective.deadline_days * 86400

    mission = await repo.create(
        goal, priority=priority, deadline=deadline,
        meta={"objective": objective.as_dict()},
    )

    index_to_id: dict[int, int] = {}
    roles: dict[str, str] = {}
    for i, spec in enumerate(specs):
        deps = [index_to_id[d] for d in spec.depends_on if d in index_to_id]
        task = await repo.add_task(mission.id, spec.description, depends_on=deps)
        index_to_id[i] = task.id
        roles[str(task.id)] = spec.role  # so the model router can route per task

    # persist the role map alongside the objective (no task-schema change needed)
    meta = dict(mission.meta)
    meta["roles"] = roles
    return await repo.update_meta(mission.id, meta)
