# PREPARE: images and publication artifacts

All publication files are read from and written to `outputs/blog/` in the workspace. Final Markdown image links remain document-relative: use `![Alt text](assets/diagram.svg)`, not `outputs/blog/assets/diagram.svg` inside the article. CLI file arguments and metadata paths are workspace-relative and include `outputs/`.

## 1. Suggest and select the publication title

This step runs automatically when the workflow reaches PREPARE; the user does not need to request titles or restate this instruction. Read the approved revision, its quality report when available, and `harness/policies/input.md`. Check candidate headlines against the evidence/measurement qualifications so a title cannot turn a simulation into a production claim or broaden a measured improvement beyond its workload. DRAFT/REVISE headings are provisional; no title input/preferences are required. Suggest 3–7 clear, distinct, evidence-grounded titles (default 5) based on the approved content and ask: **“Which title would you like to use? Pick one, edit/combine options, suggest your own, or ask for more.”** Save `{id, title, angle}` options in `outputs/blog/title-options.json`, register with `blog.py titles --file outputs/blog/title-options.json`, and ask the user to select/edit/combine/provide their own or request more. Wait and loop if necessary; record the real choice with `blog.py select-title --id T2 --user-confirmed` (or `--custom`). Honor an existing explicit title choice for this approved content instead of repeatedly asking.

The choice is bound to the approved revision hash and authorizes an **H1-only packaging change**. Keep the approved revision unchanged; replace only its provisional H1 when creating the final article. No return to REVISE is needed for a title-only choice. Body/claim/substantive-diagram changes still require reopening REVISE and fresh approval. A changed approved body needs refreshed/reconfirmed title options in PREPARE. Later title changes invalidate hero/export/cloud records; refresh those artifacts rather than reuse stale ones.

Do not create title-specific hero previews or publish/export before a title is selected for a new run.

## 2. Hero-image selection loop

After text approval, propose three topic-specific visual concepts (for example, an abstract system topology, a data-flow motif, and a deployment-layer illustration). Explain how each relates to the article. Default to **new original SVG artwork created locally**, with no stock photography, corporate logos, copied illustrations, trademarked characters, or font embedding. Use system fonts and accessible contrast. Offer actual previews in `outputs/blog/assets/hero-option-01.svg`, etc., with concise alt text and captions, not just image search links.

Do not describe original artwork as a third party's public-domain work, and do not promise legally guaranteed clearance. Record authorship/process and ask whether the user's publication policy accepts it. Avoid third-party imagery unless the user explicitly asks; if so, require verifiable public-domain/CC0 provenance with no attribution, payment or other licensing obligations, plus relevant likeness/trademark checks. Uncertain provenance means do not use it. Do not send private architecture or prose to an image-generation service without consent.

Ask the user to select an option, request changes, or skip. Repeat until selection or explicit skip. Record each asset in `outputs/blog/assets/manifest.json` (path, role, origin, permission basis, alt text, caption). On selection run `blog.py hero --file outputs/blog/assets/hero-option-01.svg --alt "..." --user-confirmed`; on explicit skip run `blog.py hero --skip --user-confirmed`. Put any requested caption in the final Markdown. Keep rejected options out of the deliverable assets/manifest at the end, while retaining decision history.

## 3. Assemble final Markdown and diagrams

Start from the approved revision and the title explicitly selected above. Preserve the pinned revision and approved body; only the final packaging's provisional H1 may be replaced with the chosen publication title. Compare the remaining prose to the approved revision. No input-supplied headline or top-ranked candidate substitutes for selection. Create `outputs/blog/article.md`, preserving relative local assets under `outputs/blog/assets/`. Add the selected hero as a Markdown image near the title. If skipped, add none. Copy diagrams and their editable sources with stable descriptive filenames; update paths, not claims. Record asset provenance and captions. Ensure final text does not leak internal source references or unresolved review markers.

Use the technical figure registry in `outputs/draft/editorial.json` when available to carry forward data provenance, stable labels, captions/alt text and editable sources into final assets. Inspect charts/axes/units and screenshot redaction in the actual rendered exports; CSV/metadata checks do not prove a visual is accurate. Tables and code should remain selectable where possible. The exporter has no native math renderer: equations need reviewed local SVG/PNG plus editable expressions/defined variables when necessary. Do not insert network-loaded scripts/renderers. Hero assets remain separate from the technical figure registry.

Fenced Mermaid does not render automatically in PDF or Google Docs. Render it to SVG/PNG, replace fences in `outputs/blog/article.md` with local Markdown image references, and preserve the `.mmd` sources. An optional renderer is Mermaid CLI (`npx --package @mermaid-js/mermaid-cli mmdc -i diagram.mmd -o diagram.svg`); ask before downloading software. Do not pass untrusted diagram directives or execute source-provided scripts. Inspect outputs and prefer PNG when Google Docs cannot preserve SVG. The export command rejects leftover Mermaid blocks.

