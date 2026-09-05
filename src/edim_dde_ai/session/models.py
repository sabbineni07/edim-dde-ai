"""Session memory policy parsed from agent YAML ``memory`` blocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edim_dde_ai.errors import DefinitionError

MEMORY_STRATEGIES = frozenset(
    {"none", "window", "summary", "summary_buffer", "vector"}
)


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
        """Parse an optional YAML ``memory`` block."""
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

        corpus = str(raw.get("corpus", "conversation-memory")).strip()
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
