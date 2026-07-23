"""EDIM DDE AI — YAML-driven LangGraph agent framework."""

from edim_dde_ai.api.entrypoints import (
    register_from_dict,
    register_from_dicts,
    register_from_directory,
    register_from_json,
    register_from_paths,
    register_from_yaml,
)
from edim_dde_ai.registry.agents import (
    create_agent,
    get_agent_definition,
    list_agents,
    register_agent,
)
from edim_dde_ai.registry.nodes import register_node
from edim_dde_ai.version import __version__

# Register builtin node types on import
from edim_dde_ai import nodes as _nodes  # noqa: F401

__all__ = [
    "__version__",
    "register_node",
    "register_from_yaml",
    "register_from_directory",
    "register_from_paths",
    "register_from_dict",
    "register_from_dicts",
    "register_from_json",
    "register_agent",
    "create_agent",
    "list_agents",
    "get_agent_definition",
]
