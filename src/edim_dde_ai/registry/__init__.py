"""Agent, node, chain, and router registries (Strategy catalogs).

Public registration APIs stay stable. Routers are factories
(``config -> state -> label``), same pattern as node types.

Prefer ``get_router_factory``; ``get_router`` is an alias for compatibility.
"""

from edim_dde_ai.registry.agents import (
    create_agent,
    get_agent_definition,
    list_agents,
    register_agent,
)
from edim_dde_ai.registry.chains import (
    get_chain_invoker,
    list_chain_invokers,
    register_chain_invoker,
)
from edim_dde_ai.registry.nodes import get_node_factory, list_node_types, register_node
from edim_dde_ai.registry.routers import (
    get_router,
    get_router_factory,
    list_routers,
    register_router,
)

__all__ = [
    "register_node",
    "get_node_factory",
    "list_node_types",
    "register_agent",
    "create_agent",
    "list_agents",
    "get_agent_definition",
    "register_chain_invoker",
    "get_chain_invoker",
    "list_chain_invokers",
    "register_router",
    "get_router",
    "get_router_factory",
    "list_routers",
]
