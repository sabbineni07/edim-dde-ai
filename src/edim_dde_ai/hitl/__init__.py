"""Human-in-the-loop pause / resume (StateStore sessions).

Business purpose
----------------
Framework HITL Facade: ``hitl.gate`` pauses a graph, persists a session, and
``resume_hitl_session`` continues after approve / reject / modify.

Public API
----------
* ``resume_hitl_session`` / ``persist_hitl_pause`` / ``close_hitl_session``
* ``hitl_gate_factory`` / ``skip_until_resume`` / ``apply_gate_build_config``
* ``HITL_DECISIONS`` / ``HitlPaused`` / ``HitlError``
"""

from edim_dde_ai.errors import HitlError, HitlPaused
from edim_dde_ai.hitl.decorator import RESUME_AT_KEY, skip_until_resume
from edim_dde_ai.hitl.gate import apply_gate_build_config, hitl_gate_factory
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
    "apply_gate_build_config",
    "close_hitl_session",
    "hitl_gate_factory",
    "merge_hitl_decision",
    "persist_hitl_pause",
    "prior_decision_for_gate",
    "resume_hitl_session",
    "skip_until_resume",
]
