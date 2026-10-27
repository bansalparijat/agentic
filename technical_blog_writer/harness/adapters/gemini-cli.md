# Gemini CLI adapter

Entrypoint: `GEMINI.md`, which directs the agent to read `AGENTS.md` and this adapter. Follow `harness/contracts/host-capabilities.md`; Gemini-specific tools are only a transport for the shared workflow.

- Open the workspace in Gemini CLI and verify project context includes `GEMINI.md`. If not, explicitly attach/read the entrypoint and shared files in the initial prompt.
- Use the available file-edit/read and shell tools for local helpers. Respect trust, sandbox, approval and execution restrictions; ask for scoped access when necessary.
- Configure selected MCP servers/authentication through Gemini CLI's installed-version settings. Use its exposed tool inventory/discovery capabilities; do not assume Codex's configuration or tool names.
- If a native structured question mechanism is absent, ask in ordinary chat and stop for a reply. Do not rely on a noninteractive invocation to collect consent; pause and request an interactive session instead.
- Use the collection request controller even if a built-in web-fetch/search tool could reach the source directly. It is still a remote operation subject to scope and load policy.
- Local check: `python3 scripts/host.py --host gemini-cli`; then follow the capability contract's workspace/startup protocol.
