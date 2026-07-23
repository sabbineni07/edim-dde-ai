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
Builtin `field_truthy` requires `config.field` (agent-specific; no hardcoded default).

YAML::

    conditional_edges:
      - source: generate_recommendation   # use source, not from
        router: field_truthy
        config:
          field: include_explanation
          # true_label: yes
          # false_label: no
        mapping:
          yes: generate_explanation
          no: END

Python::

    from edim_dde_ai.registry.routers import register_router

    @register_router("risk_level")
    def risk_level_factory(config):
        def _route(state):
            return "high" if state.get("risk") == "high" else "low"
        return _route

## LLM chains (optional)

```python
from edim_dde_ai.registry.chains import register_chain_invoker

@register_chain_invoker("my_chain")
def my_chain(state, config):
    return {"text": "stub response"}
```

Without a registered invoker, `llm_chain` nodes raise a clear error.

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
