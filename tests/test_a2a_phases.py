"""ADR-001 Phase 1–6 tests: correlation, resolve, dialers, compose."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from edim_dde_ai.a2a.bindings import clear_runtime_bindings, register_runtime_binding
from edim_dde_ai.a2a.correlation import child_correlation
from edim_dde_ai.a2a.dialers import DialerError, get_dialer, list_transports
from edim_dde_ai.a2a.resolve import resolve_invoke_target
from edim_dde_ai.api.entrypoints import register_from_dict
from edim_dde_ai.errors import DefinitionError
from edim_dde_ai.registry.agents import create_agent


def test_child_correlation_shares_request_id():
    cfg, headers, extras = child_correlation(
        {"request_id": "corr-1", "span_id": "parent-span"},
        child_agent_id="child",
    )
    assert cfg["metadata"]["request_id"] == "corr-1"
    assert cfg["metadata"]["parent_span_id"] == "parent-span"
    assert headers["X-Request-Id"] == "corr-1"
    assert extras["request_id"] == "corr-1"
    assert extras["parent_span_id"] == "parent-span"
    assert extras["span_id"] != "parent-span"


def test_mapped_invoke_propagates_request_id():
    register_from_dict(
        {
            "agent_id": "corr_child",
            "graph": {
                "nodes": [
                    {
                        "id": "echo",
                        "type": "set_value",
                        "field": "echo_rid",
                        "template": "{request_id}",
                    }
                ],
                "edges": [["START", "echo"], ["echo", "END"]],
            },
        }
    )
    register_from_dict(
        {
            "agent_id": "corr_parent",
            "graph": {
                "nodes": [
                    {
                        "id": "call",
                        "type": "invoke_agent",
                        "agent_id": "corr_child",
                        "input_keys": ["request_id"],
                        "output_map": {"echo_rid": "child_rid"},
                    }
                ],
                "edges": [["START", "call"], ["call", "END"]],
            },
        }
    )
    out = create_agent("corr_parent").invoke({"request_id": "rid-99"})
    assert out.get("child_rid") == "rid-99"


def test_resolve_auto_local_default():
    register_from_dict(
        {
            "agent_id": "res_local_child",
            "graph": {
                "nodes": [{"id": "a", "type": "passthrough"}],
                "edges": [["START", "a"], ["a", "END"]],
            },
        }
    )
    d = resolve_invoke_target("res_local_child")
    assert d.mode == "local"


def test_resolve_remote_via_runtime_binding(monkeypatch):
    clear_runtime_bindings()
    monkeypatch.delenv("EDIM_AGENT_DIRECTORY_JSON", raising=False)
    register_runtime_binding(
        {
            "agent_id": "remote_only",
            "mode": "remote",
            "transport": "http",
            "endpoint": "http://127.0.0.1:9",
            "invoke_path": "/api/v1/agents/remote_only/invoke",
        }
    )
    d = resolve_invoke_target("remote_only", resolve="remote")
    assert d.mode == "remote"
    assert d.binding and d.binding["endpoint"]
    clear_runtime_bindings()


def test_resolve_local_missing_raises():
    with pytest.raises(DefinitionError, match="not loaded"):
        resolve_invoke_target("no_such_local_agent_xyz", resolve="local")


def test_http_dialer_roundtrip():
    """Spin a tiny HTTP invoke peer and dial it via invoke_agent resolve=remote."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length)
            body = json.loads(raw.decode("utf-8"))
            assert "X-Request-Id" in self.headers
            name = (body.get("input") or {}).get("name", "anon")
            out = {
                "agent_id": "peer_leaf",
                "request_id": self.headers.get("X-Request-Id"),
                "status": "completed",
                "state": {"greeting": f"remote-{name}"},
            }
            payload = json.dumps(out).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):  # quiet
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        clear_runtime_bindings()
        register_runtime_binding(
            {
                "agent_id": "peer_leaf",
                "mode": "remote",
                "transport": "http",
                "endpoint": f"http://127.0.0.1:{port}",
                "invoke_path": "/api/v1/agents/peer_leaf/invoke",
            }
        )
        register_from_dict(
            {
                "agent_id": "peer_parent",
                "graph": {
                    "nodes": [
                        {
                            "id": "seed",
                            "type": "set_value",
                            "field": "name",
                            "value": "ada",
                        },
                        {
                            "id": "call",
                            "type": "invoke_agent",
                            "agent_id": "peer_leaf",
                            "input_keys": ["name", "request_id"],
                            "output_map": {"greeting": "remote_greeting"},
                            "resolve": "remote",
                        },
                    ],
                    "edges": [
                        ["START", "seed"],
                        ["seed", "call"],
                        ["call", "END"],
                    ],
                },
            }
        )
        out = create_agent("peer_parent").invoke({"request_id": "hop-1"})
        assert out.get("remote_greeting") == "remote-ada"
    finally:
        server.shutdown()
        clear_runtime_bindings()


def test_mcp_dialer_stub():
    assert "mcp" in list_transports()
    dialer = get_dialer("mcp")
    with pytest.raises(DialerError, match="not implemented"):
        dialer.invoke({"agent_id": "x"}, {})
