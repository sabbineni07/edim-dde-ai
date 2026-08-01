"""Builtin allowlisted node types.

Factories registered under ids such as ``passthrough``, ``set_value``, and
``llm_chain``. Each is ``(config) -> (state) -> partial_updates``.

``llm_chain`` prefers a registered chain invoker; otherwise builds messages
from content providers and calls ``LLMProvider``.
Product agents add more types via ``register_node``.
"""


from __future__ import annotations

import contextvars
import re
from typing import Any

from edim_dde_ai.content.messages import build_chat_messages
from edim_dde_ai.content.registry import get_llm_provider
from edim_dde_ai.errors import ChainInvokerError
from edim_dde_ai.registry.chains import get_chain_invoker, list_chain_invokers

_TEMPLATE_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
_INVOKE_AGENT_DEPTH: contextvars.ContextVar[int] = contextvars.ContextVar(
    "edim_invoke_agent_depth", default=0
)


def _substitute(template: str, state: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(state.get(key, ""))

    return _TEMPLATE_RE.sub(repl, template)


def passthrough_factory(_config: dict[str, Any]):
    def _node(_state: dict[str, Any]) -> dict[str, Any]:
        return {}

    return _node


def set_value_factory(config: dict[str, Any]):
    field = config.get("field")
    if not isinstance(field, str) or not field:
        raise ValueError("set_value requires 'field'")

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        if "template" in config:
            value = _substitute(str(config["template"]), state)
        else:
            value = config.get("value")
        return {field: value}

    return _node


def echo_result_factory(config: dict[str, Any]):
    from_fields = config.get("from_fields") or []
    if not isinstance(from_fields, list):
        raise ValueError("echo_result.from_fields must be a list")

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        return {"result": {k: state.get(k) for k in from_fields}}

    return _node


def invoke_agent_factory(config: dict[str, Any]):
    """Call another registered agent and merge selected outputs (BL-025).

    Config:
      agent_id: str (required) — target agent
      input_keys: list[str] — keys to pass (default: all parent state keys)
      output_map: dict[str, str] — child_key → parent_key (default: merge all)
      max_depth: int — nested invoke limit (default 3)
      caller_agent_id: str — injected by GraphBuilder (parent agent)
    """
    target = config.get("agent_id")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("invoke_agent requires non-empty 'agent_id'")
    input_keys = config.get("input_keys")
    if input_keys is not None and not isinstance(input_keys, list):
        raise ValueError("invoke_agent.input_keys must be a list when set")
    output_map = config.get("output_map")
    if output_map is not None and not isinstance(output_map, dict):
        raise ValueError("invoke_agent.output_map must be a mapping when set")
    max_depth = int(config.get("max_depth", 3))
    if max_depth < 1:
        raise ValueError("invoke_agent.max_depth must be >= 1")

    parent_agent_id = config.get("caller_agent_id")

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        from edim_dde_ai.errors import DefinitionError
        from edim_dde_ai.registry.agents import create_agent

        depth = _INVOKE_AGENT_DEPTH.get()
        if depth >= max_depth:
            raise DefinitionError(
                f"invoke_agent max_depth={max_depth} exceeded "
                f"(target={target!r}, parent={parent_agent_id!r})"
            )
        if parent_agent_id and parent_agent_id == target:
            raise DefinitionError(
                f"invoke_agent refuses direct self-call to {target!r}"
            )

        if input_keys is None:
            child_in = dict(state)
        else:
            child_in = {k: state.get(k) for k in input_keys}

        token = _INVOKE_AGENT_DEPTH.set(depth + 1)
        try:
            child_out = create_agent(target).invoke(child_in)
        finally:
            _INVOKE_AGENT_DEPTH.reset(token)

        if not isinstance(child_out, dict):
            return {}
        if output_map:
            return {
                parent_key: child_out.get(child_key)
                for child_key, parent_key in output_map.items()
            }
        return dict(child_out)

    return _node


def llm_chain_factory(config: dict[str, Any]):
    chain = config.get("chain")
    if not isinstance(chain, str) or not chain:
        raise ValueError("llm_chain requires 'chain' name")
    output_key = config.get("output_key", "llm_raw")
    attach_skills = bool(config.get("attach_skills", False))
    agent_id = config.get("agent_id")

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        # Custom invoker wins when registered for this chain name.
        if chain in list_chain_invokers():
            invoker = get_chain_invoker(chain)
            value = invoker(state, config)
            return {output_key: value}

        if not agent_id:
            raise ChainInvokerError(
                f"No invoker for '{chain}' and no agent_id on llm_chain config "
                "(GraphBuilder injects agent_id; ensure the node was built via GraphBuilder)."
            )
        llm = get_llm_provider()
        if llm is None:
            raise ChainInvokerError(
                f"No chain invoker registered for '{chain}' and no LLMProvider set. "
                "Register one with register_chain_invoker() or set_llm_provider()."
            )
        messages = build_chat_messages(
            agent_id=str(agent_id),
            chain=chain,
            state=state,
            attach_skills=attach_skills,
        )
        text = llm.invoke(messages, config=config)
        return {output_key: text}

    return _node


# Single source of truth for builtin type_id → factory (seeded into the node registry).
BUILTIN_NODE_FACTORIES = {
    "passthrough": passthrough_factory,
    "set_value": set_value_factory,
    "echo_result": echo_result_factory,
    "llm_chain": llm_chain_factory,
    "invoke_agent": invoke_agent_factory,
}
