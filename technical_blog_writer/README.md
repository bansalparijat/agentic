# Technical blog meta harness for coding agents

A file-based, resumable workflow run inside **Codex, Claude Code, OpenCode, Gemini CLI, Cursor, or a compatible interactive coding harness**, using that host's tools and MCP connections. No nested agent, model API key, or MCP server is included. Thin host entrypoints reference shared `AGENTS.md` rules; Python helpers record evidence, approvals, state and exports. The agent does the research, writing, diagrams and interactive review.

## Start

1. Open this folder in your preferred core harness. Use its entrypoint from the table below and verify the shared instructions loaded. If uncertain, explicitly ask it to read `AGENTS.md` and the matching adapter.
2. Copy one of the [sample briefs](input/README.md) to **`input/blog.json`** in your workspace, then customize it and replace every placeholder link/file. The [input README](input/README.md) explains the **JSON syntax, field semantics, defaults, single/series behavior, and examples**. `input/blog.json` is your personal, Git-ignored input; no sample is automatically used.
3. Configure only the sources selected in that file using **your current host's MCP settings**, with least-privilege access. Microsoft/SharePoint/Teams/Webex, Google, Atlassian, custom systems and local files are all valid choices; no vendor stack is mandatory. This repository does not configure or bundle connectors. Cloud destination selection and upload authorization remain separate.
4. Use this short prompt:

   > Start a technical blog using input/blog.json.

   Later: **“Resume the blog workflow.”**

The harness automatically reads the [input syntax/semantics guide](input/README.md), validates/prefills a new brief, asks only for missing/conflicting information and required approvals, and preserves/resumes existing saved state without replaying input. At PREPARE it automatically suggests titles and asks you to pick one or provide your own. These are built-in responsibilities—not instructions you need to paste into a prompt. A run stopped after an MCP warning still requires an explicit request to resume.

If your file has a different name, replace **`input/blog.json` in the startup prompt** with that exact workspace-relative or absolute path. Never use sample placeholder links as real collection targets. See [input/README.md](input/README.md) for the complete input guide.

Python **3.10+** is enough for workflow/state commands. No installation is needed until HTML/PDF export. Do not initialize a real project just to test the harness; tests use temporary directories.

## Host adapters and startup

| Core harness | Project entrypoint | Adapter |
| --- | --- | --- |
| Codex | `AGENTS.md` | `harness/adapters/codex.md` |
| Claude Code | `CLAUDE.md` (imports shared rules) | `harness/adapters/claude-code.md` |
| OpenCode | `AGENTS.md` | `harness/adapters/opencode.md` |
| Gemini CLI | `GEMINI.md` | `harness/adapters/gemini-cli.md` |
| Cursor Agent | `.cursor/rules/technical-blog.mdc` | `harness/adapters/cursor.md` |
| GitHub Copilot (capable interactive agent surface) | `.github/copilot-instructions.md` | `harness/adapters/copilot.md` |
| Other/uncertain host | Explicitly read `AGENTS.md` | `harness/adapters/generic.md` |

These are instruction-level adapters, not plugins that install or launch those products. Verify project instructions/rules are enabled in your installed version. Unsupported or unattended surfaces must pause at human gates rather than invent answers. The model provider is not the host: a Claude model inside OpenCode uses the OpenCode adapter.

```sh
python3 scripts/host.py --list
python3 scripts/host.py --host claude-code
python3 scripts/host.py --host opencode
```

The read-only check validates local adapter references and shows workspace-aware startup commands; it makes **no MCP calls**, writes no state, and does not prove host permissions/authentication. Python 3.10+ is required. For a generic host, use:

> Follow AGENTS.md with harness/adapters/generic.md. Start a technical blog using input/blog.json.

The explicit file-loading prefix is only for hosts without native instruction loading; it does not change the shared workflow or require you to restate its steps.

Each host needs its **own** MCP setup/authentication; do not copy credential files or assume another host's connections are inherited. Missing selected capabilities retain the same proceed/exit prompt on every host. No structured question tool? Ask in chat and wait for the next user turn. See `harness/contracts/host-capabilities.md` for permission handling and the tool capability contract.

### Separate installation and workspace; switching hosts

The simplest setup uses this folder for both harness and project. If the project lives elsewhere, explicitly load the installation's instruction/adapter files, confirm the target workspace, and use absolute helper paths with `--root` **before the subcommand**:

```sh
python3 /path/to/harness/scripts/host.py --host opencode --root /path/to/project
python3 /path/to/harness/scripts/blog.py --root /path/to/project status
python3 /path/to/harness/scripts/collection.py --root /path/to/project status
```

