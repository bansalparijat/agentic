#!/usr/bin/env python3
"""Single-writer collection frontier and request permits; never calls MCP itself."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from blog import ROOT, fail, load, save

STATE = "outputs/data/collection-state.json"
LIMITS = ("max_depth", "max_items_per_source", "max_items_total", "max_links_per_item",
          "max_requests_per_backend", "max_requests_total", "max_elapsed_seconds",
          "min_interval_seconds", "max_retries", "branch_low_value_limit", "global_low_value_limit")


def canonical(url):
    p = urlsplit(url.strip())
    if p.scheme not in {"https", "http", "file"} or (p.scheme != "file" and not p.hostname):
        fail("Use a stable http(s) permalink or file URI, not a search snippet or relative URL.")
    if p.username or p.password:
        fail("Do not put credentials in source locators.")
    decoded = p.path
    for _ in range(5):
        previous, decoded = decoded, unquote(decoded)
        if decoded == previous:
            break
    if "\\" in decoded or any(part in {".", ".."} for part in decoded.split("/")):
        fail("Normalize dot segments and ambiguous paths before scope checks.")
    pairs = parse_qsl(p.query, keep_blank_values=True)
    if any(k.lower() in {"token", "access_token", "auth", "signature", "sig"} or k.lower().startswith("x-amz-") for k, _ in pairs):
        fail("Use a stable permalink without credentials or signed query parameters.")
    query = [(k, v) for k, v in pairs
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    host = p.netloc.lower()
    if (p.scheme == "https" and p.port == 443) or (p.scheme == "http" and p.port == 80):
        host = host.rsplit(":", 1)[0]
    return urlunsplit((p.scheme, host, p.path.rstrip("/") or "/", urlencode(sorted(query)), ""))


def in_scope(url, prefixes):
    item = urlsplit(canonical(url))
    for prefix in prefixes:
        scope = urlsplit(canonical(prefix))
        if (item.scheme, item.netloc) == (scope.scheme, scope.netloc):
            base = scope.path.rstrip("/")
            if item.path == base or item.path.startswith(base + "/"):
                if not scope.query or item.query == scope.query:
                    return True
    return False


def selected(project):
    plan = project.get("source_plan") or fail("Confirm selected sources first.")
    research = {s["name"]: s["mode"] for s in plan["sources"]}
    remote = {s for s, mode in research.items() if mode == "mcp"} | set(plan["destinations"])
    return research, remote


def validate(config, project):
    if not isinstance(config, dict):
        fail("Collection configuration must be a JSON object.")
    if config.get("mode") not in {"none", "children", "links", "both"}:
        fail("Navigation mode must be none, children, links or both.")
    for key in LIMITS:
        value = config.get(key)
        minimum = 0 if key in {"max_depth", "max_retries"} else 1
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            fail(f"{key} must be an integer >= {minimum}.")
    research, remote = selected(project)
    sources = config.get("sources")
    if not isinstance(sources, dict) or not sources:
        fail("Configure selected sources, backend groups and approved scope_prefixes.")
    for name, entry in sources.items():
        if name not in research and name not in remote:
            fail(f"Unselected source: {name}")
        if not isinstance(entry, dict):
            fail("Each source configuration must be an object.")
        if not isinstance(entry.get("backend"), str) or not entry["backend"].strip():
            fail("Each source needs a backend group; shared services must use the same group.")
        scopes = entry.get("scope_prefixes")
        if not isinstance(scopes, list):
            fail("Each source needs an explicit scope_prefixes list (empty for publication-only).")
        for scope in scopes:
            if not isinstance(scope, str):
                fail("Scope prefixes must be URL/file-URI strings.")
            canonical(scope)


def event(state, action, **details):
    state.setdefault("events", []).append({"at": time.time(), "action": action, **details})
    state["events"] = state["events"][-200:]


def budget(state, clock):
    c = state["config"]
    if clock - state["started_at"] >= c["max_elapsed_seconds"]:
        fail("Collection time budget exhausted. Stop and ask the user; do not reset counters.")
    if state["low_value_streak"] >= c["global_low_value_limit"]:
        fail("Collection stopped: consecutive items added little value. Summarize gaps before expanding.")


def add(state, source, url, parent=None, relation=None, reason=""):
    c = state["config"]
    if source not in c["sources"]:
        fail("Source not in the approved collection configuration.")
    url = canonical(url)
    if not in_scope(url, c["sources"][source]["scope_prefixes"]):
        fail("Out-of-scope target. Get user approval before expanding source boundaries.")
    key = hashlib.sha256((source + "\n" + url).encode()).hexdigest()[:20]
    nodes = state["nodes"]
    if key in nodes:
        return {"decision": "duplicate", "key": key}
    depth, low = 0, 0
    if parent:
        ancestor = nodes.get(parent) or fail("Unknown parent")
        if ancestor["source"] != source:
            fail("Cross-source navigation needs a separately approved root and source selection.")
        if ancestor["status"] not in {"useful", "low-value"}:
            fail("Finish and assess the parent before adding descendants.")
        if relation not in {"child", "link"} or not reason.strip():
            fail("Discovered items need child/link relation and a concrete relevance reason.")
        if c["mode"] == "none" or (c["mode"] == "children" and relation != "child") or (c["mode"] == "links" and relation != "link"):
            fail("This relation is not authorized by the selected recursion mode.")
        depth, low = ancestor["depth"] + 1, ancestor["low_value_streak"]
        if low >= c["branch_low_value_limit"]:
            fail("Low-value branch pruned.")
        if sum(n.get("parent") == parent for n in nodes.values()) >= c["max_links_per_item"]:
            fail("Per-item child/link fan-out limit reached.")
    elif relation:
        fail("Relations require a parent; explicit seeds have depth zero.")
    if depth > c["max_depth"]:
        fail("Maximum recursion depth reached.")
    if len(nodes) >= c["max_items_total"] or sum(n["source"] == source for n in nodes.values()) >= c["max_items_per_source"]:
        fail("Item budget reached (includes pending, failed and visited items).")
    nodes[key] = {"key": key, "source": source, "url": url, "parent": parent, "relation": relation,
                  "reason": reason, "depth": depth, "low_value_streak": low, "status": "pending"}
    event(state, "queued", key=key)
    return nodes[key]


def permit(state, project, source, clock):
    _, remote = selected(project)
    if source not in remote or source not in state["config"]["sources"]:
        fail("Request permits are only for selected, configured MCP sources/destinations.")
    if state.get("inflight"):
        fail("A request is already in flight. Record its result before another request.")
    c = state["config"]
    backend = c["sources"][source]["backend"]
    group = state["backends"].setdefault(backend, {"requests": 0, "next_at": 0, "retries": 0, "open": False})
    if group["open"]:
        fail("Backend circuit is open. Stop calls; apply the selected-source proceed/exit policy.")
    if clock < group["next_at"]:
        fail(f"WAIT {math.ceil(group['next_at'] - clock)} seconds before this backend; do not poll.")
    if state["requests"] >= c["max_requests_total"] or group["requests"] >= c["max_requests_per_backend"]:
        fail("Request budget exhausted. Stop; do not silently increase it.")
    state["requests"] += 1
    group["requests"] += 1
    group["next_at"] = clock + c["min_interval_seconds"]
    state["inflight"] = {"source": source, "backend": backend, "at": clock, "number": state["requests"]}
    event(state, "request_permitted", source=source, backend=backend)
    return state["inflight"]


def result(state, outcome, retry_after, clock):
    flight = state.get("inflight") or fail("No request permit to finish.")
    if retry_after < 0 or not math.isfinite(retry_after):
        fail("Retry-After seconds must be finite and nonnegative.")
    group = state["backends"][flight["backend"]]
    c = state["config"]
    if outcome == "retry":
        group["retries"] += 1
        group["open"] = group["retries"] > c["max_retries"]
        group["next_at"] = max(group["next_at"], clock + max(retry_after, 5 * 2 ** min(group["retries"] - 1, 10)))
    elif outcome == "failed":
        group["open"] = True
    else:
        group["retries"] = 0
    # Also space requests from completion, not only from their start.
    group["next_at"] = max(group["next_at"], clock + c["min_interval_seconds"])
    state["inflight"] = None
    event(state, "request_result", source=flight["source"], outcome=outcome)
    return group


def run_unlocked(args):
    root = Path(args.root).resolve()
    project = load(root / "project.json")
    path = root / STATE
    if args.command == "status":
        print(json.dumps(load(path), indent=2) if path.exists() else "No collection policy configured; ask the user first.")
        return
    if project.get("workflow_stopped"):
        fail("Workflow stopped by user; do not continue collection.")
    clock = time.time()
    if args.command == "configure":
        if path.exists():
            fail("Collection state already exists. Resume it; never reset budgets to bypass a stop.")
        config = load(root / args.config)
        validate(config, project)
        state = {"schema_version": 1, "config": config, "started_at": clock, "nodes": {},
                 "requests": 0, "backends": {}, "inflight": None, "low_value_streak": 0}
        output = {"configured": True, "policy": config}
    else:
        state = load(path)
        c = state["config"]
        if args.command not in {"result", "finish"}:
            budget(state, clock)
        if args.command == "add":
            research, _ = selected(project)
            if args.source not in research:
                fail("Navigation is only for currently selected research sources.")
            output = add(state, args.source, args.url, args.parent, args.relation, args.reason)
        elif args.command == "next":
            research, _ = selected(project)
            if any(n["status"] == "active" for n in state["nodes"].values()):
                fail("Finish the active item before requesting another.")
            pending = [n for n in state["nodes"].values() if n["status"] == "pending" and n["source"] in research]
            output = min(pending, key=lambda n: n["depth"]) if pending else {"decision": "frontier exhausted"}
            if pending:
                output["status"] = "active"
        elif args.command == "finish":
            node = state["nodes"].get(args.key) or fail("Unknown item")
            if node["status"] != "active":
                fail("Only an active item can be finished.")
            if state.get("inflight"):
                fail("Record the remote request result before finishing the item.")
            node["status"] = args.value
            node["summary"] = args.summary
            node["low_value_streak"] = node["low_value_streak"] + 1 if args.value == "low-value" else 0
            state["low_value_streak"] = state["low_value_streak"] + 1 if args.value == "low-value" else 0
            event(state, "item_finished", key=args.key, value=args.value)
            output = node
        elif args.command == "request":
            output = permit(state, project, args.source, clock)
        elif args.command == "result":
            output = result(state, args.outcome, args.retry_after, clock)
    save(path, state)
    print(json.dumps(output, indent=2))


def run(args):
    # The atomic lock prevents overlapping local mutations/permits. The durable
    # inflight slot separately prevents concurrent remote calls across commands.
    if args.command == "status":
        return run_unlocked(args)
    root = Path(args.root).resolve()
    if not (root / "project.json").is_file():
        fail("Initialize a project first.")
    lock = root / "outputs/data/.collection.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        fail("Collection controller busy. Do not run parallel writers; inspect a stale lock before recovery.")
    try:
        os.write(fd, str(os.getpid()).encode())
        return run_unlocked(args)
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=str(ROOT))
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("configure")
    s.add_argument("--config", required=True)
    s.add_argument("--user-confirmed", action="store_true", required=True)
    sub.add_parser("status")
    s = sub.add_parser("add")
    s.add_argument("--source", required=True)
    s.add_argument("--url", required=True)
    s.add_argument("--parent")
    s.add_argument("--relation", choices=("child", "link"))
    s.add_argument("--reason", default="")
    sub.add_parser("next")
    s = sub.add_parser("finish")
    s.add_argument("--key", required=True)
    s.add_argument("--value", choices=("useful", "low-value", "failed"), required=True)
    s.add_argument("--summary", required=True)
    s = sub.add_parser("request")
    s.add_argument("--source", required=True)
    s = sub.add_parser("result")
    s.add_argument("--outcome", choices=("success", "retry", "failed", "resource-error"), required=True)
    s.add_argument("--retry-after", type=float, default=0, help="Provider Retry-After converted to seconds")
    return p


if __name__ == "__main__":
    try:
        run(parser().parse_args())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
