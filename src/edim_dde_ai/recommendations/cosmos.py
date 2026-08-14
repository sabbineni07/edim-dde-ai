"""Azure Cosmos DB recommendation history store."""

from __future__ import annotations

import logging
import os
from typing import Any

from edim_dde_ai.recommendations.models import RecommendationRecord
from edim_dde_ai.recommendations.support import RecommendationStatusMixin
from edim_dde_ai.store.connection_env import resolve_cosmos_account

logger = logging.getLogger(__name__)


class CosmosRecommendationStore(RecommendationStatusMixin):
    """Recommendation history in Cosmos (shares account env with StateStore).

    Install: ``pip install 'edim-dde-ai[cosmos]'``

    Env: ``EDIM_COSMOS_ENDPOINT``, ``EDIM_COSMOS_KEY``, ``EDIM_COSMOS_DATABASE``,
    optional ``EDIM_COSMOS_RECOMMENDATIONS_CONTAINER`` (default ``recommendations``).
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
            from azure.cosmos.exceptions import CosmosResourceNotFoundError
        except ImportError as exc:
            raise RuntimeError(
                "EDIM_RECOMMENDATION_STORE=cosmos requires azure-cosmos. "
                "Install: pip install 'edim-dde-ai[cosmos]'"
            ) from exc

        endpoint, key, db_name = resolve_cosmos_account(
            endpoint=endpoint, key=key, database=database
        )
        container = os.environ.get(
            "EDIM_COSMOS_RECOMMENDATIONS_CONTAINER", "recommendations"
        ).strip()

        client = CosmosClient(endpoint, credential=key)
        db = client.create_database_if_not_exists(id=db_name)
        self._container = db.create_container_if_not_exists(
            id=container,
            partition_key=PartitionKey(path="/recommendation_id"),
        )
        self._not_found = CosmosResourceNotFoundError

    @property
    def name(self) -> str:
        return "cosmos"

    def ping(self) -> bool:
        _ = self._container.read()
        return True

    def save(self, record: RecommendationRecord) -> RecommendationRecord:
        body = record.to_dict()
        body["id"] = record.recommendation_id
        self._container.upsert_item(body)
        return record

    def get(self, recommendation_id: str) -> RecommendationRecord | None:
        try:
            item = self._container.read_item(
                item=recommendation_id, partition_key=recommendation_id
            )
        except self._not_found:
            return None
        return RecommendationRecord.from_dict(_strip_cosmos(item))

    def list(
        self,
        *,
        job_id: str | None = None,
        cluster_id: str | None = None,
        status: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[RecommendationRecord]:
        clauses = ["1=1"]
        params: list[dict[str, Any]] = []
        if job_id is not None:
            clauses.append("c.job_id = @job_id")
            params.append({"name": "@job_id", "value": job_id})
        if cluster_id is not None:
            clauses.append("c.cluster_id = @cluster_id")
            params.append({"name": "@cluster_id", "value": cluster_id})
        if status is not None:
            clauses.append("c.status = @status")
            params.append({"name": "@status", "value": status})
        if agent_id is not None:
            clauses.append("c.agent_id = @agent_id")
            params.append({"name": "@agent_id", "value": agent_id})
        query = (
            "SELECT * FROM c WHERE "
            + " AND ".join(clauses)
            + " ORDER BY c.created_at DESC"
        )
        items = list(
            self._container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
                max_item_count=max(1, limit),
            )
        )
        return [RecommendationRecord.from_dict(_strip_cosmos(i)) for i in items[:limit]]


def _strip_cosmos(item: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v
        for k, v in item.items()
        if not k.startswith("_") and k not in {"id"}
    }
