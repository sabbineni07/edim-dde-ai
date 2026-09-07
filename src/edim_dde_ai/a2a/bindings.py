"""Agent Directory binding models + local/overlay/runtime sources.

Business purpose
----------------
Logical ``agent_id`` → how to call (local in-process vs remote endpoint).
Used by API directory routes and by ``invoke_agent`` resolve (ADR-001).

Sources (merged, later wins on key conflicts per field via overlay merge):
1. In-process registry → ``mode=local``, ``transport=in_process``
2. ``EDIM_AGENT_DIRECTORY_JSON`` env overlay
3. Runtime register/heartbeat store (Phase 5)
4. Optional ``EDIM_DIRECTORY_URL`` fetch (Phase 5; best-effort)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

ENV_DIRECTORY_JSON = "EDIM_AGENT_DIRECTORY_JSON"
ENV_DIRECTORY_URL = "EDIM_DIRECTORY_URL"

_RUNTIME_LOCK = threading.Lock()
_RUNTIME_BINDINGS: dict[str, dict[str, Any]] = {}


class AgentBinding(TypedDict, total=False):
    """Stable directory binding shape (ADR-001 §5)."""

    agent_id: str
    env: str
    mode: str  # local | remote
    transport: str  # in_process | http | mcp | …
    endpoint: str | None
    invoke_path: str | None
    version: str | None
    healthy: bool
    metadata: dict[str, Any]


def resolve_env_label() -> str:
    """Return the env label stamped on bindings (``EDIM_ENV`` or ``dev``)."""
    return (os.environ.get("EDIM_ENV") or "dev").strip() or "dev"


def clear_runtime_bindings() -> None:
    """Clear heartbeat/register overlay (tests)."""
    with _RUNTIME_LOCK:
        _RUNTIME_BINDINGS.clear()


def register_runtime_binding(binding: dict[str, Any]) -> dict[str, Any]:
    """Upsert a binding from heartbeat/register (Phase 5).

    Args:
        binding: Partial or full binding; ``agent_id`` required.

    Returns:
        Normalized stored binding.

    Raises:
        ValueError: Missing ``agent_id``.
    """
    agent_id = str(binding.get("agent_id") or "").strip()
    if not agent_id:
        raise ValueError("register requires non-empty agent_id")
    env = str(binding.get("env") or resolve_env_label()).strip() or resolve_env_label()
    stored: dict[str, Any] = {
        "agent_id": agent_id,
        "env": env,
        "mode": str(binding.get("mode") or "remote"),
        "transport": str(binding.get("transport") or "http"),
        "endpoint": binding.get("endpoint"),
        "invoke_path": binding.get("invoke_path"),
        "version": binding.get("version"),
        "healthy": bool(binding.get("healthy", True)),
        "metadata": dict(binding.get("metadata") or {}),
    }
    with _RUNTIME_LOCK:
        _RUNTIME_BINDINGS[agent_id] = stored
    return dict(stored)


def _runtime_overlay() -> dict[str, dict[str, Any]]:
    with _RUNTIME_LOCK:
        return {k: dict(v) for k, v in _RUNTIME_BINDINGS.items()}


def _json_overlay() -> dict[str, dict[str, Any]]:
    raw = (os.environ.get(ENV_DIRECTORY_JSON) or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("EDIM_AGENT_DIRECTORY_JSON is not valid JSON; ignoring")
        return {}
    if not isinstance(data, dict):
        logger.warning("EDIM_AGENT_DIRECTORY_JSON must be a JSON object; ignoring")
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, value in data.items():
        if isinstance(key, str) and isinstance(value, dict):
            out[key] = value
    return out


def _fetch_remote_directory_overlay() -> dict[str, dict[str, Any]]:
    """Best-effort GET ``{EDIM_DIRECTORY_URL}/api/v1/directory/agents``."""
    base = (os.environ.get(ENV_DIRECTORY_URL) or "").strip().rstrip("/")
    if not base:
        return {}
    url = f"{base}/api/v1/directory/agents"
    try:
        req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:  # noqa: S310 — ops URL
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        logger.warning("EDIM_DIRECTORY_URL fetch failed (%s): %s", url, exc)
        return {}
    agents = body.get("agents") if isinstance(body, dict) else None
    if not isinstance(agents, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in agents:
        if isinstance(item, dict) and isinstance(item.get("agent_id"), str):
            out[item["agent_id"]] = item
    return out


def _local_binding(agent_id: str, *, env: str) -> dict[str, Any]:
    from edim_dde_ai.errors import AgentRegistryError
    from edim_dde_ai.registry.agents import get_agent_definition

    meta: dict[str, Any] = {}
    version: str | None = None
    try:
        definition = get_agent_definition(agent_id)
        raw_meta = (definition.raw or {}).get("metadata") or {}
        if isinstance(raw_meta, dict):
            for key in ("owner", "risk_tier", "lifecycle", "hitl_required"):
                if key in raw_meta:
                    meta[key] = raw_meta[key]
        version = str(definition.version) if definition.version is not None else None
    except AgentRegistryError:
        pass
    return {
        "agent_id": agent_id,
        "env": env,
        "mode": "local",
        "transport": "in_process",
        "endpoint": None,
        "invoke_path": None,
        "version": version,
        "healthy": True,
        "metadata": meta,
    }


def list_bindings(*, env: str | None = None) -> list[dict[str, Any]]:
    """Return merged directory bindings for this process / env."""
    from edim_dde_ai.registry.agents import list_agents

    env_name = env or resolve_env_label()
    overlay: dict[str, dict[str, Any]] = {}
    overlay.update(_fetch_remote_directory_overlay())
    overlay.update(_json_overlay())
    overlay.update(_runtime_overlay())

    bindings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for agent_id in list_agents():
        seen.add(agent_id)
        base = _local_binding(agent_id, env=env_name)
        extra = overlay.get(agent_id) or {}
        merged = {**base, **extra, "agent_id": agent_id, "env": env_name}
        bindings.append(merged)
    for agent_id, extra in overlay.items():
        if agent_id in seen:
            continue
        bindings.append(
            {
                "agent_id": agent_id,
                "env": env_name,
                "mode": str(extra.get("mode") or "remote"),
                "transport": str(extra.get("transport") or "http"),
                "endpoint": extra.get("endpoint"),
                "invoke_path": extra.get("invoke_path"),
                "version": extra.get("version"),
                "healthy": bool(extra.get("healthy", True)),
                "metadata": dict(extra.get("metadata") or {}),
            }
        )
    bindings.sort(key=lambda b: str(b.get("agent_id") or ""))
    return bindings


def get_binding(agent_id: str, *, env: str | None = None) -> dict[str, Any] | None:
    """Return one binding or ``None`` if unknown."""
    aid = (agent_id or "").strip()
    if not aid:
        return None
    for binding in list_bindings(env=env):
        if binding.get("agent_id") == aid:
            return binding
    return None
