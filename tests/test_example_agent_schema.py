"""BL-002: example agents match R1 JSON Schema (+ extended blocks)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytest.importorskip("jsonschema")

from edim_dde_ai.core.definition import parse_agent_definition
from edim_dde_ai.schema.validate import validate_agent_dict

_EXAMPLES = sorted(
    (Path(__file__).resolve().parents[1] / "examples" / "agents").rglob(
        "*.agent.yaml"
    )
)


@pytest.mark.parametrize(
    "path",
    _EXAMPLES,
    ids=[p.name for p in _EXAMPLES],
)
def test_example_agent_matches_schema(path: Path) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    validate_agent_dict(data)
    validate_agent_dict(data, use_jsonschema=True)
    parse_agent_definition(data)
