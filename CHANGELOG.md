## Unreleased

### Added
- **Pluggable public-web search** (`web/`): provider Strategy + registry,
  `none`/`memory`/host-managed `http_json` adapters, and bounded opt-in
  `web.search` graph node with domain allowlisting and non-fatal fallback
- **Evaluation framework seam** (`evaluation/`): `Evaluator` Strategy,
  `EvaluationResult` (quality score vs evidence-based confidence), registry and
  `evaluate(...)` facade for deterministic or future model-based rubrics
- **Experience index** (`experiences/`): `ExperienceDocument`, `ExperienceTransform` registry, `ExperienceIndexingStore` proxy on RecommendationStore writes, `maybe_index_experience`, retrieve-time `dedupe_retrieval_hits` (collapsed duplicates counted via `metadata.occurrences` / `also_job_ids`); `search_corpus(..., dedupe=True)` default
- `ExperienceDocument.feature_labels` replaces scenario-specific
  `situation_labels`; deserialization still accepts the legacy field for replay
- **Pluggable RecommendationStore** (`recommendations/`): `none` · `memory` · `postgres` · `cosmos` · `redis`; `configure_recommendation_store_from_env` / `EDIM_RECOMMENDATION_STORE` (default inherits `EDIM_STATE_STORE`)
- Shared `store/connection_env.py` for Postgres/Cosmos/Redis DSN resolution (StateStore + RecommendationStore)

## 1.0.0 — 2026-07-31 (Release 1)

### Added
- Canonical agent JSON Schema (`schemas/agent.schema.json`) and extended-block validation (`schema` package)
- Builtin `invoke_agent` node (nested agent call with depth limit + self-call guard)
- **Pluggable observability providers** (`ObservabilityProvider`): `none` · `langsmith` · `mlflow`; `configure_observability_from_env` / `EDIM_OBSERVABILITY`
- LangSmith/LangChain run config helpers; `MetadataAgent` merges provider config on invoke
- Optional extras: `[observability]`, `[mlflow]`, `[schema]`, `[postgres]`, `[cosmos]`, `[redis]`
- Example agents: `invoke_agent_parent` / `invoke_agent_child`
- **Pluggable control-plane StateStore** (`store/`): `memory` · `postgres` · `cosmos` · `redis`; `configure_state_store_from_env` / `sync_registered_agents_to_store`
- **Pluggable RetrievalProvider** (`retrieval/`): `none` · `memory` · `faiss` · `azure_ai_search` · `databricks_vector`; builtin `rag.retrieve`; corpus registry
- Optional extras: `[postgres]`, `[cosmos]`, `[redis]`, `[faiss]`, `[azure-search]`, `[databricks-vector]`, `[retrieval]`

### Notes
- **Tag + changelog only** for this release — publishing wheels to an internal index (Artifactory/etc.) remains an ops step when you are ready; no publish was performed as part of R1.
- Azure DevOps / Git remains source of truth for `*.agent.yaml`; StateStore holds catalog metadata, sessions, and audit.
- Similarity search ≠ RAG: providers retrieve hits; agent graphs compose RAG (retrieve → prompt → LLM).
