import pytest

from edim_dde_ai.content.messages import build_chat_messages
from edim_dde_ai.memory.manager import ConversationMemoryManager
from edim_dde_ai.memory.memory_store import MemoryConversationStore
from edim_dde_ai.memory.models import ConversationMessage, MemoryPolicy
from edim_dde_ai.errors import (
    ConversationMemoryDisabledError,
    DefinitionError,
)


def test_memory_policy_defaults_to_disabled():
    policy = MemoryPolicy.from_raw(None)
    assert policy.strategy == "none"
    assert policy.k == 10
    assert policy.context_chars <= 16000
    assert MemoryPolicy.from_raw({}).strategy == "none"
    assert MemoryPolicy.from_raw({"strategy": "window"}).k == 10


def test_disabled_memory_does_not_read_or_write_conversation_store():
    store = MemoryConversationStore()
    manager = ConversationMemoryManager(
        MemoryPolicy(strategy="none"), agent_id="demo", store=store
    )
    state = {
        "request_id": "r-1",
        "user_message": "standalone question",
    }

    assert manager.prepare(state) == state
    manager.record_response(state, {"llm_raw": "standalone answer"})
    assert store.list_messages("disabled-1", agent_id="demo") == []


def test_disabled_memory_rejects_conversation_id():
    manager = ConversationMemoryManager(
        MemoryPolicy(strategy="none"),
        agent_id="demo",
        store=MemoryConversationStore(),
    )

    with pytest.raises(ConversationMemoryDisabledError, match="memory is disabled"):
        manager.prepare(
            {
                "conversation_id": "disabled-1",
                "user_message": "follow up without context",
            }
        )


def test_memory_policy_accepts_turns_alias_and_rejects_unsafe_values():
    assert MemoryPolicy.from_raw({"turns": 3}).k == 3
    with pytest.raises(DefinitionError, match="memory.k"):
        MemoryPolicy.from_raw({"k": 0})
    with pytest.raises(DefinitionError, match="memory.strategy"):
        MemoryPolicy.from_raw({"strategy": "unbounded"})


def test_window_memory_isolated_and_bounded():
    store = MemoryConversationStore()
    manager = ConversationMemoryManager(
        MemoryPolicy(strategy="window", k=1, max_chars=1000),
        agent_id="demo",
        store=store,
    )
    first = {
        "conversation_id": "c-1",
        "request_id": "r-1",
        "user_message": "first question",
    }
    prepared = manager.prepare(first)
    assert prepared["conversation_context"] == "(no prior conversation messages)"
    manager.record_response(first, {"llm_raw": "first answer"})

    second = {
        "conversation_id": "c-1",
        "request_id": "r-2",
        "user_message": "follow up",
    }
    prepared = manager.prepare(second)
    assert "[USER]\nfirst question" in prepared["conversation_context"]
    assert "[ASSISTANT]\nfirst answer" in prepared["conversation_context"]
    assert "follow up" not in prepared["conversation_context"]

    other = {
        "conversation_id": "c-2",
        "request_id": "r-3",
        "user_message": "unrelated",
    }
    assert "first answer" not in manager.prepare(other)["conversation_context"]


def test_memory_context_and_current_question_are_separate_prompt_messages():
    from edim_dde_ai.content import clear_prompt_provider, set_prompt_provider
    from edim_dde_ai.content.inline import InlineContentStore

    prompts = InlineContentStore()
    prompts.set_prompt("demo", "chat", "system", "You are a test agent.")
    prompts.set_prompt("demo", "chat", "human", "Answer the request.")
    set_prompt_provider(prompts)
    try:
        messages = build_chat_messages(
            agent_id="demo",
            chain="chat",
            state={
                "conversation_context": "[ASSISTANT]\nold answer",
                "user_message": "please refine it",
            },
        )
    finally:
        clear_prompt_provider()
    assert messages[-2][0] == "human"
    assert "old answer" in messages[-2][1]
    assert messages[-1] == (
        "human",
        "=== CURRENT ENGINEER QUESTION ===\nplease refine it",
    )


def test_message_roles_and_store_idempotency():
    store = MemoryConversationStore()
    message = ConversationMessage(
        message_id="m-1",
        conversation_id="c-1",
        agent_id="demo",
        role="user",
        content="hello",
    )
    store.append_message(message)
    store.append_message(message)
    assert len(store.list_messages("c-1")) == 1
    with pytest.raises(ValueError, match="Unsupported"):
        ConversationMessage(
            message_id="m-2",
            conversation_id="c-1",
            agent_id="demo",
            role="unknown",
            content="bad",
        )


def test_summary_buffer_maintains_persisted_summary():
    from edim_dde_ai.content.registry import clear_llm_provider, set_llm_provider

    class SummaryLLM:
        def invoke(self, messages, *, config=None):
            del config
            return "older goals and decisions"

    store = MemoryConversationStore()
    manager = ConversationMemoryManager(
        MemoryPolicy(strategy="summary_buffer", k=1, max_chars=4000),
        agent_id="demo",
        store=store,
    )
    set_llm_provider(SummaryLLM())
    try:
        for index in range(2):
            state = {
                "conversation_id": "summary-1",
                "request_id": f"r-{index}",
                "user_message": f"question {index}",
            }
            manager.prepare(state)
            manager.record_response(state, {"llm_raw": f"answer {index}"})
    finally:
        clear_llm_provider()
    summary = store.get_summary("summary-1", agent_id="demo")
    assert summary is not None
    assert summary.content == "older goals and decisions"


def test_vector_memory_uses_retrieval_and_conversation_filter():
    from edim_dde_ai.retrieval import (
        MemoryRetrieval,
        clear_retrieval_provider,
        set_retrieval_provider,
    )

    store = MemoryConversationStore()
    set_retrieval_provider(MemoryRetrieval())
    manager = ConversationMemoryManager(
        MemoryPolicy(strategy="vector", corpus="test-memory", top_k=5),
        agent_id="demo",
        store=store,
    )
    try:
        first = {
            "conversation_id": "vector-1",
            "request_id": "v-1",
            "user_message": "executor memory pressure",
        }
        manager.prepare(first)
        manager.record_response(first, {"llm_raw": "increase executor memory"})
        follow_up = {
            "conversation_id": "vector-1",
            "request_id": "v-2",
            "user_message": "executor memory",
        }
        context = manager.prepare(follow_up)["conversation_context"]
        assert "increase executor memory" in context
    finally:
        clear_retrieval_provider()
