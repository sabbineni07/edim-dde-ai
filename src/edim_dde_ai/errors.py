"""Framework errors.

Business purpose:
  All public exceptions subclass ``FoundationError``. Use specific types for
  definition/loader/registry failures so callers can handle precisely.

Public API:
  - ``FoundationError`` — base
  - ``DefinitionError`` / ``LoaderError``
  - ``NodeRegistryError`` / ``AgentRegistryError`` / ``ChainInvokerError`` /
    ``RouterRegistryError``
  - ``ContentError`` / ``ConversationMemoryDisabledError``

``RouterRegistryError`` covers unknown routers and invalid router config
(for example missing ``field`` for ``field_truthy``).

``HitlPaused`` is control flow (not a failure): a ``hitl.gate`` stopped the
graph for human approval. ``HitlError`` is an invalid session or decision.
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


class ConversationMemoryDisabledError(FoundationError):
    """Conversation context was requested for an agent without memory enabled."""


class HitlPaused(Exception):
    """Graph stopped at a HITL gate pending human approval (not a failure).

    Attributes:
        session_id: Persisted StateStore session key.
        agent_id: Agent that paused.
        state: Flat metadata snapshot at the gate (includes ``hitl_status``).
    """

    def __init__(
        self,
        session_id: str,
        agent_id: str,
        state: dict,
    ) -> None:
        self.session_id = session_id
        self.agent_id = agent_id
        self.state = state
        super().__init__(
            f"HITL pause session_id={session_id!r} agent_id={agent_id!r}"
        )


class HitlError(FoundationError):
    """Invalid HITL session, status, or decision (resume rejected)."""
