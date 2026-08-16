"""Build chat messages from prompt/skill providers.

Business purpose:
  Turn ContentHub prompts (and optional skills) into ``(role, text)`` tuples for
  ``LLMProvider.invoke``, with ``{var}`` substitution from flat agent state.

Public API:
  - ``substitute_vars(template, state)``
  - ``build_chat_messages(*, agent_id, chain, state, attach_skills=False, roles=...)``
"""

from __future__ import annotations

import re
from typing import Any

from edim_dde_ai.content.registry import get_prompt_provider, get_skill_provider
from edim_dde_ai.errors import ContentError

_TEMPLATE_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def substitute_vars(template: str, state: dict[str, Any]) -> str:
    """Replace ``{var}`` with ``str(state[var])``; unknown keys become empty string.

    Args:
        template: Prompt text with optional ``{identifier}`` placeholders.
        state: Flat agent metadata.

    Returns:
        Rendered string.
    """

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(state.get(key, ""))

    return _TEMPLATE_RE.sub(repl, template)


def _format_skills_block(skills: list) -> str:
    """Render skills as a markdown block appended to the system prompt."""
    parts = ["## Domain skills"]
    for skill in skills:
        parts.append(f"### {skill.title}\n{skill.content}")
    return "\n\n".join(parts)


def build_chat_messages(
    *,
    agent_id: str,
    chain: str,
    state: dict[str, Any],
    attach_skills: bool = False,
    roles: tuple[str, ...] = ("system", "human"),
) -> list[tuple[str, str]]:
    """Load prompts for ``roles``, substitute state vars, optionally attach skills.

    Requires a non-empty **system** prompt. Other roles in ``roles`` are optional
    (skipped when missing).

    Args:
        agent_id: Agent whose prompts/skills to load.
        chain: Prompt chain key (matches YAML / file naming).
        state: Flat metadata for ``{var}`` substitution.
        attach_skills: When True, append skill markdown to system text.
        roles: Ordered roles to load (system must be present and non-empty).

    Returns:
        List of ``(role, content)`` starting with system.

    Raises:
        ContentError: Missing system prompt.

    Example::

        messages = build_chat_messages(
            agent_id="demo", chain="chat", state={"name": "Ada"}, attach_skills=True
        )
    """
    prompts = get_prompt_provider()
    messages: list[tuple[str, str]] = []
    system_text: str | None = None

    for role in roles:
        text = prompts.get_prompt(agent_id, chain, role)
        if text is None:
            if role == "system":
                raise ContentError(
                    f"Missing system prompt for agent={agent_id!r} chain={chain!r}"
                )
            continue
        rendered = substitute_vars(text, state)
        if role == "system":
            system_text = rendered
        else:
            messages.append((role, rendered))

    if system_text is None:
        raise ContentError(
            f"Missing system prompt for agent={agent_id!r} chain={chain!r}"
        )

    if attach_skills:
        skills = get_skill_provider().list_skills(agent_id, chain=chain)
        if skills:
            block = _format_skills_block(skills)
            system_text = f"{system_text.rstrip()}\n\n{block}"

    return [("system", system_text), *messages]
