# Core-harness adapters

One shared workflow, thin host-specific entrypoints. Read `harness/contracts/host-capabilities.md` for the common startup/permission contract. `harness/manifest.json` registers each host's entrypoint and adapter. The host name identifies the core application, not the model provider.

| Host ID | Native entrypoint | Activation/fallback |
| --- | --- | --- |
| `codex` | `AGENTS.md` | Project instructions; explicitly read `harness/adapters/codex.md` |
| `claude-code` | `CLAUDE.md` | Imports `AGENTS.md` and its adapter; explicit file reads if imports are unavailable |
| `opencode` | `AGENTS.md` | Project instructions; explicitly read `harness/adapters/opencode.md` |
| `gemini-cli` | `GEMINI.md` | Project context directs reads of shared rules and its adapter |
| `cursor` | `.cursor/rules/technical-blog.mdc` | Project rule enabled; otherwise explicitly attach/read shared rules and adapter |
| `copilot` | `.github/copilot-instructions.md` | Repository instructions in an interactive tool-capable surface; otherwise explicit read |
| `generic` | explicit prompt | Read `AGENTS.md` plus `harness/adapters/generic.md` |

No host configuration or credential files are installed automatically. Existing higher-priority instructions, trust settings and tool permissions still apply. When embedding into an existing project, merge/review entrypoint instructions rather than replacing unrelated project rules. Check effective instruction loading in the installed host version; a file being present is not proof it loaded.

## Shared startup prompt

> Start a technical blog using input/blog.json.

Later: **“Resume the blog workflow.”** Instruction loading, input-guide reading/validation, missing-field-only intake, approval gates, saved-state precedence and PREPARE title suggestions are automatic host-neutral responsibilities. They must not depend on the user repeating them. A generic host without native instruction loading may need the prefix **“Follow AGENTS.md with harness/adapters/generic.md.”** once to load the harness.

If installation and workspace differ, explicitly load the installation's instruction files, name the project workspace, and keep the brief path relative to that workspace (or supply its absolute path). Run every helper with absolute installation paths and `--root WORKSPACE`. `scripts/host.py --host ID --root WORKSPACE` prints the read-only bootstrap and status commands without executing them. A generic host may require instructions to be attached explicitly every session.

## Per-host manual smoke checklist

Local regression tests cannot launch every commercial/core harness or prove its real MCP permissions. Before calling an installed host/version operational, run this checklist in a **fresh test workspace**, not by resetting a real article's state. Record host/version and results locally, without tokens/private source contents.

1. **Instruction loading:** ask which entrypoint and adapter it is using. It should identify the host application correctly, reference shared policies and not automatically start collection when only editing code.
2. **Local tools/root:** use the short startup prompt without a workflow checklist. Verify the agent loads the input guide and uses read-only `blog.py startup` routing before status/intake. Run the local adapter check and status. Confirm the intended workspace, Python 3.10+, and actual read/write/command access. The check must not initialize a project, call MCP or claim remote readiness. If a permission is denied, it should pause and ask for scoped access.
3. **Input/source selection:** supply a test input with word count, single/series framing, sources/links and navigation. Verify known preferences are not re-asked, only missing/conflicting values and required approvals; the sample is never auto-applied. Verify decisions/snapshot are under `outputs/`, not the harness root. Otherwise select a manual source or one test connector. Verify no missing-Google/Slack/Confluence warnings for unselected services. A manual-only plan needs no MCP. Give a custom source name and confirm it is accepted.
4. **Questions:** verify the host asks and waits. Native structured questions are optional; chat with the next user turn is sufficient. No fabricated consent in plan mode, batch execution or unattended coding tasks.
5. **Missing selected connector:** use a deliberately unavailable test source. Confirm the quality warning and proceed/exit choice. Choose exit: no further collection/writes beyond saved stop/decision; stage stays unchanged. Resume explicitly; choose proceed and verify the selected failure is skipped without retries/prompts.
6. **Bounded recursion/load:** approve narrow test roots and small limits. Verify the agent uses `collection.py` before each remote call, follows only allowed children/links, skips cycles and respects WAIT, Retry-After, low-value/depth/item/request/time stops. Do not deliberately overload a production source to test throttling; use the local regression suite/mocks.
7. **Article quality/titles/review/publishing:** verify blueprint selection and thesis/coverage/word-budget planning are internal agent work with no added mandatory input questionnaire. Check that measurement/reproducibility/figure records are evidence-grounded, example commands are not executed automatically, and sequential reviews plus fresh local reports precede presentation/approval. A passing report is not proof of truth. New/opted-in gates must reject stale reports; legacy saved runs must not be rewritten or retroactively blocked. Verify no title preferences/research notes are demanded in input. DRAFT/REVISE use provisional headings; after body approval, PREPARE suggests 3–7 headlines and waits for explicit selection/edit/custom-title choice. A selected H1 is applied only during packaging; the approved body hash stays unchanged. Verify draft selection, missing word-count preferences, repeated feedback and specific-revision satisfaction are real questions. Cloud writes require separate destination/upload consent. A missing destination cannot produce a fabricated document.
8. **Resume/handoff:** stop the first host before opening another on the same workspace. Confirm counters/approvals/frontier/accepted skips persist, selected MCP access is checked in the new host, and nothing is silently reinitialized.
9. **Git:** verify outputs remain ignored and the configured guard rejects a force-staged test artifact. Do not test against private real evidence or disable an existing repository hook.

Adapters must not claim live validation based solely on `host.py` or unit tests. If a host cannot honor interactive gates or local persistence, use a different capable surface or pause with an honest limitation. Strict network-level enforcement requires a separate reviewed gateway/interceptor; these files do not provide one.
