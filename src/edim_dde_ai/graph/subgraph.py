"""Compile-time LangGraph subgraph embedding + remote dial for ``invoke_agent``.

Mental model::

    YAML ``type: invoke_agent`` + ``agent_id``
      → resolve local vs remote (ADR-001)
      → local: compile child as subgraph; attach native or mapped
      → remote: attach HTTP (or other) dialer node

Guards (compile-time, local path):
  * refuse direct self-call
  * refuse cycles in the agent embed stack
  * enforce ``max_depth`` on nest depth
  * refuse session-enabled children (checkpointer/session_prepare are not
    subgraph-safe under the current model)

YAML author surface: ``agent_id``, ``input_keys``, ``output_map``,
``max_depth``, optional ``resolve`` (``auto``|``local``|``remote``).
"""

from __future__ import annotations

from typing import Any, Callable

from edim_dde_ai.a2a.correlation import child_correlation
from edim_dde_ai.a2a.dialers import get_dialer
from edim_dde_ai.a2a.resolve import resolve_invoke_target
from edim_dde_ai.core.definition import AgentDefinition, NodeSpec
from edim_dde_ai.errors import DefinitionError
from edim_dde_ai.hitl.decorator import NodeFn, skip_until_resume

NodeRunnable = Any  # Compiled LangGraph graph or flat node callable


