"""Tests for framework JSON helpers."""

from edim_dde_ai.util.json_util import dumps, parse_json_object


def test_parse_json_object_fenced_and_prose():
    assert parse_json_object('{"a": 1}') == {"a": 1}
    assert parse_json_object('```json\n{"ok": true}\n```') == {"ok": True}
    assert parse_json_object("Here is JSON:\n{\"x\": 2}") == {"x": 2}
    assert parse_json_object("[1,2]") == {}
    assert dumps({"a": 1}).startswith("{")
