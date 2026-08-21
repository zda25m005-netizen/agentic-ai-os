"""Failure recovery: ladder decisions + the async recovery runner."""
import pytest

from app.missions.recovery import (
    FailureContext,
    RecoveryEngine,
    RecoveryExhausted,
    RecoveryStrategy,
    execute_with_recovery,
)

S = RecoveryStrategy


def ctx(attempts: int, error_type: str = "error") -> FailureContext:
    return FailureContext(task_id=1, error="boom", error_type=error_type, attempts=attempts)


# --- pure decision policy ---

def test_ladder_progresses_one_rung_per_failure():
    e = RecoveryEngine(max_attempts=10)
    got = [e.decide(ctx(i)).strategy for i in range(6)]
    assert got == [S.RETRY, S.ALT_TOOL, S.CACHED, S.REPLAN, S.ESCALATE, S.TERMINATE]


def test_error_type_sets_start_rung():
    e = RecoveryEngine(max_attempts=10)
    assert e.decide(ctx(0, "tool_error")).strategy == S.ALT_TOOL
    assert e.decide(ctx(0, "invalid_plan")).strategy == S.REPLAN
    assert e.decide(ctx(0, "timeout")).strategy == S.RETRY


def test_terminates_after_max_attempts():
    e = RecoveryEngine(max_attempts=2)
    assert e.decide(ctx(2)).strategy == S.TERMINATE


# --- async runner ---

async def test_happy_path_needs_no_recovery():
    async def primary():
        return "ok"
    res = await execute_with_recovery(primary, engine=RecoveryEngine())
    assert res.value == "ok"
    assert res.trail == []


async def test_timeout_recovers_on_retry():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("tool timed out")
        return "recovered"

    res = await execute_with_recovery(
        flaky, engine=RecoveryEngine(), error_type="timeout"
    )
    assert res.value == "recovered"
    assert res.trail[0].strategy == S.RETRY  # timeout starts with a retry


async def test_tool_error_falls_back_to_alternate_tool():
    async def primary():
        raise RuntimeError("primary tool broke")

    async def alternate():
        return "from-alternate"

    res = await execute_with_recovery(
        primary,
        engine=RecoveryEngine(),
        error_type="tool_error",
        handlers={S.ALT_TOOL: alternate},
    )
    assert res.value == "from-alternate"
    assert res.trail[0].strategy == S.ALT_TOOL


async def test_climbs_to_cached_when_alternate_also_fails():
    async def primary():
        raise RuntimeError("broke")

    async def bad_alt():
        raise RuntimeError("alt broke too")

    async def cached():
        return "from-cache"

    res = await execute_with_recovery(
        primary,
        engine=RecoveryEngine(),
        error_type="tool_error",  # starts at ALT_TOOL, then climbs to CACHED
        handlers={S.ALT_TOOL: bad_alt, S.CACHED: cached},
    )
    assert res.value == "from-cache"
    assert [d.strategy for d in res.trail] == [S.ALT_TOOL, S.CACHED]


async def test_exhausts_to_recovery_exhausted():
    async def always_fails():
        raise RuntimeError("nope")

    with pytest.raises(RecoveryExhausted):
        await execute_with_recovery(
            always_fails, engine=RecoveryEngine(max_attempts=10)
        )
