# GitHub Copilot / VS Code guidance (edim-dde-ai)

This folder is the **team source of truth** for engineers using **VS Code + GitHub Copilot** (not Cursor-specific).

| Path | Purpose |
|------|---------|
| [`copilot-instructions.md`](./copilot-instructions.md) | Always-on repo instructions for Copilot Chat |
| [`instructions/`](./instructions/) | Path-scoped rules (`applyTo` globs) |
| [`prompts/`](./prompts/) | Reusable chat prompts — type `/` in Copilot Chat |

Sibling EDIM packages (`edim-dde-domain`, `edim-dde-api`) have the same layout; keep the shared practices section aligned when you edit it.

Optional Cursor rules under `.cursor/rules/` are for Cursor users only and should not diverge from these files.
