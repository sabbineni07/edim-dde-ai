# EDIM DDE AI

YAML-driven LangGraph agent framework packaged as an installable Python wheel.
Compose agent graphs in YAML; implement node types in Python via an allowlisted registry.
**API and UI are separate future projects** — this package is the runtime foundation only.

| | |
|---|---|
| Distribution | `edim-dde-ai` |
| Import | `edim_dde_ai` |
| CLI | `edim-dde-ai` |
| Python | `>=3.10` |
| Version | `0.1.0` |
| Project path | `/Users/sabbineni/projects/edim/edim-dde-ai` |

Further reading:

- [Stack engineer docs](../edim-dde-domain/docs/README.md) — quickstart, architecture, framework guides (temporary home under domain)
- [docs/DESIGN.md](docs/DESIGN.md) — architecture, hybrid model, security stance
- [docs/USAGE.md](docs/USAGE.md) — install, registration, custom nodes, CLI
- [docs/PUBLISHING.md](docs/PUBLISHING.md) — wheel build, private index / twine publish
- [docs/ROADMAP.md](docs/ROADMAP.md) — phases and status

---

## Overview

### Problem

Product AI agents (RCA, cluster tuning, and others) need a shared way to declare graphs, register node types safely, and run them on LangGraph — without baking API or UI into the runtime package, and without letting YAML pull in arbitrary Python.

### Hybrid model

| Layer | Responsibility |
|-------|----------------|
| **YAML** | Declares agent id, display metadata, graph topology (nodes, edges, optional conditional edges), and per-node config |
| **Python** | Implements node *types* registered by allowlisted `type` ids; optional chain invokers and routers |

YAML **composes**; Python **implements**. YAML never specifies arbitrary import paths — only registered `type` strings are resolved.

### What you get

- Installable package (`pip install -e .` or a built wheel) with a stable public API
- Builtin node types: `set_value`, `passthrough`, `echo_result`, `llm_chain`
- Loaders: single YAML file, multiple paths, a directory of `*.agent.yaml`, or dict/JSON (`register_from_dict` / `register_from_json`)
- In-process agent registry + `create_agent` → `MetadataAgent` (`invoke` / `ainvoke`)
- CLI for validate / register / list / run
- Extensibility via `@register_node`, routers, chain invokers, and prompt/skill/LLM providers
- Tests (`pytest`) and Makefile targets for install, demo, and wheel build

### Runtime flow

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
graph.builder   ── uses registry.nodes (+ routers / chains)
      │
      ▼
graph.runtime.MetadataAgent  (invoke / ainvoke)
```

### Package layout

```
edim_dde_ai/
  __init__.py          # public API re-exports
  errors.py            # shared exceptions
  version.py
  core/                # definition + YAML loading
  registry/            # agents, nodes, chains, routers
  graph/               # LangGraph builder + MetadataAgent runtime
  nodes/               # builtin node implementations
  api/                 # register_from_yaml / paths / directory / dict / JSON
  cli/                 # argparse CLI + path store
```

---

## Design (summary)

**Patterns (GoF):** Registry (keyed catalogs), Strategy (nodes / chains / routers), Builder (`GraphBuilder`), Factory Method (`AgentFactory`), Adapter (LangGraph state wraps), Template Method (`MetadataAgent` invoke/ainvoke), Facade (public API). Details: [docs/DESIGN.md](docs/DESIGN.md#design-patterns-gof).

**Compose, don't interpret.** Agent topology lives in YAML; behavior lives in Python behind an allowlist. That keeps product graphs declarative while preventing YAML from becoming a code-loading surface.

Conceptual product-style graph (illustrative — not a shipped agent):

```yaml
agent_id: example_rca
display_name: Example RCA
version: 1
graph:
  nodes:
    - id: collect
      type: set_value
      field: stage
      value: collected
    - id: analyze
      type: llm_chain
      chain: rca_summary
    - id: finish
      type: echo_result
      from_fields: [stage, text]
  edges:
    - [START, collect]
    - [collect, analyze]
    - [analyze, finish]
    - [finish, END]
```

Builtins such as `set_value`, `passthrough`, `echo_result`, and `llm_chain` ship with the package. Custom node types are registered in application code before YAML that references them is loaded.

Full design notes: [docs/DESIGN.md](docs/DESIGN.md).

---

## Setup

From the project root (`/Users/sabbineni/projects/edim/edim-dde-ai`):

### Option A — Make (recommended)

```bash
make install-dev
make test
```

### Option B — Editable install via pip

```bash
pip install -e ".[dev]"
# or runtime only:
pip install -e .
```

### Option C — Requirements files

```bash
pip install -r requirements-dev.txt
pip install -e .
# or runtime only:
pip install -r requirements.txt
```

### Option D — Wheel

```bash
make release
# or: ./scripts/build_wheel.sh
pip install dist/edim_dde_ai-*.whl
```

Publish to a private index (Artifactory / Azure Artifacts / etc.): see [docs/PUBLISHING.md](docs/PUBLISHING.md).
Requires `TWINE_REPOSITORY_URL` + credentials, then `make publish` / `./scripts/publish.sh`.

### Supporting files

| File | Role |
|------|------|
| `requirements.txt` | Runtime deps (aligned with `pyproject.toml`) |
| `requirements-dev.txt` | Runtime + `pytest` / `build` |
| `Makefile` | install, test, demo, validate, register, run, release, publish, clean |

Runtime dependencies: `langgraph>=0.2`, `langchain-core>=0.3`, `PyYAML>=6`.

---

## Usage

Engineer-oriented samples: [`examples/README.md`](examples/README.md).

### Quick demo CLI

```bash
make demo
# equivalent to: validate + register + run echo_agent
```

Or call the CLI directly:

```bash
edim-dde-ai version
edim-dde-ai validate examples/agents/echo_agent.agent.yaml
edim-dde-ai register examples/agents/echo_agent.agent.yaml
edim-dde-ai register-dir examples/agents
edim-dde-ai list
edim-dde-ai run echo_agent --input '{"message":"hi"}'
edim-dde-ai --help
```

Makefile shortcuts: `make validate`, `make register`, `make register-dir`, `make list`, `make run`, `make version`, `make cli-help`.

### Register and run from Python

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
print(result)
```

