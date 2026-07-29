from pathlib import Path

from app.memory.episodic import EpisodicMemory


def test_save_and_recent():
    mem = EpisodicMemory.open(":memory:")
    mem.save("goal one", "answer one", ts=1.0)
    mem.save("goal two", "answer two", ts=2.0)

    recent = mem.recent()
    assert [e.goal for e in recent] == ["goal two", "goal one"]  # newest first
    assert recent[0].answer == "answer two"
    assert mem.count() == 2


def test_recent_respects_limit():
    mem = EpisodicMemory.open(":memory:")
    for i in range(5):
        mem.save(f"g{i}", f"a{i}", ts=float(i))
    assert len(mem.recent(limit=2)) == 2


def test_search_matches_goal_and_answer():
    mem = EpisodicMemory.open(":memory:")
    mem.save("summarize the Q3 report", "revenue grew 12%", ts=1.0)
    mem.save("draft an email", "hello team", ts=2.0)

    assert [e.goal for e in mem.search("revenue")] == ["summarize the Q3 report"]
    assert [e.goal for e in mem.search("email")] == ["draft an email"]
    assert mem.search("nonexistent") == []


def test_persists_to_disk(tmp_path: Path):
    db = str(tmp_path / "mem.db")
    mem = EpisodicMemory.open(db)
    mem.save("remember me", "persisted answer", ts=1.0)
    mem.close()

    reopened = EpisodicMemory.open(db)
    assert reopened.count() == 1
    assert reopened.recent()[0].goal == "remember me"


def test_save_returns_incrementing_ids():
    mem = EpisodicMemory.open(":memory:")
    first = mem.save("a", "1")
    second = mem.save("b", "2")
    assert second > first
