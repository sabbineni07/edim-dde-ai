"""In-graph message list helpers for checkpoint-backed session state."""

from __future__ import annotations

import json
from typing import Any


def normalize_messages(raw: Any) -> list[dict[str, str]]:
    """Coerce checkpoint/input messages into a simple role/content list."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            role = str(item.get("role") or "user").strip() or "user"
            content = str(item.get("content") or "").strip()
            if content:
                out.append({"role": role, "content": content[:8000]})
        else:
            role = str(getattr(item, "type", None) or getattr(item, "role", "user"))
            content = str(getattr(item, "content", "") or "").strip()
            if content:
                out.append({"role": role, "content": content[:8000]})
    return out


def append_message(
    messages: list[dict[str, str]], *, role: str, content: str
) -> list[dict[str, str]]:
    """Return a new message list with one bounded turn appended."""
    text = str(content or "").strip()
    if not text:
        return list(messages)
    updated = list(messages)
    updated.append({"role": role, "content": text[:8000]})
    return updated


def trim_messages(
    messages: list[dict[str, str]], *, k: int, max_chars: int
) -> list[dict[str, str]]:
    """Keep the last ``k`` user/assistant turns within a character budget."""
    if k < 1:
        return []
    allowed = [m for m in messages if m.get("role") in {"user", "assistant"}]
    recent = allowed[-(k * 2) :]
    trimmed: list[dict[str, str]] = []
    used = 0
    for message in recent:
        item = f"[{message['role'].upper()}]\n{message['content']}"
        if used + len(item) + 2 > max_chars:
            break
        trimmed.append(message)
        used += len(item) + 2
    return trimmed


def format_messages_for_prompt(messages: list[dict[str, str]]) -> str:
    """Render bounded messages for LLM context injection."""
    parts = [
        f"[{message['role'].upper()}]\n{message['content']}"
        for message in messages
        if message.get("content")
    ]
    return "\n\n".join(parts) or "(no prior conversation messages)"


def assistant_text_from_final(final: dict[str, Any]) -> str:
    """Extract a bounded assistant record from a graph result."""
    if isinstance(final.get("result"), dict):
        value: Any = final["result"]
    elif final.get("explanation"):
        value = final["explanation"]
    elif final.get("recommendation"):
        value = {
            "recommendation": final.get("recommendation"),
            "rationale": final.get("pattern_analysis"),
            "explanation": final.get("explanation"),
        }
    else:
        value = final.get("llm_raw") or final.get("output")
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:8000]
    try:
        return json.dumps(value, ensure_ascii=False, default=str)[:8000]
    except (TypeError, ValueError):
        return str(value)[:8000]