Dict / JSON registration (FastAPI-friendly):

```python
from edim_dde_ai import register_from_dict, register_from_json, create_agent

# FastAPI body is already a dict
register_from_dict(request_body, overwrite=True)
# or raw JSON string
register_from_json(raw_json, overwrite=True)

agent = create_agent("echo_agent")
```

### Example agent YAML

Shipped at `examples/agents/echo_agent.agent.yaml`:

```yaml
agent_id: echo_agent
display_name: Echo Agent
version: 1
entry:
  method: invoke
  sync: true
graph:
  nodes:
    - id: greet
      type: set_value
      field: greeting
      value: "hello"
    - id: finish
      type: echo_result
      from_fields: [greeting, message]
  edges:
    - [START, greet]
    - [greet, finish]
    - [finish, END]
```

### Custom node types

Register a node type **before** loading YAML that references it:

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

See `examples/register_custom_nodes.py` for a complete runnable sample.

### Optional LLM chains + content providers

`llm_chain` prefers a registered chain invoker. Otherwise it builds chat messages from
**PromptProvider** / **SkillProvider** (inline YAML, `content_dir` markdown, or a custom
provider) and calls **LLMProvider**. Set one with `set_llm_provider(...)`.

```python
from edim_dde_ai.registry.chains import register_chain_invoker
from edim_dde_ai import set_llm_provider

@register_chain_invoker("my_chain")
def my_chain(state, config):
    return {"text": "stub response"}

# Or: set_llm_provider(my_llm) + prompts in agent YAML / content_dir
```

See [docs/USAGE.md](docs/USAGE.md) (inline, directory, invoker) and [docs/DESIGN.md](docs/DESIGN.md).

### Public API surface

Re-exported from `edim_dde_ai` (`__all__`):

```python
__all__ = [
    "__version__",
    "register_node",
    "register_from_yaml",
    "register_from_directory",
    "register_from_paths",
    "register_from_dict",
    "register_from_dicts",
    "register_from_json",
    "register_agent",
    "create_agent",
    "list_agents",
    "get_agent_definition",
    "Skill",
    "DirectoryContentProvider",
    "set_prompt_provider",
    "set_skill_provider",
    "set_llm_provider",
    "get_prompt_provider",
    "get_skill_provider",
    "get_llm_provider",
    "register_skill",
    "clear_content_providers",
]
```

More detail: [docs/USAGE.md](docs/USAGE.md).

---

## Make cheatsheet

```text
make help            Show targets
make install         Editable install (runtime)
make install-dev     Editable install + pytest/build
make install-req     pip install -r requirements.txt
make install-req-dev requirements-dev.txt + editable install
make test            pytest -q
make validate        Validate echo example YAML
make register        Register echo example into CLI store
make register-dir    Register all *.agent.yaml under examples/agents
make list            List registered agents (CLI store)
make run             Run AGENT_ID with INPUT JSON (defaults: echo_agent)
make demo            validate + register + run
make build / wheel   Build wheel into dist/ (legacy; prefer release)
make release / dist  Clean + build wheel and sdist
make publish         Upload dist/ via twine (needs TWINE_*; see docs/PUBLISHING.md)
make clean-dist      Remove dist/ and build artifacts
make clean           clean-dist + caches
make version         Print package version via CLI
make cli-help        Show CLI help
```

Publishing details: [docs/PUBLISHING.md](docs/PUBLISHING.md).

Variables: `PYTHON`, `PIP`, `AGENT_ID` (default `echo_agent`), `INPUT` (default `{"message":"hi"}`).

---

## Status and roadmap

| Phase | Focus | Status |
|-------|--------|--------|
| **0** | Scaffold, packaging, docs, example YAMLs | Done |
| **1** | Core runtime (load, registry, graph, API, CLI, tests) | Done |
| **2** | Wheel publish + CLI polish | Done (local publish capability; remote index is ops) |
| **3** | Prompt / skill hooks | Done |
| **4** | Richer routers / YAML sugar | Done (`field_*`, `choice`, `graph.routes`) |
| **5** | Product adoption (RCA, cluster tuning, …) | Done in `edim-dde-ai-agents` |

API and UI remain **out of scope** for this repository — they are separate future projects that will consume this wheel.

Full checklist and execution log: [docs/ROADMAP.md](docs/ROADMAP.md).

---

## License

MIT — see [LICENSE](LICENSE).
