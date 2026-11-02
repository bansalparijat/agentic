#!/usr/bin/env python3
"""Run pinned Harbor oracle regressions, serially, without installing anything.

Task runtime networking is disabled. Docker/Harbor may fetch build/helper images.
No real models/MCPs/cloud writes are used. Requires separate tooling approval.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

from prepare_harbor import ROOT, SCENARIOS, prepare


def check_job(job, expected):
    """A successful Harbor process alone is not a passing test result."""
    summary = json.loads((job / "result.json").read_text())
    stats = summary["stats"]
    if not summary.get("finished_at") or stats.get("n_completed_trials") != len(expected) or stats.get("n_errored_trials") != 0:
        raise ValueError("Harbor job incomplete or errored")
    trials = [json.loads(path.read_text()) for path in sorted(job.glob("*/result.json"))]
    names = [t["task_name"].split("/")[-1] for t in trials]
    if len(names) != len(expected) or set(names) != set(expected):
        raise ValueError("Missing/duplicate/unexpected Harbor trial results")
    for trial in trials:
        rewards = (trial.get("verifier_result") or {}).get("rewards") or {}
        value = rewards.get("reward")
        if (trial.get("exception_info") or not trial.get("finished_at") or set(rewards) != {"reward"}
                or isinstance(value, bool) or not isinstance(value, (int, float)) or value != 1):
            raise ValueError("Harbor trial failed or has no passing reward: " + trial["task_name"])
    return {"status": "pass", "tasks": names, "job": str(job)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", choices=(*SCENARIOS, "all"), default="all")
    p.add_argument("--harbor", default="harbor", help="Installed Harbor 0.25.0 executable, e.g. .venv-harbor/bin/harbor")
    p.add_argument("--jobs-dir", type=Path, default=ROOT / "build/harbor/jobs")
    p.add_argument("--prepare-only", action="store_true", help="Stage public task inputs only; no dependencies or Docker required")
    args = p.parse_args()
    try:
        if args.prepare_only:
            print(prepare())
            return
        executable = shutil.which(args.harbor)
        if not executable:
            raise ValueError("Harbor is not installed. See tests/README.md; ask before installing test dependencies.")
        executable = str(Path(executable).resolve())
        env = {**os.environ, "HARBOR_TELEMETRY": "0"}
        version = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=15, env=env)
        if version.returncode or not re.search(r"\b0\.25\.0\b", version.stdout + version.stderr):
            raise ValueError("This suite is pinned to Harbor 0.25.0; review compatibility before using another release.")
        if not shutil.which("docker"):
            raise ValueError("Docker is required for Harbor scenarios")
        subprocess.run(["docker", "info"], check=True, capture_output=True, timeout=15)
        dataset = prepare()
        tasks = dataset if args.scenario == "all" else dataset / args.scenario
        job_name = "harness-" + uuid.uuid4().hex[:12]
        jobs = args.jobs_dir.resolve()
        if jobs.is_relative_to(ROOT) and not jobs.is_relative_to(ROOT / "build"):
            raise ValueError("Keep job logs outside the installation or under ignored build/ only")
        command = [executable, "run", "-p", str(tasks), "-a", "oracle", "-n", "1", "-k", "1", "-r", "0",
                   "-o", str(jobs), "--job-name", job_name]
        print("Dataset:", dataset, flush=True)
        subprocess.run(command, cwd=ROOT, check=True, env=env, timeout=2400)
        expected = SCENARIOS if args.scenario == "all" else (args.scenario,)
        print(json.dumps(check_job(jobs / job_name, expected), indent=2))
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        p.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
