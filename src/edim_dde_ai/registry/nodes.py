"""Allowlisted node type registry (Strategy catalog via Registry).

YAML ``graph.nodes[].type`` must match a registered id. Python registers
factories of shape ``(config) -> (state) -> partial_updates``.

Builtins are seeded from ``nodes.builtin.BUILTIN_NODE_FACTORIES``.

Example::

    from edim_dde_ai.registry.nodes import register_node

    @register_node("echo")
    def echo_factory(config):
        key = config.get("key", "message")
        def _node(state):
            return {key: state.get(key, "")}
        return _node
"""


from __future__ import annotations

from typing import Any, Callable

from edim_dde_ai.errors import NodeRegistryError
from edim_dde_ai.nodes.builtin import BUILTIN_NODE_FACTORIES
from edim_dde_ai.registry.base import Registry

# factory(config) -> callable(state) -> partial state update
NodeFactory = Callable[[dict[str, Any]], Callable[[dict[str, Any]], dict[str, Any]]]

_REGISTRY: Registry[NodeFactory] = Registry(
    kind="node type",
    error_cls=NodeRegistryError,
    allow_overwrite=False,
    seed=BUILTIN_NODE_FACTORIES,
)


def register_node(type_id: str, factory: NodeFactory | None = None):
    """Register a node type by allowlisted id.

    Can be used as ``@register_node("my_type")`` or ``register_node("my_type", factory)``.
    """
    return _REGISTRY.register(type_id, factory)


def get_node_factory(type_id: str) -> NodeFactory:
    try:
        return _REGISTRY.get(type_id)
    except NodeRegistryError as exc:
        raise NodeRegistryError(
            f"Unknown node type '{type_id}'. Register it with register_node() "
            "before building the graph."
        ) from exc


def list_node_types() -> list[str]:
    return _REGISTRY.list_keys()


def clear_node_registry(*, keep_builtins: bool = False) -> None:
    """Clear registered nodes. Used in tests."""
    _REGISTRY.clear(restore_seed=keep_builtins)
