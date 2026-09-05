"""Human-in-the-loop pause / resume (StateStore sessions).

Business purpose
----------------
Framework HITL Facade: ``hitl.gate`` pauses a graph, persists a session, and
``resume_hitl_session`` continues after approve / reject / modify. YAML
``hitl.decisions`` / ``hitl.patch_allowlist`` policy lives in ``hitl.policy``.

Public API
----------
* ``resume_hitl_session`` / ``persist_hitl_pause`` / ``close_hitl_session``
* ``hitl_gate_factory`` / ``hitl_apply_outcome_factory`` / ``skip_until_resume``
* ``allowed_decisions`` / ``filter_hitl_patch`` / ``is_hitl_waiting`` / …
* ``HITL_DECISIONS`` / ``HitlPaused`` / ``HitlError``
"""

from edim_dde_ai.errors import HitlError, HitlPaused
from edim_dde_ai.hitl.apply_outcome import hitl_apply_outcome_factory
from edim_dde_ai.hitl.decorator import RESUME_AT_KEY, skip_until_resume
from edim_dde_ai.hitl.gate import apply_gate_build_config, hitl_gate_factory
from edim_dde_ai.hitl.policy import (
    allowed_decisions,
    apply_patch_to_state,
    filter_hitl_patch,
    hitl_block,
    is_hitl_waiting,
    patch_allowlist,
    patch_target,
    prepare_resume_patch,
    should_persist_after_hitl,
)
from edim_dde_ai.hitl.sessions import (
    HITL_DECISIONS,
    STATUS_CLOSED,
    STATUS_RESUMED,
    STATUS_RESUMING,
    STATUS_WAITING,
    close_hitl_session,
    merge_hitl_decision,
    persist_hitl_pause,
    prior_decision_for_gate,
    resume_hitl_session,
)

__all__ = [
    "HITL_DECISIONS",
    "RESUME_AT_KEY",
    "STATUS_CLOSED",
    "STATUS_RESUMED",
    "STATUS_RESUMING",
    "STATUS_WAITING",
    "HitlError",
    "HitlPaused",
    "allowed_decisions",
    "apply_gate_build_config",
    "apply_patch_to_state",
    "close_hitl_session",
    "filter_hitl_patch",
    "hitl_apply_outcome_factory",
    "hitl_block",
    "hitl_gate_factory",
    "is_hitl_waiting",
    "merge_hitl_decision",
    "patch_allowlist",
    "patch_target",
    "persist_hitl_pause",
    "prepare_resume_patch",
    "prior_decision_for_gate",
    "resume_hitl_session",
    "should_persist_after_hitl",
    "skip_until_resume",
]
