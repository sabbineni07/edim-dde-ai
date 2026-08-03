"""Process-wide observability provider registry."""

from __future__ import annotations

import logging
import os
from typing import Any

from edim_dde_ai.observability.langsmith import LangSmithObservability, tracing_enabled
from edim_dde_ai.observability.noop import NoOpObservability
from edim_dde_ai.observability.protocols import ObservabilityProvider

logger = logging.getLogger(__name__)

_PROVIDER: ObservabilityProvider = NoOpObservability()


def set_observability_provider(provider: ObservabilityProvider) -> None:
    """Install the process-wide observability backend."""
    global _PROVIDER
    _PROVIDER = provider
    logger.info(
        "Observability provider set to %s",
        getattr(provider, "name", type(provider).__name__),
    )


def get_observability_provider() -> ObservabilityProvider:
    return _PROVIDER


def clear_observability_provider() -> None:
    """Reset to no-op (tests)."""
    global _PROVIDER
    _PROVIDER = NoOpObservability()


def resolve_observability_name(raw: str | None = None) -> str:
    """Normalize backend name from argument or ``EDIM_OBSERVABILITY`` env.

    Values: ``none`` | ``langsmith`` | ``mlflow`` | ``auto``.
    ``auto`` (or empty env): LangSmith if tracing env is on, else none.
    """
    if raw is None:
        value = os.environ.get("EDIM_OBSERVABILITY", "").strip().lower()
    else:
        value = raw.strip().lower()

    if not value or value == "auto":
        return "langsmith" if tracing_enabled() else "none"
    if value in {"none", "off", "noop", "disabled"}:
        return "none"
    if value in {"langsmith", "smith", "langchain"}:
        return "langsmith"
    if value in {"mlflow", "mlflow-tracking"}:
        return "mlflow"
    raise ValueError(
        f"Unknown EDIM_OBSERVABILITY={value!r}; expected none|langsmith|mlflow|auto"
    )


def create_observability_provider(
    name: str | None = None, **kwargs: Any
) -> ObservabilityProvider:
    """Factory for built-in backends (``name`` overrides env when provided)."""
    resolved = resolve_observability_name(name)
    if resolved == "none":
        return NoOpObservability()
    if resolved == "langsmith":
        return LangSmithObservability(**kwargs)
    if resolved == "mlflow":
        from edim_dde_ai.observability.mlflow import MLflowObservability

        return MLflowObservability(**kwargs)
    raise ValueError(f"Unknown observability backend {resolved!r}")


def configure_observability_from_env(**kwargs: Any) -> ObservabilityProvider:
    """Create provider from ``EDIM_OBSERVABILITY`` (or auto) and install it.

    For LangSmith, defaults ``ensure_env=True`` so ``LANGCHAIN_TRACING_V2`` is
    set when unset (API key + project still required for SaaS).
    """
    resolved = resolve_observability_name(None)
    if resolved == "langsmith":
        kwargs.setdefault("ensure_env", True)
    provider = create_observability_provider(resolved, **kwargs)
    set_observability_provider(provider)
    return provider
