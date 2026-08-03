"""Observability provider protocol (pluggable backends)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ObservabilityProvider(Protocol):
    """Backend that enriches agent ``invoke`` kwargs (tags, tracing, runs).

    Implementations: ``NoOpObservability``, ``LangSmithObservability``,
    ``MLflowObservability``. Hosts select via ``set_observability_provider`` or
    ``configure_observability_from_env``.
    """

    @property
    def name(self) -> str:
        """Stable id: ``none`` | ``langsmith`` | ``mlflow`` | custom."""

    def merge_invoke_kwargs(
        self,
        agent_id: str,
        kwargs: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Return invoke kwargs with backend-specific ``config`` / side effects."""
