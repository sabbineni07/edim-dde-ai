import pytest

from edim_dde_ai.errors import ConversationMemoryDisabledError, DefinitionError
from edim_dde_ai.registry.agents import create_agent
from edim_dde_ai.session import (
    MemoryPolicy,
    clear_checkpointer,
    get_session_policy,
    is_regenerate_intent,
    resolve_session_mode,
)
from edim_dde_ai.session.router import SESSION_MODE_CONVERSE, SESSION_MODE_INITIALIZE, SESSION_MODE_REGENERATE


EXAMPLES = __import__("pathlib").Path(__file__).resolve().parents[1] / "examples" / "agents"


@pytest.fixture(autouse=True)
def _fresh_checkpointer():
    clear_checkpointer()
    yield
    clear_checkpointer()


def test_memory_policy_defaults_to_disabled():
    policy = MemoryPolicy.from_raw(None)
    assert policy.strategy == "none"
    assert policy.k == 10
    assert policy.context_chars <= 16000
    assert MemoryPolicy.from_raw({}).strategy == "none"
    assert MemoryPolicy.from_raw({"strategy": "window"}).k == 10


def test_disabled_memory_rejects_conversation_id():
    from edim_dde_ai import register_from_yaml

    register_from_yaml(EXAMPLES / "echo_agent.agent.yaml")
    agent = create_agent("echo_agent")
    with pytest.raises(ConversationMemoryDisabledError):
        agent.invoke({"conversation_id": "disabled-1", "user_message": "follow up"})


def test_memory_policy_accepts_turns_alias_and_rejects_unsafe_values():
    assert MemoryPolicy.from_raw({"turns": 3}).k == 3
    with pytest.raises(DefinitionError, match="memory.k"):
        MemoryPolicy.from_raw({"k": 0})
    with pytest.raises(DefinitionError, match="memory.strategy"):
        MemoryPolicy.from_raw({"strategy": "unbounded"})


def test_session_policy_requires_session_block_when_memory_enabled():
    from edim_dde_ai.api.entrypoints import register_from_dict

    with pytest.raises(DefinitionError, match="session block is required"):
        register_from_dict(
            {
                "agent_id": "session_bad",
                "display_name": "Session Bad",
                "version": 1,
                "memory": {"strategy": "window"},
                "graph": {
                    "nodes": [{"id": "step", "type": "set_value", "field": "ok", "value": True}],
                    "edges": [["START", "step"], ["step", "END"]],
                },
            },
            overwrite=True,
        )


def test_regenerate_intent_detection():
    from edim_dde_ai import register_from_yaml

    register_from_yaml(EXAMPLES / "session_demo.agent.yaml")
    from edim_dde_ai.registry.agents import get_agent_definition

    policy = get_session_policy(get_agent_definition("session_demo"))
    assert is_regenerate_intent("What about something cheaper?", policy)
    assert not is_regenerate_intent("Why did you recommend that?", policy)


def test_resolve_session_mode_paths():
    from edim_dde_ai import register_from_yaml

    register_from_yaml(EXAMPLES / "session_demo.agent.yaml")
    from edim_dde_ai.registry.agents import get_agent_definition

    policy = get_session_policy(get_agent_definition("session_demo"))
    assert (
        resolve_session_mode({"user_message": "first"}, policy)
        == SESSION_MODE_INITIALIZE
    )
    assert (
        resolve_session_mode(
            {"session_initialized": True, "user_message": "why?"},
            policy,
        )
        == SESSION_MODE_CONVERSE
    )
    assert (
        resolve_session_mode(
            {"session_initialized": True, "user_message": "try cheaper"},
            policy,
        )
        == SESSION_MODE_REGENERATE
    )


def test_session_demo_initialize_then_converse_and_regenerate():
    from edim_dde_ai import register_from_yaml

    register_from_yaml(EXAMPLES / "session_demo.agent.yaml")
    agent = create_agent("session_demo")

    first = agent.invoke({"user_message": "recommend"})
    thread_id = first["thread_id"]
    assert first["prepared"] == "yes"
    assert first["recommendation"] == "rec-v1"
    assert first["session_mode"] == SESSION_MODE_INITIALIZE
    assert first.get("session_initialized") is True

    second = agent.invoke(
        {"thread_id": thread_id, "user_message": "why?"},
        config={"configurable": {"thread_id": thread_id}},
    )
    assert second["session_mode"] == SESSION_MODE_CONVERSE
    assert second["explanation"] == "because metrics"
    assert second["prepared"] == "yes"
    assert second["recommendation"] == "rec-v1"

    third = agent.invoke(
        {"thread_id": thread_id, "user_message": "try cheaper"},
        config={"configurable": {"thread_id": thread_id}},
    )
    assert third["session_mode"] == SESSION_MODE_REGENERATE
    assert third["recommendation"] == "rec-v2"
    assert len(third.get("messages") or []) >= 4


def test_session_disabled_agent_uses_flat_graph():
    from edim_dde_ai import register_from_yaml
    from edim_dde_ai.graph.session_builder import build_session_graph, session_enabled

    register_from_yaml(EXAMPLES / "echo_agent.agent.yaml")
    from edim_dde_ai.registry.agents import get_agent_definition

    definition = get_agent_definition("echo_agent")
    assert not session_enabled(definition)
    graph = build_session_graph(definition)
    assert graph is not None
