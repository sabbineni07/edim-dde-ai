"""Registered chain invoker still wins over LLMProvider / prompts."""

from __future__ import annotations

from pathlib import Path

from edim_dde_ai import create_agent, register_from_yaml, set_llm_provider
from edim_dde_ai.registry.chains import register_chain_invoker

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "agents"


class BoomLLM:
    def invoke(self, messages, *, config=None):
        raise AssertionError("LLMProvider must not be called when invoker is registered")


def test_invoker_wins_over_providers():
    set_llm_provider(BoomLLM())

    @register_chain_invoker("chat")
    def chat_invoker(state, config):
        return f"INVOKER:{state.get('question', '')}"

    register_from_yaml(EXAMPLES / "prompt_inline.agent.yaml")
    agent = create_agent("prompt_inline")
    out = agent.invoke({"question": "hi"})
    assert out["llm_raw"] == "INVOKER:hi"
