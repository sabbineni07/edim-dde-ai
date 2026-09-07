"""Dialer plugin registry (ADR-001 Phase 4 / 6)."""

from __future__ import annotations

from edim_dde_ai.a2a.dialers.base import (
    Dialer,
    DialerError,
    get_dialer,
    list_transports,
    register_dialer,
)

__all__ = [
    "Dialer",
    "DialerError",
    "get_dialer",
    "list_transports",
    "register_dialer",
]
