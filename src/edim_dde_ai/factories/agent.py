"""Factory Method: construct MetadataAgent from a registered definition.

Business purpose:
Look up ``AgentDefinition`` by id, compile the LangGraph via ``build_graph_for_definition``,
and return a ``MetadataAgent`` ready for ``invoke`` / ``ainvoke``.

Public API:
  - ``AgentFactory.create(agent_id)`` — fresh compile (uncached)

Prefer ``create_agent(agent_id)`` from the registry facade — it caches the
compiled graph. Use ``AgentFactory.create`` only when you need a fresh compile.

Example::

    from edim_dde_ai.factories.agent import AgentFactory

    agent = AgentFactory.create("demo")
"""

from __future__ import annotations

from edim_dde_ai.graph.session_builder import build_graph_for_definition
from edim_dde_ai.graph.runtime import MetadataAgent
from edim_dde_ai.registry.agents import get_agent_definition


class AgentFactory:
    """Compile agents from registry definitions (uncached; see ``create_agent``).

    Uses ``build_graph_for_definition`` so session-enabled YAML gets multi-turn
    routing + checkpointer automatically; other agents get plain ``build_graph``.
    """

    @staticmethod
    def create(agent_id: str) -> MetadataAgent:
        """Build a new ``MetadataAgent`` for ``agent_id``.

        Args:
            agent_id: Registered agent id.

        Returns:
            Freshly compiled ``MetadataAgent`` (not cached here).

        Raises:
            AgentRegistryError: If ``agent_id`` is unknown.
        """
        definition = get_agent_definition(agent_id)
        graph = build_graph_for_definition(definition)
        return MetadataAgent(definition, graph)
