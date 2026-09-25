"""ADR-002 call envelope + call_agent + multi-turn."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from edim_dde_ai.a2a import (
    call_agent,
    clear_conversation_turns,
    clear_runtime_bindings,
    needs_continue,
)
from edim_dde_ai.a2a.bindings import register_runtime_binding
from edim_dde_ai.a2a.envelope import (
    STATUS_COMPLETED,
    STATUS_INPUT_NEEDED,
    build_call_envelope,
    normalize_status,
)
from edim_dde_ai.a2a.turns import append_turn, turn_count
from edim_dde_ai.api.entrypoints import register_from_dict
from edim_dde_ai.registry.agents import create_agent


def test_normalize_waiting_to_input_needed():
    assert normalize_status("waiting") == STATUS_INPUT_NEEDED
    assert normalize_status("waiting_hitl") == STATUS_INPUT_NEEDED
    env = build_call_envelope(
        agent_id="x",
        request_id="r",
        state={"hitl_status": "waiting_hitl"},
    )
    assert env["status"] == STATUS_INPUT_NEEDED
    assert needs_continue(env)


def test_conversation_turns_bag():
    clear_conversation_turns()
    append_turn("c1", "hi", reply="ack-hi")
    append_turn("c1", "again", reply="ack-again")
    assert turn_count("c1") == 2
    clear_conversation_turns()


def test_a2a_partner_local_two_turns():
    clear_conversation_turns()
    register_from_dict(
        {
            "agent_id": "a2a_partner_unit",
            "graph": {
                "nodes": [
                    {
                        "id": "turn",
                        "type": "a2a.conversation_turn",
                        "message_key": "message",
                        "reply_template": "ack-{message}",
                    }
                ],
                "edges": [["START", "turn"], ["turn", "END"]],
            },
        }
    )
    from edim_dde_ai.observability.base import build_run_config

    a = create_agent("a2a_partner_unit")
    cfg = build_run_config(
        agent_id="a2a_partner_unit",
        request_id="r1",
        metadata={"edim_a2a": True},
    )
    t1 = a.invoke({"conversation_id": "u1", "message": "one"}, config=cfg)
    assert t1["turn_count"] == 1
    t2 = a.invoke({"conversation_id": "u1", "message": "two"}, config=cfg)
    assert t2["turn_count"] == 2
    assert t2["reply"] == "ack-two"
    clear_conversation_turns()


def test_call_agent_remote_envelope(monkeypatch):
    clear_runtime_bindings()
    clear_conversation_turns()
    monkeypatch.delenv("EDIM_A2A_TOKEN", raising=False)
    monkeypatch.setenv("EDIM_A2A_HTTP_RETRIES", "0")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = json.loads(self.rfile.read(length).decode("utf-8"))
            cid = raw.get("conversation_id") or (raw.get("input") or {}).get(
                "conversation_id"
            )
            msg = (raw.get("input") or {}).get("message", "")
            out = {
                "agent_id": "peer",
                "request_id": self.headers.get("X-Request-Id") or "r",
                "status": "completed",
                "conversation_id": cid,
                "state": {
                    "reply": f"ack-{msg}",
                    "turn_count": 1,
                    "conversation_id": cid,
                },
            }
            payload = json.dumps(out).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        register_runtime_binding(
            {
                "agent_id": "peer_only",
                "mode": "remote",
                "transport": "http",
                "endpoint": f"http://127.0.0.1:{port}",
                "invoke_path": "/api/v1/agents/peer_only/invoke",
            }
        )
        env = call_agent(
            "peer_only",
            {"message": "hi"},
            conversation_id="conv-x",
            resolve="remote",
        )
        assert env["status"] == STATUS_COMPLETED
        assert env["conversation_id"] == "conv-x"
        assert env["state"]["reply"] == "ack-hi"
    finally:
        server.shutdown()
        clear_runtime_bindings()
        clear_conversation_turns()
