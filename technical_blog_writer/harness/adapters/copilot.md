# GitHub Copilot adapter

Entrypoint: `.github/copilot-instructions.md`. Follow `harness/contracts/host-capabilities.md`, shared `AGENTS.md`, and the manifest/workflow. Instruction loading and tool availability differ between Copilot surfaces; this adapter requires an interactive agent surface with local workspace and command access.

- Confirm repository instructions are enabled and included. For a surface that does not load this file, explicitly read `AGENTS.md` and this adapter before starting.
- Map local reads/writes and Python helpers to available workspace and terminal tools. If the current Copilot surface cannot execute commands or modify files, ask for a capable interactive agent environment or user-run command results; do not claim execution.
- Configure only selected MCP servers through the active Copilot surface's settings. Do not assume IDE MCP connections are present in a remote/cloud coding agent, or vice versa.
- This workflow requires ongoing human feedback. If the surface is unattended/PR-only and cannot wait for responses, pause at user gates and request an interactive session; never synthesize choices or publish without approval.
- Do not allow an automatic commit/PR workflow to include `outputs/`. Honor Git ignore/guard instructions even if the host normally stages generated changes.
- Local check: `python3 scripts/host.py --host copilot`; then follow the capability contract's workspace/startup protocol.
