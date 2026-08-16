"""Pluggable LLM chain invokers keyed by chain name (Strategy catalog).

Business purpose:
  ``llm_chain`` nodes look up an invoker by the ``chain`` config field. Product
  code registers custom Python callables when prompts+LLMProvider are not enough
  (or for fully deterministic chains in tests).

Public API:
  - ``ChainInvoker`` — type alias ``(state, config) -> Any``
  - ``register_chain_invoker`` / ``get_chain_invoker`` / ``list_chain_invokers`` /
    ``clear_chain_invokers``

Nothing is seeded by default; product code registers invokers before build.

Example::

    from edim_dde_ai.registry.chains import register_chain_invoker

    @register_chain_invoker("my_prompt")
    def invoke_my_prompt(state, config):
        return f"hello {state.get('name', '')}"
"""

from __future__ import annotations

from typing import Any, Callable

from edim_dde_ai.errors import ChainInvokerError
from edim_dde_ai.registry.base import Registry

ChainInvoker = Callable[[dict[str, Any], dict[str, Any]], Any]

_REGISTRY: Registry[ChainInvoker] = Registry(
    kind="chain invoker",
    error_cls=ChainInvokerError,
    allow_overwrite=False,
)


def register_chain_invoker(name: str, invoker: ChainInvoker | None = None):
    """Register a chain invoker by name.

    Invoker signature: ``(state, config) -> Any`` (value written to output_key).

    Args:
        name: Chain name matching ``llm_chain`` config ``chain``.
        invoker: Optional callable; omit for decorator form.

    Returns:
        Registered invoker, or a decorator.
    """
    return _REGISTRY.register(name, invoker)


def get_chain_invoker(name: str) -> ChainInvoker:
    """Return the invoker for ``name``.

    Raises:
        ChainInvokerError: If not registered.
    """
    try:
        return _REGISTRY.get(name)
    except ChainInvokerError as exc:
        raise ChainInvokerError(
            f"No chain invoker registered for '{name}'. "
            "Register one with register_chain_invoker() before using llm_chain nodes."
        ) from exc


def list_chain_invokers() -> list[str]:
    """Return sorted registered chain invoker names."""
    return _REGISTRY.list_keys()


def clear_chain_invokers() -> None:
    """Remove all chain invokers (tests)."""
    _REGISTRY.clear(restore_seed=False)
