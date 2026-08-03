"""MLflow observability backend (optional extra)."""

from __future__ import annotations

import logging
import os
from typing import Any

from edim_dde_ai.observability.base import merge_base_config

logger = logging.getLogger(__name__)


class MLflowObservability:
    """Attach EDIM correlation tags via MLflow when the ``mlflow`` package is installed.

    Install: ``pip install 'edim-dde-ai[mlflow]'``

    Env (optional):
      - ``MLFLOW_TRACKING_URI`` — tracking server / Databricks tracking
      - ``EDIM_MLFLOW_EXPERIMENT`` — experiment name (default ``edim-dde``)
    """

    def __init__(self, *, experiment: str | None = None, autolog: bool = True) -> None:
        try:
            import mlflow  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "EDIM_OBSERVABILITY=mlflow requires the mlflow package. "
                "Install: pip install 'edim-dde-ai[mlflow]'"
            ) from exc

        import mlflow

        self._mlflow = mlflow
        exp = (
            experiment
            or os.environ.get("EDIM_MLFLOW_EXPERIMENT")
            or "edim-dde"
        ).strip()
        self.experiment = exp
        if autolog:
            try:
                if hasattr(mlflow, "langchain"):
                    mlflow.langchain.autolog(disable=False, silent=True)
            except Exception as exc:  # noqa: BLE001
                logger.debug("mlflow.langchain.autolog unavailable: %s", exc)

        try:
            mlflow.set_experiment(exp)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not set MLflow experiment %s: %s", exp, exc)

    @property
    def name(self) -> str:
        return "mlflow"

    def merge_invoke_kwargs(
        self,
        agent_id: str,
        kwargs: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        out = merge_base_config(
            agent_id,
            kwargs,
            request_id=request_id,
            extra_tags=["obs:mlflow"],
            extra_metadata={"observability": "mlflow"},
        )
        meta = (out.get("config") or {}).get("metadata") or {}
        tags = {
            "edim.agent_id": agent_id,
            "edim.env": str(meta.get("edim_env") or ""),
            "edim.request_id": str(meta.get("request_id") or ""),
            "edim.observability": "mlflow",
        }
        try:
            if self._mlflow.active_run() is not None:
                self._mlflow.set_tags(tags)
            else:
                out.setdefault("config", {})
                out["config"].setdefault("metadata", {})
                out["config"]["metadata"]["mlflow_tags"] = tags
        except Exception as exc:  # noqa: BLE001
            logger.debug("MLflow set_tags skipped: %s", exc)
        return out
