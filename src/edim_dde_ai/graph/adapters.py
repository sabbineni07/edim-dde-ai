"""Adapter: flat metadata callables ↔ LangGraph AgentState.data bag.

LangGraph nodes see ``{"data": {...}}``; product code and registries use a flat
metadata dict. These adapters unwrap before calling and re-wrap updates.

``adapt_router`` expects a ``RouterFn`` already produced by a router factory
(``factory(config)``), not the factory itself.
"""

from __future__ import annotations

from typing import Any, Callable

from edim_dde_ai.registry.routers import RouterFn

NodeFn = Callable[[dict[str, Any]], dict[str, Any]]


def adapt_node(fn: NodeFn) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Unwrap ``AgentState.data`` → ``fn`` → wrap updates under ``data``."""

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        current = dict(state.get("data") or {})
        updates = fn(current) or {}
        if not isinstance(updates, dict):
            raise TypeError("Node must return a dict of state updates")
        return {"data": updates}

    return _node


def adapt_router(router: RouterFn) -> Callable[[dict[str, Any]], str]:
    """Unwrap ``AgentState.data`` for a flat-state router."""

    def _route(state: dict[str, Any]) -> str:
        data = dict(state.get("data") or {})
        return router(data)

    return _route
