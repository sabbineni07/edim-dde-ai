"""Directory-backed prompts/skills via content_dir."""

from __future__ import annotations

from pathlib import Path

from edim_dde_ai import create_agent, register_from_yaml, set_llm_provider
from edim_dde_ai.content.messages import build_chat_messages

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "agents"


class FakeLLM:
    def invoke(self, messages, *, config=None):
        return messages[-1][1]


def test_directory_content_dir():
    set_llm_provider(FakeLLM())
    register_from_yaml(EXAMPLES / "prompt_demo" / "prompt_demo.agent.yaml")
    agent = create_agent("prompt_demo")
    out = agent.invoke({"question": "ping"})
    assert "ping" in out["llm_raw"]

    msgs = build_chat_messages(
        agent_id="prompt_demo",
        chain="chat",
        state={"question": "ping"},
        attach_skills=True,
    )
    assert "You are a demo assistant" in msgs[0][1]
    assert "Domain skills" in msgs[0][1]
    assert "Keep answers short" in msgs[0][1] or "short" in msgs[0][1].lower()
