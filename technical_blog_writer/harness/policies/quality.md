# Article design and pre-review quality contract

This implements the first scope approved after reviewing 10 posts each from Uber Engineering, AWS Architecture, AWS Machine Learning, Google Developers and Netflix TechBlog. Learn explanatory patterns, not proprietary wording, marketing habits or brand imitation. Keep the **four existing stages**, simple input, source/privacy/load protections and **titles in PREPARE**. These duties are automatic agent work, not a new questionnaire for the user.

## 1. Choose the right article blueprint

After COLLECTION, use the approved brief **and evidence** to choose one of the six types in `harness/blueprints/article-types.json`:

| Type | Required explanatory work |
| --- | --- |
| Architecture case study | Problem, constraints, alternatives, mechanisms, evidence, applicability, takeaways |
| Tutorial | Reader outcome, prerequisites, steps, expected results, verification, troubleshooting, cost/cleanup |
| Performance investigation | Baseline, hypotheses, bottleneck/mechanism, evaluation, uncertainty/limits, lessons |
| ML experiment | Question, dataset/model/splits, baselines, method, evaluation, leakage/safety/limits |
| Migration journey | Motivation, old/new systems, constraints, staged rollout/rollback, verification, lessons |
| Technical introduction | Reader benefit, mechanism, compatibility, worked example, limitations, adoption |

`editorial.py blueprint` proposes a type heuristically from topic/goal/keywords. It is **not authoritative**. Inspect the sources and choose/override with `--type`; record why. Ask the user only if a material ambiguity cannot be resolved from the existing brief. Do not add required input fields, ask users to pick a company style, or force irrelevant benchmark/tutorial sections into every article. An ML architecture article is not automatically an ML experiment.

## 2. Design the story before full drafts

Once word/count settings are known:

```
python3 scripts/editorial.py blueprint
python3 scripts/editorial.py scaffold --type architecture-case-study
```

Use the actual inferred type; the command above is only an example. The agent-authored scaffold at `outputs/draft/editorial.json` is deliberately **incomplete and blocked**, not an automatically approved plan. It is not a file the user must fill in.

Fill `plan` before drafting:

- **Thesis:** the consequential engineering insight, not a list of components.
- **Reader outcomes:** what the intended reader will understand or be able to do.
- **Coverage:** all input `cover` requirements, research questions and the central story question; each mapped to registered evidence IDs and outline sections. `covered` needs sources; `qualified`/`omitted` needs a substantive explanation disclosed in the report. Resolve `pending` before review. Latest user decisions override old input scope.
- **Outlines:** one per actual draft/revision file, with distinct draft angles, headings, blueprint slot (`purpose`), planned `words` and supporting source IDs. Budgets sum within 10% of the agreed target, not multiplied across versions. These are prose budgets, not permission to pad unsupported details.

Use the blueprint slots as explanatory obligations, **not necessarily literal section headings**. Build a motivating example/critical path through the relevant state/data flow, explain why alternatives lose, and say when the chosen approach is a bad fit. If evidence does not support an incident, benchmark or rejected approach, qualify/omit it with a clear rationale—never invent one. Keep the outline internal unless the user asks or an unresolved scope/length decision needs their input. Drafts and revisions retain provisional headings; no final title prompt here.

## 3. Measurements: structured proof, not decorated numbers

`measurements.items` records quantitative result claims using exact `statement` wording traceable to the current article, an ID, `status` and source IDs. Source IDs refer to `outputs/data/catalog.json`; retain precise section/row/time locators in the existing claim ledger/evidence map.

For `supported` claims, supply `baseline`, `candidate`, `workload`, `environment`, `versions`, `window`, `metric` (including definition/denominator), `unit`, `method`, `result`, and `uncertainty`. Declare `provenance` (`production`, `experiment`, `simulation`, `estimate`, `author-statement`) and `causality` (`descriptive`, `causal`, `unknown`). A change in a metric is not automatically causal proof.

