"""Process-wide observability provider registry.

Business purpose:
  Hold the active ``ObservabilityProvider`` for ``MetadataAgent.invoke``.
  Configure from ``EDIM_OBSERVABILITY`` (none|langsmith|mlflow|auto) or install
  an explicit provider in app startup.

Public API:
  - ``set_observability_provider`` / ``get_observability_provider`` /
    ``clear_observability_provider``
  - ``resolve_observability_name`` / ``create_observability_provider`` /
    ``configure_observability_from_env``
"""

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
    """Install the process-wide observability backend.

    Args:
        provider: Backend implementing ``ObservabilityProvider``.
    """
    global _PROVIDER
    _PROVIDER = provider
    logger.info(
        "Observability provider set to %s",
        getattr(provider, "name", type(provider).__name__),
    )


def get_observability_provider() -> ObservabilityProvider:
    """Return the active provider (defaults to ``NoOpObservability``)."""
    return _PROVIDER


def clear_observability_provider() -> None:
    """Reset to no-op (tests)."""
    global _PROVIDER
    _PROVIDER = NoOpObservability()


def resolve_observability_name(raw: str | None = None) -> str:
    """Normalize backend name from argument or ``EDIM_OBSERVABILITY`` env.

    Values: ``none`` | ``langsmith`` | ``mlflow`` | ``auto``.
    ``auto`` (or empty env): LangSmith if tracing env is on, else none.

    Args:
        raw: Explicit name, or ``None`` to read env.

    Returns:
        Canonical backend id: ``none``, ``langsmith``, or ``mlflow``.

    Raises:
        ValueError: Unknown name.
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
    """Factory for built-in backends (``name`` overrides env when provided).

    Args:
        name: Optional backend name (see ``resolve_observability_name``).
        **kwargs: Forwarded to the backend constructor.

    Returns:
        A new provider instance (not installed until ``set_*`` /
        ``configure_observability_from_env``).
    """
    resolved = resolve_observability_name(name)
    if resolved == "none":
        return NoOpObservability()
    if resolved == "langsmith":
        return LangSmithObservability(**kwargs)
    if resolved == "mlflow":
        from edim_dde_ai.observability.mlflow import MLflowObservability

        return MLflowObservability(**kwargs)
    raise ValueError(f"Unknown observability backend {resolved!r}")


def disable_langchain_tracing() -> None:
    """Stop LangChain/LangSmith SDK from emitting traces when observability is off.

    Hosts often load ``LANGCHAIN_TRACING_V2=true`` from a shared ``.env``. When
    ``EDIM_OBSERVABILITY=none``, clear that flag so local Docker does not attempt
    unreachable LangSmith endpoints.
    """
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGCHAIN_TRACING"] = "false"


def configure_observability_from_env(**kwargs: Any) -> ObservabilityProvider:
    """Create provider from ``EDIM_OBSERVABILITY`` (or auto) and install it.

    For LangSmith, defaults ``ensure_env=True`` so ``LANGCHAIN_TRACING_V2`` is
    set when unset (API key + project still required for SaaS). When the
    resolved backend is ``none``, tracing env flags are forced off.

    Args:
        **kwargs: Forwarded to the backend constructor.

    Returns:
        The installed provider.
    """
    resolved = resolve_observability_name(None)
    if resolved == "none":
        disable_langchain_tracing()
    elif resolved == "langsmith":
        kwargs.setdefault("ensure_env", True)
    provider = create_observability_provider(resolved, **kwargs)
    set_observability_provider(provider)
    return provider
