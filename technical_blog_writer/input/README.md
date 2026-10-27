# Simple blog briefs

Pick an example, copy it to **`input/blog.json`**, and edit it. Examples use placeholder URLs/files—replace them before collection. Personal input files are Git-ignored; the explicitly listed samples are safe to track.

| Example | Use case |
| --- | --- |
| `input/input_sample.json` | Part 1 of a three-part customer-sandbox series; latest preferences from the original run, with sanitized links |
| `input/sample_single.json` | One public engineering blog, GitHub + Confluence |
| `input/sample_microsoft.json` | One internal migration article, SharePoint + Teams + Azure DevOps |
| `input/sample_local_tutorial.json` | One tutorial from local files only; no MCP needed |
| `input/sample_custom_sources.json` | One operations article, Webex/custom sources + Office exports |

## A small brief is enough

```json
{
  "topic": "How we made background jobs safe to retry",
  "audience": "Backend developers",
  "words": 1200,
  "publication": "public",
  "sources": {
    "GitHub": ["https://github.com/example/job-service"]
  }
}
```

No version marker, nested `blog`/`draft`/`research` blocks, source objects, title preferences or research notes are required. Omit anything unknown; the harness asks only for missing essentials and scope/permission decisions.

### Common fields

- `topic`, `audience`, `goal`, `words`: the subject, readers, purpose and target words per draft.
- `sources`: service name → list of starting links. Any name is allowed; these are MCP-backed choices. An empty list selects a service for scoped search without supplied links.
- `files`: local file paths (manual evidence, no MCP). For named manual sources use `manual_sources`, e.g. `{"Office exports": ["notes.docx", "cost.xlsx"]}`. Local paths are workspace-relative; URLs still require real access.
- `keywords`, `cover`, `exclude`: search terms, required details and what to leave out.
- `publication`: `public` or `internal`; `cutoff_date`/`from_date`: optional YYYY-MM-DD limits.
- `scope`: a short boundary description. A starting link does not authorize an entire tenant.
- `series`: omit for a **single blog**. For one part of a series: `{"part": 1, "total": 3, "roadmap": ["Initial design", "Cost improvements", "Developer environments"]}`. One run writes only the current part.
- `follow`: `both`, `children`, `links` or `none`; `max_depth`: optional recursion limit.
- `store_confidential_locally`: storage preference, not permission to publish confidential details.

**Proposed defaults:** single blog, two alternative drafts, body/caption word count excluding references/code, practical technical depth, clear prose, local Markdown/HTML/PDF, and the existing bounded collection policy (both children/links, depth 2). The agent shows defaults in one combined scope/storage/navigation confirmation before remote work. It never assumes confidential-storage or upload permission.

Optional extras, only when useful: `drafts` (2 or 3), `depth`, `tone`, `questions`, `count_scope`, `outputs`, `cloud_destinations`, free-form `notes`, per-source `source_scopes`, advanced `source_settings` (backend/scope prefixes) and `limits` (collection budgets). You do not need to fill these in. Choosing `google_doc` in `outputs` explicitly requests a Google Docs publication destination, not Google research access or upload permission. Other cloud targets still need an agreed import workflow.

Article type, thesis/outline/section budgets, evidence coverage, measurement/reproducibility records, figure data and quality reviews are **agent-generated internal work**, not additional required input fields. The harness infers the blueprint from your brief and sources, checks for unsupported claims/unexecuted examples and shows material warnings in the normal review conversation. It does not run code or deploy resources merely to verify an article. You still only need the short startup prompt below. See `harness/policies/quality.md` for details.

**Do not supply `title_preferences` or a title.** The harness suggests 3–7 titles from the revised content in **PREPARE**, asks you to choose/edit/provide one, and then creates title-specific hero options and final artifacts. Drafts use provisional headings.

## Run it

```sh
python3 scripts/blog.py inspect-input --file input/blog.json
python3 scripts/blog.py init --input input/blog.json
```

Or tell any supported core harness:

> Start a technical blog using input/blog.json.

The harness reads this syntax/semantics guide, validates/prefills the brief, asks only for missing/conflicting information and real approvals, preserves any existing run, and suggests titles in PREPARE automatically. You do not need to include those instructions in your prompt.

The read-only `blog.py startup --input input/blog.json` router validates a new brief or uses existing saved state without reopening/replaying input. The agent invokes it automatically; it never initializes a project or clears stopped state. `inspect-input` is an independent validation tool. Plain `init` also detects workspace `input/blog.json`; examples are **never auto-loaded**. After the actual combined scope/navigation/storage confirmation, the agent uses `apply-input --user-confirmed` and the normal MCP/collection checks. A named input can live elsewhere; with a separate workspace use an absolute helper path and `--root WORKSPACE` before the subcommand.

The original simple brief is snapshotted at `outputs/input.json`; normalized internal preferences live in `project.json`. Latest `outputs/decisions.md` entries override the original brief on resume. Never replay changed files over an existing run. Older nested v1 inputs remain readable for compatibility; old title hints are ignored, not used to choose a headline.

Schema: `harness/schemas/input.schema.json`. Policy: `harness/policies/input.md`. No input can supply runtime approvals or skip missing-MCP proceed/exit, review/satisfaction, title/hero choice, disclosure checks or upload authorization.
