"""Compile-time LangGraph subgraph embedding for ``invoke_agent``.

Mental model::

    YAML ``type: invoke_agent`` + ``agent_id``
      → resolve child definition
      → compile child as a plain flat graph (subgraph unit)
      → attach to parent:
           shared state (no input_keys / output_map)
             → ``add_node(id, compiled_child)``  # LangGraph native subgraph
           mapped state
             → thin wrapper that maps keys then ``compiled_child.invoke``

Guards (compile-time):
  * refuse direct self-call
  * refuse cycles in the agent embed stack
  * enforce ``max_depth`` on nest depth
  * refuse session-enabled children (checkpointer/session_prepare are not
    subgraph-safe under the current model)

YAML author surface is unchanged: ``agent_id``, ``input_keys``, ``output_map``,
``max_depth``.
"""

from __future__ import annotations

from typing import Any, Callable

from edim_dde_ai.core.definition import AgentDefinition, NodeSpec
from edim_dde_ai.errors import DefinitionError
from edim_dde_ai.hitl.decorator import NodeFn, skip_until_resume

NodeRunnable = Any  # Compiled LangGraph graph or flat node callable


def parse_invoke_agent_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate ``invoke_agent`` YAML config; return normalized fields.

    Returns:
        Dict with keys ``target``, ``input_keys``, ``output_map``, ``max_depth``.

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
    return {
        "target": target.strip(),
        "input_keys": list(input_keys) if input_keys is not None else None,
        "output_map": dict(output_map) if output_map is not None else None,
        "max_depth": max_depth,
    }


def uses_mapped_state(input_keys: list[str] | None, output_map: dict[str, str] | None) -> bool:
    """True when parent/child need an explicit I/O map (LangGraph pattern #1)."""
    return input_keys is not None or output_map is not None


def mapped_subgraph_node(
    compiled_child: Any,
    *,
    input_keys: list[str] | None,
    output_map: dict[str, str] | None,
) -> NodeFn:
    """Return a node that maps parent state ↔ compiled child subgraph.

    This is LangGraph's "call a subgraph inside a node" pattern. The child is a
    real compiled graph (not a fresh ``MetadataAgent`` phone-call).
    """

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        if input_keys is None:
            child_in = dict(state)
        else:
            child_in = {k: state.get(k) for k in input_keys}
        child_out = compiled_child.invoke(child_in)
        if not isinstance(child_out, dict):
            return {}
        if output_map:
            return {
                parent_key: child_out.get(child_key)
                for child_key, parent_key in output_map.items()
            }
        return dict(child_out)

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
    """Compile child and register parent node (native subgraph or mapped wrapper).

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

    child_compiled = compile_child_subgraph(
        target,
        parent_agent_id=parent.agent_id,
        embed_stack=embed_stack,
        max_depth=max_depth,
    )

    if uses_mapped_state(input_keys, output_map):
        # Different schemas / explicit I/O — LangGraph pattern #1.
        runnable: NodeRunnable = skip_until_resume(
            node.id,
            mapped_subgraph_node(
                child_compiled,
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