Helpers default to the harness repository, not the current shell directory. Default configs/policies stay in the installation; copy only approved runtime configuration to the workspace. Ensure that workspace has equivalent `outputs/` Git exclusion/guard protection before storing evidence. Native instruction files in a different folder may not auto-load: explicitly reference their absolute paths or add a reviewed host entrypoint there without overwriting existing instructions.

To switch hosts, first stop the previous session, reconcile any in-flight call/lock, then open the **same workspace** and resume on-disk state. Do not run multiple hosts concurrently, reset budgets, or approve content again on the user's behalf. Check selected MCP access in the new host while preserving accepted skips for an unchanged source plan.

## Input files: fewer intake prompts

The complete [input syntax and semantics guide](input/README.md) documents each field, optional settings, defaults and sample types. The startup prompt above uses **`input/blog.json`** explicitly; a sample file is only a template to customize, not an implicit input.

Use a small, flat JSON brief—no nested intake blocks or version marker required:

```json
{
  "topic": "How we made background jobs safe to retry",
  "audience": "Backend developers",
  "words": 1200,
  "publication": "public",
  "sources": {"GitHub": ["https://github.com/example/job-service"]}
}
```

Copy an example to ignored `input/blog.json` and replace placeholders:

- `input/sample_single.json`: one public engineering blog.
- `input/sample_microsoft.json`: one internal SharePoint/Teams/Azure DevOps migration article.
- `input/sample_local_tutorial.json`: one tutorial using local files only, no MCP.
- `input/sample_custom_sources.json`: Webex/custom services and manual Office exports.
- `input/input_sample.json`: Part 1 of a three-part sandbox series, based on the latest original decisions with sanitized links.

Omit `series` for a **single blog**. For a series use `"series": {"part": 1, "total": 3, "roadmap": ["Initial design", "Cost improvements", "Developer environments"]}`. Optional flat fields retain goals, keywords, coverage/exclusions, date cutoffs, depth, scope, storage/output preferences and bounded-navigation overrides; see `input/README.md`. There are **no `title_preferences` or required research/source notes**. Omitted settings use proposed safe defaults (two drafts, local formats and bounded collection) shown for confirmation, not automatic permission.

```sh
# Optional diagnostics; the agent invokes startup handling automatically:
python3 scripts/blog.py startup --input input/blog.json
# Independent read-only validation, even when a run already exists:
python3 scripts/blog.py inspect-input --file input/blog.json
# New project; plain init also detects input/blog.json if present:
python3 scripts/blog.py init --input input/blog.json
# Only after actual combined source/navigation/storage confirmation:
python3 scripts/blog.py apply-input --user-confirmed
```

The sample is never auto-loaded. A named file overrides default-path discovery; conflicting CLI topic/audience are rejected rather than silently replacing file values. The agent presents one concise summary and asks only for missing/conflicting preferences plus material scope/permission confirmation—not the full source menu or word-count questions again. Original brief snapshot: `outputs/input.json`; normalized preferences stay internal to `project.json`. Older nested v1 files remain readable; latest user decisions in `outputs/decisions.md` override old input on resume. Do not reinitialize existing projects or replay input over approved prose.

### Title selection

At the start of **PREPARE**, after body revision/approval, the harness suggests **3–7 evidence-grounded headlines** (default 5) from the approved article and asks you to select, edit/combine, provide your own, or request more. No title is requested in input, DRAFT or REVISE. Choices are saved in `outputs/blog/title-options.json` and bound to the approved revision hash. Your explicit choice authorizes an H1-only change in final packaging while the approved body/revision stays unchanged. Title-only changes refresh hero/exports/cloud verification; body changes still require REVISE and fresh text approval.

```sh
# After the agent has written the options and the user has actually chosen:
python3 scripts/blog.py titles --file outputs/blog/title-options.json
python3 scripts/blog.py select-title --id T2 --user-confirmed
# Or: select-title --custom "Your own headline" --user-confirmed
```

Input never bypasses missing-MCP proceed/exit, title choice, draft review, explicit revision satisfaction, hero selection/skip, disclosure approval, upload consent or final acceptance. See `input/README.md`, `harness/policies/input.md`, and `harness/schemas/input.schema.json`.

## Article design and quality checks (automatic)

The agent now chooses the right **article blueprint** from the brief and evidence: architecture case study, tutorial, performance investigation, ML experiment, migration journey or technical introduction. You do **not** need to choose a company style, add input fields or fill an editorial questionnaire.

