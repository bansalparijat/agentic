import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import blog
import host


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.brief = {"topic": "Safe retries", "audience": "Backend developers", "words": 1200,
                      "publication": "public", "files": ["notes.md"], "store_confidential_locally": False}

    def call(self, *args, root=None):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            blog.run(blog.parser().parse_args(["--root", str(root or self.root), *args]))
        return json.loads(output.getvalue())

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_new_run_validates_and_prefills_default_input_without_initializing(self):
        blog.save(self.root / "input/blog.json", self.brief)
        before = self.snapshot()
        output = self.call("startup")
        self.assertEqual(output["action"], "new_intake")
        self.assertTrue(output["input_validated"])
        self.assertEqual(output["preferences"], self.brief)
        self.assertEqual(output["missing_fields"], [])
        self.assertEqual(output["titles_stage"], "PREPARE")
        self.assertEqual(Path(output["input_guide"]), REPO / "input/README.md")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / "project.json").exists())
        self.assertFalse((self.root / "outputs").exists())

    def test_named_file_wins_over_default(self):
        blog.save(self.root / "input/blog.json", {"words": -1})
        blog.save(self.root / "input/chosen.json", self.brief)
        output = self.call("startup", "--input", "input/chosen.json")
        self.assertEqual(output["input_file"], str(self.root / "input/chosen.json"))
        self.assertEqual(output["preferences"], self.brief)

    def test_invalid_new_input_fails_without_writing_state(self):
        blog.save(self.root / "input/blog.json", {"words": -1})
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.call("startup")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / "outputs").exists())

    def test_existing_run_never_reopens_invalid_or_missing_input(self):
        state = {"stage": "REVISE", "approval": {"sha256": "preserve"}, "intake": {"private": "sentinel"}}
        blog.save(self.root / "project.json", state)
        blog.save(self.root / "outputs/input.json", {"original": "keep"})
        (self.root / "outputs/decisions.md").write_text("Latest decisions win", encoding="utf-8")
        blog.save(self.root / "input/blog.json", {"words": -1})
        before = self.snapshot()
        for args in ((), ("--input", "input/blog.json"), ("--input", "missing.json")):
            with self.subTest(args=args):
                output = self.call("startup", *args)
                self.assertEqual(output["action"], "resume_saved_run")
                self.assertEqual(output["stage"], "REVISE")
                self.assertNotIn("preferences", output)
                self.assertNotIn("sentinel", json.dumps(output))
                self.assertNotIn("input_validated", output)
        self.assertEqual(self.snapshot(), before)

    def test_stopped_run_stays_stopped_until_actual_resume(self):
        blog.save(self.root / "project.json", {"stage": "COLLECTION", "workflow_stopped": True})
        before = self.snapshot()
        output = self.call("startup", "--input", "does-not-exist.json")
        self.assertEqual(output["action"], "await_explicit_resume")
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(blog.load(self.root / "project.json")["workflow_stopped"])

    def test_no_input_asks_only_missing_essentials_without_using_samples(self):
        blog.save(self.root / "input/sample_single.json", self.brief)
        before = self.snapshot()
        output = self.call("startup")
        self.assertEqual(output["action"], "ask_for_input_or_missing_preferences")
        self.assertFalse(output["input_validated"])
        self.assertIn("words", output["missing_fields"])
        self.assertNotIn("title", output["missing_fields"])
        self.assertNotIn("notes", output["missing_fields"])
        self.assertEqual(self.snapshot(), before)

    def test_missing_workspace_and_named_file_are_not_created(self):
        missing_root = self.root / "new-workspace"
        output = self.call("startup", root=missing_root)
        self.assertTrue(output["read_only"])
        self.assertFalse(missing_root.exists())
        with self.assertRaises(OSError):
            self.call("startup", "--input", "missing.json", root=missing_root)
        self.assertFalse(missing_root.exists())

    def test_all_host_checks_expose_same_workspace_aware_bootstrap(self):
        before = self.snapshot()
        _, hosts = host.registry()
        manifest = blog.load(REPO / "harness/manifest.json")
        self.assertEqual(manifest["runtime"]["bootstrap_command"], ["scripts/blog.py", "startup"])
        for name in hosts:
            output = host.check(name, self.root)
            command = output["bootstrap_command"]
            self.assertEqual(command[1:], [str(REPO / "scripts/blog.py"), "--root", str(self.root), "startup"])
        self.assertEqual(self.snapshot(), before)

    def test_saved_prepare_routes_to_prepare_without_loading_new_brief(self):
        blog.save(self.root / "project.json", {"stage": "PREPARE", "require_title_selection": True})
        output = self.call("startup", "--input", "not-present.json")
        self.assertEqual(output["stage"], "PREPARE")
        self.assertEqual(output["titles_stage"], "PREPARE")
        self.assertTrue(output["supplied_input_ignored"])
        self.assertEqual(output["action"], "resume_saved_run")


class PromptContractTests(unittest.TestCase):
    def test_user_prompts_only_need_intent_and_file(self):
        simple = "> Start a technical blog using input/blog.json."
        for name in ("README.md", "input/README.md", "harness/adapters/README.md"):
            text = (REPO / name).read_text(encoding="utf-8")
            self.assertIn(simple, text, name)
            for line in text.splitlines():
                if line.lstrip().startswith(">"):
                    self.assertNotIn("Suggest titles", line, name)
                    self.assertNotIn("Ask only", line, name)
                    self.assertNotIn("syntax and semantics", line, name)
                    self.assertNotIn("reinitializing", line, name)

    def test_shared_rules_own_automatic_intake_and_prepare_title_question(self):
        agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("mandatory harness responsibilities", agents)
        self.assertIn("scripts/blog.py startup", agents)
        prepare = (REPO / "harness/stages/prepare.md").read_text(encoding="utf-8")
        self.assertIn("runs automatically", prepare)
        self.assertIn("Which title would you like to use?", prepare)
        self.assertIn("suggest your own", prepare)


if __name__ == "__main__":
    unittest.main()
