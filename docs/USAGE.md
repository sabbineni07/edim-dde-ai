# Usage

## Install (editable)

```bash
cd /path/to/edim-dde-ai
pip install -e ".[dev]"
```

## Register and run from Python

```python
from edim_dde_ai import (
    register_from_yaml,
    register_from_directory,
    register_from_paths,
    create_agent,
    list_agents,
)

register_from_yaml("examples/agents/echo_agent.agent.yaml")
# or: register_from_directory("examples/agents")
# or: register_from_paths(["a.agent.yaml", "b.agent.yaml"])

print(list_agents())
agent = create_agent("echo_agent")
result = agent.invoke({"message": "hello"})
```


## Register from dict / JSON (API-friendly)

Use these helpers when the definition arrives as a FastAPI/JSON body rather than a YAML file:

```python
from edim_dde_ai import (
    register_from_dict,
    register_from_json,
    register_from_dicts,
    create_agent,
)

# FastAPI body is already a dict
register_from_dict(request_body, overwrite=True)
# or raw JSON string
register_from_json(raw_json, overwrite=True)
# or batch
register_from_dicts([body_a, body_b], overwrite=True)

agent = create_agent("echo_agent")
result = agent.invoke({"message": "hello"})
```

Invalid JSON or a non-object JSON root raises `DefinitionError`. Missing required fields (for example `agent_id`) also raise `DefinitionError`.

## Custom nodes

Register a node type before loading YAML that references it:

```python
from edim_dde_ai import register_node, register_from_yaml, create_agent

@register_node("upper_message")
def upper_message(config):
    def _node(state):
        msg = state.get("message", "")
        return {"message": str(msg).upper()}
    return _node

register_from_yaml("path/to/agent.agent.yaml")
agent = create_agent("my_agent")
```

See `examples/register_custom_nodes.py`.

## Conditional edges (routers)

Routers are factories: `(config) -> (state) -> branch_label`, same idea as node types.

### Builtins

| Router | Config | Labels |
|--------|--------|--------|
| `field_truthy` | `field` | `true_label` / `false_label` (default `yes` / `no`) |
| `field_equals` | `field`, `value` | same |
| `field_in` | `field`, `values` (list) | same |
| `field_compare` | `field`, `op` (`eq\|ne\|lt\|le\|gt\|ge`), `value` | same |
| `choice` | `field`, optional `default` (default `default`) | mapping keys = `str(state[field])` |

### Explicit YAML

    conditional_edges:
      - source: generate_recommendation   # use source, not from
        router: field_truthy
        config:
          field: include_explanation
        mapping:
          yes: generate_explanation
          no: END

### Routes sugar (desugars to `conditional_edges`)

    routes:
      - after: generate_recommendation
        when:
          field: include_explanation
          op: truthy          # truthy | equals | in | compare
        then: generate_explanation
        else: END

      - after: classify
        switch: category
        cases:
          oom: handle_oom
          timeout: handle_timeout
        else: handle_other    # maps to choice default label

See `examples/agents/routes_sugar_agent.agent.yaml`.

### Custom routers

    from edim_dde_ai.registry.routers import register_router

    @register_router("risk_level")
    def risk_level_factory(config):
        def _route(state):
            return "high" if state.get("risk") == "high" else "low"
        return _route

## LLM chains (optional)

### Option A — Custom chain invoker (wins if registered)

```python
from edim_dde_ai.registry.chains import register_chain_invoker

@register_chain_invoker("my_chain")
def my_chain(state, config):
    return {"text": "stub response"}
```

### Option B — Inline prompts + LLMProvider

Agent YAML:

```yaml
prompts:
  chat:
    system: "You are helpful."
    human: "Question: {question}"
skills:
  - key: brevity
    title: Brevity
    content: "Keep it short."
graph:
  entry: call
  nodes:
    - id: call
      type: llm_chain
      chain: chat
      attach_skills: true
  edges:
    - [call, END]
```

Python:

```python
from edim_dde_ai import register_from_yaml, create_agent, set_llm_provider

class MyLLM:
    def invoke(self, messages, *, config=None):
        # messages: list[tuple[str, str]] e.g. ("system", "..."), ("human", "...")
        return "model reply"

set_llm_provider(MyLLM())
register_from_yaml("examples/agents/prompt_inline.agent.yaml")
print(create_agent("prompt_inline").invoke({"question": "hi"}))
```

### Option C — Directory content + `content_dir`

```yaml
content_dir: ./content   # relative to the agent YAML file
```

Layout under that directory:

```
prompts/chat.system.md
prompts/chat.human.md
skills/brevity.md        # optional first line: # Title
```

See `examples/agents/prompt_demo/`.

Without a registered invoker **and** without `set_llm_provider`, `llm_chain` raises `ChainInvokerError`.

## Examples

Runnable samples (YAML agents + small Python runners) are indexed in
[`examples/README.md`](../examples/README.md).

## Control-plane state store

Optional durable catalog / sessions / audit (not a replacement for Git YAML):

```bash
export EDIM_STATE_STORE=postgres   # or cosmos | redis | memory
export EDIM_DATABASE_URL=postgresql://edim:edim@localhost:5432/edim
pip install 'edim-dde-ai[postgres]'
```

```python
from edim_dde_ai import (
    configure_state_store_from_env,
    sync_registered_agents_to_store,
    get_state_store,
)

configure_state_store_from_env()
# after register_from_yaml / bootstrap:
sync_registered_agents_to_store()
print(get_state_store().list_agents())
```

Full engineer guide lives in the domain docs hub:
`edim-dde-domain/docs/platform/state-store.md`.

## CLI


Tip: run `edim-dde-ai --help` (or `-V` / `--version`) for subcommands and examples.

```bash
edim-dde-ai --help
edim-dde-ai version
edim-dde-ai validate examples/agents/echo_agent.agent.yaml
edim-dde-ai register examples/agents/echo_agent.agent.yaml
edim-dde-ai register-dir examples/agents
edim-dde-ai list
edim-dde-ai run echo_agent --input '{"message":"hi"}'
```

## Build wheel

```bash
./scripts/build_wheel.sh
# or
python -m build --wheel
pip install dist/edim_dde_ai-*.whl
```
