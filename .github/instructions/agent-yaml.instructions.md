---
description: Agent YAML conventions for edim-dde-ai
applyTo: "**/*.{yaml,yml}"
---

# Agent YAML conventions

Engineer templates with field comments live under `examples/agents/*.agent.yaml`.
Canonical contract: `edim-dde-domain/docs/framework/yaml-schema.md`.

## Required shape

```yaml
agent_id: my_agent          # required — registry / invoke id
display_name: My Agent      # optional — defaults to agent_id
version: 1                  # optional int
graph:
  nodes:
    - id: start             # required per node
      type: set_value       # required — allowlisted factory id
      field: stage          # factory config (all keys except id/type)
      value: begun
  edges:
    - [START, start]        # or set graph.entry
    - [start, END]
```

## Common optional blocks

| Block | Purpose |
|-------|---------|
| `metadata` | Catalog: `owner`, `risk_tier`, `lifecycle`, `hitl_required` |
| `hitl` | Runtime gate policy: `enabled`, `decisions`, `patch_*` |
| `memory` + `session` | Multi-turn (checkpointer); required together when strategy ≠ none |
| `prompts` / `skills` / `content_dir` | LLM content for `llm_chain` |
| `bindings` | Per-agent LLM / search / SQL / cosmos targets (`${ENV:…}`) |
| `rag` | Retrieval knobs for `rag.retrieve` |

## Graph rules

- Extra keys on a node (beyond `id` / `type`) become `NodeSpec.config`.
- Graph entry: set `graph.entry` **or** include a `[START, node]` edge (or both if they agree).
- `START` / `END` are reserved edge endpoints — not node ids.
- Conditional edges use `source`, `router` (registered id), and `mapping`.
- Prefer `graph.routes` sugar for simple field ops; use `conditional_edges` for custom routers.
- Prefer `*.agent.yaml` under agent directories (loader default pattern).
- **Do not** put Python module paths or callables in YAML.
- Keep product-specific topology in consuming projects (`edim-dde-domain`), not in foundation examples unless illustrating the framework.

## `invoke_agent` (subgraphs)

```yaml
- id: call_child
  type: invoke_agent
  agent_id: child_agent_id   # required — must already be registered
  input_keys: [a, b]         # optional — omit for native shared-state subgraph
  output_map: {x: y}         # optional — child_key → parent_key
  max_depth: 3               # optional — compile-time nest limit
```

- Mapped I/O → LangGraph “call subgraph inside a node”.
- No map → native `add_node(compiled_child)`.
- Refuse: self-call, cycles, session-enabled children, `max_depth` overflow.
- Examples: `examples/agents/invoke_agent_*.agent.yaml`.
