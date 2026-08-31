"""Backend-neutral conversation-memory storage protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from edim_dde_ai.memory.models import ConversationMessage, ConversationSummary


@runtime_checkable
class ConversationStore(Protocol):
    """Durable conversation messages and summaries.

    This is intentionally separate from ``StateStore`` (control sessions and
    audit) and ``RecommendationStore`` (RCA/tuning product history).
    """

    @property
    def name(self) -> str:
        """Backend identifier."""

    def ping(self) -> bool:
        """Return whether the backend is reachable."""

    def append_message(self, message: ConversationMessage) -> None:
        """Append one message; repeated message ids must be idempotent."""

    def list_messages(
        self,
        conversation_id: str,
        *,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[ConversationMessage]:
        """Return messages in chronological order."""

    def get_summary(
        self, conversation_id: str, *, agent_id: str | None = None
    ) -> ConversationSummary | None:
        """Return the latest summary for a conversation."""

    def upsert_summary(self, summary: ConversationSummary) -> None:
        """Replace the latest summary for a conversation."""

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation messages and summary where supported."""
