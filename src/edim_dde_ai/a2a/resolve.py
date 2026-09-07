"""Resolve ``invoke_agent`` targets to local subgraph vs remote dial.

Policy (``EDIM_AGENT_RESOLVE`` or YAML ``resolve``):
  * ``auto`` (default) — local pack unless binding forces remote
  * ``local`` — require in-process registry
  * ``remote`` — require remote binding with dialable endpoint
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from edim_dde_ai.a2a.bindings import get_binding
from edim_dde_ai.errors import DefinitionError

ResolveMode = Literal["auto", "local", "remote"]
ENV_AGENT_RESOLVE = "EDIM_AGENT_RESOLVE"


@dataclass(frozen=True)
class ResolveDecision:
    """Outcome of resolve for one ``agent_id``."""

    mode: Literal["local", "remote"]
    agent_id: str
    binding: dict[str, Any] | None = None


def resolve_policy(explicit: str | None = None) -> ResolveMode:
    """Return effective resolve mode from YAML override or env."""
    raw = (explicit or os.environ.get(ENV_AGENT_RESOLVE) or "auto").strip().lower()
    if raw not in ("auto", "local", "remote"):
        raise DefinitionError(
            f"invoke_agent resolve must be auto|local|remote, got {raw!r}"
        )
    return raw  # type: ignore[return-value]


def _local_loaded(agent_id: str) -> bool:
    from edim_dde_ai.errors import AgentRegistryError
    from edim_dde_ai.registry.agents import get_agent_definition

    try:
        get_agent_definition(agent_id)
        return True
    except AgentRegistryError:
        return False


def _is_remote_binding(binding: dict[str, Any] | None) -> bool:
    if not binding:
        return False
    mode = str(binding.get("mode") or "").strip().lower()
    transport = str(binding.get("transport") or "").strip().lower()
    if mode == "remote":
        return True
    if transport and transport not in ("in_process", "local"):
        return True
    return False


def resolve_invoke_target(
    agent_id: str,
    *,
    resolve: str | None = None,
) -> ResolveDecision:
    """Decide local subgraph vs remote dial for ``agent_id``.

    Raises:
        DefinitionError: Cannot satisfy the requested policy.
    """
    target = (agent_id or "").strip()
    if not target:
        raise DefinitionError("invoke_agent requires non-empty agent_id")
    policy = resolve_policy(resolve)
    binding = get_binding(target)
    local = _local_loaded(target)
    remote = _is_remote_binding(binding)

    if policy == "local":
        if not local:
            raise DefinitionError(
                f"invoke_agent resolve=local but {target!r} is not loaded in-process"
            )
        return ResolveDecision(mode="local", agent_id=target, binding=binding)

    if policy == "remote":
        if not remote or not binding:
            raise DefinitionError(
                f"invoke_agent resolve=remote but no remote binding for {target!r}"
            )
        if not binding.get("endpoint"):
            raise DefinitionError(
                f"invoke_agent resolve=remote requires endpoint for {target!r}"
            )
        return ResolveDecision(mode="remote", agent_id=target, binding=binding)

    # auto
    if remote and binding and binding.get("endpoint"):
        # Overlay / directory forced remote wins even if pack is local.
        return ResolveDecision(mode="remote", agent_id=target, binding=binding)
    if local:
        return ResolveDecision(mode="local", agent_id=target, binding=binding)
    if remote and binding:
        raise DefinitionError(
            f"invoke_agent auto: remote binding for {target!r} missing endpoint"
        )
    raise DefinitionError(
        f"invoke_agent cannot resolve {target!r}: not local and no remote binding"
    )
