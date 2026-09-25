"""In-process multi-turn bag for A2A demo partners (ADR-002).

Not a product store — process-local history keyed by ``conversation_id`` so
smoke tests can prove two turns without a durable checkpointer.
"""

from __future__ import annotations

import threading
from typing import Any

_LOCK = threading.Lock()
_TURNS: dict[str, list[dict[str, Any]]] = {}


def clear_conversation_turns() -> None:
    """Drop all turn history (tests / smoke)."""
    with _LOCK:
        _TURNS.clear()


def append_turn(conversation_id: str, message: str, *, reply: str) -> dict[str, Any]:
    """Record one turn; return ``turn_count`` and history length."""
    cid = (conversation_id or "").strip()
    if not cid:
        raise ValueError("conversation_id required")
    entry = {"message": message, "reply": reply}
    with _LOCK:
        hist = _TURNS.setdefault(cid, [])
        hist.append(entry)
        count = len(hist)
    return {"turn_count": count, "reply": reply, "conversation_id": cid}


def turn_count(conversation_id: str) -> int:
    """Return how many turns are stored for ``conversation_id``."""
    cid = (conversation_id or "").strip()
    with _LOCK:
        return len(_TURNS.get(cid) or [])
