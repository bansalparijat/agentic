#!/usr/bin/env python3
"""Local editorial planning/quality checks. Never calls models/MCP or executes examples."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

from intake import validate_node

ROOT = Path(__file__).resolve().parents[1]
PACKET = "outputs/draft/editorial.json"
REPORT = "outputs/draft/quality-report.json"
BLUEPRINTS = ROOT / "harness/blueprints/article-types.json"
SCHEMA = ROOT / "harness/schemas/editorial.schema.json"
ROLES = ("evidence", "technical", "editorial")
MEASUREMENT_FIELDS = ("baseline", "candidate", "workload", "environment", "versions", "window", "metric", "unit", "method", "result", "uncertainty")
ML_FIELDS = ("dataset", "split", "leakage", "model", "inference_settings", "offline_vs_online", "safety")
METRIC = re.compile(r"(?<!\w)(?:\d[\d,.]*\s*(?:%|ms\b|milliseconds?\b|seconds?\b|req/s\b|GiB\b|GB\b)|\$\s*\d)", re.I)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def local(root, name):
    path = (root / name).resolve()
    boundary = (root / "outputs").resolve()
    if not boundary.is_relative_to(root.resolve()) or not path.is_relative_to(boundary):
        raise ValueError("Editorial references must stay inside outputs/ (including resolved symlinks).")
    if not path.is_file() or not path.stat().st_size:
        raise ValueError(f"Missing/empty editorial reference: {name}")
    return path


def text_ok(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {"todo", "tbd", "unknown", "n/a", "not available", "not reported"}


def has_code(text):
    fence = None
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if not match:
            continue
        marker, info = match.groups()
        if fence:
            if marker[0] == fence[0] and len(marker) >= len(fence) and not info.strip():
                fence = None
        else:
            if info.strip().lower() != "mermaid":
                return True
            fence = marker
    return False


def infer(state, requested="auto"):
    types = load(BLUEPRINTS)["types"]
    if requested != "auto":
        if requested not in types:
            raise ValueError("Unknown article blueprint")
        return requested, "Agent selected this blueprint after examining the brief/evidence."
    intake = state.get("intake", {}).get("blog", {})
    words = " ".join([state.get("topic", ""), intake.get("purpose", ""), *intake.get("keywords", [])]).lower()
    scores = {kind: sum(signal in words for signal in value["signals"]) for kind, value in types.items()}
    kind = max(scores, key=scores.get) if any(scores.values()) else "architecture-case-study"
    return kind, "Heuristic proposal from topic/goal/keywords; the agent must verify against evidence, not ask the user unless ambiguous."


def targets_for(state, supplied=()):
    if supplied:
        targets = list(supplied)
    elif state["stage"] == "DRAFT":
        settings = state.get("draft_settings") or {}
        if "versions" not in settings:
            raise ValueError("Resolve draft settings before editorial checks.")
        targets = [f"outputs/draft/version-{i:02d}.md" for i in range(1, settings["versions"] + 1)]
    else:
        raise ValueError("In REVISE specify --file outputs/revised_draft/revision-NNN.md.")
    for name in targets:
        pattern = r"outputs/draft/version-\d{2}\.md" if state["stage"] == "DRAFT" else r"outputs/revised_draft/revision-\d{3,}\.md"
        if not re.fullmatch(pattern, name):
            raise ValueError("Quality targets must be stage-appropriate draft/revision Markdown paths.")
    if len(set(targets)) != len(targets):
        raise ValueError("Duplicate quality targets")
    return sorted(targets)


def template(state, kind):
    slots = load(BLUEPRINTS)["types"][kind]["slots"]
    settings = state.get("draft_settings") or {}
    if not settings.get("words"):
        raise ValueError("Resolve the user's word target before scaffolding an outline.")
    targets = targets_for(state)
    budget = settings["words"]
    # Very short requested articles still need an explicit user-approved length
    # adjustment, not silently invented zero-word sections.
    if budget < len(slots):
        raise ValueError("Word target is too short for this outline; resolve it with the user.")
    outlines = []
    for name in targets:
        sections = [{"heading": slot.replace("-", " ").title(), "purpose": slot,
                     "words": budget // len(slots) + (i < budget % len(slots)), "sources": []}
                    for i, slot in enumerate(slots)]
        outlines.append({"file": name, "angle": "", "sections": sections})
    requirements = list(dict.fromkeys([*state.get("intake", {}).get("blog", {}).get("required_coverage", []),
                                      *state.get("intake", {}).get("research", {}).get("questions", [])])) or [""]
    return {"schema_version": 1,
            "plan": {"article_type": kind, "selection_reason": "", "thesis": "", "reader_outcomes": [],
                     "coverage": [{"requirement": r, "status": "pending", "sources": [], "sections": [], "note": ""}
                                  for r in requirements], "outlines": outlines},
            "measurements": {"items": [], "non_result_numbers": [], "not_applicable_reason": ""},
            "reproducibility": {"applicable": kind == "tutorial", "reason": "", "execution": {"status": "not-run", "reason": ""}},
            "figures": {"items": [], "not_applicable_reason": ""},
            "reviews": [{"file": name, "sha256": "", **{role: {"status": "blocked", "notes": "", "findings": []} for role in ROLES}} for name in targets]}


def evaluate(root, state, targets):
    root = root.resolve()
    findings, dependencies, texts = [], {}, {}

    def issue(message, location="packet", severity="blocker", origin="automatic"):
        findings.append({"severity": severity, "location": location, "message": message, "origin": origin})

    def track(name):
        path = local(root, name)
        dependencies[name] = sha(path)
        return path

    def need(value, location):
        if not text_ok(value):
            issue("Missing substantive value (do not invent it; qualify/omit if evidence is unavailable).", location)

    packet = load(track(PACKET))
    catalog_path = track("outputs/data/catalog.json")
    catalog = load(catalog_path)
    known = {entry["id"] for entry in catalog}
    for entry in catalog:
        path = track(entry["file"])
        if sha(path) != entry["sha256"]:
            issue("Registered evidence changed; preserve the original and register a new version.", entry["id"])
    for name in ("outputs/data/claims.md", "outputs/data/research-brief.md", "outputs/decisions.md"):
        track(name)
    for name in ("outputs/draft/evidence-map.md", "outputs/draft/diagram-notes.md"):
        if (root / name).is_file():
            track(name)
    for name in targets:
        texts[name] = track(name).read_text(encoding="utf-8")
    contracts = {str(path.relative_to(ROOT)): sha(path) for path in (
        BLUEPRINTS, SCHEMA, Path(__file__), ROOT / "scripts/intake.py",
        ROOT / "harness/policies/quality.md", ROOT / "harness/policies/editorial.md")}

    def refs(values, location, required=False):
        if required and not values:
            issue("Provide registered source IDs or explicitly qualify/omit this claim.", location)
        for value in values:
            if value not in known:
                issue("Unknown source ID: " + value, location)

    def finish():
        configuration = {k: state.get(k) for k in ("topic", "audience", "intake", "source_plan", "draft_settings")}
        fingerprint = digest({"dependencies": dependencies, "contracts": contracts, "configuration": configuration, "targets": targets})
        return {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "blocked" if any(f["severity"] == "blocker" for f in findings) else "pass",
                "targets": targets, "dependencies": dependencies, "contracts": contracts,
                "fingerprint": fingerprint, "findings": findings,
                "limitations": "Local checks plus agent-attested sequential reviews; not proof of factual correctness, execution, permissions or visual quality."}

    try:
        validate_node(packet, load(SCHEMA), "editorial")
    except ValueError as exc:
        issue(str(exc))
        return finish()
    plan = packet["plan"]
    blueprint = load(BLUEPRINTS)["types"][plan["article_type"]]
    for key in ("selection_reason", "thesis"):
        need(plan[key], "plan." + key)
    if not plan["reader_outcomes"]:
        issue("State what the reader will understand or be able to do.", "plan.reader_outcomes")
    for value in plan["reader_outcomes"]:
        need(value, "plan.reader_outcomes")
    if not plan["coverage"]:
        issue("Map the core research question/requirements to evidence and sections.", "plan.coverage")
    coverage = {row["requirement"]: row for row in plan["coverage"]}
    if len(coverage) != len(plan["coverage"]):
        issue("Duplicate coverage requirements.", "plan.coverage")
    for requirement in [*state.get("intake", {}).get("blog", {}).get("required_coverage", []),
                        *state.get("intake", {}).get("research", {}).get("questions", [])]:
        if requirement not in coverage:
            issue("Input required coverage is missing: " + requirement, "plan.coverage")
    for row in plan["coverage"]:
        need(row["requirement"], "plan.coverage")
        if row["status"] == "pending":
            issue("Unresolved required coverage: " + row["requirement"], "plan.coverage")
        refs(row["sources"], "plan.coverage", row["status"] == "covered")
        if row["status"] in {"qualified", "omitted"}:
            need(row["note"], "plan.coverage." + row["status"])
            issue("Coverage is " + row["status"] + ": " + row["requirement"] + ". Disclose this to the user.", "plan.coverage", "warning")
        elif not row["sections"]:
            issue("Map covered requirements to outline sections.", "plan.coverage")
    outlines = {outline["file"]: outline for outline in plan["outlines"]}
    if len(outlines) != len(plan["outlines"]):
        issue("Duplicate outline targets.", "plan.outlines")
    headings = {s["heading"] for name in targets if name in outlines for s in outlines[name]["sections"]}
    for row in plan["coverage"]:
        if row["status"] == "covered":
            if any(section not in headings for section in row["sections"]):
                issue("Coverage refers to a section absent from current outlines.", "plan.coverage")
            for name in targets:
                current_headings = {s["heading"] for s in outlines.get(name, {}).get("sections", [])}
                if not current_headings.intersection(row["sections"]):
                    issue("Map required coverage to this version's outline sections.", name)
    angles = [outlines[name]["angle"].strip().casefold() for name in targets if name in outlines]
    if len(targets) > 1 and len(set(angles)) != len(angles):
        issue("Alternative drafts need distinct substantive angles, not just different wording.", "plan.outlines")
    for name, text in texts.items():
        outline = outlines.get(name)
        if not outline:
            issue("Provide/update an outline for this target.", name)
            continue
        need(outline["angle"], name + ":angle")
        slots = {section["purpose"] for section in outline["sections"]}
        for slot in blueprint["slots"]:
            if slot not in slots:
                issue("Blueprint outline slot missing: " + slot, name)
        word_target = state.get("draft_settings", {}).get("words")
        if word_target and abs(sum(s["words"] for s in outline["sections"]) - word_target) > max(1, word_target * .1):
            issue("Section word budgets must match the agreed target within 10%.", name)
        for section in outline["sections"]:
            need(section["heading"], name + ":heading")
            refs(section["sources"], name + ":outline")
        if re.search(r"\b(?:TODO|TBD|FIXME)\b", text):
            issue("Unresolved review/placeholder marker in article.", name)
        if len(re.findall(r"^#\s+", text, re.M)) != 1:
            issue("Article needs exactly one provisional H1.", name)
        approx = len(re.findall(r"\b\w+\b", re.sub(r"(?s)```.*?```|~~~.*?~~~", "", text)))
        if word_target and abs(approx - word_target) > word_target * .1:
            issue("Approximate count differs from target by >10%; verify the agreed counting scope and avoid padding.", name, "warning")

    measurements = packet["measurements"]
    if not measurements["items"]:
        need(measurements["not_applicable_reason"], "measurements.not_applicable_reason")
    exclusions = measurements.get("non_result_numbers", [])
    for item in exclusions:
        need(item["text"], "measurements.non_result_numbers")
        need(item["reason"], "measurements.non_result_numbers.reason")
    for name, text in texts.items():
        for match in METRIC.finditer(text):
            covered = any(match.group() in item["statement"] and item["statement"] in text and item["status"] != "omitted" for item in measurements["items"])
            excluded = any(match.group() in item["text"] and item["text"] in text and text_ok(item["reason"]) for item in exclusions)
            if not covered and not excluded:
                issue("Measurement-like number is unclassified: " + match.group() + ". Record evidence or explain a non-result configuration/example number.", name)
    seen_claims = set()
    for item in measurements["items"]:
        location = "measurement:" + item["id"]
        if not item["id"].strip() or item["id"] in seen_claims:
            issue("Measurement IDs must be nonempty and unique.", location)
        seen_claims.add(item["id"])
        need(item["statement"], location)
        refs(item["sources"], location, item["status"] == "supported")
        relevant = [text for text in texts.values() if item["statement"] in text]
        if item["status"] == "omitted":
            if relevant:
                issue("An omitted measurement statement still appears in the article.", location)
            continue
        if not relevant:
            issue("Measurement statement is not traceable to current article wording.", location)
        if not item.get("provenance") or not item.get("causality"):
            issue("Declare measurement provenance and causal strength, including for qualified claims.", location)
        if item["status"] == "supported":
            for key in MEASUREMENT_FIELDS:
                need(item.get(key), location + ":" + key)
            if item.get("provenance") in {"estimate", "simulation", "author-statement"} or item.get("causality") == "unknown":
                issue("Estimates/simulations/author statements or unknown causality must be qualified, not presented as production proof.", location)
        else:
            need(item.get("qualification"), location + ":qualification")
            if not item.get("limitations"):
                issue("Qualified measurements need explicit limitations.", location)
            if any(item.get("qualification", "") not in text for text in relevant):
                issue("Show the exact qualification in every draft using this measurement.", location)
            issue("Qualified measurement requires editorial attention: " + item["id"], location, "warning")
        if plan["article_type"] == "ml-experiment":
            context = item.get("ml_context", {})
            for key in ML_FIELDS:
                if item["status"] == "supported":
                    need(context.get(key), location + ":ml_" + key)
    if plan["article_type"] == "ml-experiment" and not measurements["items"]:
        issue("An ML experiment needs measured or explicitly qualified evaluation evidence.", "measurements")

    repro = packet["reproducibility"]
    code_present = any(has_code(text) for text in texts.values())
    if not repro["applicable"]:
        need(repro["reason"], "reproducibility.reason")
        if plan["article_type"] == "tutorial" or code_present:
            issue("Tutorials/code examples need a reproducibility record; not-run is permitted with disclosure.", "reproducibility")
    else:
        for key in ("prerequisites", "versions", "permissions", "cost", "verification", "cleanup", "troubleshooting"):
            need(repro.get(key), "reproducibility." + key)
        if not repro.get("steps"):
            issue("Provide bounded steps and expected outputs.", "reproducibility.steps")
        for step in repro.get("steps", []):
            need(step["instruction"], "reproducibility.step")
            need(step["expected"], "reproducibility.expected")
        execution = repro["execution"]
        if execution["status"] == "verified":
            for key in ("permission_record", "environment"):
                need(execution.get(key), "execution." + key)
            track(execution.get("evidence_file", ""))
        else:
            need(execution.get("reason"), "execution.reason")
            need(execution.get("disclosure"), "execution.disclosure")
            if any(not execution.get("disclosure") or execution["disclosure"] not in text for text in texts.values()):
                issue("Disclose unexecuted examples in each current article.", "execution")
            issue("Examples were not run; do not claim runtime verification.", "execution", "warning")

    figures = packet["figures"]
    if not figures["items"]:
        need(figures["not_applicable_reason"], "figures.not_applicable_reason")
    seen_figures, registered_assets, diagram_targets = set(), set(), set()
    for figure in figures["items"]:
        location = "figure:" + figure["id"]
        if not figure["id"].strip() or figure["id"] in seen_figures:
            issue("Figure IDs must be nonempty and unique.", location)
        seen_figures.add(figure["id"])
        for key in ("label", "caption", "alt"):
            need(figure[key], location + ":" + key)
        refs(figure["sources"], location, not figure.get("conceptual", False))
        if figure.get("conceptual") and "conceptual" not in figure["caption"].lower():
            issue("Label conceptual figures explicitly in their caption.", location)
        if not figure["used_in"]:
            issue("Specify which article files use this figure.", location)
        for name in figure["used_in"]:
            if name in texts:
                if texts[name].count(figure["label"]) < 2 or figure["caption"] not in texts[name]:
                    issue("Include caption and a prose cross-reference using the figure label.", name + ":" + figure["id"])
                if figure["kind"] in {"architecture", "sequence", "flow", "deployment"}:
                    diagram_targets.add(name)
        for key in ("source_file", "rendered_file"):
            if figure.get(key):
                registered_assets.add(track(figure[key]).resolve())
        if figure["kind"] not in {"table", "equation"} and not figure.get("source_file") and not figure.get("rendered_file"):
            issue("Provide an editable or rendered figure asset.", location)
        if figure["kind"] == "screenshot":
            need(figure.get("permission_basis"), location + ":permission_basis")
        if figure["kind"] == "equation":
            need(figure.get("expression"), location + ":expression")
            if not figure.get("variables") or any(not text_ok(v) for v in figure.get("variables", {}).values()):
                issue("Define equation variables.", location)
        if figure["kind"] == "chart":
            active_measurements = {item["id"] for item in measurements["items"] if item["status"] != "omitted"}
            if not figure.get("measurement_ids") or any(mid not in active_measurements for mid in figure.get("measurement_ids", [])):
                issue("Charts must link to supported/qualified measurement IDs, not bypass the proof record.", location)
            data = figure.get("data")
            if not data:
                issue("Charts need data provenance, columns, units, baseline, aggregation and conditions.", location)
                continue
            for key, value in data.items():
                need(value, location + ":data." + key)
            path = track(data["file"])
            if path.suffix.lower() != ".csv" or path.stat().st_size > 5 * 1024 * 1024:
                issue("Chart checks require a CSV <=5 MiB; use a reviewed normalized CSV extract.", location)
            else:
                with path.open(encoding="utf-8", newline="") as stream:
                    rows = csv.DictReader(stream)
                    if data["x"] not in (rows.fieldnames or []) or data["y"] not in (rows.fieldnames or []):
                        issue("Chart x/y columns do not exist in the CSV.", location)
                    else:
                        count = 0
                        for row in rows:
                            count += 1
                            try:
                                if not math.isfinite(float(row[data["y"]])):
                                    raise ValueError("nonfinite")
                            except (ValueError, TypeError, KeyError):
                                issue("Chart y column must contain finite numeric values.", location)
                                break
                            if count > 100000:
                                issue("Normalize chart data to <=100000 rows for this local check.", location)
                                break
                        if not count:
                            issue("Chart CSV has no data rows.", location)
    for name, text in texts.items():
        for alt, image in re.findall(r"!\[([^\]]*)\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", text):
            if not alt.strip():
                issue("Markdown technical images need meaningful alt text.", name)
            if urlparse(image).scheme or image.startswith("//"):
                issue("Use approved local technical images, not remote/data URLs.", name)
                continue
            path = track(str((Path(name).parent / image).as_posix()))
            if path.resolve() not in registered_assets:
                issue("Technical image is absent from the figure registry.", name)
        if re.search(r"^\s*(?:```|~~~)mermaid\b", text, re.M | re.I) and name not in diagram_targets:
            issue("Register/source/caption the Mermaid diagram.", name)

    reviews = {review["file"]: review for review in packet["reviews"]}
    if len(reviews) != len(packet["reviews"]):
        issue("Duplicate review targets.", "reviews")
    for name in targets:
        review = reviews.get(name)
        if not review or review["sha256"] != dependencies[name]:
            issue("Missing/stale sequential reviews for this exact file checksum.", name)
            continue
        for role in ROLES:
            assessment = review[role]
            if assessment.get("status") != "pass":
                issue("The " + role + " review has not passed.", name, origin="agent-review")
            need(assessment.get("notes"), name + ":" + role)
            if not isinstance(assessment.get("findings"), list):
                issue("Each review needs a findings list (empty only after actual review).", name)
                continue
            for finding in assessment["findings"]:
                if not isinstance(finding, dict) or finding.get("severity") not in {"warning", "blocker"} or not text_ok(finding.get("message")):
                    issue("Review findings need severity and a substantive message.", name)
                else:
                    issue(finding["message"], name + ":" + role, finding["severity"], origin="agent-review")
    return finish()


def require_quality(root, state, targets):
    if not state.get("editorial_contract_version"):
        return  # Preserve previously created runs; explicit adopt is available.
    path = local(root, REPORT)
    report = load(path)
    current = evaluate(root, state, sorted(targets))
    if report.get("status") != "pass" or current["status"] != "pass" or report.get("fingerprint") != current["fingerprint"] or report.get("targets") != sorted(targets):
        raise ValueError("Missing, blocked or stale editorial quality report. Run editorial.py check after actual reviews; resolve blockers first.")
    return report


def run(args):
    root = Path(args.root).resolve()
    state = load(root / "project.json")
    if args.command == "blueprint":
        kind, reason = infer(state, args.type)
        print(json.dumps({"article_type": kind, "reason": reason, **load(BLUEPRINTS)["types"][kind]}, indent=2))
        return 0
    if state.get("workflow_stopped"):
        raise ValueError("Workflow stopped by user; no editorial work until explicit resume.")
    if state["stage"] not in {"DRAFT", "REVISE"}:
        raise ValueError("Editorial planning/checks require DRAFT or REVISE; do not mutate an approved body in PREPARE.")
    if args.command == "adopt":
        state["editorial_contract_version"] = 1
        state.setdefault("history", []).append({"at": datetime.now(timezone.utc).isoformat(), "action": "User opted a legacy run into editorial quality gates"})
        save(root / "project.json", state)
        return 0
    if args.command == "scaffold":
        if state["stage"] != "DRAFT":
            raise ValueError("Scaffold in DRAFT; revise the saved packet explicitly for revisions.")
        if (root / PACKET).exists():
            raise ValueError("Editorial packet already exists; update it without overwriting review history.")
        kind, _ = infer(state, args.type)
        save(root / PACKET, template(state, kind))
        print("Scaffolded " + PACKET + "; incomplete fields/reviews intentionally block quality checks.")
        return 0
    targets = targets_for(state, args.file)
    report = evaluate(root, state, targets)
    save(root / REPORT, report)
    archive = root / "outputs/draft/quality-reports" / (report["fingerprint"] + ".json")
    if not archive.exists():
        save(archive, report)
    lines = ["# Editorial quality report", "", "Status: **" + report["status"] + "**", "", report["limitations"], ""]
    lines += [f"- **{f['severity']}** [{f['location']}]: {f['message']}" for f in report["findings"]]
    if not report["findings"]:
        lines.append("No local blockers or agent-reported findings. This is not independent factual verification.")
    (root / "outputs/draft/quality-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=str(ROOT))
    sub = p.add_subparsers(dest="command", required=True)
    for command in ("blueprint", "scaffold"):
        s = sub.add_parser(command)
        s.add_argument("--type", choices=["auto", *load(BLUEPRINTS)["types"]], default="auto")
    s = sub.add_parser("check")
    s.add_argument("--file", action="append", default=[], help="Current revision target in REVISE; all versions by default in DRAFT")
    s = sub.add_parser("adopt")
    s.add_argument("--user-confirmed", action="store_true", required=True)
    return p


if __name__ == "__main__":
    try:
        sys.exit(run(parser().parse_args()))
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
