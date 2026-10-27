# Codex adapter

Entrypoint: `AGENTS.md`. Follow `harness/contracts/host-capabilities.md` and the shared manifest/workflow; this file only maps the host.

- Open this repository/workspace in Codex and verify the effective project instructions include `AGENTS.md`. Parent or nested instructions and sandbox restrictions still apply; do not bypass them.
- Use Codex's available file/patch and shell/command tools for local helpers. Tool names vary by integration. If in plan/read-only mode, request scoped execution/write permission before running mutations.
- Discover selected MCP capabilities from Codex's actual available tool inventory/discovery facilities; some tools may be deferred until discovered. If no discovery facility exists, ask which selected connectors are enabled. Do not invent discovery methods.
- Configure/authenticate the user's chosen connectors through Codex's own settings/login flow. No connector configuration is bundled here.
- Use a native question tool if available; otherwise ask in chat and wait. Source/tool approvals are distinct from editorial and publication approvals.
- Start locally with `python3 scripts/host.py --host codex`, then the built-in `python3 scripts/blog.py startup` routing and status when installation and workspace are this folder. The user only needs to name the input file, not repeat input validation, resume or title-selection instructions. For another workspace, use absolute script paths and explicit `--root` as specified by the capability contract.
