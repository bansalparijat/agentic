# Session context: technical-blog meta harness

## Scope and how to use this file

This is the **complete engineering handoff of the visible session**, organized by requirement, implementation and current contract rather than as a verbatim chat/tool transcript. It includes every user-requested harness change and the important choices that were superseded. It deliberately excludes hidden model reasoning, raw tool logs, credentials, private research contents and original internal source URLs/IDs. Those are not needed to improve the harness and must not be copied into tracked documentation.

Read `developer/README.md` first. Loading this context means **harness development**, not permission to rerun the conversation, initialize/resume a blog, collect sources or implement every suggested extension. Current code/policies and the user's latest requirement take precedence over historical descriptions below. Verify the implementation before changing it.

## 1. Product purpose and original requirements

The user wanted a meta harness in the current folder, initially to operate **inside Codex core**, with Codex supplying MCP access. The harness itself should orchestrate a technical-blog workflow, not run another model/agent or bundle MCP servers.

Original four stages:

1. **COLLECTION**: collect topic-relevant evidence from Google Docs/Sheets, Confluence, Jira, Slack and other resources; save locally.
2. **DRAFT**: obtain a target word count and create 2–3 distinct engaging technical drafts. Use simple, digestible language without losing detail, cover important mechanisms/trade-offs, and include correct design/system/flow/deployment/architecture diagrams. Structural inspiration may come from engineering teams such as Uber, Google, Amazon and Netflix, not copied prose or invented company practices.
3. **REVISE**: ask which draft is closest, collect feedback and save immutable revised versions. Loop until the user explicitly says they are satisfied.
4. **PREPARE**: suggest title/hero visuals, loop on user selection or an explicit image skip, and prepare Markdown, HTML, PDF and an actual Google Doc plus required assets.

The original request placed only hero selection in PREPARE. A later request added headline selection; the **latest** requirement specifically places headline suggestions/selection in PREPARE, after body approval.

## 2. Chronological user requests and what changed

### A. Build the initial harness

Implemented `AGENTS.md`, detailed workflow/editorial/publication instructions, a standard-library Python state/evidence CLI, optional HTML/PDF export dependencies, Git ignore rules and isolated tests. The agent writes the actual research and prose using its host's tools; the CLI does not generate blog text or query MCP.

Key early decisions retained today:

- Durable state instead of relying on chat memory.
- Provenance catalog, evidence hashes, claim ledger, research brief and source-search log.
- Explicit human gates; no fabricated approvals, access, benchmarks, citations, diagrams or cloud artifacts.
- Google Docs is cloud-native. A local `.gdoc` is a pointer to a real verified document, not a standalone offline format.
- Original locally created SVG artwork is the default hero-image approach; provenance and publication-policy acceptance still matter.
- Optional Markdown/Chromium export must fail honestly if tooling is missing. Do not relabel HTML as PDF.

### B. Put stage outputs under one parent

The user requested all stage-specific folders beneath **`outputs/`**, including all reads of those artifacts. Code, instructions, examples, catalog paths, checksums and tests were changed; existing folders were moved safely rather than recreated.

Final stage locations:

- `outputs/data/`
- `outputs/draft/`
- `outputs/revised_draft/`
- `outputs/blog/`

Paths in CLI arguments, catalogs and manifests are workspace-relative and include `outputs/`. Markdown images remain document-relative: `assets/chart.svg` in `outputs/blog/article.md` points to `outputs/blog/assets/chart.svg`.

### C. Protect outputs from Git; handle missing/unauthenticated MCPs

The user requested that outputs never be committed and that unavailable required connections trigger an informed proceed/exit decision.

