"""Session policy parsed from agent YAML ``memory`` and optional ``session`` blocks.

Example YAML (multi-turn)::

    memory:
      strategy: window
      k: 10
    session:
      initialize_entry: collect_metrics   # optional; defaults to graph.entry
      converse_entry: prepare_explanation_payload
      regenerate_entry: prepare_sizing_payload
      regenerate_phrases: [cheaper, retry, …]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edim_dde_ai.errors import DefinitionError
from edim_dde_ai.session.models import MemoryPolicy


_DEFAULT_REGENERATE_PHRASES = (
    "cheaper",
    "smaller",
    "reduce",
    "regenerate",
    "retry",
    "try again",
    "different recommendation",
)


@dataclass(frozen=True)
class SessionConfig:
    """YAML ``session`` path entries for converse / regenerate.

    ``initialize_entry`` lives on ``SessionPolicy`` (defaults to ``graph.entry``).
    """

    converse_entry: str
    regenerate_entry: str
    regenerate_phrases: tuple[str, ...] = _DEFAULT_REGENERATE_PHRASES

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any] | None,
        *,
        graph_entry: str,
    ) -> "SessionConfig":
        """Parse ``session:`` from agent YAML when memory is enabled."""
        if raw is None:
            raise DefinitionError(
                "session block is required when memory.strategy is not none; "
                "include converse_entry and regenerate_entry"
            )
        if not isinstance(raw, dict):
            raise DefinitionError("session must be a mapping")
        converse = str(raw.get("converse_entry") or "").strip()
        regenerate = str(raw.get("regenerate_entry") or "").strip()
        if not converse:
            raise DefinitionError("session.converse_entry is required")
        if not regenerate:
            raise DefinitionError("session.regenerate_entry is required")
        phrases_raw = raw.get("regenerate_phrases", _DEFAULT_REGENERATE_PHRASES)
        if not isinstance(phrases_raw, list) or not phrases_raw:
            raise DefinitionError(
                "session.regenerate_phrases must be a non-empty list of strings"
            )
        phrases = tuple(str(item).strip().lower() for item in phrases_raw if str(item).strip())
        if not phrases:
            raise DefinitionError("session.regenerate_phrases must not be empty")
        return cls(
            converse_entry=converse,
            regenerate_entry=regenerate,
            regenerate_phrases=phrases,
        )


@dataclass(frozen=True)
class SessionPolicy:
    """Combined memory + session routing policy for checkpoint-backed agents."""

    memory: MemoryPolicy
    session: SessionConfig | None = None
    initialize_entry: str = ""

    @property
    def enabled(self) -> bool:
        """True when ``memory.strategy`` is not ``none``."""
        return self.memory.enabled

    @classmethod
    def from_definition(cls, definition: Any) -> "SessionPolicy":
        """Build policy from a loaded ``AgentDefinition`` (uses ``raw`` YAML)."""
        raw = getattr(definition, "raw", None) or {}
        memory = MemoryPolicy.from_raw(raw.get("memory"))
        graph_entry = getattr(definition, "graph_entry", "")
        session_raw = raw.get("session")
        session = None
        initialize_entry = graph_entry
        if memory.enabled:
            session = SessionConfig.from_raw(session_raw, graph_entry=graph_entry)
            session_raw_dict = session_raw if isinstance(session_raw, dict) else {}
            initialize_entry = str(
                session_raw_dict.get("initialize_entry") or graph_entry
            ).strip()
        return cls(memory=memory, session=session, initialize_entry=initialize_entry)


def get_memory_policy(definition: Any) -> MemoryPolicy:
    """Return validated memory policy for an agent definition."""
    return get_session_policy(definition).memory


def get_session_policy(definition: Any) -> SessionPolicy:
    """Return validated session policy for an agent definition."""
    return SessionPolicy.from_definition(definition)