Before full drafts, it builds an internal thesis, reader outcomes, evidence coverage map and distinct per-version outlines with section word budgets. The generated packet at `outputs/draft/editorial.json` also records:

- **Measurement proof:** baseline, workload/environment/versions, metric/unit/denominator, procedure, result, uncertainty, provenance and causal strength—or explicit qualification/omission when data is missing. Supported ML experiments add dataset/split/leakage/model/serving/safety context.
- **Reproducibility:** prerequisites, versions, permissions, bounded steps/expected outputs, verification, troubleshooting, costs and cleanup. Examples are either genuinely verified with local evidence and scoped permission or visibly disclosed as **not run**. Helpers never execute stored example commands.
- **Technical figures:** diagrams, charts, tables, equations and screenshots, with source IDs, editable/rendered assets, meaningful alt text, captions and prose cross-references. Charts have approved CSV data, columns/units, baseline, aggregation and conditions; equations/screenshot rights have their own checks.
- **Sequential reviews:** evidence, technical and editorial passes on the exact draft/revision hashes, with substantive findings—not an opaque numeric score or auto-approval.

`editorial.py check` produces `outputs/draft/quality-report.json` and `.md`, plus fingerprinted report archives. It checks structure/provenance and reviewer attestations; it cannot independently prove truth, actual execution, legal rights or visual correctness. Blockers are resolved before content is presented; warnings/omissions are explained in the existing review conversation. The word-count check is approximate and does not replace your agreed counting scope.

```sh
# Agent-side commands after COLLECTION and resolved draft settings:
python3 scripts/editorial.py blueprint
python3 scripts/editorial.py scaffold --type architecture-case-study
# The agent fills the deliberately incomplete packet, writes drafts and performs
# actual sequential reviews; a scaffold alone does not pass:
python3 scripts/editorial.py check
# After feedback, update the packet/reviews for the current immutable revision:
python3 scripts/editorial.py check --file outputs/revised_draft/revision-001.md
```

Blueprint selection is heuristic/agent-verified, not a new mandatory user prompt. New projects use quality contract v1: draft-to-review transition requires a **fresh passing report for all versions**, and revision approval pins the exact revision plus quality fingerprint. Source/config/decision/packet/file changes invalidate stale reports; rerun locally immediately before a gated transition. Human satisfaction remains mandatory, and titles still happen only in PREPARE.

Existing runs are preserved without retroactive gating. To opt a legacy DRAFT/REVISE run into the new contract, first agree with the user, then run `python3 scripts/editorial.py adopt --user-confirmed`. Never remove a new run's flag to bypass a blocker. See [the quality policy](harness/policies/quality.md) for the generated packet/schema, figure and reproducibility contracts and review limits.

## Stages and outputs

All stage-specific artifacts are created and read under `outputs/` in the workspace. `project.json` remains at the workspace root; run-specific decisions are at `outputs/decisions.md`. Legacy logs can be moved byte-for-byte with `python3 scripts/blog.py migrate-decisions`, which refuses to overwrite another log. CLI `--file` arguments and paths in catalogs/checksum manifests are workspace-relative and include `outputs/`. Markdown image links remain relative to their document: `assets/diagram.svg` in `outputs/blog/article.md` resolves to `outputs/blog/assets/diagram.svg`.

| Stage | User interaction | Local outputs |
| --- | --- | --- |
| COLLECTION | Topic/audience, source scope, confidentiality, approval to draft | `outputs/data/raw/`, `outputs/data/normalized/`, `outputs/data/assets/`, source catalog, search log, research brief, claim ledger |
| DRAFT | Prefilled/missing word count and 2–3 versions; review warnings if any | `outputs/draft/version-01.md`, `outputs/draft/version-02.md`, optional `outputs/draft/version-03.md`, comparison, evidence map and diagrams |
| REVISE | Choose closest draft, give feedback, repeat until explicitly satisfied | Immutable `outputs/revised_draft/revision-NNN.md`, change notes and assets |
| PREPARE | Title suggestions/selection, hero choices/retry/skip, upload permission, final acceptance | `outputs/blog/article.md`, `.html`, `.pdf`, `.gdoc`, Google Doc metadata, assets, verification and checksum manifest |

Drafts use evidence-appropriate article blueprints and distinct substantive angles, informed by engineering writing but not copied Uber/Google/Amazon/Netflix prose. The workflow preserves source provenance and requires evidence-grounded diagrams, permission checks and an explicit user approval loop.