- `/outputs/` is ignored recursively.
- `.githooks/pre-commit` checks the Git index and rejects tracked/force-staged content under an `outputs/` directory. It allows index-only removal; local files need not be deleted.
- Hook activation is explicit (`git config core.hooksPath .githooks` once a repository exists); do not replace another repository's hooks configuration without review. Ignore rules do not untrack old files or remove prior history, and hooks can be bypassed outside the agent's rules.
- `mcp-decision` records the observed issue and actual user choice. **Proceed** skips those capabilities/errors without retry/prompt loops and discloses reduced coverage. **Exit** sets a stopped state, preserves progress and ends the workflow immediately.
- `resume --user-confirmed` is only for a later explicit request to continue. Stopping the workflow must not kill the host application or shell.
- Ignore only the accepted MCP access failure, not unrelated export/filesystem/security/validation errors. Missing evidence is never an excuse to invent facts or bypass minimum evidence checks.

### D. Let users select their own source ecosystem

The user pointed out that some teams use SharePoint/Office/Teams/Webex rather than Google/Slack/Confluence. Source selection became a first-class, open-ended intake step.

- Offer common source categories and an **Other/custom** option, or use choices already supplied in input.
- Support manual files/pasted evidence with no MCP requirement.
- Save selected MCP/manual source labels and separately selected cloud publication destinations.
- Warn only about capabilities actually needed by **selected** MCP-backed sources/destinations. Never demand Google, Slack or Atlassian just because the harness supports them.
- Clarify suite names when needed; Office/Graph access does not automatically prove access to all apps or data.
- `select-sources` saves the plan. `mcp-decision --connector` must use selected user-facing labels, not an arbitrary server alias; the CLI rejects unselected/manual-only warning records.
- A cloud destination does not authorize unrelated research reads or an upload. A Google research source does not automatically select Google Doc creation.

### E. Avoid overloading sources; add bounded recursive navigation

The user requested child-page and in-page-link traversal (e.g. from a Confluence page) without infinite loops, low-value crawling or source overload.

Implemented a collection policy, defaults and `scripts/collection.py`:

- Ask/confirm children, links, both or roots-only, narrow scope and load/navigation budgets. Defaults are proposals, not consent.
- Persistent breadth-first frontier, canonicalized URLs, pending/active/visited deduplication, depth/fan-out/item caps and relevance reasons for discovered links.
- Branch pruning and global low-value stops; relevance is assessed by the agent, not proved by the scheduler.
- Shared backend/account/MCP buckets, serialized remote calls, request permits, pacing, Retry-After/backoff and backend circuits.
- Atomic local controller lock plus a durable in-flight request slot. One orchestrator/writer; no parallel crawlers or multiple hosts mutating the same run.
- Preserve queue/counters/timers across resume. Never relabel discovered links as fresh roots to bypass depth, or reset state to evade a budget.
- Human approval for meaningful scope expansion or explicit, logged limit extension. Cross-service links do not automatically select another source or justify an unselected-MCP warning.

The user also asked for a more standard harness structure. The implementation uses common conventions (entrypoint, local manifest/schema, workflows, policies, stages, helpers, tests) but explicitly **does not claim a universal Codex/meta-harness specification exists**.

### F. Explain and implement multiple core-harness support

The user first asked how to support Codex, Claude, OpenCode and others, then requested implementation.

Implemented shared host-neutral instructions, thin native entrypoints/adapters, a capability contract and a read-only local host check. Core applications, not model providers, determine the adapter. A Claude model inside OpenCode uses the OpenCode adapter.

| Host ID | Entry file |
| --- | --- |
| `codex` | `AGENTS.md` |
| `claude-code` | `CLAUDE.md` (imports shared rules and its adapter) |
| `opencode` | `AGENTS.md` |
| `gemini-cli` | `GEMINI.md` |
| `cursor` | `.cursor/rules/technical-blog.mdc` |
| `copilot` | `.github/copilot-instructions.md` (interactive, tool-capable surface required) |
| `generic` | explicit prompt to read shared rules and generic adapter |

