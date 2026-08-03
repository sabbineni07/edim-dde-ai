"""LangSmith observability backend."""

from __future__ import annotations

import os
from typing import Any

from edim_dde_ai.observability.base import merge_base_config


def tracing_enabled() -> bool:
    if os.environ.get("EDIM_LANGSMITH_ENABLED", "").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return False
    return os.environ.get("LANGCHAIN_TRACING_V2", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class LangSmithObservability:
    """Enrich invoke config for LangSmith / LangChain tracing.

    When ``ensure_env`` is true (default), sets ``LANGCHAIN_TRACING_V2=true`` if
    unset so LangGraph emits traces (API key + project must still be configured).
    """

    def __init__(self, *, ensure_env: bool = False) -> None:
        self.ensure_env = ensure_env
        if ensure_env and "LANGCHAIN_TRACING_V2" not in os.environ:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"

    @property
    def name(self) -> str:
        return "langsmith"

    def merge_invoke_kwargs(
        self,
        agent_id: str,
        kwargs: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return merge_base_config(
            agent_id,
            kwargs,
            request_id=request_id,
            extra_tags=["obs:langsmith"],
            extra_metadata={"observability": "langsmith"},
        )


# Back-compat helpers used by API routes / older imports
def build_run_config(**kwargs: Any) -> dict[str, Any]:
    from edim_dde_ai.observability.base import build_run_config as _build

    return _build(**kwargs)


def merge_invoke_kwargs(
    agent_id: str,
    kwargs: dict[str, Any],
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Delegate to the process-wide provider (preferred) or LangSmith defaults."""
    from edim_dde_ai.observability.registry import get_observability_provider

    return get_observability_provider().merge_invoke_kwargs(
        agent_id, kwargs, request_id=request_id
    )