**Google Doc caveat:** A native Google Doc lives in Google Drive. `article.gdoc` is a local pointer to the actual document created and verified through MCP, not an offline document. Markdown/HTML/PDF are the offline copies. If creation/verification is unavailable, delivery remains incomplete with the Google Doc clearly marked blocked.

## Choose your sources

If sources are not already specified in input/saved decisions, intake offers a multi-select menu and an **Other: name your own** option:

- Documents: SharePoint, OneDrive, Microsoft Office/Word/OneNote, Google Drive/Docs, Confluence, Notion, Box, Dropbox.
- Data: Excel, Google Sheets, CSV/data exports.
- Chat/meetings: Microsoft Teams, Slack, Cisco Webex, Zoom transcripts, Google Chat.
- Planning/code: Jira, Azure DevOps, GitHub, GitLab, Bitbucket, Linear, Asana.
- Public websites, local repositories, uploaded/exported files, PDFs, pasted text, or any custom system.

Specify MCP access or manual files/paste for each choice. Only selected MCP-backed sources receive access/authentication warnings; local-only work requires no MCP. Custom labels are supported without code changes. Choices persist in `project.json` under `source_plan`. See `harness/policies/sources.md` for the full intake prompt and scope rules.

```sh
# After initialization and the user's explicit selection:
python3 scripts/blog.py select-sources \
  --mcp SharePoint --mcp "Microsoft Teams" --mcp Webex \
  --manual "Office exports" --user-confirmed
```

Cloud export destinations are selected separately (`--destination "Google Docs"` if wanted). Selecting SharePoint/Teams does not trigger a Google/Slack/Confluence warning. Without an explicitly selected Google Docs destination, deliver actual local/custom artifacts and do not claim the original four-format completion. The built-in cloud-pointer/completion tooling currently supports Google Docs, not arbitrary cloud formats.

## Missing or unauthenticated MCPs

The agent discovers and checks only needed capabilities for your explicitly selected MCP-backed sources and separately selected cloud destinations. If any are missing, unauthenticated or unavailable, it lists the affected sources/formats and warns: **proceeding without them may miss important context and may not give the best result**. It then waits for you to choose:

- **Proceed** — record your consent, skip the affected capabilities and their expected errors (no retry/prompt loop), and continue with available sources. Coverage gaps remain visible; unavailable Google Docs stays blocked, never fabricated.
- **Exit** — preserve progress and immediately end the workflow. No further work or repeated prompts until you explicitly ask to resume.

New connector/capability failures require a new decision; accepted skips persist on resume. Missing all research sources still requires real local/pasted evidence before drafting. Authentication happens through the current host, never by pasting credentials here. See `harness/policies/mcp.md`.

The CLI records decisions made in the conversation; it does not discover MCPs or authenticate them:

```sh
# Only for a selected source, after the warning and explicit consent:
python3 scripts/blog.py mcp-decision --connector "Microsoft Teams" --capability read \
  --reason "Authentication expired" --decision proceed --user-confirmed
# For a user who declines: use --decision exit instead. Stop the agent workflow.
# Only on a later explicit request to resume a stopped workflow:
python3 scripts/blog.py resume --user-confirmed
```

## Bounded recursive research and source protection

The agent prefills navigation from input or asks whether to follow **children**, **in-page links**, **both**, or **roots only**, and confirms boundaries and budgets together with source/storage scope before remote reads. Example: a Confluence seed can lead to child pages and relevant linked design documents, not an unrestricted tenant crawl.

Proposed defaults (require user approval): depth **2**, **20 items/source**, **50 total**, **8 children/links per item**, **one request in flight**, **2 seconds minimum between calls to a shared backend**, **80 requests/backend**, **150 total**, **20 minutes**. Stricter provider limits win. Two low-value items prune a branch; five consecutive low-value items stop collection. Cycles, repeated URLs, pagination loops, aliases and cached versions must not cause repeated reads. Sources served by the same MCP/account/backend share a rate bucket.

`harness/policies/collection.md` defines the prompt, relevance/stop rules, bounded retries, Retry-After handling and logging. `scripts/collection.py` persists a breadth-first frontier and request permits; it never makes MCP calls itself. The current host's orchestrator must use the controller before each remote operation, including probes, search pagination, child listings, attachments and publication calls. It cannot intercept calls made outside the helper, and must be used by one writer/orchestrator only.