- Each host supplies its own permissions, tool inventory and MCP config/authentication. No credentials/configs are copied automatically.
- Tool names are not hardcoded. A structured question tool is optional: normal chat and waiting for the next user turn is sufficient.
- Read-only/plan-mode or batch-only limitations must cause a pause, not fabricated work or consent.
- Shared workflow rules must not be forked per host.
- `scripts/host.py --list` and `--host ID --root WORKSPACE` check local references/state without starting a run or proving remote readiness.
- A manual host smoke checklist exists; local tests are **not** live certification of third-party products or MCPs.

### G. Derive an input sample from the existing decision log; move decisions; add titles

The user requested an input file containing blog-size preferences, source choices/links, keywords, single/multipart framing and similar intake answers, to reduce prompts. They also noted the decision log belongs to a specific run rather than the reusable harness.

- Reviewed the existing log and used its **latest**, not superseded, preferences for a sanitized example: around 2,000 words, two drafts, architecture-deep, Part 1 of 3, cutoff 2025-12-31, later architectures excluded except teasers.
- Original internal source URLs/tenant/channel/repository/report IDs and prior authentication/approval claims were not copied into tracked examples.
- Moved the actual log **unchanged** from root `decisions.md` to `outputs/decisions.md`. Other private run artifacts/state were preserved.
- `migrate-decisions` performs a byte-preserving move and refuses to overwrite when both logs exist.
- Added input validation, snapshots/provenance, preference prefilling, import/apply operations and tests. Preferences never act as later approvals.
- Initially the input schema was nested and included `title_preferences`/`research.source_notes`; title selection initially occurred in DRAFT. **Those user-facing choices were explicitly superseded in the next request.**

### H. Simplify input; remove title/research-note requirements; move titles to PREPARE

The user found the input too complex and asked for a simpler format without losing information, multiple example types including single blogs, no title preferences and no expected research/source notes. They clarified that titles should be suggested by the harness in PREPARE.

Final implementation:

- Flat, optional-field JSON. No version marker required. Typical keys: `topic`, `audience`, `words`, `publication`, `sources`.
- `sources` maps a custom service name to starting-link arrays; `files` selects local manual evidence; `manual_sources` supports named exports.
- Absent `series` means a **single article**. Series uses `{part, total, roadmap}`; one run writes only the current part. Draft variants are not series parts.
- Optional goals, keywords, coverage/exclusions, questions, cutoffs, scope, notes, output/storage preferences and advanced limits/source settings retain richer information without forcing users to fill them.
- Proposed defaults fill nonessential settings; actual scope/storage/navigation confirmation remains mandatory. No default Google destination or private-storage permission.
- New input rejects `title`, `title_preferences`, `source_notes` and nested `research`; optional generic `notes` is never required.
- Flat briefs normalize to stable nested internal intake for compatibility. `outputs/input.json` preserves the **original simple brief**, while `project.json` keeps normalized preferences and input provenance. Inspection shows the simple original, not a huge expanded object.
- Legacy v1 files remain readable using a legacy schema; old title hints are discarded, not used to select a headline. Existing snapshots are not silently rewritten.
- Five samples are explicitly registered and Git-whitelisted; personal inputs remain ignored. Examples are never auto-loaded.

**Final title protocol:** DRAFT/REVISE use provisional H1s. The user approves the revised body and enters PREPARE without selecting a final headline. PREPARE suggests 3–7 titles (default 5) from that approved content and asks the user to choose/edit/provide one or request more. Options live at `outputs/blog/title-options.json`.

`titles` and `select-title` are PREPARE-only. The chosen title is bound to the approved revision hash. Explicit selection authorizes an **H1-only change in final packaging**; the pinned approved revision/body remains unchanged. This avoids reopening REVISE merely to choose the initial publication title. Later title-only changes invalidate hero/export/cloud records; substantive body/claim/diagram changes still require REVISE and fresh approval, then refreshed/reconfirmed title options.

### I. Previous request: precise README prompts and developer handoff

