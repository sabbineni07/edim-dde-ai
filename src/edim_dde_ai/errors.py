"""Framework errors.

Business purpose:
  All public exceptions subclass ``FoundationError``. Use specific types for
  definition/loader/registry failures so callers can handle precisely.

Public API:
  - ``FoundationError`` — base
  - ``DefinitionError`` / ``LoaderError``
  - ``NodeRegistryError`` / ``AgentRegistryError`` / ``ChainInvokerError`` /
    ``RouterRegistryError``
  - ``ContentError``

``RouterRegistryError`` covers unknown routers and invalid router config
(for example missing ``field`` for ``field_truthy``).
"""


class FoundationError(Exception):
    """Base error for edim-dde-ai."""


class DefinitionError(FoundationError):
    """Invalid agent definition (YAML/JSON shape or contract blocks)."""


class LoaderError(FoundationError):
    """YAML load / path errors (I/O, parse, empty file)."""


class NodeRegistryError(FoundationError):
    """Unknown or duplicate node type."""


class AgentRegistryError(FoundationError):
    """Unknown or duplicate agent."""


class ChainInvokerError(FoundationError):
    """Missing or failed chain invoker / default LLM path."""


class RouterRegistryError(FoundationError):
    """Unknown or duplicate router, or invalid router config."""


class ContentError(FoundationError):
    """Missing or invalid prompts, skills, or content provider configuration."""
