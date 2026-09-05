# EDIM DDE AI — GitHub Copilot instructions

> **Team source of truth for VS Code + GitHub Copilot.**  
> Keep the shared “EDIM DDE practices” section aligned with sibling repos `edim-dde-domain` and `edim-dde-api`.  
> Deep design lives in package docs / MkDocs — keep this file short and actionable.

This package is the **YAML-composed / Python-implemented LangGraph agents framework** (runtime wheel). API hosts and product agents are out of scope here.

---

## Shared EDIM DDE practices (keep aligned across repos)

### Separation of concerns

- Prefer **config-driven composition** (YAML + registered string ids) over hard-coded graphs.
- Put **swappable backends** behind Strategy protocols + registries (LLM, retrieval, recommendation store, state store, web search, observability).
- **Fail soft** for secondary lanes (history, retrieval, web): empty/`None` is OK; do not fail the primary request.
- Do not invent citations, IDs, or evidence that was not supplied.

### Design patterns (prefer these GoF-style habits)

| Prefer | Use for |
|--------|---------|
| Registry | Catalogs keyed by string id (`register_*` / `get_*`) |
| Strategy | Swappable providers (retrieval, store, web, LLM) |
| Factory | `(config) -> callable` node factories |
| Builder | Graph assembly (`build_graph` / `build_session_graph`) |
| Facade | Stable public `__all__` / package exports |
| Null Object | `none` / noop providers for disabled planes |
| Decorator | HITL `skip_until_resume` around flat nodes |

Flat `AgentState` only — do not reintroduce nested LangGraph `data` bag adapters.

Avoid DI containers, Observer sprawl, and Abstract Factory unless there is a clear multi-runtime need.

### Code quality

- **DRY**: share helpers; do not copy provider/store boilerplate — extend the registry pattern.
- **Docstrings**: every module gets a Business purpose / Public API header; public functions/classes get Args/Returns (Examples when non-obvious).
- **Inline comments**: only for non-obvious business rules (acceptance gates, allowlists, fail-open paths) — not for obvious code.
- Match existing naming, typing, and error types (`errors.py`) in this package.

### Testing & validation

- Unit-test registries, transforms, validators, and providers with in-memory / null backends.
- Prefer deterministic stubs over live network in CI.
- **Dry** = stubs / evidence overrides / memory stores. **Live** = real Foundry / Databricks / Azure — only when credentials and a real target exist; never block product paths on optional live checks.
- When changing behavior, add or update tests next to the change.

### Documentation

- User/engineer guides belong in docs (or consuming domain docs), not only in chat.
- Code comments explain *why*; docs explain *how the system fits together*.

---

## This package (`edim-dde-ai`) — boundaries

### Hybrid model (non-negotiable)

| Layer | Responsibility |
|-------|----------------|
| YAML / dict / JSON | Topology + node config (`agent_id`, nodes, edges, routers) |
| Python registries | Node factories, routers, chain invokers behind allowlisted string ids |

- YAML **never** carries import paths, class names, or executable code.
- Extend with `@register_node` / `register_router` / `register_chain_invoker`, then reference ids in YAML.

### Extension points

```python
from edim_dde_ai import register_node

@register_node("my_type")
def my_type(config):
    def _node(state: dict) -> dict:
        return {"ok": True}
    return _node
```

- Nodes: factory `(config) -> (state) -> partial_state`
- Routers: `(state) -> str` label matched in conditional edge mapping
- Chains: `(state, config) -> Any` for `llm_chain`

### Platform seams (reuse; do not reinvent)

- **RetrievalProvider** + corpora — runbooks / knowledge / experience cards
- **RecommendationStore** + lifecycle statuses — product persistence
- **ExperienceTransform** + indexing wrapper — store writes → experience corpus
- **WebSearchProvider** — opt-in bounded public web (`EDIM_WEB_SEARCH`)
- **Evaluation** registry — deterministic quality rubrics

### When adding features

1. Prefer config-driven composition over new hard-coded graphs.
2. Parse/validate at the boundary (`core/definition.py`); keep definitions frozen.
3. Resolve unknown type/router ids early at validate/build — not only at invoke.
4. Public exports go through `__init__.py` `__all__` deliberately.
5. Do not introduce dynamic imports from config strings.
