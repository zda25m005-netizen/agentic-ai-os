"""Trajectory memory layer (config G): action space, env, dataset, prompt.

All pure-python — no ML dependencies — so this runs in CI exactly like every other test.
"""

from app.memory.policy import ADD
from app.memory.policy import NOOP as R_NOOP
from app.memory.policy import UPDATE as R_UPDATE
from app.memory.trajectory import (
    OPS,
    MemoryOp,
    TrajectoryMemoryEnv,
    build_prompt,
    make_trajectories,
    op_to_resolver_action,
    parse_action,
)
from app.memory.trajectory.actions import parse_op


def test_six_actions_defined():
    assert OPS == ("STORE", "RETRIEVE", "UPDATE", "SUMMARIZE", "DISCARD", "NOOP")
    assert len(MemoryOp) == 6


def test_op_maps_to_resolver_action():
    assert op_to_resolver_action(MemoryOp.STORE) == ADD
    assert op_to_resolver_action(MemoryOp.UPDATE) == R_UPDATE
    for op in (MemoryOp.RETRIEVE, MemoryOp.SUMMARIZE, MemoryOp.DISCARD, MemoryOp.NOOP):
        assert op_to_resolver_action(op) == R_NOOP


def test_parse_op_and_action():
    assert parse_op("please STORE this") == MemoryOp.STORE
    assert parse_op("nonsense") is None
    assert parse_action("SUMMARIZE") == MemoryOp.SUMMARIZE
    assert parse_action("garbage output") == MemoryOp.NOOP  # safe default


def test_dataset_is_labelled_and_reproducible():
    a = make_trajectories(n=20, seed=1)
    b = make_trajectories(n=20, seed=1)
    assert len(a) == 20
    steps = [s for t in a for s in t["steps"]]
    assert all(0 <= s["optimal"] < 6 for s in steps)
    assert all(
        k in s and s[k] is not None for s in steps for k in ("observation", "memory_state", "feats")
    )
    # same seed -> identical labels
    assert [s["optimal"] for t in a for s in t["steps"]] == [
        s["optimal"] for t in b for s in t["steps"]
    ]


def test_env_reward_penalises_worst_errors_hardest():
    env = TrajectoryMemoryEnv(n=30, seed=0)
    # construct explicit states to check the reward table
    store_state = {"optimal": int(MemoryOp.STORE)}
    assert env.reward(store_state, MemoryOp.STORE) == 1.0
    assert env.reward(store_state, MemoryOp.DISCARD) == -1.0  # information loss
    upd = {"optimal": int(MemoryOp.UPDATE)}
    assert env.reward(upd, MemoryOp.NOOP) == -1.0  # stale leak
    dup = {"optimal": int(MemoryOp.NOOP)}
    assert env.reward(dup, MemoryOp.STORE) == -0.7  # pollution, but less bad than loss


def test_build_prompt_has_actions_and_state():
    env = TrajectoryMemoryEnv(n=5, seed=0)
    msgs = build_prompt(env.states()[0])
    assert msgs[0]["role"] == "system"
    user = msgs[1]["content"]
    assert "Observation:" in user and "Memory state:" in user
    for name in OPS:
        assert name in user
