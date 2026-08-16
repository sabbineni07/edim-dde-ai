---
description: Python conventions for edim-dde-ai framework code
applyTo: "**/*.py"
---

# Python in edim-dde-ai

- New catalogs → generic `Registry[T]` (Strategy), not ad-hoc module-level dicts without clear/get/set.
- Graph assembly changes → `GraphBuilder` steps, not one-off compile scripts.
- LangGraph state wrapping stays in `graph/adapters.py`.
- Public exports go through `__init__.py` `__all__` deliberately.
- Prefer typed errors from `errors.py` over bare `ValueError` for user-facing failures.
- Do not introduce dynamic imports from config strings.
- Providers must be safe with Null Object defaults (`none`) for local/dev.
- Module docstring: Business purpose + Public API. Public methods: Args / Returns.
