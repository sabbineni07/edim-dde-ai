from pathlib import Path

import pytest

from edim_dde_ai.errors import LoaderError
from edim_dde_ai.core.loader import load_directory, load_paths, load_yaml

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "agents"


def test_load_yaml():
    defn = load_yaml(EXAMPLES / "echo_agent.agent.yaml")
    assert defn.agent_id == "echo_agent"
    assert defn.nodes[0].type == "set_value"
    assert defn.source_path is not None
    assert defn.source_path.endswith("echo_agent.agent.yaml")


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


def test_load_directory_recursive(tmp_path: Path):
    nested = tmp_path / "agents" / "demo"
    nested.mkdir(parents=True)
    (nested / "demo.agent.yaml").write_text(
        """
agent_id: nested_demo
version: 1
entry: {method: invoke, sync: true}
graph:
  entry: a
  nodes:
    - {id: a, type: passthrough}
  edges: [[a, END]]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(LoaderError, match="No files matching"):
        load_directory(tmp_path / "agents")
    defs = load_directory(tmp_path / "agents", recursive=True)
    assert [d.agent_id for d in defs] == ["nested_demo"]


def test_load_missing_file():
    with pytest.raises(LoaderError):
        load_yaml(EXAMPLES / "nope.agent.yaml")
