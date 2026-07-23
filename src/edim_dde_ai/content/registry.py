"""Process-wide content providers: ContentHub + LLM provider setters/getters."""

from __future__ import annotations

from pathlib import Path
from edim_dde_ai.content.directory import DirectoryContentProvider
from edim_dde_ai.content.inline import InlineContentStore
from edim_dde_ai.content.protocols import LLMProvider, PromptProvider, Skill, SkillProvider
from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.errors import ContentError, LoaderError


class CompositePromptProvider:
    """Try each provider until one returns non-None."""

    def __init__(self, providers: list[PromptProvider]) -> None:
        self.providers = list(providers)

    def get_prompt(self, agent_id: str, chain: str, role: str) -> str | None:
        for p in self.providers:
            text = p.get_prompt(agent_id, chain, role)
            if text is not None:
                return text
        return None


class CompositeSkillProvider:
    """Concatenate skills from each provider (later providers append)."""

    def __init__(self, providers: list[SkillProvider]) -> None:
        self.providers = list(providers)

    def list_skills(self, agent_id: str, *, chain: str | None = None) -> list[Skill]:
        out: list[Skill] = []
        seen: set[str] = set()
        for p in self.providers:
            for skill in p.list_skills(agent_id, chain=chain):
                if skill.key in seen:
                    continue
                seen.add(skill.key)
                out.append(skill)
        return out


class ContentHub:
    """Default PromptProvider + SkillProvider.

    Lookup order for prompts:
      1. optional user override
      2. per-agent directory (``content_dir``)
      3. inline store (YAML ``prompts`` / ``register_skill``)

    Skills: override skills (if set) replace directory+inline for that agent when
    override returns a non-empty list; otherwise merge directory then inline.
    Simpler: override checked first; if override is set, use only override.
    Directory then inline for defaults.
    """

    def __init__(self) -> None:
        self.inline = InlineContentStore()
        self.directories: dict[str, Path] = {}
        self.override_prompt: PromptProvider | None = None
        self.override_skill: SkillProvider | None = None

    def clear(self) -> None:
        self.inline.clear()
        self.directories.clear()
        self.override_prompt = None
        self.override_skill = None

    def set_directory(self, agent_id: str, root: str | Path) -> None:
        self.directories[agent_id] = Path(root)

    def get_prompt(self, agent_id: str, chain: str, role: str) -> str | None:
        if self.override_prompt is not None:
            text = self.override_prompt.get_prompt(agent_id, chain, role)
            if text is not None:
                return text
        root = self.directories.get(agent_id)
        if root is not None:
            text = DirectoryContentProvider(root, agent_id=agent_id).get_prompt(
                agent_id, chain, role
            )
            if text is not None:
                return text
        return self.inline.get_prompt(agent_id, chain, role)

    def list_skills(self, agent_id: str, *, chain: str | None = None) -> list[Skill]:
        if self.override_skill is not None:
            return self.override_skill.list_skills(agent_id, chain=chain)
        skills: list[Skill] = []
        seen: set[str] = set()
        root = self.directories.get(agent_id)
        if root is not None:
            for skill in DirectoryContentProvider(root, agent_id=agent_id).list_skills(
                agent_id, chain=chain
            ):
                if skill.key not in seen:
                    seen.add(skill.key)
                    skills.append(skill)
        for skill in self.inline.list_skills(agent_id, chain=chain):
            if skill.key not in seen:
                seen.add(skill.key)
                skills.append(skill)
        return skills

    def load_from_definition(self, definition: AgentDefinition) -> None:
        """Merge inline prompts/skills and optional ``content_dir`` from definition."""
        raw = definition.raw or {}
        if raw.get("prompts") is not None or raw.get("skills") is not None:
            self.inline.load_from_definition(definition)

        content_dir = raw.get("content_dir")
        if content_dir is None:
            return
        if not isinstance(content_dir, str) or not content_dir.strip():
            raise ContentError(
                f"content_dir must be a non-empty string (agent {definition.agent_id})"
            )
        if not definition.source_path:
            raise ContentError(
                f"content_dir requires source_path on AgentDefinition "
                f"(load via load_yaml / register_from_yaml); agent={definition.agent_id}"
            )
        base = Path(definition.source_path).resolve().parent
        resolved = (base / content_dir).resolve()
        if not resolved.is_dir():
            raise LoaderError(
                f"content_dir is not a directory: {resolved} (agent {definition.agent_id})"
            )
        self.set_directory(definition.agent_id, resolved)


_HUB = ContentHub()
_LLM: LLMProvider | None = None


def get_content_hub() -> ContentHub:
    return _HUB


def set_prompt_provider(provider: PromptProvider) -> None:
    """Set a user override PromptProvider (checked before directory/inline)."""
    _HUB.override_prompt = provider


def get_prompt_provider() -> PromptProvider:
    return _HUB


def clear_prompt_provider() -> None:
    _HUB.override_prompt = None


def set_skill_provider(provider: SkillProvider) -> None:
    """Set a user override SkillProvider (replaces directory+inline when set)."""
    _HUB.override_skill = provider


def get_skill_provider() -> SkillProvider:
    return _HUB


def clear_skill_provider() -> None:
    _HUB.override_skill = None


def set_llm_provider(provider: LLMProvider) -> None:
    global _LLM
    _LLM = provider


def get_llm_provider() -> LLMProvider | None:
    return _LLM


def clear_llm_provider() -> None:
    global _LLM
    _LLM = None


def register_skill(agent_id: str, skill: Skill) -> None:
    """Register a skill into the default inline store."""
    _HUB.inline.register_skill(agent_id, skill)


def clear_content_providers() -> None:
    """Reset hub (inline, directories, overrides) and LLM provider — for tests."""
    _HUB.clear()
    clear_llm_provider()
