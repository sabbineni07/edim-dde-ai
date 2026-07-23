"""Example: register a custom node type, then load an agent YAML."""

from __future__ import annotations

import tempfile
from pathlib import Path

from edim_dde_ai import create_agent, register_from_yaml, register_node


@register_node("upper_message")
def upper_message_factory(_config):
    def _node(state):
        msg = state.get("message", "")
        return {"message": str(msg).upper()}

    return _node


YAML = """
agent_id: upper_echo
display_name: Upper Echo
version: 1
graph:
  entry: upper
  nodes:
    - id: upper
      type: upper_message
    - id: finish
      type: echo_result
      from_fields: [message]
  edges:
    - [upper, finish]
    - [finish, END]
"""


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "upper_echo.agent.yaml"
        path.write_text(YAML, encoding="utf-8")
        register_from_yaml(path)
        agent = create_agent("upper_echo")
        result = agent.invoke({"message": "hello"})
        print(result)


if __name__ == "__main__":
    main()