```sh
# Agent first copies defaults, fills selected source/backend/scope mappings,
# and obtains user approval (see the collection policy):
python3 scripts/collection.py configure --config outputs/data/collection-config.json --user-confirmed
python3 scripts/collection.py add --source Confluence --url "<authorized stable seed URL>"
python3 scripts/collection.py next
python3 scripts/collection.py request --source Confluence
# Make exactly one authorized MCP call only if a permit was granted.
python3 scripts/collection.py result --outcome success
# Assess item, register evidence, then enqueue relevant descendants:
# python3 scripts/collection.py finish --key KEY --value useful --summary "New evidence"
# python3 scripts/collection.py add --source Confluence --url "<child URL>" --parent KEY --relation child --reason "Relevant mechanism"
python3 scripts/collection.py status
```

Throttling uses bounded backoff and opens a backend circuit after repeated failures. Pacing/budget denials are not errors that degraded-mode consent allows the agent to ignore. On a limit, summarize gaps and ask before any explicit extension; never reset counters to continue silently. Existing project content and approvals are preserved; older projects are prompted only for missing navigation/load consent.

## Keep outputs out of Git

`/outputs/` and all descendants are ignored by `.gitignore`. Never force-add them or copy generated/private output into tracked files. The included pre-commit hook also rejects **any tracked/staged outputs content**, including force-added files, while allowing index-only removal. Enable it once a Git repository exists:

```sh
git config core.hooksPath .githooks
```

This folder currently need not be a Git repository; initialize or use your intended repository before configuring the hook. If the harness lives inside a larger repository, merge this guard into that repository's existing hook instead of replacing its hooks configuration. The hook can also be run explicitly with `python3 .githooks/pre-commit` from inside the intended repository.

Ignore rules do not untrack existing files or erase history. If output files were previously tracked, review and use `git rm -r --cached -- outputs/` from this workspace to remove them from the index **without deleting local files**; address any prior disclosure separately. Git hooks are local safeguards and can be bypassed, so the agent must inspect staged paths and never disable the guard or use force-add/`--no-verify` to commit outputs. For enforcement across contributors, run the guard in repository CI as well.

## Export setup (optional until PREPARE)

Ask permission before installing software or uploading content. In a virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-export.txt
python3 -m playwright install chromium
```

On Linux, Chromium may also require OS libraries (`python3 -m playwright install --with-deps chromium`; may need administrator permission). Browser installation downloads software. HTML export embeds local images, disables raw Markdown HTML and blocks browser network requests. Mermaid must first be rendered to SVG/PNG; see `harness/stages/prepare.md` for the optional renderer. This is not a general sandbox: only render locally reviewed assets and diagrams.

## CLI reference

These commands support the agent; they do not query MCP or generate prose themselves. `--user-confirmed` and `--verified` are attestations to real conversations/checks, not automatic approval. Workflow artifacts and state are stored relative to the repository by default; `--root /path/to/workspace` (before the subcommand) can select another workspace.

```sh
python3 scripts/blog.py status
python3 scripts/blog.py init --topic "Reliable event ingestion" --audience "Backend engineers"
# Example only: use the user's actual choices, not mandatory defaults.
python3 scripts/blog.py select-sources --mcp Confluence --destination "Google Docs" --user-confirmed

# After an authorized MCP read, save readable evidence locally, then register it:
python3 scripts/blog.py source \
  --file outputs/data/normalized/design-v3.md --kind confluence \
  --title "Ingestion design" --locator "https://example.atlassian.net/wiki/...#Retry-policy" \
  --version "3" --confidentiality internal \
  --limitations "Attachment unavailable; body retrieved in full"

# Input settings can prefill word count/versions; do not ask again if known.
# After collection artifacts exist and the user agrees:
python3 scripts/blog.py advance --to DRAFT --user-confirmed
python3 scripts/blog.py draft-settings --words 1800 --versions 3 \
  --count-scope "Body and captions; exclude code and references"
# After the agent plans/writes drafts and performs actual sequential reviews:
# python3 scripts/editorial.py scaffold --type <chosen-blueprint>  # once, before full drafts
python3 scripts/editorial.py check
# After the user agrees to review; rerun check after any decision-log change:
python3 scripts/blog.py advance --to REVISE --user-confirmed
# Agent collects feedback, writes revisions and updates the packet/review hashes.
# Run after logging actual user satisfaction, before the gated approval:
python3 scripts/editorial.py check --file outputs/revised_draft/revision-003.md
python3 scripts/blog.py approve --file outputs/revised_draft/revision-003.md --user-confirmed