def parse_invoke_agent_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate ``invoke_agent`` YAML config; return normalized fields.

    Returns:
        Dict with keys ``target``, ``input_keys``, ``output_map``, ``max_depth``,
        ``resolve``.

    Raises:
        ValueError: Invalid shapes.
    """
    target = config.get("agent_id")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("invoke_agent requires non-empty 'agent_id'")
    input_keys = config.get("input_keys")
    if input_keys is not None and not isinstance(input_keys, list):
        raise ValueError("invoke_agent.input_keys must be a list when set")
    if input_keys is not None and not all(isinstance(k, str) for k in input_keys):
        raise ValueError("invoke_agent.input_keys entries must be strings")
    output_map = config.get("output_map")
    if output_map is not None and not isinstance(output_map, dict):
        raise ValueError("invoke_agent.output_map must be a mapping when set")
    if output_map is not None and not all(
        isinstance(k, str) and isinstance(v, str) for k, v in output_map.items()
    ):
        raise ValueError("invoke_agent.output_map keys/values must be strings")
    max_depth = int(config.get("max_depth", 3))
    if max_depth < 1:
        raise ValueError("invoke_agent.max_depth must be >= 1")
    resolve = config.get("resolve")
    if resolve is not None:
        if not isinstance(resolve, str) or not resolve.strip():
            raise ValueError("invoke_agent.resolve must be a non-empty string when set")
        resolve = resolve.strip().lower()
        if resolve not in ("auto", "local", "remote"):
            raise ValueError("invoke_agent.resolve must be auto|local|remote")
    return {
        "target": target.strip(),
        "input_keys": list(input_keys) if input_keys is not None else None,
        "output_map": dict(output_map) if output_map is not None else None,
        "max_depth": max_depth,
        "resolve": resolve,
    }


def uses_mapped_state(input_keys: list[str] | None, output_map: dict[str, str] | None) -> bool:
    """True when parent/child need an explicit I/O map (LangGraph pattern #1)."""
    return input_keys is not None or output_map is not None


def _map_child_input(
    state: dict[str, Any],
    input_keys: list[str] | None,
) -> dict[str, Any]:
    if input_keys is None:
        return dict(state)
    return {k: state.get(k) for k in input_keys}


def _map_child_output(
    child_out: dict[str, Any],
    output_map: dict[str, str] | None,
) -> dict[str, Any]:
    if output_map:
        return {
            parent_key: child_out.get(child_key)
            for child_key, parent_key in output_map.items()
        }
    return dict(child_out)


def mapped_subgraph_node(
    compiled_child: Any,
    *,
    child_agent_id: str,
    input_keys: list[str] | None,
    output_map: dict[str, str] | None,
) -> NodeFn:
    """Return a node that maps parent state ↔ compiled child subgraph.

    Passes LangGraph ``config`` with shared ``request_id`` and per-hop
    ``span_id`` (ADR-001 Phase 1 correlation).
    """

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        child_in = _map_child_input(state, input_keys)
        config, _headers, extras = child_correlation(
            state, child_agent_id=child_agent_id
        )
        child_in.update(extras)
        child_out = compiled_child.invoke(child_in, config=config)
        if not isinstance(child_out, dict):
            return {}
        return _map_child_output(child_out, output_map)

    return _node


def remote_dial_node(
    binding: dict[str, Any],
    *,
    child_agent_id: str,
    input_keys: list[str] | None,
    output_map: dict[str, str] | None,
) -> NodeFn:
    """Runtime node that dials a remote agent via registered transport."""

    transport = str(binding.get("transport") or "http")
    dialer = get_dialer(transport)

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        child_in = _map_child_input(state, input_keys)
        _config, headers, extras = child_correlation(
            state, child_agent_id=child_agent_id
        )
        child_in.update(extras)
        child_out = dialer.invoke(binding, child_in, headers=headers)
        if not isinstance(child_out, dict):
            return {}
        return _map_child_output(child_out, output_map)

    return _node


def compile_child_subgraph(
    target_id: str,
    *,
    parent_agent_id: str,
    embed_stack: tuple[str, ...],
    max_depth: int,
) -> Any:
    """Compile ``target_id`` as a plain flat graph for embedding in a parent.

    Args:
        target_id: Registered child agent id.
        parent_agent_id: Parent being compiled (for error messages).
        embed_stack: Agent ids already on the compile stack (cycle detection).
        max_depth: Max nest depth including this child (``len(stack)+1``).

    Returns:
        Compiled LangGraph runnable (no session checkpointer).

    Raises:
        DefinitionError: Unknown agent, session-enabled child, cycle, or depth.
        AgentRegistryError: Propagated from registry lookup.
    """
    from edim_dde_ai.graph.builder import build_graph
    from edim_dde_ai.graph.session_builder import session_enabled
    from edim_dde_ai.registry.agents import get_agent_definition

    if target_id == parent_agent_id:
        raise DefinitionError(
            f"invoke_agent refuses direct self-call to {target_id!r}"
        )
    if target_id in embed_stack:
        chain = " → ".join([*embed_stack, target_id])
        raise DefinitionError(
            f"invoke_agent cycle detected while compiling {parent_agent_id!r}: {chain}"
        )
    # embed_stack is parents above this child; depth counts this nesting level.
    depth = len(embed_stack)
    if depth >= max_depth:
        raise DefinitionError(
            f"invoke_agent max_depth={max_depth} exceeded "
            f"(target={target_id!r}, parent={parent_agent_id!r}, depth={depth})"
        )

    child_def = get_agent_definition(target_id)
    if session_enabled(child_def):
        raise DefinitionError(
            f"invoke_agent target {target_id!r} is session-enabled; "
            "embed only plain (non-session) agents as subgraphs"
        )

    # Child compile continues the stack so grandchild invoke_agent nodes nest.
    return build_graph(child_def, embed_stack=(*embed_stack, parent_agent_id))


def attach_invoke_agent_node(
    *,
    add_node: Callable[[str, NodeRunnable], None],
    node: NodeSpec,
    parent: AgentDefinition,
    embed_stack: tuple[str, ...],
) -> None:
    """Compile child or attach remote dialer for an ``invoke_agent`` node.

    Args:
        add_node: Callback ``(node_id, runnable)`` — usually
            ``StateGraph.add_node``.
        node: YAML ``invoke_agent`` node.
        parent: Parent agent definition.
        embed_stack: Agents above ``parent`` already compiling (may be empty).
    """
    parsed = parse_invoke_agent_config(dict(node.config))
    target = parsed["target"]
    input_keys = parsed["input_keys"]
    output_map = parsed["output_map"]
    max_depth = parsed["max_depth"]
    resolve = parsed["resolve"]

    decision = resolve_invoke_target(target, resolve=resolve)

    if decision.mode == "remote":
        assert decision.binding is not None
        runnable: NodeRunnable = skip_until_resume(
            node.id,
            remote_dial_node(
                decision.binding,
                child_agent_id=target,
                input_keys=input_keys,
                output_map=output_map,
            ),
        )
        add_node(node.id, runnable)
        return

    child_compiled = compile_child_subgraph(
        target,
        parent_agent_id=parent.agent_id,
        embed_stack=embed_stack,
        max_depth=max_depth,
    )

    if uses_mapped_state(input_keys, output_map):
        # Different schemas / explicit I/O — LangGraph pattern #1.
        runnable = skip_until_resume(
            node.id,
            mapped_subgraph_node(
                child_compiled,
                child_agent_id=target,
                input_keys=input_keys,
                output_map=output_map,
            ),
        )
        add_node(node.id, runnable)
        return

    # Shared flat AgentState — LangGraph native subgraph as a node.
    # HITL skip_until_resume cannot wrap a compiled Pregel without losing
    # subgraph identity; shared-state embeds therefore re-run on HITL resume
    # when a later gate is the resume target (same as re-entering the node).
    add_node(node.id, child_compiled)
