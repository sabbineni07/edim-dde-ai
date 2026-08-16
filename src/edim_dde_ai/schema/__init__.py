"""Schema package — agent definition contract helpers.

Business purpose:
  Validate optional R1 contract blocks (metadata, model, security, evaluation,
  hitl, rag) beyond structural graph validation in ``core.definition``.

Public API:
  - ``schema_path()`` — path to ``schemas/agent.schema.json``
  - ``validate_extended_blocks(data)``
  - ``validate_agent_dict(data, *, use_jsonschema=False)``
"""

from edim_dde_ai.schema.validate import schema_path, validate_agent_dict, validate_extended_blocks

__all__ = ["schema_path", "validate_agent_dict", "validate_extended_blocks"]
