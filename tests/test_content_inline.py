"""Inline prompts/skills + LLMProvider path for llm_chain."""

from __future__ import annotations

from pathlib import Path

from edim_dde_ai import create_agent, register_from_yaml, set_llm_provider

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "agents"


class FakeLLM:
    def invoke(self, messages, *, config=None):
        # Echo last human message content
        for role, content in reversed(messages):
            if role == "human":
                return f"ANSWER:{content}"
        return "ANSWER:"


def test_inline_prompts_and_skills_with_llm():
    set_llm_provider(FakeLLM())
    register_from_yaml(EXAMPLES / "prompt_inline.agent.yaml")
    agent = create_agent("prompt_inline")
    out = agent.invoke({"question": "What is 2+2?"})
    assert "ANSWER:" in out["llm_raw"]
    assert "What is 2+2?" in out["llm_raw"]
    # system should have had skills attached (attach_skills: true)
    # FakeLLM only returns human echo; verify skills via message build
    from edim_dde_ai.content.messages import build_chat_messages

    msgs = build_chat_messages(
        agent_id="prompt_inline",
        chain="chat",
        state={"question": "What is 2+2?"},
        attach_skills=True,
    )
    assert msgs[0][0] == "system"
    assert "Domain skills" in msgs[0][1]
    assert "Brevity" in msgs[0][1]
    assert msgs[1] == ("human", "Question: What is 2+2?")
