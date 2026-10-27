# Cursor adapter

Entrypoint: `.cursor/rules/technical-blog.mdc` (project rule). Follow `harness/contracts/host-capabilities.md` and read shared `AGENTS.md`; the rule applies the blog workflow only to blog start/resume/continue requests, not unrelated coding edits.

- Open the folder in Cursor with project rules enabled and verify the rule is included. If rules are disabled/not supported by the current mode, explicitly read `AGENTS.md` and this adapter in Agent chat.
- Use Agent's available file tools and terminal to execute Python helpers. An ask-only/read-only mode cannot perform mutations; request a permitted mode and scoped approvals instead of fabricating writes.
- Enable/authenticate selected MCP servers in Cursor's own settings. Tool approval/discovery behavior depends on the installed version. Inspect available tools; do not assume other hosts' MCP settings are inherited.
- Ask workflow questions in Agent chat and wait if no structured question tool exists. Automatic tool execution settings are never approval of editorial content or remote publication.
- Do not open parallel agents/background tasks on this workspace or bypass source limits through built-in web tools. Keep outputs excluded from Git; editor indexing settings are not Git protection.
- Local check through the terminal: `python3 scripts/host.py --host cursor`; then follow the capability contract's workspace/startup protocol.
