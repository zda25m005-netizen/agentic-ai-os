"""The six-action memory-control space (config G) and its mapping to the resolver.

STORE     — commit a new fact to long-term memory
RETRIEVE  — pull relevant memories into the working context (a read, not a write)
UPDATE    — supersede an existing memory with a corrected value
SUMMARIZE — consolidate several memories into a shorter one (compression)
DISCARD   — deliberately drop the candidate (noise / not worth keeping)
NOOP      — do nothing (e.g. an exact duplicate already stored)

The Mem0 resolver (config C/D/F) only distinguishes ADD / UPDATE / NOOP. The trajectory
policy's larger space is a superset, so ``op_to_resolver_action`` projects a six-action
decision down to the three-action resolver decision — letting the same learned policy
drive the existing lifecycle without changing it.
"""

from __future__ import annotations

from enum import IntEnum

# Import the resolver's action ints so the mapping is a single source of truth.
from app.memory.policy import ADD
from app.memory.policy import NOOP as R_NOOP
from app.memory.policy import UPDATE as R_UPDATE


class MemoryOp(IntEnum):
    STORE = 0
    RETRIEVE = 1
    UPDATE = 2
    SUMMARIZE = 3
    DISCARD = 4
    NOOP = 5


OPS = tuple(op.name for op in MemoryOp)  # ("STORE", "RETRIEVE", ...)


def parse_op(text: str) -> MemoryOp | None:
    """Parse an op name (case-insensitive) from free text; None if not found."""
    if not text:
        return None
    up = text.strip().upper()
    for op in MemoryOp:
        if op.name in up:
            return op
    return None


# Project the six-action decision onto the resolver's three-action space.
# RETRIEVE/SUMMARIZE are working-context ops, not writes, so for the write-path
# resolver they behave as NOOP; STORE->ADD, UPDATE->UPDATE, DISCARD/NOOP->NOOP.
_TO_RESOLVER = {
    MemoryOp.STORE: ADD,
    MemoryOp.UPDATE: R_UPDATE,
    MemoryOp.RETRIEVE: R_NOOP,
    MemoryOp.SUMMARIZE: R_NOOP,
    MemoryOp.DISCARD: R_NOOP,
    MemoryOp.NOOP: R_NOOP,
}


def op_to_resolver_action(op: MemoryOp) -> int:
    """Map a six-action op to the resolver's ADD/UPDATE/NOOP int."""
    return _TO_RESOLVER[MemoryOp(op)]
