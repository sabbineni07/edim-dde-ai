"""Observability provider protocol (pluggable backends).

Business purpose:
  Duck-typed contract for enriching agent ``invoke`` kwargs (tags, tracing,
  runs). Hosts select via ``set_observability_provider`` or
  ``configure_observability_from_env``.

Public API:
  - ``ObservabilityProvider`` — runtime-checkable Protocol

Implementations: ``NoOpObservability``, ``LangSmithObservability``,
``MLflowObservability``.
"""

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
        """Return invoke kwargs with backend-specific ``config`` / side effects.

        Args:
            agent_id: Agent being invoked.
            kwargs: Original ``invoke`` / ``ainvoke`` keyword args.
            request_id: Optional correlation id.

        Returns:
            Possibly-copied kwargs safe to pass to LangGraph.
        """
        ...
