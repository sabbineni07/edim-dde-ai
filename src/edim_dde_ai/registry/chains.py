"""Pluggable LLM chain invokers keyed by chain name (Strategy catalog).

``llm_chain`` nodes look up an invoker by the ``chain`` config field.
Invoker signature: ``(state, config) -> Any`` (value written to ``output_key``).

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
    """
    return _REGISTRY.register(name, invoker)


def get_chain_invoker(name: str) -> ChainInvoker:
    try:
        return _REGISTRY.get(name)
    except ChainInvokerError as exc:
        raise ChainInvokerError(
            f"No chain invoker registered for '{name}'. "
            "Register one with register_chain_invoker() before using llm_chain nodes."
        ) from exc


def list_chain_invokers() -> list[str]:
    return _REGISTRY.list_keys()


def clear_chain_invokers() -> None:
    _REGISTRY.clear(restore_seed=False)
