"""Inline prompts/skills stored from agent YAML dicts."""

from __future__ import annotations

from typing import Any

from edim_dde_ai.content.protocols import Skill
from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.errors import ContentError


class InlineContentStore:
    """Mutable in-memory prompt + skill store (default ContentHub backend)."""

    def __init__(self) -> None:
        # (agent_id, chain, role) -> text
        self._prompts: dict[tuple[str, str, str], str] = {}
        # agent_id -> list[Skill]
        self._skills: dict[str, list[Skill]] = {}

    def clear(self) -> None:
        self._prompts.clear()
        self._skills.clear()

    def set_prompt(self, agent_id: str, chain: str, role: str, text: str) -> None:
        self._prompts[(agent_id, chain, role)] = text

    def get_prompt(self, agent_id: str, chain: str, role: str) -> str | None:
        return self._prompts.get((agent_id, chain, role))

    def register_skill(self, agent_id: str, skill: Skill) -> None:
        skills = self._skills.setdefault(agent_id, [])
        # Replace same key if present
        skills[:] = [s for s in skills if s.key != skill.key]
        skills.append(skill)

    def list_skills(self, agent_id: str, *, chain: str | None = None) -> list[Skill]:
        del chain  # reserved for future per-chain skills
        return list(self._skills.get(agent_id, []))

    def load_from_definition(self, definition: AgentDefinition) -> None:
        """Merge ``prompts`` / ``skills`` from definition.raw into this store."""
        raw = definition.raw or {}
        agent_id = definition.agent_id
        prompts = raw.get("prompts")
        if prompts is not None:
            if not isinstance(prompts, dict):
                raise ContentError(f"prompts must be a mapping (agent {agent_id})")
            for chain, roles in prompts.items():
                if not isinstance(chain, str) or not chain.strip():
                    raise ContentError(f"prompt chain key must be a non-empty string ({agent_id})")
                if not isinstance(roles, dict):
                    raise ContentError(
                        f"prompts.{chain} must be a mapping of role -> text ({agent_id})"
                    )
                for role, text in roles.items():
                    if not isinstance(role, str) or not role.strip():
                        raise ContentError(
                            f"prompt role must be a non-empty string ({agent_id}.{chain})"
                        )
                    if not isinstance(text, str):
                        raise ContentError(
                            f"prompts.{chain}.{role} must be a string ({agent_id})"
                        )
                    self.set_prompt(agent_id, chain, role, text)

        skills = raw.get("skills")
        if skills is not None:
            if not isinstance(skills, list):
                raise ContentError(f"skills must be a list (agent {agent_id})")
            for i, item in enumerate(skills):
                if not isinstance(item, dict):
                    raise ContentError(f"skills[{i}] must be a mapping ({agent_id})")
                key = item.get("key")
                title = item.get("title", key)
                content = item.get("content", "")
                if not isinstance(key, str) or not key.strip():
                    raise ContentError(f"skills[{i}].key must be a non-empty string ({agent_id})")
                if not isinstance(title, str):
                    raise ContentError(f"skills[{i}].title must be a string ({agent_id})")
                if not isinstance(content, str):
                    raise ContentError(f"skills[{i}].content must be a string ({agent_id})")
                self.register_skill(agent_id, Skill(key=key, title=title, content=content))

    def load_from_raw(self, agent_id: str, raw: dict[str, Any]) -> None:
        """Convenience: wrap raw dict as a minimal definition-like load."""
        from edim_dde_ai.core.definition import AgentDefinition, EntrySpec

        stub = AgentDefinition(
            agent_id=agent_id,
            display_name=agent_id,
            version=1,
            entry=EntrySpec(),
            graph_entry="__",
            nodes=(),
            edges=(),
            raw=raw,
        )
        self.load_from_definition(stub)
