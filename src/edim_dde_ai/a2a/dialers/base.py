"""Dialer protocol + registry (no builtin imports — avoids cycles)."""

from __future__ import annotations

from typing import Any, Protocol

from edim_dde_ai.errors import FoundationError

_DIALERS: dict[str, Dialer] = {}


class DialerError(FoundationError):
    """Remote agent dial failed or transport unsupported."""


class Dialer(Protocol):
    """Transport plugin: binding + flat input → flat child state."""

    name: str

    def invoke(
        self,
        binding: dict[str, Any],
        state: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
        timeout_s: float = 60.0,
    ) -> dict[str, Any]:
        """POST (or equivalent) and return flat state dict."""


def register_dialer(dialer: Dialer, *, overwrite: bool = False) -> None:
    """Register a transport dialer by ``dialer.name``."""
    key = str(getattr(dialer, "name", "") or "").strip().lower()
    if not key:
        raise ValueError("dialer.name required")
    if key in _DIALERS and not overwrite:
        raise ValueError(f"dialer already registered: {key}")
    _DIALERS[key] = dialer


def get_dialer(transport: str) -> Dialer:
    """Return dialer for ``transport`` or raise ``DialerError``."""
    _ensure_builtins()
    key = (transport or "").strip().lower()
    dialer = _DIALERS.get(key)
    if dialer is None:
        raise DialerError(
            f"No dialer registered for transport={transport!r}; "
            f"known={sorted(_DIALERS)}"
        )
    return dialer


def list_transports() -> list[str]:
    """Sorted registered transport names."""
    _ensure_builtins()
    return sorted(_DIALERS)


def _ensure_builtins() -> None:
    if "http" not in _DIALERS:
        from edim_dde_ai.a2a.dialers.http import HttpDialer

        register_dialer(HttpDialer(), overwrite=True)
    if "mcp" not in _DIALERS:
        from edim_dde_ai.a2a.dialers.mcp import McpDialer

        register_dialer(McpDialer(), overwrite=True)
