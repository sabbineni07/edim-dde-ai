"""Allowlisted builtin node types for YAML-driven agent graphs.

Business purpose:
  Product agents declare nodes by ``type`` id in YAML. These factories are the
  framework defaults (passthrough, set_value, llm_chain, rag.retrieve, etc.).
  Each factory is ``(config) -> (state) -> partial_updates``: config is bound at
  graph-build time; the returned callable runs per invoke on the flat metadata
  state. Domain packs add more types via ``register_node``.

Public API:
  - ``passthrough_factory`` — no-op node (empty updates)
  - ``set_value_factory`` — write a literal or ``{var}``-templated value
  - ``echo_result_factory`` — pack selected keys under ``result``
  - ``llm_chain_factory`` — chain invoker or LLMProvider + prompts
  - ``invoke_agent_factory`` — nested agent call with depth guards
  - ``rag_retrieve_factory`` — corpus search via RetrievalProvider
  - ``web_search_factory`` — opt-in bounded public-web search
  - ``hitl_gate_factory`` — pause for human approval (StateStore session)
  - ``BUILTIN_NODE_FACTORIES`` — type_id → factory map (seeds the node registry)
"""

from __future__ import annotations

import contextvars
import logging
import re
from typing import Any

from edim_dde_ai.content.messages import build_chat_messages
from edim_dde_ai.content.registry import get_llm_provider
from edim_dde_ai.errors import ChainInvokerError
from edim_dde_ai.hitl.gate import hitl_gate_factory
from edim_dde_ai.registry.chains import get_chain_invoker, list_chain_invokers

_TEMPLATE_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
logger = logging.getLogger(__name__)
# Tracks nested invoke_agent depth across ContextVar boundaries (async-safe).
_INVOKE_AGENT_DEPTH: contextvars.ContextVar[int] = contextvars.ContextVar(
    "edim_invoke_agent_depth", default=0
)


def _substitute(template: str, state: dict[str, Any]) -> str:
    """Replace ``{identifier}`` placeholders with ``str(state[identifier])``.

    Unknown keys become empty string (same contract as content.messages).
    """

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(state.get(key, ""))

    return _TEMPLATE_RE.sub(repl, template)


def passthrough_factory(_config: dict[str, Any]):
    """No-op node: returns empty updates so the graph can place a placeholder.

    Args:
        _config: Ignored; accepted for factory shape consistency.

    Returns:
        A node callable ``(state) -> {}``.

    Example YAML::

        - id: gate
          type: passthrough
    """

    def _node(_state: dict[str, Any]) -> dict[str, Any]:
        return {}

    return _node


def set_value_factory(config: dict[str, Any]):
    """Write one state field from a literal ``value`` or ``template``.

    Config:
      field: str (required) — destination state key
      value: Any — used when ``template`` is absent
      template: str — ``{var}`` substitution against current state (wins if set)

    Args:
        config: Node config from YAML (``field`` required).

    Returns:
        A node callable that returns ``{field: value}``.

    Raises:
        ValueError: If ``field`` is missing or not a non-empty string.

    Example YAML::

        - id: stamp
          type: set_value
          field: status
          template: "done:{cluster_id}"
    """
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
    """Copy selected state keys into a nested ``result`` dict.

    Useful as a terminal shaping step so API clients receive a stable payload.

    Config:
      from_fields: list[str] — keys to include (missing keys map to ``None``)

    Args:
        config: Must include ``from_fields`` as a list (may be empty).

    Returns:
        A node callable returning ``{"result": {k: state.get(k), ...}}``.

    Raises:
        ValueError: If ``from_fields`` is not a list.
    """
    from_fields = config.get("from_fields") or []
    if not isinstance(from_fields, list):
        raise ValueError("echo_result.from_fields must be a list")

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        return {"result": {k: state.get(k) for k in from_fields}}

    return _node


