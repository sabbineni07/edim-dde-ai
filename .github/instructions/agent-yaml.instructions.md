---
description: Agent YAML conventions for edim-dde-ai
applyTo: "**/*.{yaml,yml}"
---

# Agent YAML conventions

## Required shape

```yaml
agent_id: my_agent
display_name: My Agent
version: 1
graph:
  nodes:
    - id: start
      type: set_value
      field: stage
      value: begun
  edges:
    - [START, start]
    - [start, END]
```

## Rules

- Extra keys on a node (beyond `id` / `type`) become `NodeSpec.config`.
- Graph entry: set `graph.entry` **or** include a `[START, node]` edge (or both if they agree).
- `START` / `END` are reserved edge endpoints — not node ids.
- Conditional edges use `source`, `router` (registered id), and `mapping`.
- Prefer `*.agent.yaml` under agent directories (loader default pattern).
- **Do not** put Python module paths or callables in YAML.
- Keep product-specific topology in consuming projects (`edim-dde-domain`), not in foundation examples unless illustrating the framework.
