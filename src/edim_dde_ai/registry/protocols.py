"""Light Strategy typing protocols for registry callables.

These Protocols document the shapes used by node, chain, and router registries.
Concrete modules currently use ``Callable`` aliases at runtime; this module is
**not imported by the runtime today**. Kept for a later stricter-typing pass
(see ``docs/ROADMAP.md`` → Backlog / hygiene). At that time: wire into
``register_*`` signatures or remove if still redundant.

Keep protocols in sync when signatures change (especially router factories).

Example::

    from edim_dde_ai.registry.protocols import RouterFactory

    def my_router_factory(config: dict) -> RouterFn:
        def _route(state: dict) -> str:
            return "a" if state.get("ok") else "b"
        return _route
"""

from __future__ import annotations

from typing import Any, Protocol


class NodeCallable(Protocol):
    """Flat-state node: ``(state) -> partial updates``."""

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]: ...


class NodeFactory(Protocol):
    """``(config) -> NodeCallable``."""

    def __call__(self, config: dict[str, Any]) -> NodeCallable: ...


class ChainInvoker(Protocol):
    """``(state, config) -> Any`` written to the chain output key."""

    def __call__(self, state: dict[str, Any], config: dict[str, Any]) -> Any: ...


class RouterFn(Protocol):
    """Conditional-edge router: ``(state) -> branch label``."""

    def __call__(self, state: dict[str, Any]) -> str: ...


class RouterFactory(Protocol):
    """``(config) -> RouterFn`` -- same factory shape as node types."""

    def __call__(self, config: dict[str, Any]) -> RouterFn: ...