def invoke_agent_factory(config: dict[str, Any]):
    """Call another registered agent and merge selected outputs (BL-025).

    Builds a child input dict, invokes ``create_agent(target)``, then maps
    child outputs back onto the parent state. Depth is tracked with a
    ``ContextVar`` so nested invokes cannot recurse unbounded.

    Config:
      agent_id: str (required) — target agent id
      input_keys: list[str] — keys to pass (default: all parent state keys)
      output_map: dict[str, str] — child_key → parent_key (default: merge all)
      max_depth: int — nested invoke limit (default 3)
      caller_agent_id: str — injected by GraphBuilder (parent agent)

    Args:
        config: See Config above. ``caller_agent_id`` is injected at build time.

    Returns:
        A node callable that returns mapped/merged child outputs, or ``{}``
        when the child returns a non-dict.

    Raises:
        ValueError: Invalid config shapes.
        DefinitionError: Depth exceeded or direct self-call.

    Example YAML::

        - id: sub
          type: invoke_agent
          agent_id: helper_agent
          input_keys: [query]
          output_map: {answer: helper_answer}
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
        # Direct self-call is always refused; deeper cycles still hit max_depth.
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
    """Run a named LLM chain: registered invoker first, else prompts + LLMProvider.

    Resolution order at invoke time:
      1. If ``chain`` is in ``list_chain_invokers()``, call that invoker.
      2. Else require ``agent_id`` (injected by GraphBuilder) and an
         ``LLMProvider``; build messages via ``build_chat_messages`` and invoke.

    Config:
      chain: str (required) — invoker name and/or prompt chain key
      output_key: str — state key for the result (default ``llm_raw``)
      attach_skills: bool — append domain skills to system prompt (default False)
      agent_id: str — injected by GraphBuilder for prompt lookup
      endpoint / deployment: optional — injected from agent ``bindings.llm``
        when configured (Foundry uses these; omit → process globals)

    Args:
        config: See Config above.

    Returns:
        A node callable returning ``{output_key: value}``.

    Raises:
        ValueError: Missing ``chain``.
        ChainInvokerError: No invoker and no agent_id/LLMProvider.

    Example YAML::

        - id: reason
          type: llm_chain
          chain: rca_prompt
          output_key: analysis
          attach_skills: true
    """
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


def rag_retrieve_factory(config: dict[str, Any]):
    """Similarity / hybrid search via the active RetrievalProvider (BL-021).

    Resolves a query from config/state, calls ``search_corpus``, and writes both
    structured hits and a formatted context string for downstream LLM nodes.

    Config:
      corpus: str — logical corpus name (default ``default``)
      top_k: int — max hits (default 5)
      search_mode: vector | keyword | hybrid (default hybrid)
      query: str — literal query (optional; supports ``{var}`` templates)
      query_key: str — state key holding the query string
      query_keys: list[str] — join multiple state string fields with newlines
      output_key: str — hits list key (default ``retrieval_hits``)
      context_key: str — formatted text key (default ``retrieval_context``)
      skip_if_empty_query: bool — no-op when query blank (default True)
      endpoint: str — optional Search service URL (from ``bindings.search``)
      index: str — optional physical index override (from ``bindings.search``)

    Query resolution order: ``query`` → ``query_key`` → ``query_keys`` →
    auto keys ``retrieval_query`` / ``query`` / ``question`` / ``user_query``.

    Args:
        config: See Config above.

    Returns:
        A node callable returning ``{output_key: [hit dicts], context_key: str}``.

    Example YAML::

        - id: retrieve
          type: rag.retrieve
          corpus: rca_kb
          top_k: 8
          query_key: retrieval_query
    """
    corpus = str(config.get("corpus") or "default")
    top_k = int(config.get("top_k", 5))
    search_mode = str(config.get("search_mode") or "hybrid")
    output_key = str(config.get("output_key") or "retrieval_hits")
    context_key = str(config.get("context_key") or "retrieval_context")
    skip_if_empty = bool(config.get("skip_if_empty_query", True))
    literal_query = config.get("query")
    query_key = config.get("query_key")
    query_keys = config.get("query_keys")
    override_endpoint = config.get("endpoint")
    override_index = config.get("index")

    def _resolve_query(state: dict[str, Any]) -> str:
        if isinstance(literal_query, str) and literal_query.strip():
            return _substitute(literal_query, state)
        if isinstance(query_key, str) and query_key:
            return str(state.get(query_key) or "")
        if isinstance(query_keys, list) and query_keys:
            parts = [str(state.get(k) or "").strip() for k in query_keys]
            return "\n".join(p for p in parts if p)
        # Auto: common RCA / generic keys when YAML omits an explicit source.
        for key in ("retrieval_query", "query", "question", "user_query"):
            val = state.get(key)
            if isinstance(val, str) and val.strip():
                return val
        return ""

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        from edim_dde_ai.retrieval import (
            format_hits_as_context,
            search_corpus,
        )

        query = _resolve_query(state).strip()
        if not query and skip_if_empty:
            return {output_key: [], context_key: "(no retrieval query)"}
        # Non-empty spacer keeps provider contracts happy when skip_if_empty is False.
        hits = search_corpus(
            query or " ",
            corpus=corpus,
            top_k=top_k,
            search_mode=search_mode,
            endpoint=(
                str(override_endpoint).strip()
                if isinstance(override_endpoint, str) and str(override_endpoint).strip()
                else None
            ),
            index=(
                str(override_index).strip()
                if isinstance(override_index, str) and str(override_index).strip()
                else None
            ),
        )
        return {
            output_key: [h.to_dict() for h in hits],
            context_key: format_hits_as_context(hits),
        }

    return _node


def web_search_factory(config: dict[str, Any]):
    """Bounded, opt-in public-web search via ``WebSearchProvider``.

    Safety contract: this node never builds a query from arbitrary state or
    prompt contents. The product/domain node must write a sanitized string into
    ``query_key`` first. Failures are soft — analysis continues offline.

    Config:
      enabled: bool — must be True to search (default False)
      query_key: str — state key with sanitized query (default ``web_search_query``)
      output_key: str — hits list (default ``web_search_hits``)
      context_key: str — formatted snippets (default ``web_search_context``)
      top_k: int — clamped to 1..10 (default 3)
      allowed_domains: list[str] — optional domain allowlist (lowercased)

    Args:
        config: See Config above.

    Returns:
        A node callable returning hits + context; empty/placeholder strings when
        disabled, untriggered, unconfigured, or on provider failure.

    Example YAML::

        - id: web
          type: web.search
          enabled: true
          query_key: web_search_query
          top_k: 3
          allowed_domains: [docs.python.org]
    """
    enabled = bool(config.get("enabled", False))
    query_key = str(config.get("query_key") or "web_search_query")
    output_key = str(config.get("output_key") or "web_search_hits")
    context_key = str(config.get("context_key") or "web_search_context")
    top_k = max(1, min(int(config.get("top_k", 3)), 10))
    domains = tuple(
        str(value).strip().lower()
        for value in (config.get("allowed_domains") or [])
        if str(value).strip()
    )

    def _node(state: dict[str, Any]) -> dict[str, Any]:
        if not enabled:
            return {
                output_key: [],
                context_key: "(web search disabled by agent configuration)",
            }
        query = str(state.get(query_key) or "").strip()
        if not query:
            return {
                output_key: [],
                context_key: "(web search not triggered for this analysis)",
            }

        from edim_dde_ai.web import WebSearchRequest, get_web_search_provider

        provider = get_web_search_provider()
        if getattr(provider, "name", "none") == "none":
            return {
                output_key: [],
                context_key: "(web search enabled but no provider is configured)",
            }
        try:
            hits = provider.search(
                WebSearchRequest(query=query, top_k=top_k, domains=domains)
            )
        except Exception as exc:
            # Online enrichment must not make evidence-based diagnosis fail.
            logger.warning("web search enrichment failed: %s", type(exc).__name__)
            return {
                output_key: [],
                context_key: "(web search provider failed; analysis continued offline)",
            }
        lines = [
            f"[web:{index}] {hit.title}\nURL: {hit.url}\n{hit.snippet}".strip()
            for index, hit in enumerate(hits[:top_k], start=1)
        ]
        return {
            output_key: [hit.to_dict() for hit in hits[:top_k]],
            context_key: "\n\n".join(lines) if lines else "(no web results)",
        }

    return _node


# Single source of truth for builtin type_id → factory (seeded into the node registry).
# ``hitl.gate`` lives in ``edim_dde_ai.hitl.gate``; re-exported here so the registry
# seed stays one map.
BUILTIN_NODE_FACTORIES = {
    "passthrough": passthrough_factory,
    "set_value": set_value_factory,
    "echo_result": echo_result_factory,
    "llm_chain": llm_chain_factory,
    "invoke_agent": invoke_agent_factory,
    "rag.retrieve": rag_retrieve_factory,
    "web.search": web_search_factory,
    "hitl.gate": hitl_gate_factory,
}
