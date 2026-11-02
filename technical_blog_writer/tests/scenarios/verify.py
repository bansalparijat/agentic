#!/usr/bin/env python3
"""Read-only artifact verifier used locally and uploaded separately by Harbor.

Does not run the scenario, fill attestations, render, fetch URLs or grant approval.
Missing/tampered artifacts fail closed. This is deterministic integration grading,
not an adversarial-agent sandbox or a live publishing/LLM quality evaluation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_at(root, name):
    path = (root / name).resolve()
    check(path.is_relative_to(root.resolve()) and path.is_file(), "Missing/escaping artifact: " + name)
    return path


def load(root, name):
    return json.loads(file_at(root, name).read_text(encoding="utf-8"))


def verify(workspace, scenario, installation, contracts=None):
    root, install = Path(workspace).resolve(), Path(installation).resolve()
    check(scenario in {"full-cycle", "recovery-and-limits"}, "Unknown scenario")
    file_at(root, "outputs/data/SYNTHETIC-TEST-ONLY")
    if contracts is not None:
        check(bool(contracts), "Empty installation contract")
        for name, digest in contracts.items():
            check(sha(file_at(install, name)) == digest, "Installation changed: " + name)
    result = load(root, "outputs/data/scenario-result.json")
    check(result.get("synthetic") is True and result.get("status") == "pass" and result.get("scenario") == scenario, "Wrong/missing scenario result")
    trace = load(root, "outputs/data/scenario-trace.json")
    check(isinstance(trace, list) and len(trace) >= 25 and result["commands"] == len(trace), "Incomplete CLI trace")
    errors = {t["expected_error"] for t in trace if t.get("expected_error")}
    check(result["refusals"] == sum(bool(t.get("expected_error")) for t in trace), "Incorrect refusal count")
    for entry in trace:
        expected = entry.get("expected_error")
        if expected:
            check(entry["returncode"] != 0 and expected.casefold() in (entry["stdout"] + entry["stderr"]).casefold(), "Expected refusal did not occur")
        else:
            check(entry["returncode"] == 0, "Scenario command failed")
    project = load(root, "project.json")
    check(project.get("editorial_contract_version") == 1 and not project.get("workflow_stopped"), "Quality/stop contract bypassed")
    check(not (root / "outputs/data/.collection.lock").exists(), "Leaked collection lock")
    if scenario == "full-cycle":
        check({"at least one", "Requires stage", "quality", "export", "Google Doc", "hero", "revision changed"} <= errors, "Missing workflow refusal probes")
        check(project["stage"] == "PREPARE" and bool(project.get("completed_at")), "Full cycle did not complete")
        revision = project["approval"]["file"]
        check(sha(file_at(root, revision)) == project["approval"]["sha256"], "Approved body changed")
        approved = file_at(root, revision).read_text(encoding="utf-8").split("\n", 1)[1]
        article = file_at(root, "outputs/blog/article.md").read_text(encoding="utf-8")
        check(article.split("\n", 1)[1] == approved, "Packaging modified approved body")
        check(article.splitlines()[0] == "# Buffering work with queues" and project["title_selection"]["option_id"] == "T3", "Final title reselection not exercised")
        check(project["title_selection"]["revision_sha256"] == project["approval"]["sha256"], "Title not bound to approval")
        check(project["hero"]["decision"] == "skip", "Wrong synthetic hero decision")
        report = load(root, "outputs/draft/quality-report.json")
        check(report["status"] == "pass" and report["targets"] == [revision], "Missing exact revision quality report")
        check(report["fingerprint"] == project["approval"]["quality_fingerprint"], "Approval did not pin quality proof")
        check(load(root, "outputs/draft/quality-reports/" + report["fingerprint"] + ".json") == report, "Quality archive changed")
        check(len(list((root / "outputs/draft/quality-reports").glob("*.json"))) >= 3, "Draft refresh/revision review history missing")
        for name, digest in report["dependencies"].items():
            check(sha(file_at(root, name)) == digest, "Stale quality dependency: " + name)
        for name, digest in report["contracts"].items():
            check(sha(file_at(install, name)) == digest, "Stale quality contract: " + name)
        configuration = {k: project.get(k) for k in ("topic", "audience", "intake", "source_plan", "draft_settings")}
        fingerprint = hashlib.sha256(json.dumps({"dependencies": report["dependencies"], "contracts": report["contracts"],
            "configuration": configuration, "targets": report["targets"]}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        check(fingerprint == report["fingerprint"], "Quality fingerprint does not recompute")
        for source in load(root, "outputs/data/catalog.json"):
            check(sha(file_at(root, source["file"])) == source["sha256"], "Evidence integrity lost")
        check(load(root, "outputs/input.json") == load(root, "input/blog.json"), "Original brief not preserved")
        delivery = load(root, "outputs/blog/delivery.json")
        check(sha(file_at(root, "outputs/blog/delivery.json")) == project["delivery_sha256"], "Delivery checksum differs")
        check({f"outputs/blog/article.{ext}" for ext in ("md", "html", "pdf", "gdoc")} <= delivery["files"].keys(), "Missing output formats")
        for name, digest in delivery["files"].items():
            check(sha(file_at(root, name)) == digest, "Stale delivery artifact: " + name)
        for name, digest in project["export"]["files"].items():
            check(sha(file_at(root, name)) == digest, "Stale export: " + name)
        check(project["google_doc"]["document_id"] == "harbor_SYNTHETIC_NOT_A_REAL_DOCUMENT", "Only the declared cloud test double is allowed")
        check(project["google_doc"]["article_sha256"] == sha(file_at(root, "outputs/blog/article.md")), "Cloud fixture readback stale")
        for name in ("article.html", "article.pdf", "verification.md"):
            check(b"SYNTHETIC" in file_at(root, "outputs/blog/" + name).read_bytes(), "Export boundary not labelled as synthetic")
    else:
        check({"explicitly selected", "stopped", "in flight", "WAIT", "budget exhausted", "depth", "scope", "Item budget", "time budget", "already exists", "busy"} <= errors, "Missing recovery/load probes")
        check(project["stage"] == "COLLECTION" and "completed_at" not in project, "Collection scenario advanced without consent")
        check([d["decision"] for d in project["mcp_decisions"]] == ["exit", "proceed"], "MCP decisions were lost/replayed")
        check(all(d["connectors"] == ["Mock A"] for d in project["mcp_decisions"]), "Unselected connector warning saved")
        state = load(root, "outputs/data/collection-state.json")
        check(state["started_at"] == 1000 and state["requests"] == 2, "Time/request counters reset")
        check(len(state["nodes"]) == 3 and not state["inflight"], "Frontier/request not preserved")
        check(all(n["status"] in {"useful", "low-value"} and n["depth"] <= 1 for n in state["nodes"].values()), "Depth/frontier invariant failed")
        group = state["backends"]["shared-mock"]
        check(group["requests"] == 2 and group["next_at"] == 1061 and not group["open"], "Shared pacing/Retry-After not preserved")
        permitted = [e for e in state["events"] if e["action"] == "request_permitted"]
        check([e["source"] for e in permitted] == ["Mock B", "Mock C"], "Skipped connector retried or budget bypassed")
        check(any(e["action"] == "request_result" and e.get("outcome") == "retry" for e in state["events"]), "Retry history missing")
    return {"status": "pass", "scenario": scenario, "commands_checked": len(trace), "refusals_checked": result["refusals"]}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--scenario", choices=("full-cycle", "recovery-and-limits"), required=True)
    p.add_argument("--installation", type=Path, required=True)
    p.add_argument("--contracts", type=Path)
    args = p.parse_args()
    try:
        contracts = json.loads(args.contracts.read_text()) if args.contracts else None
        print(json.dumps(verify(args.workspace, args.scenario, args.installation, contracts), indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}))
        sys.exit(1)
