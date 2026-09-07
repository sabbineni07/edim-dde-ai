"""MCP dialer stub (ADR-001 Phase 6+) — registered, not implemented."""

from __future__ import annotations

from typing import Any

from edim_dde_ai.a2a.dialers.base import DialerError


class McpDialer:
    """Placeholder transport plugin for future MCP agent dials."""

    name = "mcp"

    def invoke(
        self,
        binding: dict[str, Any],
        state: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
        timeout_s: float = 60.0,
    ) -> dict[str, Any]:
        raise DialerError(
            "MCP dialer is not implemented yet (ADR-001 Phase 6+). "
            f"agent_id={binding.get('agent_id')!r}"
        )
