"""Azure Cosmos DB state store (recommended for deployed environments).

Business purpose
----------------
Durable control-plane store for agent catalog, sessions, and audit using
Cosmos NoSQL (SQL API). Containers are created on connect if missing.

Public API
----------
* ``CosmosStateStore`` — ``StateStore`` over agents / sessions / audit containers

Install: ``pip install 'edim-dde-ai[cosmos]'``

Env
---
* ``EDIM_COSMOS_ENDPOINT`` — account URI
* ``EDIM_COSMOS_KEY`` — account key (prefer Key Vault in PROD)
* ``EDIM_COSMOS_DATABASE`` — database id (default ``edim``)
* ``EDIM_COSMOS_AGENTS_CONTAINER`` — default ``agents``
* ``EDIM_COSMOS_SESSIONS_CONTAINER`` — default ``sessions``
* ``EDIM_COSMOS_AUDIT_CONTAINER`` — default ``audit``
"""

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
        """Create client, database, and containers if they do not exist.

        Partition keys: ``/agent_id``, ``/session_id``, ``/event_id``.

        Args:
            endpoint: Account URI; defaults via ``resolve_cosmos_account``.
            key: Account key.
            database: Database id.

        Raises:
            RuntimeError: Missing ``azure-cosmos`` or required env.
        """
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
        agent_pk = PartitionKey(path="/agent_id")
        session_pk = PartitionKey(path="/session_id")
        audit_pk = PartitionKey(path="/event_id")
        self._agents = db.create_container_if_not_exists(
            id=agents_c, partition_key=agent_pk
        )
        self._sessions = db.create_container_if_not_exists(
            id=sessions_c, partition_key=session_pk
        )
        self._audit = db.create_container_if_not_exists(
            id=audit_c, partition_key=audit_pk
        )

    @property
    def name(self) -> str:
        """Backend id for health / logs (``cosmos``)."""
        return "cosmos"

    def ping(self) -> bool:
        """Read agents container properties.

        Returns:
            ``True`` on success.
        """
        # Light read of agents container properties
        _ = self._agents.read()
        return True

    def upsert_agent(self, record: AgentRecord) -> None:
        """Upsert an agent item (``id`` = ``agent_id``).

        Args:
            record: Agent catalog row.
        """
        body = record.to_dict()
        body["id"] = record.agent_id
        self._agents.upsert_item(body)

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        """Point-read an agent by partition key.

        Args:
            agent_id: Agent key.

        Returns:
            ``AgentRecord`` or ``None`` if not found.
        """
        try:
            item = self._agents.read_item(item=agent_id, partition_key=agent_id)
        except Exception:  # noqa: BLE001 — CosmosResourceNotFoundError
            return None
        return AgentRecord.from_dict(_strip_cosmos(item))

    def list_agents(self) -> list[AgentRecord]:
        """Cross-partition ``SELECT *`` of agents, sorted by id.

        Returns:
            Sorted agent rows.
        """
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
        """Delete an agent item.

        Args:
            agent_id: Agent key.

        Returns:
            ``True`` if deleted; ``False`` if missing / error.
        """
        try:
            self._agents.delete_item(item=agent_id, partition_key=agent_id)
            return True
        except Exception:  # noqa: BLE001
            return False

    def upsert_session(self, record: SessionRecord) -> None:
        """Upsert a session item (``id`` = ``session_id``).

        Args:
            record: Session document.
        """
        body = record.to_dict()
        body["id"] = record.session_id
        self._sessions.upsert_item(body)

    def get_session(self, session_id: str) -> SessionRecord | None:
        """Point-read a session by partition key.

        Args:
            session_id: Session key.

        Returns:
            ``SessionRecord`` or ``None`` if not found.
        """
        try:
            item = self._sessions.read_item(item=session_id, partition_key=session_id)
        except Exception:  # noqa: BLE001
            return None
        return SessionRecord.from_dict(_strip_cosmos(item))

    def delete_session(self, session_id: str) -> bool:
        """Delete a session item.

        Args:
            session_id: Session key.

        Returns:
            ``True`` if deleted; ``False`` if missing / error.
        """
        try:
            self._sessions.delete_item(item=session_id, partition_key=session_id)
            return True
        except Exception:  # noqa: BLE001
            return False

    def append_audit(self, event: AuditEvent) -> None:
        """Upsert an audit item (``id`` = ``event_id``).

        Args:
            event: Audit event.
        """
        body = event.to_dict()
        body["id"] = event.event_id
        self._audit.upsert_item(body)

    def list_audit(
        self, *, agent_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        """Query recent audit items ordered by ``created_at`` descending.

        Args:
            agent_id: Optional filter.
            limit: Maximum rows (SQL OFFSET/LIMIT).

        Returns:
            Up to ``limit`` audit events.
        """
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
    """Drop Cosmos system fields and document ``id`` before model hydration."""
    skip = {"_rid", "_self", "_etag", "_attachments", "_ts"}
    return {k: v for k, v in item.items() if k not in skip and k != "id"}
