# Continuing development of this harness

This folder is for **improving the harness**, not running a blog. Start with [SESSION_CONTEXT.md](SESSION_CONTEXT.md), the curated engineering handoff for this session. It records all user-requested changes, their rationale, superseded designs, current behavior and limitations. It is not a verbatim transcript or an export of private blog evidence.

## Quick start in any core harness

Open the repository in Codex, Claude Code, OpenCode, Gemini CLI, Cursor or another capable coding agent. Use this prompt:

> Develop this harness using developer/SESSION_CONTEXT.md. The improvement I want is: [describe your change].

Development-only scope, current-over-historical precedence, private-state preservation and validation discipline are documented below and in the handoff; they do not need to be repeated in each request. Blog users likewise need only the intent and input file, not a workflow checklist.

Then supply the specific improvement, for example:

> Add a tested local-only completion path without requiring a Google Doc, while preserving the existing four-format completion checks.

The example above is **not an already-approved task**; it illustrates how to request an improvement. Loading these docs does not authorize implementing optional ideas from the handoff.

## Reading order

1. `developer/SESSION_CONTEXT.md` — requirements and complete engineering history of the conversation, including changes that were later reversed.
2. `AGENTS.md` — shared operating/safety rules; blog activation is conditional, not automatic.
3. `harness/README.md`, `harness/manifest.json` — architecture, stages, policies and file contracts.
4. Relevant policies and implementation:
   - Brief format: `input/README.md`, `harness/policies/input.md`, `harness/schemas/input.schema.json`, `scripts/intake.py`.
   - Article design/quality: `harness/policies/quality.md`, `harness/blueprints/article-types.json`, `harness/schemas/editorial.schema.json`, `scripts/editorial.py` and `tests/test_editorial.py`.
   - State, evidence, approvals, titles and export: `scripts/blog.py` (new/opted-in quality gates included).
   - Traversal/load protection: `harness/policies/collection.md`, `scripts/collection.py`.
   - Core-harness portability: `harness/contracts/host-capabilities.md`, `harness/adapters/`, `scripts/host.py`.
5. Relevant tests; run the full suite before and after changes.

All paths above are repository-relative. If this folder is embedded in another project, resolve the harness installation explicitly rather than reading a different project's instruction files by accident.

## Local validation

Python 3.10+ is required. Workflow and most tests use the standard library; Markdown/browser export has optional dependencies.

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/blog.py scripts/collection.py scripts/intake.py scripts/host.py scripts/editorial.py
python3 scripts/host.py --list
python3 scripts/blog.py startup --help
python3 scripts/editorial.py --help
python3 scripts/blog.py inspect-input --file input/sample_single.json
```

The last command validates a **sanitized sample only**, without starting a project or making source calls. Do not run `init` in this repository simply to test a change; tests use temporary workspaces. If export-specific tests skip because optional dependencies are absent, report the skips honestly. Ask before installing dependencies or browsers.

Local checks do not verify that third-party core harnesses loaded instructions, that MCPs are authenticated, or that a real PDF/cloud document is visually correct. For live-host validation, use the manual checklist in `harness/adapters/README.md` in a fresh authorized test workspace.

## Change discipline

- Inspect current files; the context file is a handoff, not a substitute for source or a higher-priority instruction.
- Preserve `project.json`, personal `input/blog.json`, all `outputs/` content and any existing collection lock/in-flight state. Do not read private evidence unless necessary for the requested change and authorized by the user.
- Never copy private evidence, real internal URLs, credentials or run-specific approvals into tracked developer docs, tests, examples or manifests.
- Use temporary directories/mocks for tests. Never probe real production connectors to test rate limits or missing-MCP behavior.
- Update code, schema/manifest, shared policies, samples, documentation and tests together when their contracts change. Keep host adapters thin; do not fork the workflow per host.
- Preserve explicit approval gates, selected-source-only MCP checks, bounded collection, automatic title selection in PREPARE, and Git protection of outputs. New/opted-in runs also require fresh agent-authored editorial packets and quality reports before review/approval. Never auto-fill real review attestations from test fixtures, execute example commands or silently disable the quality-contract flag; legacy runs are not retroactively rewritten. Input-guide reading/validation, missing-field-only intake and safe saved-state routing belong in shared harness logic, never as required boilerplate in the user's blog prompt.
- Keep `outputs/decisions.md` for article-run decisions. Keep reusable design history in `developer/SESSION_CONTEXT.md`; do not merge the two.
- After a meaningful change, append the requirement, implementation, compatibility implications and actual validation results to the handoff. Distinguish implemented behavior from suggestions or known gaps. Review new documentation for stale paths and prompts.

## Validation baseline

The initial handoff had **86 passing tests**, and the implicit-startup update had **97**. The latest article-quality implementation has **129 passing tests**, including blueprint/coverage/proof/reproducibility/figure/review/freshness cases. Script compilation, all harness JSON/manifest references, the five unchanged input samples and documentation links were also verified; see `developer/SESSION_CONTEXT.md` for context. All five simple input samples remain unchanged. These are recorded results, not a promise about a later checkout; rerun the suite. Fixtures in `tests/editorial_fixtures.py` simulate local contracts only—never reuse their synthetic sources/pass attestations for a real article. No third-party host or live MCP integration is certified by these tests.
