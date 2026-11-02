#!/usr/bin/env python3
"""Stage self-contained Harbor tasks using an explicit public-file allowlist.

Never copies outputs/, project.json, arbitrary personal inputs, .git, .env or
credentials. Refuses existing destinations and symlinked/escaping source files.
Does not install dependencies, build containers, start a blog or run Harbor.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import uuid

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ("full-cycle", "recovery-and-limits")
PUBLIC_INPUTS = {"input/README.md", "input/input_sample.json", "input/sample_single.json", "input/sample_microsoft.json",
                 "input/sample_local_tutorial.json", "input/sample_custom_sources.json"}
ENTRYPOINTS = {"AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursor/rules/technical-blog.mdc", ".github/copilot-instructions.md"}
PUBLIC_MISC = {"README.md", ".githooks/pre-commit", "harness/adapters/README.md", "tests/README.md"}
SCENARIO_FILES = {"tests/editorial_fixtures.py", "tests/scenarios/run.py", "tests/scenarios/verify.py", "tests/scenarios/fixture_export.py", "tests/scenarios/clock_collection.py"}
TASK_FILES = ("instruction.md", "task.toml", "environment/Dockerfile", "environment/.dockerignore", "solution/solve.sh", "tests/test.sh")


def safe_source(root, name):
    source = root / name
    if source.resolve() != source or not source.is_file():
        raise ValueError("Missing/symlinked staging file: " + name)
    return source


def public_paths(root=ROOT):
    root = Path(root).resolve()
    manifest = json.loads((root / "harness/manifest.json").read_text())
    paths = {"harness/manifest.json", "harness/README.md", "harness/schemas/manifest.schema.json", "harness/schemas/input-v1.schema.json",
             "scripts/intake.py", *PUBLIC_INPUTS, *ENTRYPOINTS, *PUBLIC_MISC, *SCENARIO_FILES}
    paths.update(manifest[key] for key in ("workflow", "capability_contract", "input_schema", "editorial_schema", "blueprints", "defaults"))
    paths.update(manifest["policies"])
    paths.update(manifest["runtime"]["commands"])
    paths.update(manifest["input_samples"])
    paths.update(stage["guide"] for stage in manifest["stages"])
    for host in manifest["hosts"]:
        paths.update((host["adapter"], host["entrypoint"]))
    for name in paths:
        path = PurePosixPath(name)
        allowed = name in PUBLIC_INPUTS | ENTRYPOINTS | PUBLIC_MISC | SCENARIO_FILES | {"scripts/intake.py"}
        allowed |= path.parts[:1] == ("harness",) and path.suffix in {".md", ".json"}
        allowed |= name in {"scripts/blog.py", "scripts/collection.py", "scripts/editorial.py", "scripts/host.py"}
        if path.is_absolute() or ".." in path.parts or not allowed:
            raise ValueError("Unsafe public staging file: " + name)
        safe_source(root, name)
    return sorted(paths)


def prepare(destination=None, root=ROOT):
    root = Path(root).resolve()
    destination = Path(destination) if destination else root / "build/harbor" / ("dataset-" + uuid.uuid4().hex[:12])
    if destination.is_symlink():
        raise ValueError("Do not stage through a symlink")
    destination = destination.resolve()
    if destination.is_relative_to(root) and not destination.is_relative_to(root / "build"):
        raise ValueError("Stage outside the installation or under ignored build/ only")
    paths = public_paths(root)
    # Validate every template before creating a destination. Never merge/overwrite.
    for scenario in SCENARIOS:
        for name in TASK_FILES:
            safe_source(root, f"tests/harbor/tasks/{scenario}/{name}")
    destination.mkdir(parents=True, exist_ok=False)
    contracts = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}
    for scenario in SCENARIOS:
        task = destination / scenario
        for name in TASK_FILES:
            target = task / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / "tests/harbor/tasks" / scenario / name, target)
        for name in paths:
            target = task / "environment/harness" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, target)
        shutil.copy2(root / "tests/scenarios/verify.py", task / "tests/verify.py")
        (task / "tests/contracts.json").write_text(json.dumps(contracts, indent=2) + "\n")
    return destination


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destination", type=Path, help="New directory (default: unique ignored build/harbor/dataset-* directory)")
    args = p.parse_args()
    try:
        print(prepare(args.destination))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.exit(1, f"Error: {exc}\n")
