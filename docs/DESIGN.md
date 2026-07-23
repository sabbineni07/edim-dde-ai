# EDIM DDE AI — Design

## Purpose

`edim-dde-ai` is a **YAML-driven LangGraph agent framework** packaged as an installable wheel.
It is the runtime foundation for EDIM AI agents. **API and UI are separate future projects.**
Product agents (RCA, cluster tuning, and others) will consume this wheel later.

## Hybrid model

| Layer | Responsibility |
|-------|----------------|
| **YAML** | Declares agent id, graph topology (nodes, edges, optional conditional edges), and node config |
| **Python** | Implements node *types* registered by allowlisted `type` ids |

YAML never specifies arbitrary Python import paths. Only registered `type` strings are resolved.

## Design patterns (GoF)

Reuse is expressed with a small set of classic patterns — no DI container, Observer, or Abstract Factory sprawl.

| Pattern | Where | Role |
|---------|-------|------|
| **Registry** (catalog / Singleton scope) | `registry/base.py` → nodes, chains, routers, agents | One keyed catalog per concern; seed + clear/restore for builtins |
| **Strategy** | Node factories, chain invokers, router factories | Swappable algorithms selected by allowlisted id |
| **Builder** | `graph/builder.py` (`GraphBuilder`) | Stepwise graph assembly; `build_graph()` remains the public facade |
| **Factory Method** | `factories/agent.py` (`AgentFactory.create`) | Construct `MetadataAgent` from a registered definition |
| **Adapter** | `graph/adapters.py` | Flat metadata callables ↔ LangGraph `AgentState.data` bag |
| **Template Method** | `graph/runtime.py` (`MetadataAgent`) | Shared `_prepare` / `_extract` for `invoke` and `ainvoke` |
| **Facade** | `edim_dde_ai` / `api/entrypoints` / registry wrappers | Stable public API over internal structure |

Light **Protocol** typing for strategies lives in `registry/protocols.py` (documentation/typing only).

## Package layout

```
edim_dde_ai/
  __init__.py          # public API re-exports (Facade)
  errors.py            # shared exceptions
  version.py
  core/                # definition + YAML loading
  content/             # PromptProvider / SkillProvider / LLMProvider + ContentHub
  registry/            # Registry base + agents, nodes, chains, routers
  factories/           # AgentFactory
  graph/               # Builder, adapters, MetadataAgent runtime
  nodes/               # builtin node implementations + BUILTIN_NODE_FACTORIES
  api/                 # register_from_yaml / paths / directory
  cli/                 # argparse CLI + path store
```

## Components

```
YAML / directory
      │
      ▼
core.loader  ──► core.definition (parse + validate)
      │
      ▼
registry.agents  ◄── register_agent / api.register_from_*
      │
      ▼
factories.agent / graph.builder   ── uses registry.nodes + registry.routers
      │                              (+ adapters for LangGraph state)
      ▼
graph.runtime.MetadataAgent  (invoke / ainvoke)
```

### Node registry (`registry/nodes.py`)

- Backed by `Registry[NodeFactory]` seeded from `nodes.builtin.BUILTIN_NODE_FACTORIES`.
- `register_node(type_id, factory)` allowlists a node type.
- Builtin types: `passthrough`, `set_value`, `echo_result`, `llm_chain`.
- Custom types are registered in application code before loading YAML.

### Agent registry (`registry/agents.py`)

- Stores `AgentDefinition` by `agent_id` (`allow_overwrite` supported via flag).
- `create_agent(agent_id)` delegates to `AgentFactory.create` → LangGraph + `MetadataAgent`.

### Graph builder (`graph/builder.py`)

- `GraphBuilder` adds nodes, entry, edges, conditional edges, then compiles.
- `build_graph(definition)` is the public function and uses `GraphBuilder` internally.
- Adapters wrap flat-state nodes/routers for the internal `data` bag channel.
- Edges: `"END"` string maps to LangGraph `END`.

### Routers (`registry/routers.py`)

- Factories: `(config) -> (state) -> branch_label` (same shape as node factories).
- `register_router` / `get_router_factory` / `list_routers`; `get_router` is an alias of `get_router_factory`.
- Seeded with `BUILTIN_ROUTER_FACTORIES` (`BUILTIN_ROUTERS` alias kept for older imports).
- Builtin: `field_truthy` — requires `config.field`; optional `true_label` / `false_label` (default `yes` / `no`). No product-specific field default.
- Conditional-edge YAML uses `source` only (not `from`); optional `config` mapping is passed to the factory at graph-build time.

Example YAML::

    conditional_edges:
      - source: generate_recommendation
        router: field_truthy
        config:
          field: include_explanation
        mapping:
          yes: generate_explanation
          no: END

### Chain invokers (`registry/chains.py`)

- `llm_chain` nodes look up a pluggable invoker by `chain` name **first**.
- If no invoker is registered, messages are built from content providers and
  `LLMProvider.invoke` is called (must be set via `set_llm_provider`).
- Missing both invoker and LLMProvider raises `ChainInvokerError`.

### Content providers (`content/`)

Process-wide hooks for prompts, skills, and LLM calls (no database in this package):

| Piece | Role |
|-------|------|
| `PromptProvider` / `SkillProvider` / `LLMProvider` | Protocols |
| `ContentHub` | Default prompt+skill provider: optional user override → per-agent `content_dir` → inline store |
| `InlineContentStore` | YAML `prompts:` / `skills:` merged on `register_agent` |
| `DirectoryContentProvider` | `prompts/{chain}.{role}.md`, `skills/{key}.md` |
| `build_chat_messages` | Load roles, `{var}` substitution from state, optional skill appendix |

`AgentDefinition.source_path` is set by `load_yaml` so relative `content_dir` resolves next to the agent YAML.

`GraphBuilder` injects `agent_id` into each node config so `llm_chain` can resolve content.

### Entry points (`api/entrypoints.py`)

- `register_from_yaml`, `register_from_paths`, `register_from_directory` (`*.agent.yaml`).

## State model

State is an open mapping suitable for metadata agents — callers pass and receive dicts.
Nodes return partial updates merged into state.

## Security stance

No dynamic imports from YAML. Node and router ids must be pre-registered in Python.
