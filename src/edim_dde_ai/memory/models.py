"""Conversation-memory models and YAML policy."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from edim_dde_ai.errors import DefinitionError

MEMORY_STRATEGIES = frozenset(
    {"none", "window", "summary", "summary_buffer", "vector"}
)
MEMORY_ROLES = frozenset({"user", "assistant", "system", "tool"})
_SAFE_ID = re.compile(r"[^a-zA-Z0-9_.:-]+")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, *, max_chars: int) -> str:
    text = str(value or "").strip()
    return text[:max_chars]


@dataclass(frozen=True)
class MemoryPolicy:
    """Validated per-agent conversation-memory policy.

    ``k`` counts user/assistant turns. All policies also enforce a character
    budget because a turn count alone cannot protect an LLM context window.
    """

    strategy: str = "none"
    k: int = 10
    max_tokens: int = 4000
    max_chars: int = 16000
    store: str = "conversation"
    include_tool_messages: bool = False
    summary_trigger_tokens: int = 6000
    summary_max_tokens: int = 1500
    top_k: int = 5
    similarity_threshold: float = 0.0
    corpus: str = "conversation-memory"

    @property
    def enabled(self) -> bool:
        return self.strategy != "none"

    @property
    def context_chars(self) -> int:
        """Effective prompt budget using a conservative 4 chars/token estimate."""
        return max(1000, min(self.max_chars, self.max_tokens * 4))

    @classmethod
    def from_raw(cls, raw: dict[str, Any] | None) -> "MemoryPolicy":
        """Parse an optional YAML ``memory`` block.

        Missing configuration intentionally disables conversation memory.
        Invalid explicit configuration fails agent registration rather than
        silently selecting an unsafe policy.
        """
        if raw is None:
            return cls()
        if not isinstance(raw, dict):
            raise DefinitionError("memory must be a mapping")

        strategy = str(raw.get("strategy", "none")).strip().lower()
        if strategy not in MEMORY_STRATEGIES:
            raise DefinitionError(
                "memory.strategy must be one of "
                + "|".join(sorted(MEMORY_STRATEGIES))
            )

        k_raw = raw.get("k", raw.get("turns", 10))
        try:
            k = int(k_raw)
        except (TypeError, ValueError) as exc:
            raise DefinitionError("memory.k must be a positive integer") from exc
        if k < 1 or k > 100:
            raise DefinitionError("memory.k must be between 1 and 100")

        def positive_int(key: str, default: int, maximum: int) -> int:
            value = raw.get(key, default)
            try:
                parsed = int(value)
            except (TypeError, ValueError) as exc:
                raise DefinitionError(f"memory.{key} must be a positive integer") from exc
            minimum = 1000 if key == "max_chars" else 1
            if parsed < minimum or parsed > maximum:
                raise DefinitionError(
                    f"memory.{key} must be between {minimum} and {maximum}"
                )
            return parsed

        try:
            threshold = float(raw.get("similarity_threshold", 0.0))
        except (TypeError, ValueError) as exc:
            raise DefinitionError(
                "memory.similarity_threshold must be a number between 0 and 1"
            ) from exc
        if not 0 <= threshold <= 1:
            raise DefinitionError(
                "memory.similarity_threshold must be a number between 0 and 1"
            )

        store = str(raw.get("store", "conversation")).strip()
        corpus = str(raw.get("corpus", "conversation-memory")).strip()
        if not store:
            raise DefinitionError("memory.store must be a non-empty string")
        if not corpus:
            raise DefinitionError("memory.corpus must be a non-empty string")
        include_tools = raw.get("include_tool_messages", False)
        if not isinstance(include_tools, bool):
            raise DefinitionError("memory.include_tool_messages must be a boolean")

        return cls(
            strategy=strategy,
            k=k,
            max_tokens=positive_int("max_tokens", 4000, 128000),
            max_chars=positive_int("max_chars", 16000, 512000),
            store=store,
            include_tool_messages=include_tools,
            summary_trigger_tokens=positive_int(
                "summary_trigger_tokens", 6000, 128000
            ),
            summary_max_tokens=positive_int(
                "summary_max_tokens", 1500, 32000
            ),
            top_k=positive_int("top_k", 5, 50),
            similarity_threshold=threshold,
            corpus=corpus,
        )


@dataclass(frozen=True)
class ConversationMessage:
    """One persisted conversational turn."""

    message_id: str
    conversation_id: str
    agent_id: str
    role: str
    content: str
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.role not in MEMORY_ROLES:
            raise ValueError(f"Unsupported conversation role: {self.role!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationMessage":
        return cls(
            message_id=str(data.get("message_id") or data.get("id") or ""),
            conversation_id=str(data.get("conversation_id") or ""),
            agent_id=str(data.get("agent_id") or ""),
            role=str(data.get("role") or "user"),
            content=_safe_text(data.get("content"), max_chars=100000),
            created_at=str(data.get("created_at") or _utc_now()),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class ConversationSummary:
    """Summary covering older messages in one conversation."""

    conversation_id: str
    agent_id: str
    content: str
    covered_message_id: str | None = None
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationSummary":
        return cls(
            conversation_id=str(data.get("conversation_id") or ""),
            agent_id=str(data.get("agent_id") or ""),
            content=_safe_text(data.get("content"), max_chars=100000),
            covered_message_id=(
                str(data["covered_message_id"])
                if data.get("covered_message_id") is not None
                else None
            ),
            updated_at=str(data.get("updated_at") or _utc_now()),
        )


def memory_key(value: str) -> str:
    """Return a bounded safe identifier for vector-memory document ids."""
    return _SAFE_ID.sub("_", value.strip())[:180]