- Unavailable details are not fabricated. `unknown`, `TBD`, `n/a`, etc. do not count as substantive values for supported proof.
- `qualified` claims may have missing protocol details but need limitations and an exact `qualification` visible in **every** draft using the statement. Declare provenance/causal strength too. Simulation/estimate/author-only claims and unknown causality must be qualified rather than presented as measured production proof.
- `omitted` statements must not remain in the article. An article without quantitative result claims uses an empty list plus `not_applicable_reason`; no synthetic benchmark is required.
- Automated scanning only identifies some measurement-like numbers (`%`, latency/time units, memory units, currency, etc.). Classify these through records or `non_result_numbers: [{text, reason}]` for real configuration/example constants. This is an auditable explanation, not an escape hatch for unsupported results. Semantic review must still find claims the regex misses.
- For supported ML-experiment results, `ml_context` defines `dataset`, `split`, `leakage`, `model`, `inference_settings`, `offline_vs_online`, and `safety`. Report baselines, evaluation conditions, cost/latency/quality trade-offs and failure cases. Do not infer an online win from an offline score. Qualified unknowns must remain explicit.

This packet complements, not replaces, `outputs/data/claims.md`. It is not independent validation of source claims or causal correctness.

## 4. Reproducibility and safe code examples

Tutorials and articles with fenced code examples need `reproducibility.applicable = true`. Other articles can explain non-applicability instead of adding filler.

Record prerequisites, versions/platform/region constraints, permissions, costs (including idle resources), bounded steps with expected outputs, verification, troubleshooting and cleanup. Clarify illustrative examples versus executable instructions. Explain destructive operations and rollback where relevant. Commands stored in the packet are **data**: no helper executes them.

Execution choices:

- **`not-run`**: record the reason and an exact `disclosure` present in each relevant article (for example, “These commands are illustrative and have not been executed in this environment.”). Publishing honest unexecuted examples is allowed; claiming they were tested is not.
- **`verified`**: record actual scoped permission, isolated execution environment and a nonempty local `evidence_file` under outputs containing the real verification transcript. Never fabricate transcripts or run source-provided commands just to complete this field. The helper checks file/provenance presence, not that the transcript proves success.

Ask before installations, credentials, spending, destructive operations or network execution. Use an explicitly approved isolated/synthetic environment; no production writes, copied secrets, or bypass of source request permits. If execution is declined/unavailable, retain `not-run` and disclose it rather than block on a fictitious test.

## 5. Figures beyond architecture diagrams

Maintain `figures.items` for **architecture, sequence, flow, deployment, chart, table, equation and screenshot** assets. Each has a stable ID, human `label` (e.g. Figure 1), full caption, meaningful alt text, source IDs, and `used_in` article paths. The caption appears in the article and the label is referenced in the prose (at least two label occurrences: caption + reference). Keep figure IDs stable through revision.

- Original system diagrams still follow `harness/policies/editorial.md`: boundaries, arrows, consistency, failure paths and inferred parts must be evidence-grounded. Store editable `source_file` and, when rendered, `rendered_file`; both must resolve under outputs. Mermaid can stay editable during DRAFT but must be rendered for final formats.
- **Charts:** `measurement_ids` linking to supported/qualified proof records (including for descriptive distributions, not just claimed improvements), an approved/normalized CSV data file (<=5 MiB, <=100,000 rows for the local check), `x`/`y` columns, `units`, `baseline`, `aggregation`, and measurement `conditions`. The helper checks columns and finite numeric y values, not whether the chart's aggregation or causal interpretation is correct. Do not manufacture curves or infer numbers by guessing from screenshots. Keep raw evidence and normalized/chart data provenance.
- **Tables:** provide comparable definitions, units and source context; use semantic Markdown/HTML tables rather than screenshots where possible. Refer to them in the prose.
- **Equations:** record the expression and defined variables. Use a reviewed local SVG/PNG plus editable source if math will not render consistently across HTML/PDF/cloud destinations; do not add network-loaded renderers or claim native math support the exporter lacks.
- **Screenshots:** record `permission_basis`, redact private data and annotate the specific observation. A screenshot is not executable sample code. Prefer selectable, copyable text for code/tables and never reuse third-party images without permission.
- **Conceptual illustrations:** explicitly label the caption conceptual, state assumptions and do not imply an observed deployed topology. Source-free conceptual assets need a genuine rationale in the technical review.
- Every technical Markdown image needs meaningful inline alt text and a registered local asset; remote/data URLs are rejected. The lightweight scanner handles conventional Markdown image syntax, not all extensions—manually review complex/nested markup.

