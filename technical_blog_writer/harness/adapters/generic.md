# Generic core-harness adapter

Entrypoint: explicit user prompt to read `AGENTS.md`, this adapter, and `harness/contracts/host-capabilities.md`. This is the fallback for other coding hosts or uncertain instruction-loading behavior; it is not a claim of native integration with every agent product.

- Ask which core harness and workspace are active if ambiguous. The model name is not the host identity. Use an available native instruction-file mechanism if known; otherwise explicitly read the shared files. Never assume files are auto-loaded.
- Map the actual host's file-read/write, command execution and interaction facilities to the capability contract. Request scoped permissions if missing; pause rather than invent capabilities.
- Discover selected source tools from the real tool inventory, or ask how the host exposes MCP connections. Configure/authenticate through that host's own supported flow, not copied credential files from another product.
- If no question API exists, ordinary chat followed by waiting for the next user turn is sufficient. A batch-only/noninteractive host must pause at every human gate; no automatic answers.
- Keep one orchestrator and the same saved project/collection state. All scope, consent, provenance, source-load, Git protection and remote-write rules remain unchanged.
- Local check: `python3 scripts/host.py --host generic`; then run the shared startup/status protocol. The check only validates local adapter files/metadata, not real host permissions or MCP readiness.
