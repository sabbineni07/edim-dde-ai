"""Prompt / skill / LLM content providers."""

from edim_dde_ai.content.directory import DirectoryContentProvider
from edim_dde_ai.content.inline import InlineContentStore
from edim_dde_ai.content.messages import build_chat_messages, substitute_vars
from edim_dde_ai.content.protocols import LLMProvider, PromptProvider, Skill, SkillProvider
from edim_dde_ai.content.registry import (
    CompositePromptProvider,
    CompositeSkillProvider,
    ContentHub,
    clear_content_providers,
    clear_llm_provider,
    clear_prompt_provider,
    clear_skill_provider,
    get_content_hub,
    get_llm_provider,
    get_prompt_provider,
    get_skill_provider,
    register_skill,
    set_llm_provider,
    set_prompt_provider,
    set_skill_provider,
)

__all__ = [
    "Skill",
    "PromptProvider",
    "SkillProvider",
    "LLMProvider",
    "InlineContentStore",
    "DirectoryContentProvider",
    "ContentHub",
    "CompositePromptProvider",
    "CompositeSkillProvider",
    "build_chat_messages",
    "substitute_vars",
    "set_prompt_provider",
    "get_prompt_provider",
    "clear_prompt_provider",
    "set_skill_provider",
    "get_skill_provider",
    "clear_skill_provider",
    "set_llm_provider",
    "get_llm_provider",
    "clear_llm_provider",
    "register_skill",
    "get_content_hub",
    "clear_content_providers",
]
