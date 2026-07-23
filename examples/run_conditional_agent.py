"""Run conditional_agent twice: include_details True vs False.

Teaches YAML conditional_edges + builtin field_truthy (requires config.field).
"""

from __future__ import annotations

from pathlib import Path

from edim_dde_ai import create_agent, register_from_yaml

YAML = Path(__file__).resolve().parent / "agents" / "conditional_agent.agent.yaml"


def main() -> None:
    register_from_yaml(YAML)
    agent = create_agent("conditional_agent")

    with_details = agent.invoke({"include_details": True})
    without = agent.invoke({"include_details": False})

    print("include_details=True :", with_details.get("branch_message"))
    print("include_details=False:", without.get("branch_message"))


if __name__ == "__main__":
    main()
