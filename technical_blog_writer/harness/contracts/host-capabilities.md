# Host capability contract

The shared workflow runs inside a core coding harness, not inside a nested model or agent. Host adapters translate tool access and instruction loading; they must not duplicate or weaken the workflow, approvals, privacy, source selection, load limits or exit behavior. Follow the host's higher-priority instructions and permission system. Never request unsafe permission overrides to satisfy this contract.

## Startup protocol

Apply the blog workflow only when asked to start/resume/continue a blog. Loading an instruction file while editing this repository is not authorization to start a blog or query sources.

1. Read `AGENTS.md`, `harness/README.md`, the manifest, this contract and the **current host's** adapter. Do not load every host adapter as active instructions. Use the real host/session context or its entrypoint, not the model provider, to identify the host. For example, a Claude model running inside OpenCode uses the OpenCode adapter. If uncertain, ask once or use `harness/adapters/generic.md`; never assume Codex.
2. Resolve the harness installation (where scripts and policies live) separately from the project workspace (where `project.json`, `input/blog.json`, `outputs/decisions.md` and other `outputs/` artifacts live). By default they are the same folder. Confirm any separate workspace before writing; pass `--root` explicitly to every runtime command when they differ. Do not change the helper defaults based on the host or current shell directory.
3. Optional local check: `python3 /absolute/harness/scripts/host.py --host HOST_ID --root /absolute/workspace`. It reads local metadata/state only. It does **not** prove the host loaded instructions, has tools, authenticated MCPs, or can export PDFs. Do not interpret its `local-ready` result as remote readiness.
4. A short blog request naming a brief is sufficient; never require a pasted workflow checklist. Automatically read the installation's `input/README.md` and `harness/policies/input.md`, then run `blog.py --root WORKSPACE startup [--input PATH]`. For a new run this validates/prefills the named/default brief; for an existing run it uses saved state/latest decisions without reopening or reapplying input. Read status and ask only for missing/conflicting preferences and actual human approvals. Titles are automatically suggested/selected in PREPARE. Check collection status before remote work. Startup/status never clear stopped state or authorize resume.
5. Verify the following capabilities using actual host tools. If a mandatory local capability is missing or permission denied, explain the limitation and pause; do not invent tool success or bypass permission controls. Missing selected remote MCPs use the existing proceed/exit policy, not a new host-specific behavior.

## Required local capabilities

| Capability | Acceptable host mapping | If unavailable |
| --- | --- | --- |
| Read files | read/open-file tool or permitted shell file read | Ask the user to enable workspace access; pause |
| Write files | edit/write/apply-patch or permitted shell tooling | Request scoped workspace write permission; pause if denied |
| Execute Python 3.10+ | shell/terminal/command tool, with the correct Python environment | Ask for execution access or provide commands for the user; do not claim execution |
| Interactive review | native question tool **or an ordinary chat message followed by waiting for the next user turn** | Pause rather than choose an answer automatically |
| Persistent state | local project files, source catalog, queue, approval hashes and decisions | Do not substitute conversation memory or ephemeral agent tasks |

Use whichever local tools actually exist. Shared policies do not require tools literally named `read`, `bash`, `ask_user`, or `list_mcp_resources`. If the host only allows user-run commands, wait for real command results before continuing; never invent local artifacts. Keep credentials out of terminal output and local metadata.

## Selected remote capabilities

- Each host supplies its **own** MCP registration, enabled tools, credentials and per-tool permissions. Do not assume another host's MCP config or authentication is inherited. Never automatically copy credential files or alter a user's global MCP/security settings.
- Discover the current tool inventory/resource listing using facilities available in this host. If discovery is unsupported, ask which connections are enabled and test only the selected capabilities with authorized, paced probes. An absent discovery API is not proof every connector is missing.
- Map user-facing source labels to the actual server/tool capabilities in `outputs/decisions.md`; read, search, children, attachments, create and readback may be separate tools. Do not invent tool names or universal connector semantics.
- Use `collection.py` request permits for each actual remote operation. Selected-source MCP warnings, explicit proceed/exit, Retry-After/backoff and recursive scope limits are identical on every host.
- Editorial planning and review are host-neutral too: infer the blueprint, fill the internal packet, run sequential evidence/technical/editorial passes and `scripts/editorial.py check` before presenting content. No additional MCP/model/agent is required; never auto-attest reviews, execute stored examples or add required intake fields. Respect new/opted-in quality gates and preserve legacy state. See `harness/policies/quality.md`.
- Keep a single orchestrator/writer. Do not spawn subagents, background crawlers or parallel host sessions against the same workspace. Switching hosts is allowed only after the prior host has stopped and any in-flight request/lock is reconciled, without resetting counters.
- A host tool approval, "always allow", plan-mode approval, or model response is **not** user satisfaction with prose, source-selection consent, permission to publish, or acceptance of quality degradation. Ask for each workflow decision explicitly.
- Browser/image tools are optional. Use local SVGs and permitted Markdown/Playwright tooling; ask before installations. No browser means no assertion that visual inspection happened. Git hooks are optional local safeguards, not an MCP interception layer.

## Handoff and portability limits

All hosts read/write the same artifact formats; no host-specific project-state migration is needed. Recheck selected MCP access in the new host, while honoring accepted skips for an unchanged source plan. Stop means end the current blog workflow, never kill the user's host application/shell.

Adapters and local tests provide instruction-level integration, not certification against every host version. Host instruction precedence, MCP discovery/config syntax, sandbox modes and permissions evolve. Consult the installed host's documentation/settings when enabling connections. For strict enforcement of every remote call, use a separately reviewed MCP gateway or host-specific interception hooks; these adapters cannot intercept direct tool calls made outside the controller.
