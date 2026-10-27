# OpenCode adapter

Entrypoint: `AGENTS.md`. Follow `harness/contracts/host-capabilities.md` and the shared workflow. A model from Anthropic/OpenAI/etc. running in OpenCode still uses this adapter, not the model provider's adapter.

- Open the repository in OpenCode and verify its effective project instructions include `AGENTS.md`. If instruction auto-loading is disabled or differs in your version, explicitly request that file and this adapter in the startup prompt.
- Use the current agent's available read/edit/write and shell tools. If the active mode/agent lacks editing or execution, ask to switch to an appropriately permitted mode; do not work around restrictions.
- Register/enable/authenticate selected MCP connections using OpenCode's own configuration and UI/CLI for the installed version. Server names, tool exposure and OAuth support depend on that version/connector; no universal MCP config file is supplied by this repository.
- Discover tools from the actual session inventory/resource facilities. Tool names need not match Codex or Claude Code; document selected source-to-tool mappings without changing shared policies.
- Ask using OpenCode's question tool if available, otherwise chat and wait. Keep one orchestrator; do not use subagents/parallel sessions for collection.
- Local check: `python3 scripts/host.py --host opencode`; then follow the capability contract's workspace/startup protocol.