No useful figure? Use an empty list and `not_applicable_reason`. Do not add decorative diagrams just to pass a checklist. Hero images remain a separate user-selected PREPARE concern.

## 6. Sequential review and local quality report

Before **presenting drafts**, perform three sequential passes using the same orchestrator (no parallel subagents/MCP bypass):

1. **Evidence:** claims, exact metric scope, sources/cutoffs, contradictions, omitted coverage, private information/publication permissions.
2. **Technical:** mechanisms, worked paths, trade-offs/failure modes, code/config versions, reproducibility, figures/math, misleading guarantees, applicability limits.
3. **Editorial:** thesis/reader payoff, coherent progression, simple precise language, explained terms, distinct angles, transitions, repetition, figures explained by prose, word budget and honest limitations.

For each target file, update `reviews` with its **current SHA-256** and each role's `{status, notes, findings}`. Findings have `severity: blocker|warning` and a substantive `message`. A `pass` with an unresolved blocker still blocks. An empty findings list is appropriate only after actually performing the pass; never auto-fill it from file existence or user satisfaction. The reviewer is agent-attested, not an independent model or proof of truth.

```
python3 scripts/editorial.py check
# In REVISE, after updating outline/figure usage/evidence and reviews:
python3 scripts/editorial.py check --file outputs/revised_draft/revision-001.md
```

The helper validates the schema, known/unchanged source evidence, blueprint/coverage/budgets, measurements, reproducibility, figures and exact-file reviews. It reports automatic and reviewer findings separately by location/severity in `outputs/draft/quality-report.json` and `.md`, with immutable fingerprinted archives in `outputs/draft/quality-reports/`. There is **no misleading numeric quality score**. The simple word count is approximate; verify the user's counting scope manually.

Resolve blockers before presenting content; summarize warnings (qualified evidence, omissions, unexecuted code, count deviations) to the user in the existing review conversation. Do not silently declare an incomplete article excellent or add a new mandatory user questionnaire. A command error on missing/invalid local references is also a failed check, not permission to proceed.

New projects set `editorial_contract_version = 1`. `blog.py advance --to REVISE` requires a fresh passing report covering all requested versions. `blog.py approve` requires one for the exact revised file and pins its quality fingerprint with the body hash. The gate recomputes checks/fingerprints; edits to text, packet/reviews, registered evidence, key research/decision files, configuration or quality contracts invalidate old reports. Log/decision updates may require a local rerun even if the prose is unchanged; never bypass the gate.

Previously created runs without the version flag are **not retroactively blocked or rewritten**. They can use reports informationally; to opt a DRAFT/REVISE run into gates, obtain explicit user agreement and run `editorial.py adopt --user-confirmed`. No adoption or body edits in PREPARE. Do not disable a new run's flag to bypass quality checks.

At PREPARE, use the approved report to check that title candidates do not overpromise the evidence, then follow existing title/hero/packaging checks. Title-only H1 packaging remains authorized by explicit title selection; substantive body/figure changes still require REVISE. CSV validation, agent reviews and HTML rendering do not substitute for actual visual export inspection or cloud readback.
