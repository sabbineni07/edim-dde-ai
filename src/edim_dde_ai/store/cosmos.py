"""Azure Cosmos DB state store (recommended for deployed environments)."""

from __future__ import annotations

import logging
import os
from typing import Any

from edim_dde_ai.store.connection_env import resolve_cosmos_account
from edim_dde_ai.store.models import AgentRecord, AuditEvent, SessionRecord

logger = logging.getLogger(__name__)


class CosmosStateStore:
    """Control-plane store backed by Azure Cosmos DB (NoSQL / SQL API).

    Install: ``pip install 'edim-dde-ai[cosmos]'``

    Env:
      - ``EDIM_COSMOS_ENDPOINT`` — account URI
      - ``EDIM_COSMOS_KEY`` — account key (prefer Key Vault in PROD)
      - ``EDIM_COSMOS_DATABASE`` — database id (default ``edim``)
      - ``EDIM_COSMOS_AGENTS_CONTAINER`` — default ``agents``
      - ``EDIM_COSMOS_SESSIONS_CONTAINER`` — default ``sessions``
      - ``EDIM_COSMOS_AUDIT_CONTAINER`` — default ``audit``
    """

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
                "EDIM_STATE_STORE=cosmos requires azure-cosmos. "
                "Install: pip install 'edim-dde-ai[cosmos]'"
            ) from exc

        endpoint, key, db_name = resolve_cosmos_account(
            endpoint=endpoint, key=key, database=database
        )

        self._PartitionKey = PartitionKey
        agents_c = os.environ.get("EDIM_COSMOS_AGENTS_CONTAINER", "agents").strip()
        sessions_c = os.environ.get("EDIM_COSMOS_SESSIONS_CONTAINER", "sessions").strip()
        audit_c = os.environ.get("EDIM_COSMOS_AUDIT_CONTAINER", "audit").strip()

        client = CosmosClient(endpoint, credential=key)
        db = client.create_database_if_not_exists(id=db_name)
        self._agents = db.create_container_if_not_exists(
            id=agents_c,
            partition_key=PartitionKey(path="/agent_id"),
        )
        self._sessions = db.create_container_if_not_exists(
            id=sessions_c,
            partition_key=PartitionKey(path="/session_id"),
        )
        self._audit = db.create_container_if_not_exists(
            id=audit_c,
            partition_key=PartitionKey(path="/event_id"),
        )

    @property
    def name(self) -> str:
        return "cosmos"

    def ping(self) -> bool:
        # Light read of agents container properties
        _ = self._agents.read()
        return True

    def upsert_agent(self, record: AgentRecord) -> None:
        body = record.to_dict()
        body["id"] = record.agent_id
        self._agents.upsert_item(body)

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        try:
            item = self._agents.read_item(item=agent_id, partition_key=agent_id)
        except Exception:  # noqa: BLE001 — CosmosResourceNotFoundError
            return None
        return AgentRecord.from_dict(_strip_cosmos(item))

    def list_agents(self) -> list[AgentRecord]:
        items = list(
            self._agents.query_items(
                query="SELECT * FROM c",
                enable_cross_partition_query=True,
            )
        )
        return sorted(
            (AgentRecord.from_dict(_strip_cosmos(i)) for i in items),
            key=lambda r: r.agent_id,
        )

    def delete_agent(self, agent_id: str) -> bool:
        try:
            self._agents.delete_item(item=agent_id, partition_key=agent_id)
            return True
        except Exception:  # noqa: BLE001
            return False

    def upsert_session(self, record: SessionRecord) -> None:
        body = record.to_dict()
        body["id"] = record.session_id
        self._sessions.upsert_item(body)

    def get_session(self, session_id: str) -> SessionRecord | None:
        try:
            item = self._sessions.read_item(item=session_id, partition_key=session_id)
        except Exception:  # noqa: BLE001
            return None
        return SessionRecord.from_dict(_strip_cosmos(item))

    def delete_session(self, session_id: str) -> bool:
        try:
            self._sessions.delete_item(item=session_id, partition_key=session_id)
            return True
        except Exception:  # noqa: BLE001
            return False

    def append_audit(self, event: AuditEvent) -> None:
        body = event.to_dict()
        body["id"] = event.event_id
        self._audit.upsert_item(body)

    def list_audit(
        self, *, agent_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        if agent_id is None:
            query = "SELECT * FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit"
            params: list[dict[str, Any]] = [{"name": "@limit", "value": limit}]
        else:
            query = (
                "SELECT * FROM c WHERE c.agent_id = @agent_id "
                "ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit"
            )
            params = [
                {"name": "@agent_id", "value": agent_id},
                {"name": "@limit", "value": limit},
            ]
        items = list(
            self._audit.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )
        return [AuditEvent.from_dict(_strip_cosmos(i)) for i in items]


def _strip_cosmos(item: dict[str, Any]) -> dict[str, Any]:
    skip = {"_rid", "_self", "_etag", "_attachments", "_ts"}
    return {k: v for k, v in item.items() if k not in skip and k != "id"}
