# Examples

Runnable samples for engineers learning the YAML + Python hybrid model.
Install the package first (`pip install -e .` from the repo root), or run with
`PYTHONPATH=src`.

| Path | What it teaches | How to run |
|------|-----------------|------------|
| `agents/echo_agent.agent.yaml` | Basic graph: `set_value` + `echo_result` | `edim-dde-ai validate/register/run echo_agent --input '{"message":"hi"}'` |
| `agents/two_step_agent.agent.yaml` | `set_value` templates (`{field}`) | Same CLI pattern with `two_step_agent` |
| `agents/prompt_inline.agent.yaml` | Phase 3 inline prompts/skills + `llm_chain` | Needs LLMProvider or invoker; see `run_llm_provider_demo.py` |
| `agents/prompt_demo/` | Phase 3 `content_dir` markdown prompts/skills | Same; see tests or provider demo pattern |
| `agents/conditional_agent.agent.yaml` | `conditional_edges` + `field_truthy` (`config.field`) | `python examples/run_conditional_agent.py` |
| `agents/routes_sugar_agent.agent.yaml` | `graph.routes` sugar → same branching | `python examples/run_routes_sugar_agent.py` |
| `register_custom_nodes.py` | `@register_node` then load YAML | `python examples/register_custom_nodes.py` |
| `run_conditional_agent.py` | Branch on `include_details` True/False | `python examples/run_conditional_agent.py` |
| `run_routes_sugar_agent.py` | Same as conditional via `routes` sugar | `python examples/run_routes_sugar_agent.py` |
| `run_llm_provider_demo.py` | Plug-and-play `set_llm_provider` (no Postgres) | `python examples/run_llm_provider_demo.py` |
| `run_custom_invoker_demo.py` | `register_chain_invoker` overrides providers | `python examples/run_custom_invoker_demo.py` |

Also available: `register_from_dict` / `register_from_json` (see `docs/USAGE.md`) — not duplicated here beyond the invoker demo’s dict registration.
