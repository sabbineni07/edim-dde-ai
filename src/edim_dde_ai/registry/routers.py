"""Conditional-edge router registry (Strategy catalog).

Routers decide which branch to take after a node (LangGraph conditional edges).
YAML references a router by allowlisted name; Python registers factories.

Each factory is ``(config) -> (state) -> branch_label``, same shape as node
factories: resolve config at graph-build time, return a flat-state router.

Builtins:

- ``field_truthy`` — truthiness of ``config.field``
- ``field_equals`` — ``state[field] == config.value``
- ``field_in`` — ``state[field] in config.values``
- ``field_compare`` — compare ``state[field]`` to ``config.value`` with ``config.op``
- ``choice`` — multi-way: label is ``str(state[field])`` or ``config.default``

Binary routers use optional ``true_label`` / ``false_label`` (default ``yes`` / ``no``).
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

Or sugar (see ``core.routes_sugar``)::

    routes:
      - after: decide
        when:
          field: include_explanation
          op: truthy
        then: explain
        else: END
"""

from __future__ import annotations

from typing import Any, Callable

from edim_dde_ai.errors import RouterRegistryError
from edim_dde_ai.registry.base import Registry

RouterFn = Callable[[dict[str, Any]], str]
RouterFactory = Callable[[dict[str, Any]], RouterFn]

_COMPARE_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "ge": lambda a, b: a >= b,
}


def _require_field(config: dict[str, Any], router_name: str) -> str:
    field = config.get("field")
    if not isinstance(field, str) or not field.strip():
        raise RouterRegistryError(
            f"{router_name} requires config.field (state key to inspect)"
        )
    return field


def _binary_labels(config: dict[str, Any]) -> tuple[str, str]:
    return str(config.get("true_label", "yes")), str(config.get("false_label", "no"))


def field_truthy_factory(config: dict[str, Any]) -> RouterFn:
    """Route on truthiness of a configured state field.

    Requires ``config.field``. Returns ``true_label`` or ``false_label``
    (defaults ``"yes"`` / ``"no"``).
    """
    field = _require_field(config, "field_truthy")
    true_label, false_label = _binary_labels(config)

    def _route(state: dict[str, Any]) -> str:
        return true_label if state.get(field) else false_label

    return _route


def field_equals_factory(config: dict[str, Any]) -> RouterFn:
    """Route when ``state[field] == config.value``."""
    field = _require_field(config, "field_equals")
    if "value" not in config:
        raise RouterRegistryError("field_equals requires config.value")
    expected = config["value"]
    true_label, false_label = _binary_labels(config)

    def _route(state: dict[str, Any]) -> str:
        return true_label if state.get(field) == expected else false_label

    return _route


def field_in_factory(config: dict[str, Any]) -> RouterFn:
    """Route when ``state[field]`` is in ``config.values``."""
    field = _require_field(config, "field_in")
    values = config.get("values")
    if not isinstance(values, list) or not values:
        raise RouterRegistryError("field_in requires non-empty config.values list")
    allowed = list(values)
    true_label, false_label = _binary_labels(config)

    def _route(state: dict[str, Any]) -> str:
        return true_label if state.get(field) in allowed else false_label

    return _route


def field_compare_factory(config: dict[str, Any]) -> RouterFn:
    """Route by comparing ``state[field]`` to ``config.value`` with ``config.op``.

    ``op`` is one of: ``eq``, ``ne``, ``lt``, ``le``, ``gt``, ``ge``.
    """
    field = _require_field(config, "field_compare")
    op = config.get("op")
    if not isinstance(op, str) or op.strip().lower() not in _COMPARE_OPS:
        raise RouterRegistryError(
            "field_compare requires config.op in "
            f"{sorted(_COMPARE_OPS)} (got {op!r})"
        )
    if "value" not in config:
        raise RouterRegistryError("field_compare requires config.value")
    cmp_fn = _COMPARE_OPS[op.strip().lower()]
    rhs = config["value"]
    true_label, false_label = _binary_labels(config)

    def _route(state: dict[str, Any]) -> str:
        lhs = state.get(field)
        try:
            ok = cmp_fn(lhs, rhs)
        except TypeError:
            ok = False
        return true_label if ok else false_label

    return _route


def choice_factory(config: dict[str, Any]) -> RouterFn:
    """Multi-way route: return ``str(state[field])`` or ``config.default``.

    Missing/``None`` values map to ``default`` (default label ``\"default\"``).
    Mapping keys in YAML should match the string form of field values.
    """
    field = _require_field(config, "choice")
    default = str(config.get("default", "default"))

    def _route(state: dict[str, Any]) -> str:
        if field not in state or state.get(field) is None:
            return default
        return str(state.get(field))

    return _route


BUILTIN_ROUTER_FACTORIES: dict[str, RouterFactory] = {
    "field_truthy": field_truthy_factory,
    "field_equals": field_equals_factory,
    "field_in": field_in_factory,
    "field_compare": field_compare_factory,
    "choice": choice_factory,
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
