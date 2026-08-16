"""LangSmith observability backend.

Business purpose:
  Attach LangSmith/LangChain-friendly tags and metadata on invoke, and optionally
  ensure ``LANGCHAIN_TRACING_V2`` is set so LangGraph emits traces.

Public API:
  - ``tracing_enabled()`` — detect if LangSmith tracing env is on
  - ``LangSmithObservability`` — provider implementation
  - ``build_run_config`` / ``merge_invoke_kwargs`` — back-compat helpers
"""

from __future__ import annotations

import os
from typing import Any

from edim_dde_ai.observability.base import merge_base_config


def tracing_enabled() -> bool:
    """Return True when LangSmith tracing should be considered active.

    Honors ``EDIM_LANGSMITH_ENABLED`` as an explicit off switch, otherwise
    checks ``LANGCHAIN_TRACING_V2``.

    Returns:
        Whether auto observability should pick LangSmith.
    """
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

    When ``ensure_env`` is true (default for ``configure_observability_from_env``),
    sets ``LANGCHAIN_TRACING_V2=true`` if unset so LangGraph emits traces (API key
    + project must still be configured).

    Args:
        ensure_env: If True, set ``LANGCHAIN_TRACING_V2`` when missing.
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
        """Merge LangSmith correlation tags into invoke kwargs.

        Args:
            agent_id: Agent being invoked.
            kwargs: Original ``invoke`` / ``ainvoke`` kwargs.
            request_id: Optional correlation id.

        Returns:
            Kwargs with merged ``config`` (tags/metadata).
        """
        return merge_base_config(
            agent_id,
            kwargs,
            request_id=request_id,
            extra_tags=["obs:langsmith"],
            extra_metadata={"observability": "langsmith"},
        )


# Back-compat helpers used by API routes / older imports
def build_run_config(**kwargs: Any) -> dict[str, Any]:
    """Delegate to ``observability.base.build_run_config``."""
    from edim_dde_ai.observability.base import build_run_config as _build

    return _build(**kwargs)


def merge_invoke_kwargs(
    agent_id: str,
    kwargs: dict[str, Any],
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Delegate to the process-wide provider (preferred) or LangSmith defaults.

    Args:
        agent_id: Agent being invoked.
        kwargs: Original invoke kwargs.
        request_id: Optional correlation id.

    Returns:
        Merged kwargs from the active observability provider.
    """
    from edim_dde_ai.observability.registry import get_observability_provider

    return get_observability_provider().merge_invoke_kwargs(
        agent_id, kwargs, request_id=request_id
    )
