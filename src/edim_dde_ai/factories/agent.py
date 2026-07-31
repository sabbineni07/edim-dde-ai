"""Factory Method: construct MetadataAgent from a registered definition.

Looks up ``AgentDefinition`` by id, compiles the LangGraph via ``build_graph``,
and returns a ``MetadataAgent`` ready for ``invoke`` / ``ainvoke``.

Prefer ``create_agent(agent_id)`` from the registry facade — it caches the
compiled graph. Use ``AgentFactory.create`` only when you need a fresh compile.

Example::

    from edim_dde_ai.factories.agent import AgentFactory

    agent = AgentFactory.create("demo")
"""


from __future__ import annotations

from edim_dde_ai.graph.builder import build_graph
from edim_dde_ai.graph.runtime import MetadataAgent
from edim_dde_ai.registry.agents import get_agent_definition


class AgentFactory:
    """Compile agents from registry definitions (uncached; see ``create_agent``)."""

    @staticmethod
    def create(agent_id: str) -> MetadataAgent:
        definition = get_agent_definition(agent_id)
        graph = build_graph(definition)
        return MetadataAgent(definition, graph)
