"""argparse CLI for edim-dde-ai.

Business purpose:
  Operator-facing commands to validate, register, list, and invoke YAML agents
  without writing Python. Loads remembered paths from ``cli.store`` before
  list/run.

Public API:
  - ``build_parser()`` — construct the argparse tree
  - ``main(argv=None)`` — parse and dispatch; return exit code

Commands: ``version``, ``list``, ``register``, ``register-dir``, ``run``,
``validate``.

Example::

    python -m edim_dde_ai register path/to/demo.agent.yaml
    python -m edim_dde_ai run demo --input '{"x": 1}'
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from edim_dde_ai import __version__
from edim_dde_ai.api.entrypoints import register_from_directory, register_from_yaml
from edim_dde_ai.cli.store import (
    load_remembered_into_registry,
    remember_paths,
)
from edim_dde_ai.core.loader import load_yaml
from edim_dde_ai.errors import FoundationError
from edim_dde_ai.registry.agents import create_agent, list_agents

_EPILOG = """\
examples:
  edim-dde-ai version
  edim-dde-ai validate examples/agents/echo_agent.agent.yaml
  edim-dde-ai register examples/agents/echo_agent.agent.yaml
  edim-dde-ai register-dir examples/agents
  edim-dde-ai list
  edim-dde-ai run echo_agent --input '{"message":"hi"}'
  edim-dde-ai run echo_agent --yaml path/to/agent.agent.yaml --input '{}'

Store path can be overridden with EDIM_DDE_AI_STORE.
See docs/USAGE.md and docs/PUBLISHING.md.
"""


def _error(msg: str) -> int:
    """Print ``error: ...`` to stderr and return exit code 1."""
    print(f"error: {msg}", file=sys.stderr)
    return 1


def _format_exc(exc: BaseException) -> str:
    """Friendly message; include FoundationError subclass name when useful."""
    if isinstance(exc, FoundationError):
        name = type(exc).__name__
        if name != "FoundationError":
            return f"{name}: {exc}"
    return str(exc)


def _cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def _cmd_list(_args: argparse.Namespace) -> int:
    load_remembered_into_registry(overwrite=True)
    agents = list_agents()
    if not agents:
        print("(no agents registered)")
    else:
        print(f"agents ({len(agents)}):")
        for agent_id in agents:
            print(agent_id)
    return 0


def _cmd_register(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2
    agent_id = register_from_yaml(path, overwrite=True)
    abs_path = path.resolve()
    remember_paths([abs_path])
    print(f"registered: {agent_id}")
    print(f"remembered: {abs_path}")
    return 0


def _cmd_register_dir(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.is_dir():
        print(f"error: directory not found: {path}", file=sys.stderr)
        return 2
    files = sorted(path.glob("*.agent.yaml"))
    if not files:
        print(
            f"error: no *.agent.yaml files in {path.resolve()}",
            file=sys.stderr,
        )
        return 1
    ids = register_from_directory(path, overwrite=True)
    remember_paths(files)
    for agent_id in ids:
        print(f"registered: {agent_id}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2
    definition = load_yaml(path)
    n_nodes = len(definition.nodes)
    print(f"valid: {definition.agent_id} ({definition.display_name})")
    print(f"nodes: {n_nodes}; entry: {definition.graph_entry}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    if args.yaml:
        yaml_path = Path(args.yaml)
        if not yaml_path.is_file():
            print(f"error: file not found: {yaml_path}", file=sys.stderr)
            return 2
        register_from_yaml(yaml_path, overwrite=True)
        remember_paths([yaml_path.resolve()])
    else:
        load_remembered_into_registry(overwrite=True)

    available = list_agents()
    if args.agent_id not in available:
        if available:
            listed = ", ".join(available)
            return _error(
                f"agent '{args.agent_id}' is not registered. "
                f"Available: {listed}. "
                "Use 'register' / 'register-dir', or pass --yaml PATH."
            )
        return _error(
            f"agent '{args.agent_id}' is not registered "
            "(no agents in the store). "
            "Use 'register' / 'register-dir', or pass --yaml PATH."
        )
    try:
        payload = json.loads(args.input) if args.input else {}
    except json.JSONDecodeError as exc:
        return _error(f"invalid --input JSON: {exc}")
    if not isinstance(payload, dict):
        return _error("--input must be a JSON object")
    agent = create_agent(args.agent_id)
    result = agent.invoke(payload)
    print(json.dumps(result, default=str, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argparse parser and subcommands.

    Returns:
        Configured ``ArgumentParser`` (``command`` required).
    """
    parser = argparse.ArgumentParser(
        prog="edim-dde-ai",
        description=(
            "YAML-driven LangGraph agent foundation.\n\n"
            "Register agent YAML definitions, validate them, list remembered "
            "agents, and invoke graphs from the command line."
        ),
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_version = sub.add_parser("version", help="Print package version")
    p_version.set_defaults(func=_cmd_version)

    p_list = sub.add_parser(
        "list",
        help="List registered agent ids",
        description="List agent ids loaded from the CLI store (remembered YAML paths).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="example:\n  edim-dde-ai list",
    )
    p_list.set_defaults(func=_cmd_list)

    p_reg = sub.add_parser(
        "register",
        help="Register an agent from a YAML file",
        description="Parse and register one .agent.yaml; remember its path in the CLI store.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "example:\n"
            "  edim-dde-ai register examples/agents/echo_agent.agent.yaml"
        ),
    )
    p_reg.add_argument("path", help="Path to .agent.yaml")
    p_reg.set_defaults(func=_cmd_register)

    p_regdir = sub.add_parser(
        "register-dir",
        help="Register all *.agent.yaml files in a directory",
        description="Register every non-recursive *.agent.yaml under a directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="example:\n  edim-dde-ai register-dir examples/agents",
    )
    p_regdir.add_argument("path", help="Directory path")
    p_regdir.set_defaults(func=_cmd_register_dir)

    p_val = sub.add_parser(
        "validate",
        help="Validate an agent YAML without registering",
        description="Load and validate definition YAML; print agent id, node count, entry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "example:\n"
            "  edim-dde-ai validate examples/agents/echo_agent.agent.yaml"
        ),
    )
    p_val.add_argument("path", help="Path to .agent.yaml")
    p_val.set_defaults(func=_cmd_validate)

    p_run = sub.add_parser(
        "run",
        help="Invoke a registered agent",
        description=(
            "Invoke an agent by id with a JSON object --input. "
            "Optionally register a YAML in the same process with --yaml."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  edim-dde-ai run echo_agent --input '{\"message\":\"hi\"}'\n"
            "  edim-dde-ai run echo_agent --yaml examples/agents/echo_agent.agent.yaml "
            "--input '{}'"
        ),
    )
    p_run.add_argument("agent_id", help="Agent id")
    p_run.add_argument(
        "--input",
        default="{}",
        help='JSON object input state, e.g. \'{"message":"hi"}\'',
    )
    p_run.add_argument(
        "--yaml",
        default=None,
        help="Optional YAML to register before run (same process)",
    )
    p_run.set_defaults(func=_cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint.

    Args:
        argv: Optional argv list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 success; 1 general error; 2 not found).
    """
    import edim_dde_ai.nodes  # noqa: F401

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except FoundationError as exc:
        return _error(_format_exc(exc))
    except FileNotFoundError as exc:
        path = getattr(exc, "filename", None) or exc
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2
    except OSError as exc:
        return _error(f"OS error: {exc}")
    except Exception as exc:  # noqa: BLE001 — surface CLI failures cleanly
        return _error(_format_exc(exc))


if __name__ == "__main__":
    raise SystemExit(main())
