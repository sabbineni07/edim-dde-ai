"""Azure Cosmos DB conversation store."""

from __future__ import annotations

import os

from edim_dde_ai.memory.models import ConversationMessage, ConversationSummary
from edim_dde_ai.store.connection_env import resolve_cosmos_account


class CosmosConversationStore:
    """Conversation messages and summaries in dedicated Cosmos containers."""

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        key: str | None = None,
        database: str | None = None,
    ) -> None:
        try:
            from azure.cosmos import CosmosClient, PartitionKey
        except ImportError as exc:
            raise RuntimeError(
                "Conversation store requires azure-cosmos. "
                "Install: pip install 'edim-dde-ai[cosmos]'"
            ) from exc
        endpoint, key, database = resolve_cosmos_account(
            endpoint=endpoint, key=key, database=database
        )
        client = CosmosClient(endpoint, credential=key)
        db = client.create_database_if_not_exists(id=database)
        messages_name = os.environ.get(
            "EDIM_COSMOS_CONVERSATION_MESSAGES_CONTAINER",
            "conversation_messages",
        )
        summaries_name = os.environ.get(
            "EDIM_COSMOS_CONVERSATION_SUMMARIES_CONTAINER",
            "conversation_summaries",
        )
        self._messages = db.create_container_if_not_exists(
            id=messages_name, partition_key=PartitionKey(path="/conversation_id")
        )
        self._summaries = db.create_container_if_not_exists(
            id=summaries_name, partition_key=PartitionKey(path="/conversation_id")
        )

    @property
    def name(self) -> str:
        return "cosmos"

    def ping(self) -> bool:
        self._messages.read()
        return True

    def append_message(self, message: ConversationMessage) -> None:
        body = message.to_dict()
        body["id"] = message.message_id
        try:
            self._messages.create_item(body)
        except Exception as exc:  # Cosmos conflict is idempotent
            if "Conflict" not in str(exc):
                raise

    def list_messages(
        self,
        conversation_id: str,
        *,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[ConversationMessage]:
        if limit <= 0:
            return []
        query = (
            "SELECT TOP @limit * FROM c "
            "WHERE c.conversation_id = @conversation_id"
        )
        params = [
            {"name": "@limit", "value": int(limit)},
            {"name": "@conversation_id", "value": conversation_id},
        ]
        if agent_id is not None:
            query += " AND c.agent_id = @agent_id"
            params.append({"name": "@agent_id", "value": agent_id})
        query += " ORDER BY c.created_at DESC"
        rows = list(
            self._messages.query_items(
                query=query,
                parameters=params,
                partition_key=conversation_id,
            )
        )
        rows.reverse()
        return [ConversationMessage.from_dict(row) for row in rows]

    def get_summary(
        self, conversation_id: str, *, agent_id: str | None = None
    ) -> ConversationSummary | None:
        try:
            row = self._summaries.read_item(
                item=conversation_id, partition_key=conversation_id
            )
        except Exception:
            return None
        summary = ConversationSummary.from_dict(row)
        if agent_id is not None and summary.agent_id != agent_id:
            return None
        return summary

    def upsert_summary(self, summary: ConversationSummary) -> None:
        body = summary.to_dict()
        body["id"] = summary.conversation_id
        self._summaries.upsert_item(body)

    def delete_conversation(self, conversation_id: str) -> bool:
        rows = list(
            self._messages.query_items(
                query="SELECT c.id FROM c WHERE c.conversation_id = @conversation_id",
                parameters=[{"name": "@conversation_id", "value": conversation_id}],
                partition_key=conversation_id,
            )
        )
        for row in rows:
            self._messages.delete_item(
                item=row["id"], partition_key=conversation_id
            )
        try:
            self._summaries.delete_item(
                item=conversation_id, partition_key=conversation_id
            )
            summary_removed = True
        except Exception:
            summary_removed = False
        return bool(rows or summary_removed)
