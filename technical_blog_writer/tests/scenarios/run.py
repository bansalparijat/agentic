#!/usr/bin/env python3
"""Deterministic long-horizon harness scenarios; synthetic operator, no live services.

Only new, isolated workspaces are allowed. Used locally and by Harbor's oracle;
not an LLM writing benchmark or authorization for a real blog's approvals.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "tests")]
from editorial_fixtures import passing_packet

SCENARIOS = ("full-cycle", "recovery-and-limits")
DOC_URL = "https://docs.google.com/document/d/harbor_SYNTHETIC_NOT_A_REAL_DOCUMENT/edit"
BODY = "A queue buffers work. Consumers process queued work independently.\n\nThis synthetic explanation makes no performance claims.\n"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Scenario:
    def __init__(self, root, name):
        self.root, self.name, self.trace = Path(root).resolve(), name, []
        check(not self.root.exists(), "Scenario workspace must not already exist; never overwrite a run")
        check(not self.root.is_relative_to(ROOT), "Use an isolated workspace outside the installation")
        self.put("outputs/data/SYNTHETIC-TEST-ONLY", "Synthetic fixtures only; not production approvals.\n")

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def json(self, name, value):
        return self.put(name, json.dumps(value, indent=2) + "\n")

    def state(self):
        return load(self.root / "project.json")

    def cli(self, script, *args, error=None, clock=None):
        if clock is not None:
            command = [sys.executable, str(ROOT / "tests/scenarios/clock_collection.py"), str(self.root), str(clock), *args]
        elif script == "fixture_export":
            command = [sys.executable, str(ROOT / "tests/scenarios/fixture_export.py"), str(self.root)]
        else:
            command = [sys.executable, str(ROOT / "scripts" / f"{script}.py"), "--root", str(self.root), *args]
        state = self.root / "project.json"
        before = state.read_bytes() if state.exists() else None
        readonly = script == "blog" and args[0] == "startup"
        files_before = {str(p.relative_to(self.root)): sha(p) for p in self.root.rglob("*") if p.is_file()} if readonly else None
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=20)
        if error:
            check(result.returncode != 0 and error.casefold() in (result.stdout + result.stderr).casefold(),
                  f"Expected refusal {error!r}: {result.stdout}{result.stderr}")
            check((state.read_bytes() if state.exists() else None) == before, "Rejected command mutated workflow state")
        else:
            check(result.returncode == 0, f"{script} {args}: {result.stdout}{result.stderr}")
        if readonly:
            check(files_before == {str(p.relative_to(self.root)): sha(p) for p in self.root.rglob("*") if p.is_file()}, "Startup wrote workspace files")
        self.trace.append({"script": script, "args": list(args), "clock": clock, "returncode": result.returncode,
                           "expected_error": error, "stdout": result.stdout, "stderr": result.stderr})
        self.json("outputs/data/scenario-trace.json", self.trace)
        return result.stdout

    def quality(self, targets):
        # Explicitly synthetic attestations; never called by production helpers.
        passing_packet(self.root, targets)
        args = ["check"]
        if self.state()["stage"] == "REVISE":
            args += ["--file", targets[0]]
        self.cli("editorial", *args)

    def done(self):
        report = {"scenario": self.name, "synthetic": True, "status": "pass", "commands": len(self.trace),
                  "refusals": sum(bool(t["expected_error"]) for t in self.trace),
                  "scope": "Local contracts only; no live MCP, real human approval, browser rendering or cloud document."}
        self.json("outputs/data/scenario-result.json", report)
        return report


def full_cycle(s):
    brief = {"topic": "Queue architecture", "audience": "Engineers", "words": 700, "publication": "internal",
             "drafts": 2, "files": ["fixture-evidence.md"], "store_confidential_locally": False}
    s.json("input/blog.json", brief)
    startup = json.loads(s.cli("blog", "startup", "--input", "input/blog.json"))
    check(startup["action"] == "new_intake" and startup["missing_fields"] == [], "Brief was not prefilled")
    s.cli("blog", "init", "--input", "input/blog.json")
    s.cli("blog", "apply-input", "--user-confirmed")
    s.cli("blog", "advance", "--to", "DRAFT", "--user-confirmed", error="at least one")
    s.put("outputs/data/normalized/queue.md", "SYNTHETIC evidence: a queue buffers work; consumers process it independently.\n")
    s.cli("blog", "source", "--file", "outputs/data/normalized/queue.md", "--kind", "local", "--title", "Synthetic queue explanation",
          "--locator", "synthetic-local#queue", "--confidentiality", "internal")
    for name in ("research-brief.md", "claims.md", "search-log.md"):
        s.put("outputs/data/" + name, "SYNTHETIC fixture: S001 supports queue buffering and independent consumers; no measured results.\n")
    s.cli("blog", "advance", "--to", "DRAFT", "--user-confirmed")
    s.cli("blog", "titles", "--file", "outputs/blog/title-options.json", error="Requires stage")
    targets = [f"outputs/draft/version-{i:02d}.md" for i in (1, 2)]
    for target in targets:
        s.put(target, "# Provisional heading\n\n" + BODY)
    for name in ("comparison.md", "evidence-map.md", "diagram-notes.md"):
        s.put("outputs/draft/" + name, "SYNTHETIC: two test variants use S001; no figures or performance claims.\n")
    s.cli("blog", "advance", "--to", "REVISE", "--user-confirmed", error="quality")
    s.quality(targets)
    s.put(targets[0], "# Changed provisional heading\n\n" + BODY)
    s.cli("blog", "advance", "--to", "REVISE", "--user-confirmed", error="quality")
    s.quality(targets)
    s.cli("blog", "advance", "--to", "REVISE", "--user-confirmed")
    revision = "outputs/revised_draft/revision-001.md"
    s.put(revision, "# Provisional heading\n\n" + BODY)
    s.put("outputs/revised_draft/revision-001-notes.md", "SYNTHETIC operator selected variant one and approved its explanatory body; no real publication approval.\n")
    s.cli("blog", "approve", "--file", revision, "--user-confirmed", error="quality")
    s.quality([revision])
    s.cli("blog", "approve", "--file", revision, "--user-confirmed")
    approved_bytes = (s.root / revision).read_bytes()
    s.json("outputs/blog/title-options.json", [
        {"id": "T1", "title": "Understanding queues", "angle": "Explanation"},
        {"id": "T2", "title": "How queues buffer work", "angle": "Mechanism"},
        {"id": "T3", "title": "Buffering work with queues", "angle": "Decoupling"}])
    s.cli("blog", "titles", "--file", "outputs/blog/title-options.json")
    s.cli("blog", "select-title", "--id", "T2", "--user-confirmed")
    def package(title):
        s.cli("blog", "hero", "--skip", "--user-confirmed")
        s.put("outputs/blog/article.md", "# " + title + "\n\n" + BODY)
        s.cli("fixture_export")
        s.cli("blog", "google-doc", "--url", DOC_URL, "--verified", "--user-confirmed")
        s.put("outputs/blog/verification.md", "SYNTHETIC ONLY: HTML/PDF and cloud readback are test doubles; no actual document or visual inspection.\n")
        s.cli("blog", "complete", "--user-confirmed")
    s.cli("blog", "hero", "--skip", "--user-confirmed")
    s.put("outputs/blog/article.md", "# How queues buffer work\n\n" + BODY)
    s.cli("blog", "complete", "--user-confirmed", error="export")
    s.cli("fixture_export")
    s.cli("blog", "complete", "--user-confirmed", error="Google Doc")
    s.cli("blog", "google-doc", "--url", DOC_URL, "--verified", "--user-confirmed")
    s.put("outputs/blog/verification.md", "SYNTHETIC: browser rendering and remote readback are test doubles, not real integrations.\n")
    s.cli("blog", "complete", "--user-confirmed")
    s.cli("blog", "select-title", "--id", "T3", "--user-confirmed")
    check(not any(key in s.state() for key in ("export", "google_doc", "hero", "completed_at")), "Title change kept stale delivery records")
    s.cli("blog", "complete", "--user-confirmed", error="hero")
    package("Buffering work with queues")
    s.put(revision, "Unapproved tampering")
    s.cli("blog", "hero", "--skip", "--user-confirmed", error="revision changed")
    (s.root / revision).write_bytes(approved_bytes)
    check(sha(s.root / revision) == s.state()["approval"]["sha256"], "Body approval was not pinned")
    check(load(s.root / "outputs/input.json") == brief, "Input snapshot changed")
    return s.done()


def recovery_and_limits(s):
    s.cli("blog", "init", "--topic", "Synthetic collection recovery", "--audience", "Test engineers")
    s.cli("blog", "select-sources", "--mcp", "Mock A", "--mcp", "Mock B", "--mcp", "Mock C", "--manual", "Local fixture", "--user-confirmed")
    s.cli("blog", "mcp-decision", "--connector", "Unselected", "--capability", "read", "--reason", "Synthetic unavailable", "--decision", "proceed", "--user-confirmed", error="explicitly selected")
    decision = ["mcp-decision", "--connector", "Mock A", "--capability", "read", "--reason", "Synthetic unavailable", "--user-confirmed"]
    s.cli("blog", *decision, "--decision", "exit")
    route = json.loads(s.cli("blog", "startup", "--input", "missing-or-invalid.json"))
    check(route["action"] == "await_explicit_resume" and route["supplied_input_ignored"], "Stopped saved state lost precedence")
    s.cli("blog", "advance", "--to", "DRAFT", "--user-confirmed", error="stopped")
    s.cli("collection", "add", "--source", "Mock B", "--url", "https://example.invalid/b/root", clock=1000, error="stopped")
    s.cli("blog", "resume", "--user-confirmed")
    s.cli("blog", *decision, "--decision", "proceed")
    config = load(ROOT / "harness/config.collection.json")
    config.update({"max_depth": 1, "max_items_total": 3, "max_requests_total": 2, "max_requests_per_backend": 2,
                   "min_interval_seconds": 1, "sources": {name: {"backend": "shared-mock", "scope_prefixes": [url]}
                        for name, url in (("Mock B", "https://example.invalid/b"), ("Mock C", "https://example.invalid/c"))}})
    s.json("outputs/data/test-config.json", config)
    def c(*args, at=1000, error=None):
        return s.cli("collection", *args, clock=at, error=error)
    c("configure", "--config", "outputs/data/test-config.json", "--user-confirmed")
    node = json.loads(c("add", "--source", "Mock B", "--url", "https://example.invalid/b/root"))
    check(json.loads(c("next"))["key"] == node["key"], "Persistent frontier lost root")
    c("request", "--source", "Mock B")
    c("request", "--source", "Mock C", error="in flight")
    c("result", "--outcome", "retry", "--retry-after", "60")
    c("request", "--source", "Mock C", at=1059, error="WAIT")
    c("request", "--source", "Mock C", at=1060)
    c("result", "--outcome", "success", at=1060)
    c("request", "--source", "Mock B", at=1061, error="budget exhausted")
    c("finish", "--key", node["key"], "--value", "useful", "--summary", "Synthetic root assessed", at=1061)
    check(json.loads(c("add", "--source", "Mock B", "--url", "https://example.invalid/b/root/?utm_source=test#fragment", at=1061))["decision"] == "duplicate", "Cycle/URL deduplication failed")
    child = json.loads(c("add", "--source", "Mock B", "--url", "https://example.invalid/b/child", "--parent", node["key"], "--relation", "child", "--reason", "Synthetic relevant mechanism", at=1061))
    c("next", at=1061)
    c("finish", "--key", child["key"], "--value", "low-value", "--summary", "Synthetic low-value assessment", at=1061)
    c("add", "--source", "Mock B", "--url", "https://example.invalid/b/grandchild", "--parent", child["key"], "--relation", "link", "--reason", "Synthetic relevance", at=1061, error="depth")
    c("add", "--source", "Mock B", "--url", "https://example.invalid/outside", at=1061, error="scope")
    c("add", "--source", "Mock C", "--url", "https://example.invalid/c/root", at=1061)
    c("add", "--source", "Mock C", "--url", "https://example.invalid/c/extra", at=1061, error="Item budget")
    c("next", at=1061)
    state = load(s.root / "outputs/data/collection-state.json")
    active = next(n["key"] for n in state["nodes"].values() if n["status"] == "active")
    c("finish", "--key", active, "--value", "useful", "--summary", "Synthetic final root", at=1061)
    check(json.loads(c("next", at=1061))["decision"] == "frontier exhausted", "Frontier did not finish")
    c("add", "--source", "Mock B", "--url", "https://example.invalid/b/new", at=2200, error="time budget")
    c("configure", "--config", "outputs/data/test-config.json", "--user-confirmed", at=2200, error="already exists")
    s.put("outputs/data/.collection.lock", "SYNTHETIC owned lock\n")
    c("request", "--source", "Mock B", at=2200, error="busy")
    (s.root / "outputs/data/.collection.lock").unlink()
    check(load(s.root / "outputs/data/collection-state.json")["requests"] == 2, "Counters were reset or denied calls consumed permits")
    return s.done()


def execute(root, name):
    s = Scenario(root, name)
    return (full_cycle if name == "full-cycle" else recovery_and_limits)(s)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", choices=(*SCENARIOS, "all"), default="all")
    p.add_argument("--workspace", type=Path, help="New path outside installation; retained for inspection. Never an existing run.")
    args = p.parse_args()
    names = SCENARIOS if args.scenario == "all" else (args.scenario,)
    def run(base):
        # Independent verification is shared with Harbor, but never fills results.
        from verify import verify
        for name in names:
            path = base / name if args.scenario == "all" else base
            report = execute(path, name)
            verification = verify(path, name, ROOT)
            print(json.dumps({**report, "verification": verification}, indent=2))
    if args.workspace:
        if args.workspace.exists():
            p.error("--workspace must not already exist")
        run(args.workspace.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="blog-scenarios-") as temp:
            run(Path(temp) / "run")


if __name__ == "__main__":
    main()
