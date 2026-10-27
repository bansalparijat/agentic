import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import blog


class MCPDecisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.call("init", "--topic", "Queues", "--audience", "Engineers")
        self.call("select-sources", "--mcp", "slack", "--mcp", "jira", "--user-confirmed")

    def call(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            blog.run(blog.parser().parse_args(["--root", str(self.root), *args]))
        return output.getvalue()

    def decision(self, choice):
        return self.call("mcp-decision", "--connector", "slack", "--connector", "jira",
                         "--capability", "read", "--reason", "Authentication unavailable",
                         "--decision", choice, "--user-confirmed")

    def state(self):
        return blog.load(self.root / "project.json")

    def test_custom_sources_and_manual_modes_are_saved(self):
        self.call("select-sources", "--mcp", "SharePoint", "--mcp", "Microsoft Teams", "--mcp", "Webex",
                  "--mcp", "Our custom wiki", "--manual", "Office exports", "--user-confirmed")
        plan = self.state()["source_plan"]
        self.assertEqual([s["name"] for s in plan["sources"]],
                         ["SharePoint", "Microsoft Teams", "Webex", "Our custom wiki", "Office exports"])
        self.assertEqual(plan["sources"][-1]["mode"], "manual")
        self.assertEqual(plan["destinations"], [])
        self.call("mcp-decision", "--connector", "Our custom wiki", "--capability", "read",
                  "--reason", "No connector", "--decision", "proceed", "--user-confirmed")
        self.assertEqual(blog.delivery(self.root, self.state())["source_plan"], plan)

    def test_unselected_and_manual_sources_cannot_trigger_mcp_decisions(self):
        self.call("select-sources", "--mcp", "SharePoint", "--manual", "Word exports", "--user-confirmed")
        for name in ("Confluence", "slack", "Google Docs", "Word exports"):
            with self.assertRaisesRegex(ValueError, "only for explicitly selected"):
                self.call("mcp-decision", "--connector", name, "--capability", "read",
                          "--reason", "No access", "--decision", "exit", "--user-confirmed")
        self.assertFalse(self.state().get("workflow_stopped"))
        self.assertNotIn("mcp_decisions", self.state())

    def test_manual_only_plan_needs_no_mcp(self):
        self.call("select-sources", "--manual", "Local PDFs and transcripts", "--user-confirmed")
        self.assertTrue(all(s["mode"] == "manual" for s in self.state()["source_plan"]["sources"]))
        with self.assertRaisesRegex(ValueError, "only for explicitly selected"):
            self.decision("proceed")

    def test_explicit_cloud_destination_is_separate(self):
        self.call("select-sources", "--mcp", "SharePoint", "--destination", "Google Docs", "--user-confirmed")
        self.assertEqual(self.state()["source_plan"]["destinations"], ["Google Docs"])
        self.call("mcp-decision", "--connector", "Google Docs", "--capability", "create document",
                  "--reason", "Missing write tool", "--decision", "proceed", "--user-confirmed")
        self.assertEqual(self.state()["mcp_decisions"][0]["connectors"], ["Google Docs"])

    def test_missing_plan_requires_source_intake(self):
        state = self.state()
        state.pop("source_plan")
        blog.save(self.root / "project.json", state)
        with self.assertRaisesRegex(ValueError, "select sources before"):
            self.decision("proceed")

    def test_duplicate_or_empty_source_choices_are_rejected(self):
        for args in (("--mcp", "Teams", "--manual", "teams"), ("--mcp", "   "), ()):
            with self.assertRaises(ValueError):
                self.call("select-sources", *args, "--user-confirmed")

    def test_proceed_records_skips_without_stopping(self):
        self.decision("proceed")
        state = self.state()
        self.assertFalse(state.get("workflow_stopped"))
        entry = state["mcp_decisions"][0]
        self.assertEqual(entry["connectors"], ["slack", "jira"])
        self.assertEqual(entry["decision"], "proceed")
        self.assertEqual(entry["stage"], "COLLECTION")
        # Actual available work can continue.
        path = self.root / "outputs/data/normalized/local.md"
        path.write_text("User-provided evidence", encoding="utf-8")
        self.call("source", "--file", str(path.relative_to(self.root)), "--kind", "local",
                  "--title", "Evidence", "--locator", "user-upload", "--confidentiality", "internal")
        self.assertEqual(len(blog.load(self.root / "outputs/data/catalog.json")), 1)
        self.assertEqual(blog.delivery(self.root, self.state())["mcp_decisions"], [entry])

    def test_exit_preserves_stage_and_blocks_mutations(self):
        self.decision("exit")
        self.assertTrue(self.state()["workflow_stopped"])
        self.assertEqual(self.state()["stage"], "COLLECTION")
        self.assertIn("workflow_stopped", self.call("status"))
        for args in (("advance", "--to", "DRAFT", "--user-confirmed"),
                     ("export",), ("complete", "--user-confirmed")):
            with self.assertRaisesRegex(ValueError, "Workflow stopped"):
                self.call(*args)

    def test_explicit_resume_preserves_issue_history(self):
        self.decision("exit")
        self.call("resume", "--user-confirmed")
        self.assertNotIn("workflow_stopped", self.state())
        self.assertEqual(self.state()["mcp_decisions"][0]["decision"], "exit")
        self.decision("proceed")
        self.assertEqual(len(self.state()["mcp_decisions"]), 2)

    def test_proceed_does_not_bypass_evidence_validation(self):
        self.decision("proceed")
        with self.assertRaisesRegex(ValueError, "at least one real source"):
            self.call("advance", "--to", "DRAFT", "--user-confirmed")


@unittest.skipUnless(shutil.which("git"), "Git not installed")
class GitOutputGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "--quiet")
        shutil.copyfile(REPO / ".gitignore", self.root / ".gitignore")
        (self.root / "outputs/data").mkdir(parents=True)
        (self.root / "outputs/data/evidence.md").write_text("private evidence", encoding="utf-8")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def guard(self):
        return subprocess.run([sys.executable, str(REPO / ".githooks/pre-commit")],
                              cwd=self.root, capture_output=True, text=True)

    def test_outputs_are_ignored_recursively(self):
        self.git("add", ".")
        tracked = self.git("ls-files").stdout.decode()
        self.assertNotIn("outputs/", tracked)
        self.git("check-ignore", "outputs/data/evidence.md")
        self.assertEqual(self.guard().returncode, 0)

    def test_guard_rejects_force_add_and_allows_index_only_removal(self):
        self.git("add", "-f", "outputs/data/evidence.md")
        result = self.guard()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Commit blocked", result.stderr)
        self.git("rm", "--cached", "outputs/data/evidence.md")
        self.assertEqual(self.guard().returncode, 0)
        self.assertTrue((self.root / "outputs/data/evidence.md").is_file())

    def test_personal_input_is_ignored_but_sanitized_sample_is_trackable(self):
        (self.root / "input").mkdir()
        (self.root / "input/blog.json").write_text('{"private": true}', encoding="utf-8")
        (self.root / "input/input_sample.json").write_text('{"schema_version": 1}', encoding="utf-8")
        (self.root / "input/README.md").write_text("Sanitized example documentation", encoding="utf-8")
        self.git("add", ".")
        tracked = self.git("ls-files").stdout.decode()
        self.assertNotIn("input/blog.json", tracked)
        self.assertIn("input/input_sample.json", tracked)
        self.assertIn("input/README.md", tracked)
        self.git("check-ignore", "input/blog.json")

    def test_hook_is_executable(self):
        self.assertTrue((REPO / ".githooks/pre-commit").stat().st_mode & 0o111)


if __name__ == "__main__":
    unittest.main()
