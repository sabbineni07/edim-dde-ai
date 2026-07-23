"""Custom ``register_chain_invoker`` wins over LLMProvider / prompts.

When a chain invoker is registered for the node's ``chain`` id, ``llm_chain``
calls it directly and does **not** need ``set_llm_provider`` (or YAML prompts).
A registered invoker always overrides the provider path.
"""

from __future__ import annotations

from edim_dde_ai import create_agent, register_from_dict
from edim_dde_ai.registry.chains import register_chain_invoker


@register_chain_invoker("stub")
def stub_invoker(state, config):
    return f"stub:{state.get('message', '')}"


AGENT = {
    "agent_id": "stub_invoker_demo",
    "display_name": "Stub invoker demo",
    "version": 1,
    "graph": {
        "entry": "call",
        "nodes": [
            {
                "id": "call",
                "type": "llm_chain",
                "chain": "stub",
                "output_key": "llm_raw",
            }
        ],
        "edges": [["call", "END"]],
    },
}


def main() -> None:
    # No set_llm_provider — invoker alone is enough.
    register_from_dict(AGENT, overwrite=True)
    agent = create_agent("stub_invoker_demo")
    result = agent.invoke({"message": "hello"})
    print(result)


if __name__ == "__main__":
    main()
