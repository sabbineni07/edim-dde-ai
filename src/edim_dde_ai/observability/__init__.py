"""Pluggable observability backends (LangSmith, MLflow, none).

Business purpose:
  Enrich agent ``invoke`` kwargs with correlation tags/metadata and optionally
  enable an external tracing SaaS. Hosts pick a backend via env or setters.

Public API:
  - ``ObservabilityProvider`` — protocol
  - ``NoOpObservability`` / ``LangSmithObservability`` / ``MLflowObservability`` (lazy)
  - ``build_run_config`` / ``merge_base_config`` / ``merge_invoke_kwargs``
  - ``tracing_enabled``
  - ``set_observability_provider`` / ``get_observability_provider`` /
    ``clear_observability_provider`` / ``create_observability_provider`` /
    ``configure_observability_from_env`` / ``disable_langchain_tracing`` /
    ``resolve_observability_name``
"""

from edim_dde_ai.observability.base import build_run_config, merge_base_config
from edim_dde_ai.observability.langsmith import (
    LangSmithObservability,
    merge_invoke_kwargs,
    tracing_enabled,
)
from edim_dde_ai.observability.noop import NoOpObservability
from edim_dde_ai.observability.protocols import ObservabilityProvider
from edim_dde_ai.observability.registry import (
    clear_observability_provider,
    configure_observability_from_env,
    disable_langchain_tracing,
    create_observability_provider,
    get_observability_provider,
    resolve_observability_name,
    set_observability_provider,
)

__all__ = [
    "ObservabilityProvider",
    "NoOpObservability",
    "LangSmithObservability",
    "build_run_config",
    "merge_base_config",
    "merge_invoke_kwargs",
    "tracing_enabled",
    "set_observability_provider",
    "get_observability_provider",
    "clear_observability_provider",
    "create_observability_provider",
    "configure_observability_from_env",
    "disable_langchain_tracing",
    "resolve_observability_name",
]


def __getattr__(name: str):
    # Lazy export so importing observability does not require mlflow installed.
    if name == "MLflowObservability":
        from edim_dde_ai.observability.mlflow import MLflowObservability

        return MLflowObservability
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
