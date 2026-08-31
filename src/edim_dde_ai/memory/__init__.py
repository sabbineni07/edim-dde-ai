"""Configurable conversation memory for EDIM agents.

Conversation memory is deliberately separate from control-plane sessions,
RecommendationStore product history, and LangGraph execution checkpoints.
"""

from edim_dde_ai.memory.manager import (
    ConversationMemoryManager,
    get_memory_policy,
    prepare_memory_state,
    record_memory_response,
)
from edim_dde_ai.memory.models import (
    ConversationMessage,
    ConversationSummary,
    MemoryPolicy,
)
from edim_dde_ai.memory.registry import (
    clear_conversation_store,
    configure_conversation_store_from_env,
    get_conversation_store,
    set_conversation_store,
)
from edim_dde_ai.memory.protocols import ConversationStore

__all__ = [
    "ConversationMemoryManager",
    "ConversationMessage",
    "ConversationSummary",
    "ConversationStore",
    "MemoryPolicy",
    "clear_conversation_store",
    "configure_conversation_store_from_env",
    "get_conversation_store",
    "get_memory_policy",
    "prepare_memory_state",
    "record_memory_response",
    "set_conversation_store",
]
