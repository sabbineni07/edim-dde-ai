"""Tests for agent-agnostic session host helpers."""

from __future__ import annotations

import pytest

from edim_dde_ai.errors import ConversationMemoryDisabledError
from edim_dde_ai.session.host import (
    attach_thread_id,
    normalize_conversation_payload,
    normalize_http_session_status,
    project_session_state,
)
from edim_dde_ai.store.models import SessionRecord
from edim_dde_ai.session.host import project_session_record


def test_normalize_conversation_payload_mints_ids_when_memory_on():
    payload, cid = normalize_conversation_payload(
        {"job_id": "j1", "message": "hello"},
        request_id="r1",
        memory_enabled=True,
    )
    assert cid
    assert payload["user_message"] == "hello"
    assert payload["conversation_id"] == cid
    assert payload["thread_id"] == cid
    assert payload["request_id"] == "r1"
    assert "message" not in payload


def test_normalize_conversation_payload_rejects_id_when_memory_off():
    with pytest.raises(ConversationMemoryDisabledError):
        normalize_conversation_payload(
            {"conversation_id": "c1"},
            request_id="r1",
            memory_enabled=False,
        )


def test_attach_thread_id_and_session_projection():
    assert attach_thread_id({}, None) == {}
    cfg = attach_thread_id({"tags": ["t"]}, "cid")
    assert cfg["configurable"]["thread_id"] == "cid"
    assert normalize_http_session_status("resumed") == "closed"
    projected = project_session_state(
        agent_id="demo",
        state={"session_id": "s1", "hitl_status": "waiting_hitl", "hitl_prompt": "ok?"},
        request_id="r1",
    )
    assert projected["status"] == "waiting_hitl"
    assert projected["hitl_prompt"] == "ok?"
    rec = SessionRecord(
        session_id="s1",
        agent_id="demo",
        status="waiting_hitl",
        state={"hitl_decision": "approved"},
        request_id="r1",
        extra={"prompt": "from-extra"},
    )
    assert project_session_record(rec)["hitl_prompt"] == "from-extra"
