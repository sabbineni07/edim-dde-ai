"""In-process agent definition registry and factory facade."""

from __future__ import annotations

import threading

from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.errors import AgentRegistryError
from edim_dde_ai.graph.runtime import MetadataAgent
from edim_dde_ai.registry.base import Registry

_REGISTRY: Registry[AgentDefinition] = Registry(
    kind="agent",
    error_cls=AgentRegistryError,
    allow_overwrite=True,
)

_CACHE: dict[str, MetadataAgent] = {}
_CACHE_LOCK = threading.Lock()


def register_agent(definition: AgentDefinition, *, overwrite: bool = False) -> str:
    """Register an AgentDefinition. Returns agent_id."""
    agent_id = definition.agent_id
    _REGISTRY.register(agent_id, definition, overwrite=overwrite)
    with _CACHE_LOCK:
        _CACHE.pop(agent_id, None)
    raw = definition.raw or {}
    if (
        raw.get("prompts") is not None
        or raw.get("skills") is not None
        or raw.get("content_dir") is not None
    ):
        from edim_dde_ai.content.registry import get_content_hub

        get_content_hub().load_from_definition(definition)
    return agent_id


def get_agent_definition(agent_id: str) -> AgentDefinition:
    """Return the registered definition for ``agent_id``."""
    try:
        return _REGISTRY.get(agent_id)
    except AgentRegistryError as exc:
        raise AgentRegistryError(f"Unknown agent: {agent_id}") from exc


def list_agents() -> list[str]:
    """Return sorted registered agent ids."""
    return _REGISTRY.list_keys()


def create_agent(agent_id: str) -> MetadataAgent:
    """Return a compiled MetadataAgent for ``agent_id`` (cached after first build)."""
    with _CACHE_LOCK:
        cached = _CACHE.get(agent_id)
        if cached is not None:
            return cached

        from edim_dde_ai.factories.agent import AgentFactory

        agent = AgentFactory.create(agent_id)
        _CACHE[agent_id] = agent
        return agent


def clear_agent_cache() -> None:
    """Drop all compiled agents (definitions stay registered)."""
    with _CACHE_LOCK:
        _CACHE.clear()


def clear_agent_registry() -> None:
    """Clear definitions and compiled cache (tests / process reset)."""
    clear_agent_cache()
    _REGISTRY.clear(restore_seed=False)