The user requested that README startup prompts explicitly name the input file, link to `input/README.md` for syntax/semantics, and include a developer folder with this session's context and instructions for continuing improvements.

Implemented:

- At that point, main/generic startup prompts explicitly named **workspace `input/blog.json`** but also repeated guide-reading, validation, minimal-question, resume and PREPARE title instructions. **That verbose prompt design is superseded by J below.**
- Users with a different input filename must replace the path explicitly. Existing runs resume saved state/latest decisions rather than reapplying input.
- `developer/README.md` provides a development-only continuation prompt, reading order, safe validation and update discipline.
- This file captures the full reusable engineering context without exporting private run evidence. It is not live run state or an instruction to replay previous tasks.

### J. Latest request: make workflow conventions implicit, not user-prompt boilerplate

The user correctly noted that guide-reading, input validation/prefilling, minimal questions, PREPARE title suggestions and preserving an existing run should be harness logic, not instructions the user must paste into every prompt.

Current contract:

- Normal startup prompt: **“Start a technical blog using input/blog.json.”** Normal continuation: **“Resume the blog workflow.”** A generic host may need a minimal AGENTS/adapter loading prefix, but no workflow checklist.
- Shared `AGENTS.md`, workflow, input policy and host capability contract own those behaviors unconditionally once the blog workflow is activated. The harness automatically reads the input syntax guide and policy. Merely loading instructions for a coding task still does not start a blog.
- Added read-only `blog.py startup [--input PATH]`. For new runs it validates the exact named/default file and returns original preferences/missing essentials. For existing runs it reads saved state **without opening/revalidating/replaying a newly supplied file**, even if that file is changed, invalid or missing. Stopped runs return an await-explicit-resume route and remain stopped. No input/sample/workspace/project is silently created.
- Host checks expose the same workspace-aware bootstrap command; the local manifest declares it. `inspect-input` remains independent validation, while `init` remains an explicit new-project mutation that refuses to overwrite saved state.
- PREPARE automatically suggests titles from approved content and asks the user to pick/edit/combine/provide their own or request more. Existing title-selection and hash/packaging safeguards remain unchanged.
- README/input/adapter startup prompts are shortened. Detailed semantics and responsibilities remain in the guides/policies, outside user prompts. Developer documentation records this supersession rather than telling future maintainers to restore verbose startup instructions.
- Added regression coverage for new-vs-existing input routing, no state writes, stopped-state preservation, sample avoidance, workspace/host bootstrap parity and short-prompt/policy consistency. Validation after this change: **97 tests passed**, script compilation succeeded, and harness JSON plus documentation links were verified. No live MCP/third-party-host validation was claimed.

### K. Review 10 recent technical posts per publisher; recommendations only

The user requested a review of 10 preferably recent posts each from Uber Engineering, AWS Architecture, AWS Machine Learning, Google Developers and Netflix TechBlog, explicitly asking for suggestions first and no changes until confirmation. The review used 50 article texts/structures, with full publisher RSS bodies for AWS/Netflix and article pages for Uber/Google. One Uber page returned HTTP 406 and was replaced by the next accessible technical post; a nontechnical announcement was excluded. Benchmark claims/code were not independently validated or executed. Research cache stayed temporary, not in private run outputs or tracked harness files.

Key conclusion: research governance was already strong, but article design/technical proof and pre-review quality needed to be more explicit than company-inspired structures and manual prose checklists. Recommended article-type blueprints, story design, measurement proof, tutorial reproducibility, applicability/failure cases, richer figures, ML-specific review, sequential critique, evidence-change impact tracking and richer publication/series handling.

The recommended **first implementation scope** was five items: article-type blueprints, internal story outline/coverage map, structured measurement/reproducibility checks, first-class charts/figures, and a pre-review content-quality report. Keep the four stages, simple input/few prompts, privacy/selected MCP/load gates, and titles in PREPARE. Broader evidence dependency graphs, local-only completion, metadata/series improvements and a universal MCP interceptor were not included in that first scope.

