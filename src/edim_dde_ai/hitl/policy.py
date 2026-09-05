"""YAML-driven HITL policy helpers (decisions + patch allowlist).

Business purpose
----------------
Product agents declare HITL rules in ``hitl:`` YAML. Hosts and
``resume_hitl_session`` use these helpers so policy is not hard-coded by
``agent_id`` in the API layer.

Public API
----------
* ``hitl_block`` / ``allowed_decisions`` / ``patch_allowlist`` / ``patch_target``
* ``filter_hitl_patch`` / ``prepare_resume_patch``
* ``is_hitl_waiting`` / ``should_persist_after_hitl``
"""

from __future__ import annotations

from typing import Any

from edim_dde_ai.core.definition import AgentDefinition
from edim_dde_ai.errors import HitlError
from edim_dde_ai.hitl.sessions import HITL_DECISIONS, STATUS_WAITING


def hitl_block(definition: AgentDefinition | dict[str, Any] | None) -> dict[str, Any]:
    """Return the agent ``hitl`` mapping (empty dict when absent)."""
    if definition is None:
        return {}
    if isinstance(definition, AgentDefinition):
        raw = (definition.raw or {}).get("hitl") or {}
    elif isinstance(definition, dict):
        raw = definition.get("hitl") or definition
    else:
        return {}
    return dict(raw) if isinstance(raw, dict) else {}


def allowed_decisions(
    definition: AgentDefinition | dict[str, Any] | None = None,
) -> frozenset[str]:
    """Return allowlisted resume decisions from ``hitl.decisions``.

    When ``hitl.decisions`` is omitted, all framework decisions are allowed
    (``approved`` | ``rejected`` | ``modified``).
    """
    listed = hitl_block(definition).get("decisions")
    if not isinstance(listed, list) or not listed:
        return HITL_DECISIONS
    allowed = {
        str(item).strip().lower()
        for item in listed
        if str(item).strip()
    }
    # Intersect with framework vocabulary so YAML cannot invent decisions.
    return frozenset(allowed & HITL_DECISIONS) if allowed else HITL_DECISIONS


def patch_allowlist(
    definition: AgentDefinition | dict[str, Any] | None = None,
) -> frozenset[str] | None:
    """Return ``hitl.patch_allowlist`` keys, or ``None`` when unset.

    ``None`` means the agent did not declare an allowlist (hosts may still
    reject ``modified`` via ``allowed_decisions``). An explicit empty list means
    fail-closed: no patch keys are accepted.
    """
    listed = hitl_block(definition).get("patch_allowlist")
    if listed is None:
        return None
    if not isinstance(listed, list):
        return frozenset()
    return frozenset(str(item).strip() for item in listed if str(item).strip())


def patch_target(
    definition: AgentDefinition | dict[str, Any] | None = None,
) -> str | None:
    """Optional state dict key that receives allowlisted patch merges.

    Example: ``patch_target: recommendation`` merges into ``state.recommendation``
    instead of littering top-level keys (and avoids replacing the whole dict
    when clients send ``{"recommendation": {...}}``).
    """
    value = hitl_block(definition).get("patch_target")
    if value is None or value == "":
        return None
    text = str(value).strip()
    return text or None


def filter_hitl_patch(
    patch: dict[str, Any] | None,
    allowlist: frozenset[str] | None,
    *,
    target_key: str | None = None,
) -> dict[str, Any]:
    """Return allowlisted flat field updates from a HITL patch body.

    Accepts a flat map or a nested map under ``target_key`` /
    ``recommendation``. When ``allowlist`` is ``None``, all source keys are
    kept (except decision meta keys). When ``allowlist`` is empty, returns ``{}``.
    """
    if not patch or not isinstance(patch, dict):
        return {}

    raw: dict[str, Any] = patch
    nested_keys = [k for k in (target_key, "recommendation") if k]
    for key in nested_keys:
        nested = patch.get(key)
        if isinstance(nested, dict) and (len(patch) == 1 or key == target_key):
            raw = nested
            break

    if allowlist is not None and not allowlist:
        return {}

    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key in {"decision", "comment", "actor"}:
            continue
        if allowlist is None or key in allowlist:
            out[str(key)] = value
    return out


def prepare_resume_patch(
    definition: AgentDefinition | dict[str, Any] | None,
    *,
    decision: str,
    patch: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Validate decision/patch against YAML policy; return merge-ready flat patch.

    Raises:
        HitlError: Decision not allowlisted, or ``modified`` without usable patch.
    """
    choice = (decision or "").strip().lower()
    allowed = allowed_decisions(definition)
    if choice not in allowed:
        raise HitlError(
            f"hitl decision {choice!r} not allowed; expected one of {sorted(allowed)}"
        )
    if choice != "modified":
        return None
    allowlist = patch_allowlist(definition)
    target = patch_target(definition)
    if allowlist is None:
        raise HitlError(
            "hitl.decisions includes modified but hitl.patch_allowlist is not set"
        )
    filtered = filter_hitl_patch(patch, allowlist, target_key=target)
    if not filtered:
        raise HitlError(
            "modified requires an allowlisted patch; allowed keys: "
            + ", ".join(sorted(allowlist))
        )
    return filtered


def apply_patch_to_state(
    state: dict[str, Any],
    patch: dict[str, Any] | None,
    *,
    target_key: str | None = None,
) -> dict[str, Any]:
    """Return state with filtered patch applied (flat or into ``target_key``)."""
    out = dict(state)
    if not patch:
        return out
    if target_key:
        bag = dict(out.get(target_key) or {})
        if not isinstance(bag, dict):
            bag = {}
        bag.update(patch)
        out[target_key] = bag
    else:
        out.update(patch)
    return out


def is_hitl_waiting(final: dict[str, Any] | None) -> bool:
    """True when invoke returned a ``waiting_hitl`` pause snapshot."""
    if not final:
        return False
    return str(final.get("hitl_status") or "") == STATUS_WAITING


def should_persist_after_hitl(final: dict[str, Any] | None) -> bool:
    """True when a host may persist product history after HITL completes.

    Waiting and rejected outcomes should not create an official RecStore row.
    """
    if not final or is_hitl_waiting(final):
        return False
    outcome = str(final.get("hitl_outcome") or final.get("hitl_decision") or "").lower()
    if outcome == "rejected" or str(final.get("status") or "") == "rejected":
        return False
    return True
