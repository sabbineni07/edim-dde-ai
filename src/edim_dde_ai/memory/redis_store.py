"""Redis conversation store for low-latency conversation memory."""

from __future__ import annotations

import json
import os

from edim_dde_ai.memory.models import ConversationMessage, ConversationSummary
from edim_dde_ai.store.connection_env import resolve_redis_settings


class RedisConversationStore:
    """Conversation messages in Redis lists and summaries in Redis hashes."""

    def __init__(
        self,
        url: str | None = None,
        *,
        prefix: str | None = None,
        name: str = "redis",
    ) -> None:
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError(
                "Conversation store requires redis. "
                "Install: pip install 'edim-dde-ai[redis]'"
            ) from exc
        resolved_url, resolved_prefix = resolve_redis_settings(url, prefix=prefix)
        self._r = redis.Redis.from_url(resolved_url, decode_responses=True)
        self._prefix = resolved_prefix
        self._name = name
        self._max_messages = max(
            20, int(os.environ.get("EDIM_CONVERSATION_MAX_MESSAGES", "200"))
        )

    @property
    def name(self) -> str:
        return self._name

    def _key(self, *parts: str) -> str:
        return ":".join((self._prefix, "conversation", *parts))

    def ping(self) -> bool:
        return bool(self._r.ping())

    def append_message(self, message: ConversationMessage) -> None:
        seen_key = self._key("seen", message.conversation_id)
        if self._r.hsetnx(seen_key, message.message_id, "1"):
            key = self._key("messages", message.conversation_id)
            self._r.rpush(key, json.dumps(message.to_dict()))
            self._r.ltrim(key, -self._max_messages, -1)

    def list_messages(
        self,
        conversation_id: str,
        *,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[ConversationMessage]:
        if limit <= 0:
            return []
        raw = self._r.lrange(self._key("messages", conversation_id), 0, -1)
        rows = [ConversationMessage.from_dict(json.loads(value)) for value in raw]
        if agent_id is not None:
            rows = [row for row in rows if row.agent_id == agent_id]
        return rows[-int(limit) :]

    def get_summary(
        self, conversation_id: str, *, agent_id: str | None = None
    ) -> ConversationSummary | None:
        raw = self._r.get(self._key("summary", conversation_id))
        if not raw:
            return None
        summary = ConversationSummary.from_dict(json.loads(raw))
        if agent_id is not None and summary.agent_id != agent_id:
            return None
        return summary

    def upsert_summary(self, summary: ConversationSummary) -> None:
        self._r.set(
            self._key("summary", summary.conversation_id),
            json.dumps(summary.to_dict()),
        )

    def delete_conversation(self, conversation_id: str) -> bool:
        keys = [
            self._key("messages", conversation_id),
            self._key("seen", conversation_id),
            self._key("summary", conversation_id),
        ]
        return bool(self._r.delete(*keys))
