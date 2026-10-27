# User-selected sources (no mandatory vendor stack)

Read this before MCP readiness checks. Never assume a user has Google Workspace, Slack, Atlassian, or Microsoft 365. First read `harness/policies/input.md`. If input already lists source choices/access modes, use those in the combined confirmation; present this menu only for missing choices or requested changes. Do not replay known answers just because connectors are available. Users can choose multiple items, name their own, or use only local files/pasted text.

> Which sources should I use for this blog? Select any of these, or list your own:
>
> - **Documents / knowledge:** SharePoint, OneDrive, Microsoft Word / Office / Microsoft 365, OneNote, Google Drive / Docs, Confluence, Notion, Dropbox, Box.
> - **Spreadsheets / data:** Microsoft Excel, Google Sheets, CSV files or other data exports.
> - **Chat / meetings:** Microsoft Teams, Slack, Cisco Webex, Zoom transcripts, Google Chat.
> - **Issues / planning:** Jira, Azure DevOps, GitHub Issues, GitLab Issues, Linear, Asana.
> - **Code / technical references:** GitHub, GitLab, Bitbucket, local repositories, public websites/documentation.
> - **Local / manual:** uploaded files, exported documents, PDFs, diagrams, pasted notes or transcripts (no MCP required).
> - **Other:** name any service, repository, internal system or source you use.
>
> For each choice, will I access it through this core harness's MCP connections, or will you provide files/pasted content? Please share the authorized links, sites, folders, channels, projects and date range. You do not need to configure services you do not select.

If a user has already listed sources, summarize that list and ask them to confirm it or add others; do not make them answer the entire menu again. An existing project without a saved selection needs one combined confirmation of input-supplied sources (or the menu if absent) on resume; do not infer selection from old connector errors or sample documentation.

Clarify suite names. For “Microsoft Office,” ask which Word/Excel/OneNote documents and whether they are local, on SharePoint, or on OneDrive. For Teams/Webex ask whether channels, meeting transcripts or shared attachments are intended. A connector for one service does not imply access to all services in the suite. Preserve the user's source labels and map each label to the discovered tool/server capabilities; do not invent a universal Microsoft/Google/Atlassian connector.

## Navigation consent

After source selection, prefill input navigation settings and include them in the combined confirmation using the recursion/load prompt in `harness/policies/collection.md`. Ask whether to inspect child pages, in-page links, both, or roots only, with source boundaries, relevance and hard budgets. A seed link is not authorization to crawl its entire tenant, all channels, external domains, or every linked service. Default proposals still require an explicit answer. Use the same bounded policy for custom sources and local linked documents.

## Persist the plan

Record the confirmed plan using `blog.py select-sources` plus detailed scope/tool mappings in `outputs/decisions.md`. Names are open-ended, not an enum. Use exactly these source labels in `mcp-decision --connector` (not an unrelated server alias). The CLI permits MCP warnings only for selected MCP sources or selected publication destinations, and rejects manual-only/unselected services.

```
python3 scripts/blog.py select-sources \
  --mcp SharePoint --mcp "Microsoft Teams" --mcp Webex \
  --manual "Word and Excel exports" --user-confirmed
```

This replaces the selected plan, so include every source/destination the user still wants. Confirm before adding/removing sources. Keep already collected evidence with its provenance; deselection means do not make further reads, not delete evidence. Reconfirm whether previously collected content remains in scope. A plan change is explicit scope consent; readiness/skip decisions must be assessed against the current plan, not automatically copied from removed sources. On an unchanged plan/resume, retain previously accepted skips without repeated prompts.

## Separate research sources from publication destination

The original Google Doc deliverable does not imply permission to read Google Docs or require a Google MCP during collection. Separately ask whether the user wants the Google Doc cloud export, local-only delivery, or another cloud target. Do not assume a Google account for a Microsoft-only user. Add a destination only after they explicitly select it:

```
python3 scripts/blog.py select-sources \
  --mcp SharePoint --mcp "Microsoft Teams" \
  --destination "Google Docs" --user-confirmed
```

Only explicitly selected cloud destinations receive capability/authentication warnings; this is separate from research-source selection. Do not select Google Docs automatically to satisfy the original format list. Markdown/HTML/PDF remain local. The existing automated cloud-pointer/completion tooling supports Google Docs only. If the user selects Microsoft Word/OneDrive, SharePoint, or another custom target, confirm an authorized MCP/manual import workflow and any extra format requirements; do not claim the built-in exporter supports them. If Google Docs is not selected, hand off the actual requested local/custom artifacts, state that the original Google Doc/all-four-format requirement was not delivered, and do not invoke the four-format `complete` command. Do not warn about missing Google MCPs in that case.

## Evidence from any selected source

Use the same provenance/claim checks regardless of vendor. Capture stable URL/path and item ID, title, version, retrieval time, section/page/cell/message locator, confidentiality and access limitations. For SharePoint/OneDrive/Office retain site/library/file/version and sheet/range details; for Teams/Webex retain channel/meeting/thread/message context, timestamps and transcript limitations. Meeting transcripts and AI summaries may contain errors—validate technical claims against primary evidence. Export only authorized information and minimize personal data. Follow `harness/policies/mcp.md` only for selected MCP-backed capabilities; manual sources never trigger an MCP warning.
