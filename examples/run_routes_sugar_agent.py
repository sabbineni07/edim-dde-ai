#!/usr/bin/env python3
"""Run the routes-sugar conditional agent example.

Teaches graph.routes YAML sugar (desugars to conditional_edges + field_truthy).
"""

from __future__ import annotations

from pathlib import Path

from edim_dde_ai import create_agent, register_from_yaml

ROOT = Path(__file__).resolve().parents[1]
YAML = ROOT / "examples" / "agents" / "routes_sugar_agent.agent.yaml"


def main() -> None:
    register_from_yaml(YAML, overwrite=True)
    agent = create_agent("routes_sugar_agent")
    yes = agent.invoke({"include_details": True})
    no = agent.invoke({"include_details": False})
    print("details:", yes.get("branch_message"))
    print("summary:", no.get("branch_message"))


if __name__ == "__main__":
    main()
