---
name: add-unit-tests
description: Add unit tests using memory/null backends for framework changes
agent: agent
argument-hint: What behavior or module to cover
---

# Add unit tests (edim-dde-ai)

- Prefer Memory / Null providers over live Azure/Databricks/network
- Follow existing tests under `tests/`
- Clear registries between tests when globals are involved
- Cover happy path + unknown id / validation errors + fail-soft empty results
- Keep tests deterministic

Do not add credentials or hit real cloud endpoints in CI tests.