### L. Latest implementation: approved first article-quality scope

The user approved that first scope and required code, instruction files, all README guides and developer context to stay synchronized.

Implemented local contracts:

- `harness/blueprints/article-types.json`: architecture case study, tutorial, performance investigation, ML experiment, migration journey and technical introduction. Heuristic inference is a proposal; the agent verifies/overrides it from evidence without a new mandatory user question.
- `harness/schemas/editorial.schema.json` plus agent-authored `outputs/draft/editorial.json`: thesis, reader outcomes, required coverage/research-question-to-source mapping, per-version angle/outline/word budgets, measurement proof/qualifications, reproducibility and figure registry, exact-file sequential evidence/technical/editorial review attestations. This is internal work, not another user intake file.
- Measurement records classify production/experiment/simulation/estimate/author statements and causal strength, require substantive protocol for supported results, visibly qualify missing/uncertain evidence, or omit claims. Supported ML experiments add data/model/split/leakage/serving/safety context. A narrow numeric regex catches some unclassified results; explained non-result constants are permitted. This does not prove statistical correctness.
- Tutorials/fenced code require prerequisites, versions, permissions, bounded steps/expected outputs, costs, verification, troubleshooting and cleanup. Execution is either visibly `not-run` with a reason or `verified` with an actual permission/environment/local transcript record. The helper **never executes example commands**, deploys resources, calls MCP or judges transcript truth.
- Technical figure registry includes diagrams, charts, tables, equations and screenshots; stable labels, captions, alt text, source IDs, local assets and prose references. Charts link measurement IDs and reviewed CSV data/columns/units/baseline/aggregation/conditions. CSV checks are bounded and validate finite numeric y values; screenshots need permission context, equations need definitions/export-compatible assets. Final visual review remains required.
- `scripts/editorial.py`: read-only blueprint proposals, deliberately incomplete scaffolds, local schema/metadata/asset/coverage/review checks, JSON/Markdown quality reports and fingerprinted write-once-by-helper report archives. No numeric quality score. Automatic and agent-review findings are identified separately. Missing local references/schema errors/blockers fail checks; approximate word-count deviations and honest qualifications/not-run disclosures remain visible warnings.
- New `blog.py init` projects set `editorial_contract_version = 1`. DRAFT→REVISE requires a fresh passing report for all versions; revision approval requires a fresh report for the exact revision and pins its fingerprint with the body hash. Changed packet/reviews/text/evidence/decision/research/configuration/contracts invalidate old reports. Run the local check again after logging the actual stage/approval decision if needed.
- Existing runs without this flag remain compatible and are not retroactively blocked or rewritten. Explicit `editorial.py adopt --user-confirmed` opts a legacy DRAFT/REVISE run in; no adoption/body mutation in PREPARE and no silent removal of a new run's flag.
- Before presentation, the agent performs sequential review passes and resolves blockers; warnings and scope omissions are summarized in the existing review conversation. User satisfaction and title/hero/upload permissions remain independent. PREPARE uses the approved report to check headline promises, then the existing title/hero/packaging flow.
- Public brief syntax and all five sanitized samples remain unchanged. Manifest/schema, host checks, shared policies/workflow, root/input/harness/adapter READMEs and this developer handoff describe the same contract. No private real run was scaffolded, adopted or modified as part of development.

Local tests use clearly marked synthetic source/packet/review fixtures. These prove validator/gate behavior, not actual editorial quality of fixture prose. Never copy them into production approvals. Final validation for this implementation: **129 tests passed**; all scripts compiled; harness JSON/manifest references, all five unchanged input samples and documentation links were verified. No live MCP calls, sample-command execution, new production run/adoption or third-party-host certification occurred. Section 5 records the broader validation history.

## 3. Current repository map

