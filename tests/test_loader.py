from pathlib import Path

import pytest

from edim_dde_ai.errors import LoaderError
from edim_dde_ai.core.loader import load_directory, load_paths, load_yaml

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "agents"


def test_load_yaml():
    defn = load_yaml(EXAMPLES / "echo_agent.agent.yaml")
    assert defn.agent_id == "echo_agent"
    assert defn.nodes[0].type == "set_value"


def test_load_paths():
    defs = load_paths(
        [
            EXAMPLES / "echo_agent.agent.yaml",
            EXAMPLES / "two_step_agent.agent.yaml",
        ]
    )
    assert [d.agent_id for d in defs] == ["echo_agent", "two_step_agent"]


def test_load_directory():
    defs = load_directory(EXAMPLES)
    ids = {d.agent_id for d in defs}
    assert "echo_agent" in ids
    assert "two_step_agent" in ids


def test_load_missing_file():
    with pytest.raises(LoaderError):
        load_yaml(EXAMPLES / "nope.agent.yaml")
