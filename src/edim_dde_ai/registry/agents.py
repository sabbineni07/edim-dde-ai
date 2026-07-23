"""In-process agent definition registry and factory facade.

Stores parsed ``AgentDefinition`` objects by ``agent_id``. Overwrite is allowed
by default so CLI/API reloads are easy; pass ``overwrite=False`` to forbid.

``create_agent(agent_id)`` builds a ``MetadataAgent`` via ``AgentFactory``.

Example::

    from edim_dde_ai.registry.agents import register_agent, create_agent
    from edim_dde_ai.core.loader import load_yaml

    register_agent(load_yaml("demo.agent.yaml"))
    agent = create_agent("demo")
    agent.invoke({"x": 1})
"""


from __future__ import annotations

from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.errors import AgentRegistryError
from edim_dde_ai.graph.runtime import MetadataAgent
from edim_dde_ai.registry.base import Registry

_REGISTRY: Registry[AgentDefinition] = Registry(
    kind="agent",
    error_cls=AgentRegistryError,
    allow_overwrite=True,
)


def register_agent(definition: AgentDefinition, *, overwrite: bool = False) -> str:
    """Register an AgentDefinition. Returns agent_id.

    When the definition ``raw`` includes ``prompts`` / ``skills`` or
    ``content_dir``, content is merged into the process-wide ContentHub
    (inline store and/or per-agent directory roots).
    """
    agent_id = definition.agent_id
    _REGISTRY.register(agent_id, definition, overwrite=overwrite)
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
    try:
        return _REGISTRY.get(agent_id)
    except AgentRegistryError as exc:
        raise AgentRegistryError(f"Unknown agent: {agent_id}") from exc


def list_agents() -> list[str]:
    return _REGISTRY.list_keys()


def create_agent(agent_id: str) -> MetadataAgent:
    """Build a MetadataAgent for ``agent_id`` (delegates to AgentFactory)."""
    from edim_dde_ai.factories.agent import AgentFactory

    return AgentFactory.create(agent_id)


def clear_agent_registry() -> None:
    _REGISTRY.clear(restore_seed=False)