```
AGENTS.md                         shared rules; Codex/OpenCode entrypoint
CLAUDE.md / GEMINI.md              host entrypoints
.cursor/rules/                    Cursor rule
.github/copilot-instructions.md   Copilot instructions
README.md                         user startup and usage
input/
  README.md                       simple input syntax and semantics
  input_sample.json               sanitized series-part example
  sample_single.json              single public engineering article
  sample_microsoft.json           SharePoint/Teams/Azure DevOps
  sample_local_tutorial.json      files only; no MCP
  sample_custom_sources.json      Webex/custom sources/manual Office exports
  blog.json                       personal input, ignored (not a shipped sample)
harness/
  README.md / manifest.json       architecture and local contracts
  workflows/technical-blog.md     four-stage orchestration
  policies/                       input, sources, collection, MCP, editorial voice and structured quality
  blueprints/article-types.json   six evidence-appropriate explanatory blueprints
  stages/prepare.md               title, hero, packaging, cloud/export checks
  contracts/host-capabilities.md  host-neutral startup/tool contract
  adapters/                       thin per-host mappings and smoke checklist
  schemas/                        manifest, simple/legacy input and editorial-packet schemas
  config.collection.json          proposed bounded collection defaults
scripts/
  blog.py                         read-only startup router; state/evidence/approval/title/export CLI
  intake.py                       input validation and normalization (not a CLI)
  collection.py                   frontier and source-load controller
  host.py                         read-only local adapter check
  editorial.py                    blueprint/story/proof/figure/review checks and freshness gates
tests/                            temporary-workspace/mocked regression tests
.githooks/pre-commit               optional activated Git-index guard
developer/                        development handoff (this folder)
project.json                      ignored per-run state at workspace root
outputs/                          ignored per-run evidence/artifacts/logs/snapshot
```

Stage artifacts and input snapshots all remain under `outputs/`; only `project.json` intentionally remains at root. This is one blog/current series part per workspace.

## 4. Important implementation contracts

### CLI and workspace paths

- Python **3.10+** for the standard-library helpers; no nested LLM calls.
- Helpers default to the installation repository, **not the current shell directory**. If installation and workspace differ, use absolute helper paths and `--root WORKSPACE` before the subcommand.
- `blog.py`: `startup`, `inspect-input`, `init`, `import-input`, `apply-input`, `migrate-decisions`, `status`, `resume`, `select-sources`, `mcp-decision`, `source`, `advance`, `draft-settings`, `approve`, `reopen`, `titles`, `select-title`, `hero`, `export`, `google-doc`, `complete`.
- `collection.py`: `configure`, `status`, `add`, `next`, `finish`, `request`, `result`.
- `host.py`: `--list` or `--host ID`, optional `--root WORKSPACE`.
- `editorial.py`: `blueprint [--type TYPE]`, `scaffold [--type TYPE]`, `check [--file REVISION]`, and legacy `adopt --user-confirmed`; global `--root` precedes the subcommand. No model, MCP or example-execution calls.
- Flags such as `--user-confirmed`/`--verified` attest to **real prior conversation/checks**; the CLI cannot establish that they happened.
- `import-input` is only for COLLECTION with no saved intake; it does not overwrite a source plan or newer conversational draft settings. `apply-input` does not fetch anything or configure the controller automatically.

### Input and decisions

- A minimal request naming the brief is sufficient; guide-reading, validation, missing-field-only questions, save/resume precedence and PREPARE titles are automatic harness duties.
- Run read-only `startup` before intake: only a new run opens the named/default brief; an existing run wins without input replay. Explicit stopped-state resume consent is still required.
- Auto-discover only `input/blog.json` when no explicit file is supplied. Never auto-use any sample.
- Missing essentials/ambiguity get questions; do not repeat supplied answers or require optional research notes/title preferences.
- One combined source/scope/navigation/storage confirmation before remote work. Later gates remain distinct.
- Original input file edits do not silently mutate a run. Latest saved user decisions win over old preferences.
- `outputs/decisions.md` is the run's human decision log. `developer/SESSION_CONTEXT.md` is reusable engineering history. Keep them separate.

