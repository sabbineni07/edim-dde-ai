"""Logical corpus registry (name → backend override + index pointers).

Business purpose
----------------
Agents refer to knowledge by **logical corpus** (e.g. ``spark-runbooks``),
not by Azure index names or FAISS directories. This module maps those names to
optional provider overrides and backend-specific paths so ``provider_for_corpus``
can wire the right client.

Public API
----------
* ``CorpusConfig`` — one corpus definition
* ``register_corpus`` / ``get_corpus`` / ``list_corpora`` / ``clear_corpora``
* ``load_corpora_yaml`` — load + register from a YAML file
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CorpusConfig:
    """One logical knowledge corpus.

    Attributes:
        name: Stable corpus id used in ``SearchRequest.corpus``.
        provider: Optional override of process ``EDIM_RETRIEVAL``
            (e.g. ``faiss``, ``azure_ai_search``).
        description: Human-readable summary for operators.
        index_path: FAISS directory override (local or Databricks Volume).
        azure_index: Azure AI Search index name for this corpus.
        databricks_index: Databricks Vector Search index name.
        extra: Unknown YAML keys preserved for host extensions.
    """

    name: str
    provider: str | None = None  # override EDIM_RETRIEVAL when set
    description: str = ""
    # FAISS
    index_path: str | None = None  # directory override
    # Azure
    azure_index: str | None = None
    # Databricks VS
    databricks_index: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


_CORPORA: dict[str, CorpusConfig] = {}


def clear_corpora() -> None:
    """Drop all registered corpus configs (tests / re-bootstrap)."""
    _CORPORA.clear()


def register_corpus(config: CorpusConfig) -> None:
    """Register or replace a corpus by ``config.name``.

    Args:
        config: Corpus definition to store in the process registry.
    """
    _CORPORA[config.name] = config


def get_corpus(name: str) -> CorpusConfig | None:
    """Look up a registered corpus.

    Args:
        name: Logical corpus id.

    Returns:
        ``CorpusConfig`` or ``None`` if unregistered.
    """
    return _CORPORA.get(name)


def list_corpora() -> list[str]:
    """Return sorted registered corpus names.

    Returns:
        Alphabetically sorted corpus ids.
    """
    return sorted(_CORPORA)


def load_corpora_yaml(path: str | Path) -> list[CorpusConfig]:
    """Load corpora from YAML and register them.

    Args:
        path: Filesystem path to a YAML document with a top-level ``corpora`` map.

    Returns:
        List of ``CorpusConfig`` instances that were registered (empty if
        missing/invalid ``corpora`` block).

    Example::

        corpora:
          spark-runbooks:
            description: Spark RCA runbooks / playbooks
            # provider: faiss   # optional override
            # index_path: /Volumes/.../edim_indexes
            azure_index: spark-runbooks

    ``index_path`` values of the form ``${ENV_KEY}`` are expanded from the
    environment (missing env → ``None``).
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    block = raw.get("corpora") if isinstance(raw, dict) else None
    if not isinstance(block, dict):
        return []
    loaded: list[CorpusConfig] = []
    for name, cfg in block.items():
        cfg = cfg or {}
        if not isinstance(cfg, dict):
            continue
        known = {
            "provider",
            "description",
            "index_path",
            "azure_index",
            "databricks_index",
        }
        extra = {k: v for k, v in cfg.items() if k not in known}
        item = CorpusConfig(
            name=str(name),
            provider=(str(cfg["provider"]) if cfg.get("provider") else None),
            description=str(cfg.get("description") or ""),
            index_path=(str(cfg["index_path"]) if cfg.get("index_path") else None),
            azure_index=(str(cfg["azure_index"]) if cfg.get("azure_index") else None),
            databricks_index=(
                str(cfg["databricks_index"]) if cfg.get("databricks_index") else None
            ),
            extra=extra,
        )
        # Env expansion for index_path (${VAR} → os.environ[VAR])
        if item.index_path and item.index_path.startswith("${") and item.index_path.endswith("}"):
            env_key = item.index_path[2:-1]
            item.index_path = os.environ.get(env_key) or None
        register_corpus(item)
        loaded.append(item)
    return loaded
