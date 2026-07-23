"""Plug-and-play LLMProvider demo (no Postgres, no custom invoker).

Invoker vs provider path for ``llm_chain``:
  1. If a chain invoker is registered for ``chain``, that wins.
  2. Otherwise prompts/skills are loaded and ``LLMProvider.invoke`` is called
     (set via ``set_llm_provider``).

This script uses path (2): FakeLLM + ``prompt_inline.agent.yaml``.
"""

from __future__ import annotations

from pathlib import Path

from edim_dde_ai import create_agent, register_from_yaml, set_llm_provider

YAML = Path(__file__).resolve().parent / "agents" / "prompt_inline.agent.yaml"


class FakeLLM:
    """Minimal LLMProvider: echo the last human message."""

    def invoke(self, messages, *, config=None):
        for role, content in reversed(messages):
            if role == "human":
                return f"echo:{content}"
        return "echo:"


def main() -> None:
    set_llm_provider(FakeLLM())
    register_from_yaml(YAML)
    agent = create_agent("prompt_inline")
    result = agent.invoke({"question": "What is EDIM?"})
    print(result)


if __name__ == "__main__":
    main()
