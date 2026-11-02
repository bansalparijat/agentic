"""Fast regression checks for the test infrastructure, not live Harbor/Vitest certification."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_harbor
import run_harbor

spec = importlib.util.spec_from_file_location("scenario_verifier", ROOT / "tests/scenarios/verify.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
try:
    import tomllib
except ImportError:  # Core helpers still support 3.10; Harbor itself needs 3.12+.
    tomllib = None


class TestToolingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harness-tooling-tests-")
        self.addCleanup(self.temp.cleanup)
        self.temp_root = Path(self.temp.name).resolve()

    def fake_installation(self):
        root = self.temp_root / "installation"
        names = prepare_harbor.public_paths()
        names += [f"tests/harbor/tasks/{task}/{name}" for task in prepare_harbor.SCENARIOS for name in prepare_harbor.TASK_FILES]
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, path)
        return root

    def test_public_allowlist_excludes_private_runtime_and_personal_inputs(self):
        names = prepare_harbor.public_paths()
        self.assertIn("input/sample_single.json", names)
        self.assertIn("tests/editorial_fixtures.py", names)
        self.assertNotIn("project.json", names)
        self.assertNotIn("input/blog.json", names)
        self.assertFalse(any(name.startswith("outputs/") or ".env" in name for name in names))

    def test_stages_complete_tasks_with_exact_public_contracts(self):
        stage = prepare_harbor.prepare(self.temp_root / "dataset")
        for name in prepare_harbor.SCENARIOS:
            task = stage / name
            for path in prepare_harbor.TASK_FILES:
                self.assertTrue((task / path).is_file(), path)
            contracts = json.loads((task / "tests/contracts.json").read_text())
            self.assertEqual(set(contracts), set(prepare_harbor.public_paths()))
            for path, digest in contracts.items():
                self.assertEqual(verifier.sha(task / "environment/harness" / path), digest)
            self.assertTrue((task / "tests/verify.py").is_file())
            self.assertFalse((task / "environment/harness/project.json").exists())

    def test_existing_stage_is_not_overwritten(self):
        stage = self.temp_root / "existing"
        stage.mkdir()
        sentinel = stage / "keep"
        sentinel.write_text("preserve")
        with self.assertRaises(FileExistsError):
            prepare_harbor.prepare(stage)
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_refuses_private_installation_destinations(self):
        with self.assertRaisesRegex(ValueError, "ignored build"):
            prepare_harbor.prepare(ROOT / "outputs/NEVER_CREATE_TEST_STAGE")
        self.assertFalse((ROOT / "outputs/NEVER_CREATE_TEST_STAGE").exists())

    def test_refuses_symlinked_sources(self):
        root = self.fake_installation()
        source = root / "harness/README.md"
        source.unlink()
        target = self.temp_root / "private.md"
        target.write_text("not for staging")
        source.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            prepare_harbor.public_paths(root)

    def test_manifest_cannot_select_private_files_for_staging(self):
        root = self.fake_installation()
        path = root / "harness/manifest.json"
        value = json.loads(path.read_text())
        value["runtime"]["commands"].append("project.json")
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "Unsafe public"):
            prepare_harbor.public_paths(root)

    def test_extra_template_files_are_not_copied(self):
        root = self.fake_installation()
        private = root / "tests/harbor/tasks/full-cycle/environment/.env"
        private.write_text("SYNTHETIC_PRIVATE_SENTINEL=do-not-copy")
        stage = prepare_harbor.prepare(self.temp_root / "safe-dataset", root)
        self.assertFalse((stage / "full-cycle/environment/.env").exists())

    @unittest.skipUnless(tomllib, "TOML inspection needs Python 3.11+; Harbor needs 3.12+")
    def test_task_policies_are_isolated_and_separately_verified(self):
        for name in prepare_harbor.SCENARIOS:
            task = tomllib.loads((ROOT / f"tests/harbor/tasks/{name}/task.toml").read_text())
            self.assertEqual(task["schema_version"], "1.4")
            self.assertEqual(task["artifacts"], ["/workspace/" + name])
            self.assertEqual(task["verifier"]["environment_mode"], "separate")
            for phase in ("environment", "agent", "verifier"):
                self.assertEqual(task[phase]["network_mode"], "no-network")
            self.assertNotIn("env", task["environment"])
            script = (ROOT / f"tests/harbor/tasks/{name}/tests/test.sh").read_text()
            self.assertLess(script.index("printf '0"), script.index("python3"))
            self.assertLess(script.index("python3"), script.index("printf '1"))

    def job(self, rewards=None):
        job = self.temp_root / "job"
        job.mkdir(exist_ok=True)
        summary = {"finished_at": "SYNTHETIC", "stats": {"n_completed_trials": 2, "n_errored_trials": 0}}
        (job / "result.json").write_text(json.dumps(summary))
        for name in prepare_harbor.SCENARIOS:
            folder = job / name
            folder.mkdir(exist_ok=True)
            trial = {"task_name": "technical-blog/" + name, "finished_at": "SYNTHETIC", "exception_info": None,
                     "verifier_result": {"rewards": {"reward": 1} if rewards is None else rewards}}
            (folder / "result.json").write_text(json.dumps(trial))
        return job

    def test_harbor_result_reader_accepts_complete_success(self):
        self.assertEqual(run_harbor.check_job(self.job(), prepare_harbor.SCENARIOS)["status"], "pass")

    def test_process_success_is_not_enough_without_passing_rewards(self):
        for reward in ({}, {"reward": 0}, {"reward": True}, {"other": 1}):
            with self.subTest(reward=reward), self.assertRaisesRegex(ValueError, "no passing reward"):
                run_harbor.check_job(self.job(reward), prepare_harbor.SCENARIOS)

    def test_incomplete_and_errored_jobs_fail_closed(self):
        for counts in ((1, 0), (2, 1)):
            job = self.job()
            path = job / "result.json"
            value = json.loads(path.read_text())
            value["stats"].update(n_completed_trials=counts[0], n_errored_trials=counts[1])
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "incomplete or errored"):
                run_harbor.check_job(job, prepare_harbor.SCENARIOS)

    def test_missing_duplicate_or_unexpected_trials_fail(self):
        job = self.job()
        for task in ("unexpected", "full-cycle"):
            path = job / "recovery-and-limits/result.json"
            value = json.loads(path.read_text())
            value["task_name"] = task
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "Missing/duplicate/unexpected"):
                run_harbor.check_job(job, prepare_harbor.SCENARIOS)
        (job / "recovery-and-limits/result.json").unlink()
        with self.assertRaisesRegex(ValueError, "Missing/duplicate/unexpected"):
            run_harbor.check_job(job, prepare_harbor.SCENARIOS)

    def test_empty_or_absent_scenario_cannot_pass_verifier(self):
        for name in prepare_harbor.SCENARIOS:
            with self.assertRaisesRegex(ValueError, "Missing/escaping artifact"):
                verifier.verify(self.temp_root / "empty", name, ROOT)

    def test_verifier_rejects_artifact_symlink_escapes(self):
        workspace = self.temp_root / "workspace"
        marker = workspace / "outputs/data/SYNTHETIC-TEST-ONLY"
        marker.parent.mkdir(parents=True)
        marker.write_text("fixture")
        outside = self.temp_root / "private.json"
        outside.write_text("{}")
        (marker.parent / "scenario-result.json").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Missing/escaping artifact"):
            verifier.verify(workspace, "full-cycle", ROOT)


if __name__ == "__main__":
    unittest.main()