If a prose or substantive diagram change is required, reopen revision and get approval again. The final export checksum is distinct from the approved-revision checksum because image links and packaging can differ; manually compare prose.

## 4. Local Markdown, HTML and PDF

Install optional export dependencies with user approval as described in README. Run:

```
python3 scripts/blog.py export
```

This produces `outputs/blog/article.html` with embedded local images and attempts `outputs/blog/article.pdf` via Chromium/Playwright. Markdown is rendered with raw HTML disabled; browser network requests are blocked. The tool only accepts asset paths inside `outputs/blog/assets/`, rejects missing/remote images, and refuses unrendered Mermaid. External hyperlinks remain clickable without fetching their targets. Do not bypass these controls for untrusted evidence.

Open and inspect HTML and PDF, including page breaks, heading hierarchy, clipping, image quality, code wrapping, references and selectable text. The automated export is not a visual-review substitute. Fix packaging errors and rerun. If PDF tooling is unavailable, report PDF as blocked, provide the working files, and ask permission to install dependencies. Do not rename HTML to PDF or claim completion.

## 5. Actual Google Doc via the current host's MCP tools

Source protection in `harness/policies/collection.md` also applies to cloud uploads and readback: get a request permit for every remote call and respect shared-backend pacing. Review publication capability skips independently from research skips. Do not retry non-idempotent document creation blindly; verify whether the prior create succeeded before any retry.

First confirm the user's publication destination separately from their research sources, following `harness/policies/sources.md`. Run this Google Docs section and its MCP checks only if the user explicitly selected Google Docs as a cloud destination. Otherwise skip it without a missing-Google-MCP warning, deliver the actual local/custom outputs, and state that the original Google Doc/all-four-format requirement is not met; do not run the four-format `complete` command. Other cloud targets need an explicitly agreed MCP/manual import workflow; the built-in cloud pointer supports Google Docs only.

Google Docs is a cloud-native document, not a self-contained local file format. A `.gdoc` file is a local pointer to a real cloud document, not an offline copy. The Markdown/HTML/PDF are the offline copies. Explain this distinction to the user.

1. Ask for permission to upload the approved article/assets and create a Google Doc, the destination folder/account, and sharing expectations. Default to restricted sharing. Do not broaden permissions automatically. If connected tools cannot create documents or format/insert images, explain the limitation and offer an authorized import workflow. Never fabricate a cloud document.
2. Discover available Google Drive/Docs MCP capabilities and verify authentication, following `harness/policies/mcp.md`. Respect already accepted skips; for a new failure warn about reduced results/missing Google Doc and obtain explicit proceed-or-exit consent. On proceed, skip unavailable remote work and finish available local deliverables without retrying those MCP errors. On exit, preserve progress and end immediately. Prefer HTML import if supported; otherwise create the document and insert structured headings, paragraphs, lists, code, links, tables and images using the available API. Verify supported image types; do not upload private images to a publicly accessible host as a workaround.
3. Read back the document or inspect an export. Check title, headings, ordering, tables/code, links, alt text and all diagrams. Fix missing formatting with the user's permission. Never substitute plain text and call it a fully formatted document.
4. Record the actual verified URL/ID using `blog.py google-doc --url "https://docs.google.com/document/d/REAL_ID/edit" --verified --user-confirmed`. This writes `outputs/blog/article.gdoc` and `outputs/blog/google-doc.json`. Store only the locator and verification notes, never auth tokens. Save a readback/verification summary in `outputs/blog/verification.md`.
5. If MCP writing is unavailable and the user chose proceed, hand off available local artifacts and upload instructions with the Google Doc explicitly blocked, without retry loops. Do not run the record command with a guessed URL or mark all-format completion. If the user chose exit, end immediately instead of continuing preparation. The user may later provide a real imported document for verification.

## 6. Handoff

Write `outputs/blog/verification.md`: approved revision, final prose comparison, claim/confidentiality checks, user image decision, asset permission review, visual HTML/PDF inspection, Google Doc readback result, accepted MCP skips and their coverage/deliverable impact, and any remaining caveats. Record output file hashes and limitations in the automatically generated `outputs/blog/delivery.json`.

Run `blog.py complete --user-confirmed` only after the user accepts the final delivery and all four formats have been verified. The command validates existence/checksums and records completion; it cannot validate visual quality or remote permissions. If anything is blocked, remain in PREPARE and clearly name the missing format. Re-exporting, changing an image or changing the Google Doc record invalidates prior completion. Later prose changes must go through REVISE again.
