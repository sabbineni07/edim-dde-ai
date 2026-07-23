"""Framework errors.

All public exceptions subclass ``FoundationError``. Use specific types for
definition/loader/registry failures so callers can handle precisely.

``RouterRegistryError`` covers unknown routers and invalid router config
(for example missing ``field`` for ``field_truthy``).
"""



class FoundationError(Exception):
    """Base error for edim-dde-ai."""


class DefinitionError(FoundationError):
    """Invalid agent definition."""


class LoaderError(FoundationError):
    """YAML load / path errors."""


class NodeRegistryError(FoundationError):
    """Unknown or duplicate node type."""


class AgentRegistryError(FoundationError):
    """Unknown or duplicate agent."""


class ChainInvokerError(FoundationError):
    """Missing or failed chain invoker."""


class RouterRegistryError(FoundationError):
    """Unknown or duplicate router."""


class ContentError(FoundationError):
    """Missing or invalid prompts, skills, or content provider configuration."""
