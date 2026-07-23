import json
from pathlib import Path

import pytest

from edim_dde_ai.cli import main
from edim_dde_ai.cli.store import clear_store

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "agents"


@pytest.fixture(autouse=True)
def _isolated_cli_store(tmp_path, monkeypatch):
    """Point CLI registry store at a temp file — never touch ~/.edim-dde-ai."""
    store = tmp_path / "registered_paths.json"
    monkeypatch.setenv("EDIM_DDE_AI_STORE", str(store))
    clear_store()
    yield
    clear_store()


def test_cli_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "0.1.0"


def test_cli_dash_v_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["-V"])
    assert excinfo.value.code == 0
    err = capsys.readouterr()
    # argparse version goes to stdout (or stderr depending on version); accept either
    combined = (err.out + err.err).strip()
    assert "0.1.0" in combined


def test_cli_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "edim-dde-ai" in out
    assert "register" in out


def test_cli_validate(capsys):
    path = str(EXAMPLES / "echo_agent.agent.yaml")
    assert main(["validate", path]) == 0
    out = capsys.readouterr().out
    assert "echo_agent" in out
    assert "nodes:" in out
    assert "entry:" in out


def test_cli_validate_missing_file(capsys):
    code = main(["validate", "/nonexistent/nope.agent.yaml"])
    assert code == 2
    err = capsys.readouterr().err
    assert "file not found" in err


def test_cli_register_list_run(capsys):
    path = str(EXAMPLES / "echo_agent.agent.yaml")
    assert main(["register", path]) == 0
    reg_out = capsys.readouterr().out
    assert "registered: echo_agent" in reg_out
    assert "remembered:" in reg_out

    assert main(["list"]) == 0
    listed = capsys.readouterr().out
    assert "agents (1):" in listed
    assert "echo_agent" in listed

    assert main(["run", "echo_agent", "--input", json.dumps({"message": "hi"})]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["result"]["message"] == "hi"
    assert data["greeting"] == "hello"


def test_cli_run_unknown_agent_lists_available(capsys):
    path = str(EXAMPLES / "echo_agent.agent.yaml")
    assert main(["register", path]) == 0
    capsys.readouterr()
    code = main(["run", "missing_agent", "--input", "{}"])
    assert code == 1
    err = capsys.readouterr().err
    assert "missing_agent" in err
    assert "echo_agent" in err
    assert "Available" in err


def test_cli_register_dir(capsys):
    assert main(["register-dir", str(EXAMPLES)]) == 0
    out = capsys.readouterr().out
    assert "echo_agent" in out
    assert "two_step_agent" in out


def test_cli_register_dir_missing(capsys):
    code = main(["register-dir", "/nonexistent/agents"])
    assert code == 2
    assert "directory not found" in capsys.readouterr().err


def test_cli_register_dir_empty(tmp_path, capsys):
    empty = tmp_path / "empty_agents"
    empty.mkdir()
    code = main(["register-dir", str(empty)])
    assert code == 1
    assert "no *.agent.yaml" in capsys.readouterr().err
