# Claude Code adapter

Entrypoint: `CLAUDE.md`, which imports the shared `AGENTS.md` and this adapter. Follow `harness/contracts/host-capabilities.md`; do not duplicate workflow rules here.

- Open the project in Claude Code and confirm the effective memory/instructions include this repository's `CLAUDE.md`. If file imports are unavailable in the installed version, explicitly read `AGENTS.md` and this adapter before starting.
- Map local reads/edits and Python helpers to the available Claude Code file and shell tools. Respect workspace trust, permission prompts and plan-mode restrictions; request scoped write/execution permission rather than bypassing them.
- Inspect the current session's MCP tool inventory/status using Claude Code's available interface. Register and authenticate selected connectors in Claude Code, not in Codex/OpenCode configuration. Do not assume a server's status or tool-name prefix from another host.
- Ask questions with the host's question facility if present, otherwise ordinary chat and wait. Never use autonomous execution or a tool-permission approval as consent to proceed past a user gate.
- Do not delegate research to parallel subagents or background tasks: use one writer and the shared request controller. Compaction/resume must reload on-disk state, not rerun intake or reset collection counters.
- Local check: `python3 scripts/host.py --host claude-code`; then follow the capability contract's workspace/startup protocol.
