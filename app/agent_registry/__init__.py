"""Persisted, owner-scoped user-agent registry (Phase 3 of the agent-first workspace).

An `Agent` here is a user-created (or template-instantiated) configuration: name,
purpose, instructions, character, tools, memory/knowledge/model config, schedule and
approval policy. It is the durable identity a character represents and a task runs under.

This is deliberately separate from `app.agents` (the LangGraph planner/executor/critic
"brain"): the brain is HOW work runs; this registry is WHICH agent the user configured and
owns. Running an agent creates a real mission in the existing mission runtime.
"""
