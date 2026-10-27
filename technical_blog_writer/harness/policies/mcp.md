# MCP readiness and degraded-mode consent

This policy applies at startup, on resume, before a stage needs a new MCP capability, and when a previously working connector fails. The current core harness supplies MCP access; the local helper cannot discover tools, authenticate accounts, or verify remote access itself.

## Determine what is required

First read `harness/policies/sources.md`, use the input-supplied choices or present its menu only for missing choices, and save the user's confirmed `source_plan` before any readiness warning. Required means only MCP capabilities for their explicitly selected MCP research sources and separately selected cloud publication destinations. SharePoint, Office, Teams, Webex and custom systems are first-class choices; Google/Slack/Atlassian are not defaults. Never warn about an unselected service, unused capability, or a manual/file/paste source. Do not add Google Docs just because the original workflow included that deliverable. If no MCP-backed source or cloud destination is selected, skip MCP readiness checks entirely and proceed with manual/local evidence.

Check only capabilities actually needed for the selected source/scope. Map user-facing labels to discovered MCP tools in `outputs/decisions.md`; one MCP may serve multiple selected sources. Warn using selected source labels, and pass those same labels to `mcp-decision --connector`. A selected Google Docs research source does not automatically select cloud document creation, and a cloud destination does not authorize reading unrelated documents. Actual upload always requires separate user permission.

Follow `harness/policies/collection.md` for all remote calls, including readiness probes. Configure pacing and request budgets after source selection/navigation consent and before probes; probing does not bypass the limiter. Missing-tool discovery itself need not contact the service. Discover tools and check access using the least invasive authorized read/status probe available. A listed tool is not proof of authentication. If discovery/probing is unavailable, report access as unverified, not authenticated. Never ask users to paste passwords, tokens or authentication cookies into chat or files. Direct them to their current host's connector configuration/login flow.

## Throttling and temporary failures

A 429/503/timeout is not proof of missing authentication. Honor the provider's Retry-After value, apply the bounded backoff/circuit rules in `harness/policies/collection.md`, and continue independent available work or pause without polling. If the retry budget is exhausted, apply the proceed/exit warning for this selected capability once; never turn it into an infinite retry loop. A 401/403 or missing tool goes directly to the access gate below without authentication retries.

## Missing, unauthenticated or failing required MCP

Only for currently selected MCP-backed sources/destinations, treat a missing server/tool/capability, expired login, 401/403, unavailable service, or inability to verify required access as a readiness issue. Distinguish connector-wide failure from a document-specific permission problem. Batch currently known issues into a single prompt. Do not repeatedly call a known-failing connector while waiting for an answer.

Show a short table: connector, required capability, observed problem (sanitized; no secrets), and affected source coverage/deliverable. Then ask exactly this decision in natural language:

> These required MCP connections are missing, unauthenticated, or unavailable: [list]. If you proceed without them, we may miss important context and technical details, so you may not get the best result. [Name any blocked deliverable, such as Google Docs.] Would you like to **proceed without these connections**, or **exit now** so you can configure/authenticate them first?

Wait for an explicit choice. Ambiguous answers require clarification; silence is not consent. If the user wants to fix access now, pause work and recheck only after they say it is ready, then ask again only for remaining issues. No automatic login/retry/prompt loop.

### If the user says proceed

- Record the exact unavailable connectors, capability, sanitized reason, user decision, stage, and time. Use `blog.py mcp-decision --connector ... --capability ... --reason ... --decision proceed --user-confirmed` (repeat `--connector` for a batch with the same capability/reason). Also summarize the decision in `outputs/decisions.md` and source-coverage logs where relevant.
- Skip the affected connector/capability for this workflow, including on resume. Ignore its expected access/authentication errors as **nonfatal**: do not retry it, repeatedly prompt about it, or let its failure stop available work. Persist and disclose the limitation; do not hide errors or label failed reads as empty results.
- Continue with available authorized MCPs and local/user-provided evidence. Do not bypass permissions, broaden scope, invent missing facts, or substitute a different service without approval.
- Carry material coverage gaps into the research brief, evidence map, revision notes, and final verification/handoff. If every research source is unavailable, ask for local files/pasted evidence or a narrower topic; do not fabricate evidence or waive the minimum evidence requirement.
- A new failure for a currently selected MCP source/destination and needed capability, not covered by the prior decision, requires a new prompt. Do not prompt for removed or unselected integrations. Never suppress unrelated filesystem, export, security, correctness, or validation errors. Only retry a skipped connection after the user explicitly asks to re-enable/check it; record the new access result in `outputs/decisions.md`.
- Proceeding without Google Docs access allows remaining local work, but does **not** authorize fake `.gdoc` files or a claim that all four formats were delivered. Hand off actual local files and report the cloud deliverable as blocked; remain incomplete in PREPARE.

### If the user says exit / declines to proceed

- Run the same `mcp-decision` command with `--decision exit --user-confirmed`. It records the issue and stops workflow mutations without advancing the current stage.
- Save a brief explanation in `outputs/decisions.md`, tell the user what to configure/authenticate, confirm progress is preserved, and **end the workflow immediately**. No further collection, drafting, publishing, background retries, or repeated question loop in that run. Do not terminate the user's core-harness application or shell.
- On a later explicit user request to resume, run `blog.py resume --user-confirmed`, rediscover/recheck unresolved access only for the confirmed current selection, and apply this gate again. Previously accepted skips remain in effect unless the user requests a recheck.

The CLI records agent attestations, not real MCP probe results or user authentication. The agent must actually perform discovery, communicate the warning, and obtain consent before recording a decision.
