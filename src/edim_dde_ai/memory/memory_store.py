"""In-process conversation store for tests and isolated local runs."""

from __future__ import annotations

from edim_dde_ai.memory.models import ConversationMessage, ConversationSummary


class MemoryConversationStore:
    """Process-local conversation store; data is lost on restart."""

    def __init__(self) -> None:
        self._messages: dict[str, dict[str, ConversationMessage]] = {}
        self._summaries: dict[str, ConversationSummary] = {}

    @property
    def name(self) -> str:
        return "memory"

    def ping(self) -> bool:
        return True

    def append_message(self, message: ConversationMessage) -> None:
        self._messages.setdefault(message.conversation_id, {}).setdefault(
            message.message_id, message
        )

    def list_messages(
        self,
        conversation_id: str,
        *,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[ConversationMessage]:
        rows = list(self._messages.get(conversation_id, {}).values())
        if agent_id is not None:
            rows = [row for row in rows if row.agent_id == agent_id]
        rows.sort(key=lambda row: (row.created_at, row.message_id))
        if limit <= 0:
            return []
        return rows[-max(0, int(limit)) :]

    def get_summary(
        self, conversation_id: str, *, agent_id: str | None = None
    ) -> ConversationSummary | None:
        summary = self._summaries.get(conversation_id)
        if summary is None or (agent_id is not None and summary.agent_id != agent_id):
            return None
        return summary

    def upsert_summary(self, summary: ConversationSummary) -> None:
        self._summaries[summary.conversation_id] = summary

    def delete_conversation(self, conversation_id: str) -> bool:
        removed = self._messages.pop(conversation_id, None) is not None
        removed = self._summaries.pop(conversation_id, None) is not None or removed
        return removed
