"""No-op observability backend."""

from __future__ import annotations

from typing import Any

from edim_dde_ai.observability.base import merge_base_config


class NoOpObservability:
    """Still attaches ``request_id`` / env tags; does not enable an external SaaS."""

    @property
    def name(self) -> str:
        return "none"

    def merge_invoke_kwargs(
        self,
        agent_id: str,
        kwargs: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return merge_base_config(agent_id, kwargs, request_id=request_id)
