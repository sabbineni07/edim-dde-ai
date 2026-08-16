"""Prompt, skill, and LLM provider protocols.

Business purpose:
  Duck-typed contracts for content backends and the LLM used by default
  ``llm_chain`` execution. Hosts implement these to plug proprietary stores/models.

Public API:
  - ``Skill`` — frozen dataclass
  - ``PromptProvider`` / ``SkillProvider`` / ``LLMProvider`` — Protocols
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Skill:
    """A named skill/instruction block attachable to prompts.

    Attributes:
        key: Stable id (also used for de-dupe in composites).
        title: Human-readable heading.
        content: Markdown/plain instruction body.
    """

    key: str
    title: str
    content: str


@runtime_checkable
class PromptProvider(Protocol):
    def get_prompt(self, agent_id: str, chain: str, role: str) -> str | None:
        """Return prompt text for ``(agent_id, chain, role)``, or None if missing."""
        ...


@runtime_checkable
class SkillProvider(Protocol):
    def list_skills(self, agent_id: str, *, chain: str | None = None) -> list[Skill]:
        """Return skills for ``agent_id`` (optional chain filter unused by default)."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    def invoke(
        self,
        messages: list[tuple[str, str]],
        *,
        config: dict[str, Any] | None = None,
    ) -> str:
        """Invoke an LLM with ``(role, content)`` messages; return assistant text.

        Args:
            messages: Chat turns as ``(role, content)`` pairs.
            config: Optional node/provider config (model name, temperature, …).

        Returns:
            Assistant text response.
        """
        ...
