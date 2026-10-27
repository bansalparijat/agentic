# Editorial and technical quality bar

Apply the structured workflow in `harness/policies/quality.md` as well as this voice/accuracy policy. Select a blueprint from `harness/blueprints/article-types.json` based on the article's purpose and evidence—not brand imitation. The generated editorial packet and quality report operationalize these checks; they do not prove truth or replace human satisfaction.

## Voice and substance

Write original prose in clear, simple English. Explain acronyms at first use. Prefer concrete examples and short sentences without removing technical detail. Introduce the problem before the solution. Each section should explain why a decision mattered, how it works, and what it costs. Avoid hype, unsupported superlatives, vendor promotion, and vague claims such as “massive scale.”

Use representative request/data flows to make mechanisms understandable. Cover requirements, constraints, alternatives, interfaces, consistency, scaling, latency/throughput, failure handling, deployment/migration and observability when relevant—not as mandatory filler. Distinguish measured outcomes from expected benefits. Never manufacture benchmark numbers, code, quotations, incident histories, customer stories, or production experience.

Word-count targets apply to each version, not the sum of versions. The CLI provides approximate counts; verify the agreed inclusion/exclusion of code, references, captions, and diagrams manually. A shorter honest article is better than unsupported padding; ask to adjust the target when sources cannot support it.

## Evidence and review

- Every substantive factual claim needs a traceable source or a clearly identified author explanation/hypothesis. Maintain the evidence map through revision.
- Quantitative claims need units, workload, baseline, measurement period, conditions and caveats. Do not compare incomparable measurements.
- Cite stable, approved references. Do not expose internal document titles, URLs, employee names, customer identifiers or private infrastructure in public output without explicit authorization.
- Mark unresolved facts in review files. Resolve, remove, or clearly qualify them before final approval. Search for TODO/TBD/FIXME and unsupported absolutes.
- Confirm permission for every reused quote, diagram and image. A publicly viewable page is not automatically licensed for reuse.
- Present sufficient detail to be useful without disclosing secrets, credentials, security-sensitive topology or proprietary information.

## Figures and diagram checklist

Architecture/sequence/flow/deployment diagrams, charts, tables, equations and annotated screenshots have distinct provenance/validation requirements in `harness/policies/quality.md`. Register technical figures in the agent-authored packet with captions, meaningful alt text and prose cross-references. Charts need approved numeric data, axes/units, baseline, aggregation and conditions; equations need defined variables and export-compatible rendering. Prefer selectable code/tables over screenshots. Never fabricate graphs, data or execution screenshots.


Use a diagram only when it improves understanding. Prefer original Mermaid or SVG diagrams supported by the evidence. Identify whether it is physical deployment, logical architecture, runtime sequence, or conceptual flow; do not mix them without labels.

Check component names, ownership/trust boundaries, arrow direction, protocols, sync vs async paths, reads/writes, queues, retries, errors and source-of-truth storage against the cited sources. Do not imply guarantees (exactly-once, failover, strong consistency, zero downtime) that sources do not establish. Include legend, caption, alt text, and a note when intentionally simplified. Unknown paths must be removed or explicitly marked as unverified for review, not silently completed.

Keep editable sources plus rendered SVG/PNG. Inspect actual rendered diagrams for clipped text, unreadable contrast, accidental identifying information and mobile readability. Rendering successfully is not technical validation.

## Final review checklist

- Correct for the intended audience and publication scope.
- All important supported details covered; assumptions and limitations visible.
- Distinct draft structures, original language, no purported company endorsement.
- Technical terms, units, examples, code and diagrams consistent.
- User-selected revision and explicit satisfaction recorded.
- No unresolved confidential-data or asset-permission issues.
- Sequential evidence/technical/editorial passes completed on exact file hashes; local quality report fresh, blockers resolved, warnings disclosed (new/opted-in runs are CLI-gated).
- Final export visually inspected; links, images, captions and headings work. Local validation is not visual or independent factual verification.
