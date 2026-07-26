from app.agents import critic
from app.agents.state import Step, new_state


def _executed_state(retries: int = 0) -> dict:
    state = new_state("goal")
    state["plan"] = [
        Step(id=0, description="find revenue", agent="research", status="done",
             result="revenue is 12%"),
    ]
    state["results"] = ["revenue is 12%"]
    state["cursor"] = 1
    state["retries"] = retries
    return state


def _patch_chat(fake):
    import app.core.llm as llm_mod
    orig = llm_mod.chat
    llm_mod.chat = fake
    return llm_mod, orig


async def test_review_approve():
    async def fake_chat(messages):
        return "APPROVE"

    verdict, reason = await critic.review("step", "result", chat_fn=fake_chat)
    assert verdict == critic.APPROVE


async def test_review_retry_with_reason():
    async def fake_chat(messages):
        return "RETRY: missing the actual number"

    verdict, reason = await critic.review("step", "result", chat_fn=fake_chat)
    assert verdict == critic.RETRY
    assert "number" in reason


async def test_critic_node_approves_and_advances():
    async def fake_chat(messages):
        return "APPROVE"

    llm_mod, orig = _patch_chat(fake_chat)
    try:
        update = await critic.critic_node(_executed_state())
    finally:
        llm_mod.chat = orig

    assert update["verdict"] == critic.APPROVE
    assert update["retries"] == 0
    assert "cursor" not in update  # cursor stays advanced


async def test_critic_node_retries_and_rolls_back():
    async def fake_chat(messages):
        return "RETRY: not good enough"

    llm_mod, orig = _patch_chat(fake_chat)
    try:
        update = await critic.critic_node(_executed_state(retries=0))
    finally:
        llm_mod.chat = orig

    assert update["verdict"] == critic.RETRY
    assert update["cursor"] == 0
    assert update["retries"] == 1
    assert update["results"] == []
    assert update["plan"][0]["status"] == "pending"


async def test_critic_node_accepts_when_retries_exhausted():
    async def fake_chat(messages):
        return "RETRY: still bad"

    llm_mod, orig = _patch_chat(fake_chat)
    try:
        update = await critic.critic_node(_executed_state(retries=critic.MAX_RETRIES))
    finally:
        llm_mod.chat = orig

    assert update["verdict"] == critic.APPROVE
    assert "cursor" not in update


async def test_critic_node_noop_before_any_step():
    update = await critic.critic_node(new_state("goal"))
    assert update == {}
