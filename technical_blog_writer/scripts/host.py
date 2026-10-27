#!/usr/bin/env python3
"""Read-only local adapter check. Does not launch hosts, discover MCPs or authenticate."""
import argparse
import json
from pathlib import Path
import sys

from blog import ROOT, fail, load


def registry():
    manifest = load(ROOT / "harness/manifest.json")
    hosts = manifest["hosts"]
    ids = [entry["id"] for entry in hosts]
    if len(ids) != len(set(ids)):
        fail("Duplicate host IDs in manifest.")
    return manifest, {entry["id"]: entry for entry in hosts}


def installed_file(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        fail(f"Missing or invalid harness file: {relative}")
    return path


def check(host_id, workspace):
    manifest, hosts = registry()
    if host_id not in hosts:
        fail(f"Unknown host: {host_id}")
    root = Path(workspace).resolve()
    if not root.is_dir():
        fail("Workspace must already exist; this check does not create or initialize it.")
    host = hosts[host_id]
    references = [host["entrypoint"], host["adapter"], manifest["entrypoint"],
                  manifest["capability_contract"], "harness/README.md", manifest["workflow"], manifest["defaults"],
                  manifest["input_schema"], manifest["input_sample"], manifest["blueprints"], manifest["editorial_schema"]]
    references += manifest["policies"] + manifest["runtime"]["commands"] + manifest.get("input_samples", [])
    references += [stage["guide"] for stage in manifest["stages"]]
    for reference in references:
        installed_file(reference)
    state_path = root / manifest["runtime"]["state"]
    state = load(state_path) if state_path.is_file() else {}
    stopped = bool(state.get("workflow_stopped"))
    bootstrap_script, bootstrap_action = manifest["runtime"]["bootstrap_command"]
    commands = [[sys.executable, str(installed_file(script)), "--root", str(root), "status"]
                for script in ("scripts/blog.py", "scripts/collection.py")]
    return {
        "status": "local-ready",
        "host": host_id,
        "activation": host["activation"],
        "harness_root": str(ROOT),
        "workspace_root": str(root),
        "entrypoint": str(installed_file(host["entrypoint"])),
        "adapter": str(installed_file(host["adapter"])),
        "capability_contract": str(installed_file(manifest["capability_contract"])),
        "project_exists": state_path.is_file(),
        "stage": state.get("stage"),
        "workflow_stopped": stopped,
        "source_selection_saved": bool(state.get("source_plan")),
        "intake_saved": bool(state.get("intake")),
        "decision_log": str(root / manifest["runtime"]["decisions"]),
        "default_input_exists": (root / manifest["runtime"]["input"]).is_file(),
        "collection_policy_saved": (root / manifest["runtime"]["collection_state"]).is_file(),
        "bootstrap_command": [sys.executable, str(installed_file(bootstrap_script)), "--root", str(root), bootstrap_action],
        "startup_commands": commands,
        "next_action": ("Wait for explicit user resume; do not restart work." if stopped else
                        "Read the host contract/adapter, run the bootstrap command, then status; input handling and PREPARE titles are built in."),
        "unverified": ["Host instruction loading and tool permissions", "Selected MCP availability/authentication",
                       "Python dependencies for optional exports", "Git guard activation in the workspace"],
        "notes": ["Local metadata check only; no source calls, writes or approvals performed.",
                  "Do not run multiple hosts concurrently against the same workspace.",
                  "If workspace and installation differ, explicitly load these instruction files and use --root for every helper.",
                  "Ensure the workspace excludes outputs/ from Git before creating evidence."],
    }


def parser():
    _, hosts = registry()
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="List provided instruction adapters")
    mode.add_argument("--host", choices=list(hosts))
    p.add_argument("--root", default=str(ROOT), help="Project workspace (default: harness repository root)")
    return p


def run(args):
    if args.list:
        _, hosts = registry()
        output = list(hosts.values())
    else:
        output = check(args.host, args.root)
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        run(parser().parse_args())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
