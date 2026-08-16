"""Factory helpers for constructing runtime objects.

Business purpose:
  Isolate "build a runnable agent from a definition" behind a small Factory
  Method surface. Prefer the caching ``create_agent`` registry facade in apps.

Public API:
  - ``AgentFactory`` — uncached compile of ``MetadataAgent``
"""

from edim_dde_ai.factories.agent import AgentFactory

__all__ = ["AgentFactory"]
