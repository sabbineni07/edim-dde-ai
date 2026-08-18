"""EDIM DDE AI — YAML-driven LangGraph agent framework.

Business purpose:
  Process-wide entry package: register agents from YAML/dicts, create runnable
  ``MetadataAgent`` instances, and configure content, observability, store,
  retrieval, evaluation, and web-search providers.

Public API:
  Re-exports registration, agent factory, content, observability, store,
  recommendations, retrieval, evaluation, and web-search helpers. See ``__all__``.

Importing this package also registers builtin node types via ``edim_dde_ai.nodes``.
"""

from edim_dde_ai.api.entrypoints import (
    register_from_dict,
    register_from_dicts,
    register_from_directory,
    register_from_json,
    register_from_paths,
    register_from_yaml,
)
from edim_dde_ai.content import (
    DirectoryContentProvider,
    Skill,
    clear_content_providers,
    get_llm_provider,
    get_prompt_provider,
    get_skill_provider,
    register_skill,
    set_llm_provider,
    set_prompt_provider,
    set_skill_provider,
)
from edim_dde_ai.observability import (
    configure_observability_from_env,
    get_observability_provider,
    set_observability_provider,
)
from edim_dde_ai.store import (
    configure_state_store_from_env,
    get_state_store,
    set_state_store,
    sync_registered_agents_to_store,
)
from edim_dde_ai.recommendations import (
    configure_recommendation_store_from_env,
    get_recommendation_store,
    set_recommendation_store,
)
from edim_dde_ai.retrieval import (
    configure_retrieval_from_env,
    get_retrieval_provider,
    set_retrieval_provider,
)
from edim_dde_ai.evaluation import (
    evaluate,
    get_evaluator,
    register_evaluator,
)
from edim_dde_ai.web import (
    configure_web_search_from_env,
    get_web_search_provider,
    set_web_search_provider,
)
from edim_dde_ai.registry.agents import (
    create_agent,
    get_agent_definition,
    list_agents,
    register_agent,
)
from edim_dde_ai.registry.nodes import register_node
from edim_dde_ai.version import __version__
from edim_dde_ai.hitl import resume_hitl_session

# Register builtin node types on import
from edim_dde_ai import nodes as _nodes  # noqa: F401

__all__ = [
    "__version__",
    "register_node",
    "register_from_yaml",
    "register_from_directory",
    "register_from_paths",
    "register_from_dict",
    "register_from_dicts",
    "register_from_json",
    "register_agent",
    "create_agent",
    "list_agents",
    "get_agent_definition",
    "Skill",
    "DirectoryContentProvider",
    "set_prompt_provider",
    "set_skill_provider",
    "set_llm_provider",
    "get_prompt_provider",
    "get_skill_provider",
    "get_llm_provider",
    "register_skill",
    "clear_content_providers",
    "set_observability_provider",
    "get_observability_provider",
    "configure_observability_from_env",
    "set_state_store",
    "get_state_store",
    "configure_state_store_from_env",
    "sync_registered_agents_to_store",
    "set_recommendation_store",
    "get_recommendation_store",
    "configure_recommendation_store_from_env",
    "set_retrieval_provider",
    "get_retrieval_provider",
    "configure_retrieval_from_env",
    "register_evaluator",
    "get_evaluator",
    "evaluate",
    "set_web_search_provider",
    "get_web_search_provider",
    "configure_web_search_from_env",
    "resume_hitl_session",
]