### Collection defaults and limits

| Setting | Proposed default |
| --- | --- |
| Navigation | Both children and in-page links |
| Max edge depth (seed = 0) | 2 |
| Items/source and total | 20 / 50, including pending/failed/visited |
| Child/link fan-out per item | 8 |
| Requests/backend and total | 80 / 150; failed attempts count |
| Elapsed collection window | 1,200 seconds, including pauses/restarts |
| Pacing | One global in-flight request; at least 2 seconds per shared backend |
| Retry attempts after initial failure | 2, with 5s/10s minimum backoff and provider Retry-After respected |
| Low-value stops | 2 consecutive along a branch; 5 consecutive globally |

Provider-specific stricter limits win. Every probe/search page/read/child listing/attachment/upload/readback needs its own permit. `result` accepts success/retry/failed/resource-error; a resource-specific failure need not disable a healthy backend. Code supplies minimum backoff; policy also asks the orchestrator for positive jitter. Repeated temporary failures open a circuit; authentication failures go to selected-source proceed/exit. No automatic reset/extension command exists: approved extensions need reviewed, logged saved-limit edits while retaining counters/history.

### Evidence and editorial quality

Readable evidence under `outputs/data/normalized/` is registered with a source ID/hash in `catalog.json`. Retain original exports/assets, queries/coverage logs, research brief and claim ledger. Distinguish planned from shipped, measured from estimated, and evidence from interpretation. Internal access never grants publication permission. Validate diagram semantics and labels against sources. Render Mermaid before export and retain editable sources.

Review revisions and notes are immutable numbered files. The agent now plans article type/thesis/coverage/budgets in `outputs/draft/editorial.json`, records measurements/reproducibility/technical figures and performs checksum-bound sequential reviews before presentation. New or explicitly adopted runs need fresh reports in `outputs/draft/quality-report.json` (plus readable `.md`/archives) before review transition or revision approval. Body approval pins SHA-256 and, for gated runs, the quality fingerprint. The selected PREPARE title separately authorizes final H1 packaging, not prose changes. Hero generation defaults to original SVGs, no stock/brand copying; record provenance, alt text and actual user selection/skip/policy acceptance.

### Exports and honest completion

- Local final `article.md`; HTML rendered with raw HTML disabled and local images embedded; PDF through optional Playwright/Chromium. Browser network requests are blocked. Remote images and unrendered Mermaid are rejected.
- Dependencies are optional until export. Ask before installing packages/browsers. On PDF failure, remove stale PDF output and report what is blocked.
- Google Doc must be really created/verified through the host's selected, authorized tools. `.gdoc` is a pointer; offline copies are Markdown/HTML/PDF.
- Selected cloud destinations do not imply upload permission or expanded sharing. No fabricated doc IDs/URLs/readback results.
- Built-in `complete` still verifies the original **four-format** delivery, including Google Docs. A local-only or other-cloud handoff is supported conversationally, but must not falsely invoke all-four-format completion. This is a known extension point, not permission to weaken existing checks.

## 5. Validation history and current baseline

Regression coverage grew through the session: initial workflow, outputs migration, Git/MCP gates, source selection, bounded collection, host adapters, input/title/migration, then simplified input and PREPARE-only titles.

At the initial documentation handoff, **86 tests passed**, and all five input samples, harness JSON and document references were validated. The implicit-startup change (J) brought the suite to **97 passing tests**. The latest first-scope article-quality implementation (L) has **129 passing tests**, with script compilation, JSON/manifest references, all five input samples and documentation links also passing. Tests use temporary workspaces and mocked remote/browser behavior as appropriate. Run them again for any change; installed optional dependencies can affect whether export tests run or skip.

Relevant suites:

