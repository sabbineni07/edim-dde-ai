"""Conditional-edge router registry (Strategy catalog).

Routers decide which branch to take after a node (LangGraph conditional edges).
YAML references a router by allowlisted name; Python registers factories.

Each factory is ``(config) -> (state) -> branch_label``, same shape as node
factories: resolve config at graph-build time, return a flat-state router.

Builtin ``field_truthy`` requires ``config.field`` (no product-specific default).
Optional ``true_label`` / ``false_label`` default to ``"yes"`` / ``"no"``.

The standard conditional-edge key is ``source`` (not ``from``).

Example YAML::

    conditional_edges:
      - source: decide
        router: field_truthy
        config:
          field: include_explanation
        mapping:
          yes: explain
          no: END

Example Python::

    from edim_dde_ai.registry.routers import register_router

    @register_router("risk_level")
    def risk_level_factory(config):
        def _route(state):
            return "high" if state.get("risk") == "high" else "low"
        return _route
"""

from __future__ import annotations

from typing import Any, Callable

from edim_dde_ai.errors import RouterRegistryError
from edim_dde_ai.registry.base import Registry

RouterFn = Callable[[dict[str, Any]], str]
RouterFactory = Callable[[dict[str, Any]], RouterFn]


def field_truthy_factory(config: dict[str, Any]) -> RouterFn:
    """Route on truthiness of a configured state field.

    Requires ``config.field``. Returns ``true_label`` or ``false_label``
    (defaults ``"yes"`` / ``"no"``).
    """
    field = config.get("field")
    if not isinstance(field, str) or not field.strip():
        raise RouterRegistryError(
            "field_truthy requires config.field (state key to test for truthiness)"
        )
    true_label = str(config.get("true_label", "yes"))
    false_label = str(config.get("false_label", "no"))

    def _route(state: dict[str, Any]) -> str:
        return true_label if state.get(field) else false_label

    return _route


BUILTIN_ROUTER_FACTORIES: dict[str, RouterFactory] = {
    "field_truthy": field_truthy_factory,
}

# Backward-compatible alias (older docs / imports).
BUILTIN_ROUTERS = BUILTIN_ROUTER_FACTORIES

_REGISTRY: Registry[RouterFactory] = Registry(
    kind="router",
    error_cls=RouterRegistryError,
    allow_overwrite=False,
    seed=BUILTIN_ROUTER_FACTORIES,
)


def register_router(name: str, factory: RouterFactory | None = None):
    """Register a conditional-edge router factory by name.

    Can be used as ``@register_router("my_router")`` or
    ``register_router("my_router", factory)``.
    """
    return _REGISTRY.register(name, factory)


def get_router_factory(name: str) -> RouterFactory:
    """Return the router factory for ``name`` (config -> RouterFn)."""
    try:
        return _REGISTRY.get(name)
    except RouterRegistryError as exc:
        raise RouterRegistryError(
            f"Unknown router '{name}'. Register it with register_router()."
        ) from exc


# Alias for less breakage; prefer get_router_factory in new code.
get_router = get_router_factory


def list_routers() -> list[str]:
    return _REGISTRY.list_keys()


def clear_routers(*, keep_builtins: bool = True) -> None:
    _REGISTRY.clear(restore_seed=keep_builtins)
