from pathlib import Path

import pytest

from edim_dde_ai import create_agent, register_from_yaml, register_node
from edim_dde_ai.core.loader import load_yaml
from edim_dde_ai.graph import build_graph
from edim_dde_ai.registry.chains import register_chain_invoker
from edim_dde_ai.errors import ChainInvokerError

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "agents"


def test_echo_agent_invoke():
    register_from_yaml(EXAMPLES / "echo_agent.agent.yaml")
    agent = create_agent("echo_agent")
    result = agent.invoke({"message": "hello"})
    assert result["greeting"] == "hello"
    assert result["result"] == {"greeting": "hello", "message": "hello"}


def test_build_graph_preserves_product_input_shape():
    definition = load_yaml(EXAMPLES / "echo_agent.agent.yaml")
    graph = build_graph(definition)

    result = graph.invoke({"message": "hello"})

    assert result["result"] == {"greeting": "hello", "message": "hello"}
    assert "data" not in result


def test_two_step_template():
    register_from_yaml(EXAMPLES / "two_step_agent.agent.yaml")
    agent = create_agent("two_step_agent")
    result = agent.invoke({"message": "hi"})
    assert result["step"] == 1
    assert result["label"] == "step=1 msg=hi"
    assert result["result"]["message"] == "hi"


def test_llm_chain_requires_invoker():
    @register_node("tmp_unused_guard")
    def _unused(_c):
        return lambda s: {}

    yaml_text = """
agent_id: llm_demo
graph:
  entry: call
  nodes:
    - id: call
      type: llm_chain
      chain: missing_chain
    - id: done
      type: passthrough
  edges:
    - [call, done]
    - [done, END]
"""
    import tempfile

    from edim_dde_ai.api.entrypoints import register_from_yaml as reg

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "llm.agent.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        reg(path)
        agent = create_agent("llm_demo")
        with pytest.raises(ChainInvokerError, match="missing_chain"):
            agent.invoke({})


def test_llm_chain_with_invoker():
    @register_chain_invoker("stub")
    def stub(state, config):
        return {"echo": state.get("message")}

    yaml_text = """
agent_id: llm_ok
graph:
  entry: call
  nodes:
    - id: call
      type: llm_chain
      chain: stub
      output_key: llm_raw
    - id: done
      type: echo_result
      from_fields: [llm_raw]
  edges:
    - [call, done]
    - [done, END]
"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "llm_ok.agent.yaml"
        path.write_text(yaml_text, encoding="utf-8")
        register_from_yaml(path)
        agent = create_agent("llm_ok")
        out = agent.invoke({"message": "x"})
        assert out["result"]["llm_raw"] == {"echo": "x"}
