"""Deterministic agent scheduler: priority, deadline, starvation, determinism."""
from app.missions.models import Mission
from app.missions.scheduler import (
    order_missions,
    pick_next,
    score_mission,
)
from app.missions.state import MissionStatus

NOW = 1_000_000.0
DAY = 86400.0


def mk(mid: int, priority=0, deadline=None, created_at=NOW, value=0.0) -> Mission:
    return Mission(
        id=mid, objective=f"m{mid}", status=MissionStatus.ACTIVE,
        priority=priority, deadline=deadline, created_at=created_at,
        updated_at=created_at, meta={"value": value},
    )


def test_higher_priority_runs_first():
    lo = mk(1, priority=0)
    hi = mk(2, priority=5)
    assert pick_next([lo, hi], now=NOW).id == hi.id


def test_nearer_deadline_wins_at_equal_priority():
    soon = mk(1, priority=1, deadline=NOW + 1 * DAY)
    later = mk(2, priority=1, deadline=NOW + 30 * DAY)
    order = order_missions([later, soon], now=NOW)
    assert [m.id for m in order] == [soon.id, later.id]


def test_overdue_mission_is_pinned_high():
    overdue = mk(1, priority=1, deadline=NOW - DAY)   # past due
    fresh = mk(2, priority=1, deadline=NOW + 10 * DAY)
    assert pick_next([fresh, overdue], now=NOW).id == overdue.id


def test_age_prevents_starvation():
    # same priority, one has been waiting 10 days -> it should edge ahead
    old = mk(1, priority=1, created_at=NOW - 10 * DAY)
    new = mk(2, priority=1, created_at=NOW)
    assert pick_next([new, old], now=NOW).id == old.id


def test_priority_dominates_age():
    # a tiny age boost must not overtake a real priority gap
    old_low = mk(1, priority=0, created_at=NOW - 10 * DAY)
    new_high = mk(2, priority=5, created_at=NOW)
    assert pick_next([old_low, new_high], now=NOW).id == new_high.id


def test_value_breaks_ties_between_equal_missions():
    plain = mk(1, priority=1, value=0.0)
    valuable = mk(2, priority=1, value=3.0)
    assert pick_next([plain, valuable], now=NOW).id == valuable.id


def test_ordering_is_deterministic_tie_break_by_id():
    a = mk(3, priority=1)
    b = mk(1, priority=1)
    c = mk(2, priority=1)
    # identical scores -> ascending id
    assert [m.id for m in order_missions([a, b, c], now=NOW)] == [1, 2, 3]


def test_score_is_a_number():
    assert isinstance(score_mission(mk(1, priority=2), now=NOW), float)


def test_pick_next_empty_is_none():
    assert pick_next([], now=NOW) is None
