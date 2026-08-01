# Changelog — edim-dde-ai

## 1.0.0 — 2026-07-31 (Release 1 / Phase 0)

### Added
- Canonical agent JSON Schema (`schemas/agent.schema.json`) and extended-block validation (`schema` package)
- Builtin `invoke_agent` node (nested agent call with depth limit + self-call guard)
- LangSmith/LangChain run config helpers (`observability` package); `MetadataAgent` merges tags/metadata on invoke
- Optional extras: `[observability]`, `[schema]`
- Example agents: `invoke_agent_parent` / `invoke_agent_child`

### Notes
- **Tag + changelog only** for this release — publishing wheels to an internal index (Artifactory/etc.) remains an ops step when you are ready; no publish was performed as part of Phase 0.