# After presenting options and receiving an explicit choice:
python3 scripts/blog.py hero --file outputs/blog/assets/hero-option-02.svg \
  --alt "An abstract event stream connecting processing layers" --user-confirmed
# Or, only if the user requested it:
# python3 scripts/blog.py hero --skip --user-confirmed

# Agent assembles article.md/assets first:
python3 scripts/blog.py export
# Only after authorized MCP creation and readback of a REAL document:
# python3 scripts/blog.py google-doc --url "<actual Google Docs URL>" --verified --user-confirmed
# After visual/technical checks, verification.md and final user acceptance:
python3 scripts/blog.py complete --user-confirmed

# If approved content must change:
python3 scripts/blog.py reopen --reason "User requested a technical correction"
```

`export` needs installed export dependencies. It refuses missing/remote images and unrendered Mermaid. If PDF generation fails, existing PDF output is removed, HTML may still be available, and the command returns an error. Completion requires fresh exports, the approved revision checksum, a verified Google Doc pointer and verification notes. Automated checks cannot establish factual correctness, legal rights, visual quality, or whether a human actually approved something; the agent must follow the workflow.

## Harness architecture and repository map

The structure follows common harness conventions, not an invented universal host standard. Native entrypoints/adapters reference the shared `AGENTS.md` operating rules; `harness/manifest.json` is this repository's versioned local specification with stage inputs/outputs/gates. See `harness/README.md` for contracts, extension points, trust boundaries and migration details.

- `AGENTS.md` — shared operating rules; native Codex/OpenCode entrypoint.
- `CLAUDE.md`, `GEMINI.md`, `.cursor/rules/`, `.github/copilot-instructions.md` — thin host entrypoints.
- `harness/adapters/`, `harness/contracts/host-capabilities.md` — host mappings and shared capability/startup contract.
- `harness/manifest.json`, `harness/schemas/manifest.schema.json` — local specification and schema.
- `harness/workflows/technical-blog.md` — four-stage orchestration and handoffs.
- `harness/policies/` — input/title flow, sources, bounded collection, MCP access, editorial voice and structured quality.
- `harness/blueprints/article-types.json`, `harness/schemas/editorial.schema.json` — article obligations and agent-authored packet contract.
- `input/*.json` samples, `input/README.md` — five sanitized simple-brief examples; personal input files are ignored.
- `harness/schemas/input.schema.json`, `scripts/intake.py` — input contract and dependency-free validation.
- `harness/stages/prepare.md` — image selection, exports, Google Docs and handoff.
- `harness/config.collection.json` — proposed collection defaults (not user consent).
- `.githooks/pre-commit` — Git-index guard against committing output files (enable as above).
- `scripts/host.py` — read-only local adapter/workspace check (no MCP calls).
- `scripts/blog.py` — read-only automatic startup routing plus project/evidence/approval/export CLI.
- `scripts/collection.py` — persistent frontier, request permits, budgets and backend backoff.
- `scripts/editorial.py` — blueprint proposals/scaffolds, local quality reports and checksum-freshness gates (no model/MCP/example execution).
- `tests/` — workflow, safety, collection and harness-contract regression tests.
- `developer/README.md`, `developer/SESSION_CONTEXT.md` — contributor startup instructions and the session's engineering context/decision history.
- `outputs/` — all stage-specific evidence, drafts, revisions, deliverables and assets (ignored by Git).
- `project.json` — runtime state at the workspace root.
- `outputs/decisions.md`, `outputs/input.json` — per-run decisions and input snapshot, ignored with all outputs.

## Improving this harness

Start with [developer/README.md](developer/README.md), then load [developer/SESSION_CONTEXT.md](developer/SESSION_CONTEXT.md). The handoff covers the session's requirements, changes and superseded designs, implementation contracts, tests, known limitations, and a safe continuation prompt. This is harness development, **not** a request to run the blog workflow or inspect private runtime evidence.

Run tests with `python3 -m unittest discover -s tests -v`. Adapter tests cover local entrypoints/contracts and host-independent saved-state behavior; they do not launch third-party products or verify live MCP access. Complete the manual smoke checklist in `harness/adapters/README.md` in each installed host before relying on it. Export-specific tests run when Markdown dependencies are installed; a real browser smoke test requires the optional setup above. One article per workspace. To start another, use a fresh copy of the harness; do not erase prior evidence or revisions. Runtime folders are ignored by Git to reduce accidental leaks, **not encrypted**. Apply your own local access controls, retention, backup, and deletion policy. Inspect everything before sharing or committing.
