# Examples

Runnable samples for engineers learning the YAML + Python hybrid model.
Install the package first (`pip install -e .` from the repo root), or run with
`PYTHONPATH=src`.

Full field contract: `edim-dde-domain/docs/framework/yaml-schema.md` ·  
Composition / subgraphs: `edim-dde-domain/docs/framework/orchestration-topology.md`

## Agent YAML templates (`examples/agents/`)

Each `*.agent.yaml` is heavily commented (identity, optional blocks, node
config keys, edges). Prefer copying a template and deleting the sections you
do not need.

| Path | What it teaches | How to run |
|------|-----------------|------------|
| `echo_agent.agent.yaml` | Minimal graph: `set_value` + `echo_result` | `edim-dde-ai validate/register/run … --input '{"message":"hi"}'` |
| `two_step_agent.agent.yaml` | `set_value` templates (`{field}`) | Same CLI pattern with `two_step_agent` |
| `conditional_agent.agent.yaml` | `conditional_edges` + `field_truthy` | `python examples/run_conditional_agent.py` |
| `routes_sugar_agent.agent.yaml` | `graph.routes` sugar → same branching | `python examples/run_routes_sugar_agent.py` |
| `hitl_demo.agent.yaml` | `hitl.gate` pause / resume fields | API `POST /api/v1/sessions` (+ resume); or unit tests |
| `session_demo.agent.yaml` | `memory` + `session` multi-turn modes | Needs checkpointer; see product dry E2E for HTTP pattern |
| `invoke_agent_child.agent.yaml` | Child subgraph unit (register first) | Used by both parents below |
| `invoke_agent_parent.agent.yaml` | `invoke_agent` **mapped** I/O (pattern #1) | Register child, then `run invoke_parent_demo --yaml …` |
| `invoke_agent_native_parent.agent.yaml` | `invoke_agent` **shared-state** native subgraph | Register child, then `run invoke_native_parent_demo --yaml …` |
| `prompt_inline.agent.yaml` | Inline `prompts` / `skills` + `llm_chain` | `python examples/run_llm_provider_demo.py` |
| `prompt_demo/` | `content_dir` markdown prompts/skills | Same provider demo pattern |

### `invoke_agent` mental model

```text
Mapped (input_keys / output_map set)
  → compile child → wrap with key map  (different schemas)

Native (no map)
  → compile child → add_node(compiled) (shared AgentState)
```

Session-enabled agents cannot be embed targets. Self-call / cycles / `max_depth`
fail at **compile** time.

## Python demos (`examples/*.py`)

| Path | What it teaches |
|------|-----------------|
| `register_custom_nodes.py` | `@register_node` then load YAML |
| `run_conditional_agent.py` | Branch on `include_details` |
| `run_routes_sugar_agent.py` | Same branching via `routes` sugar |
| `run_llm_provider_demo.py` | `set_llm_provider` (no Postgres) |
| `run_custom_invoker_demo.py` | `register_chain_invoker` overrides providers |

Also: `register_from_dict` / `register_from_json` — see `docs/USAGE.md`.

## Obsolete / do not copy

- Do **not** treat `invoke_agent` as a runtime `create_agent(child).invoke` phone
  call — the framework embeds LangGraph subgraphs at parent compile time.
- Product topology (Databricks SQL, Foundry bindings, sizing/RCA nodes) lives in
  `edim-dde-domain` agent packs, not in these foundation examples.