- `test_blog.py`: state transitions, artifact paths, evidence hashes, approvals, packaging/export integrity.
- `test_collection.py`: scope, deduplication/cycles, depth/fan-out/budgets, low-value stops, pacing/backoff/circuits, lock and manifest contracts.
- `test_hosts.py`: entrypoint/adapter references, read-only checks, workspace roots, host switching, no private-state mutation.
- `test_intake.py`: simple briefs/examples/defaults, normalization/no information loss, legacy compatibility, snapshots, decision migration, PREPARE titles and approved-body immutability.
- `test_safeguards.py`: selected-source-only MCP decisions, stopped/resume behavior, Git exclusion/guard and personal-input protection.
- `test_startup.py`: automatic read-only input/resume routing, invalid/missing input handling, no state writes, stopped-run preservation, host bootstrap parity and short-prompt/shared-policy consistency.
- `test_editorial.py`: blueprint/scaffold, coverage/outline/budget, measurement/ML context, truthful execution status, CSV/figure/equation/screenshot checks, sequential review findings, reports/archives, stale-report gates and legacy adoption. `editorial_fixtures.py` supplies explicitly synthetic local-contract fixtures, never real review approval.

No local test run proves every third-party host works live, MCP authentication succeeds, source API quotas are safe, technical facts/legal rights are correct, or visual exports/cloud formatting were actually inspected. Never repeat those claims without real checks.

## 6. Known limitations and safe future extension points

These are observations/options, **not already-approved implementation tasks**:

1. **Instruction-level enforcement:** collection helpers cannot intercept MCP calls the host makes directly. Strict universal enforcement needs a reviewed gateway or host-specific interception layer.
2. **Single writer:** collection has a local mutation lock/in-flight slot; the overall workflow is not a distributed/concurrent-agent system. Do not add parallelism casually.
3. **Local-only completion:** a dedicated persisted local-only/custom-destination completion contract could be added, with schema/CLI/docs/tests, rather than claiming the current Google-required command supports it.
4. **Other cloud formats:** Word/SharePoint/etc. can be selected sources/destinations, but built-in cloud-pointer/completion handling currently targets Google Docs. New formats need real implementation/readback validation, not just manifest entries.
5. **Manual quality checks:** local editorial checks now enforce packet/measurement/figure/review structure and freshness, but relevance, alias/resource-ID recognition, actual technical/statistical correctness, real execution success, rights, visual quality and publication approval remain agent/human tasks. Reviews are attestations, not independent verification; scanners/heuristics are intentionally limited.
6. **Custom validation:** `intake.py` validates the schema keywords used here, not all of JSON Schema. New schema constructs require corresponding validator code/tests or an explicitly approved dependency.
7. **Budget recovery:** elapsed time includes interruptions, and extensions/recovery are intentionally manual/reviewed. A future extension command must preserve audit/counters rather than silently reset a crawl.
8. **Git protection:** ignore rules and optional local hook do not erase history or prevent an external user from bypassing hooks. CI enforcement could supplement them. Never commit existing runtime evidence for convenience.
9. **Host versions:** native instruction and MCP behaviors evolve. Keep adapters thin, verify effective instruction loading and use the manual checklist on the installed product/version.
10. **Handoff freshness:** this document is a session baseline, not dynamically generated source truth. Update it after meaningful improvements, with actual validation results and explicit supersessions.

## 7. Continuation rules

- Read `developer/README.md` and inspect current implementation before coding.
- Do not initialize a blog or touch real run artifacts just to understand the harness.
- Preserve the latest user intent over old decisions: simple briefs, chosen sources only, bounded collection, outputs privacy, decisions under outputs, and **titles in PREPARE**.
- Ask what the next improvement is; do not automatically execute the optional ideas above.
- For an approved change, update implementation, policies, schemas/manifest, relevant samples, docs and tests together; add compatibility handling when persisted state changes.
- Document the next change here without private content. Keep source evidence/run decisions in their ignored runtime locations.
