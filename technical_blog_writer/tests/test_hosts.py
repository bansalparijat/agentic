import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import blog
import host


class HostAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name).resolve()

    def snapshot(self):
        return {str(p.relative_to(self.workspace)): p.read_bytes()
                for p in self.workspace.rglob("*") if p.is_file()}

    def test_all_declared_adapters_have_entrypoints_and_contract(self):
        manifest, hosts = host.registry()
        self.assertEqual(set(hosts), {"codex", "claude-code", "opencode", "gemini-cli", "cursor", "copilot", "generic"})
        self.assertTrue(host.installed_file(manifest["capability_contract"]).is_file())
        for name, entry in hosts.items():
            with self.subTest(host=name):
                entrypoint = host.installed_file(entry["entrypoint"]).read_text(encoding="utf-8")
                adapter = host.installed_file(entry["adapter"]).read_text(encoding="utf-8")
                if entry["entrypoint"] != manifest["entrypoint"]:
                    self.assertIn("AGENTS.md", entrypoint)
                self.assertIn("harness/contracts/host-capabilities.md", adapter)
                self.assertIn("scripts/host.py --host " + name, adapter)

    def test_local_check_is_read_only_for_every_host(self):
        before = self.snapshot()
        _, hosts = host.registry()
        for name in hosts:
            with self.subTest(host=name):
                info = host.check(name, self.workspace)
                self.assertEqual(info["status"], "local-ready")
                self.assertFalse(info["project_exists"])
                self.assertFalse(info["workflow_stopped"])
                self.assertTrue(info["unverified"])
                self.assertEqual(info["workspace_root"], str(self.workspace))
                self.assertEqual(info["harness_root"], str(REPO))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_check_preserves_stopped_state_and_does_not_expose_source_data(self):
        blog.save(self.workspace / "project.json", {
            "stage": "REVISE", "workflow_stopped": True, "topic": "PRIVATE_SENTINEL",
            "source_plan": {"sources": [{"name": "Private wiki", "mode": "mcp"}], "destinations": []}})
        blog.save(self.workspace / "outputs/data/collection-state.json", {"requests": 7, "nodes": {}})
        before = self.snapshot()
        for name in ("codex", "claude-code", "opencode", "generic"):
            info = host.check(name, self.workspace)
            self.assertTrue(info["workflow_stopped"])
            self.assertTrue(info["source_selection_saved"])
            self.assertTrue(info["collection_policy_saved"])
            self.assertEqual(info["stage"], "REVISE")
            self.assertIn("explicit user resume", info["next_action"])
            self.assertNotIn("PRIVATE_SENTINEL", json.dumps(info))
        self.assertEqual(self.snapshot(), before)

    def test_workspace_aware_startup_commands_only_read_status(self):
        before = self.snapshot()
        info = host.check("opencode", self.workspace)
        for index, command in enumerate(info["startup_commands"]):
            self.assertEqual(command[-3:], ["--root", str(self.workspace), "status"])
            self.assertEqual(Path(command[1]).parent, REPO / "scripts")
            # blog status can read an empty workspace; collection status requires a project.
            if index == 0:
                result = subprocess.run(command, cwd=self.workspace, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("No project", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_switching_host_keeps_same_workspace_and_shared_state(self):
        blog.save(self.workspace / "project.json", {"stage": "DRAFT", "approval": {"sha256": "unchanged"}})
        before = self.snapshot()
        one = host.check("claude-code", self.workspace)
        two = host.check("opencode", self.workspace)
        self.assertEqual(one["startup_commands"], two["startup_commands"])
        self.assertEqual(one["stage"], two["stage"])
        self.assertNotEqual(one["adapter"], two["adapter"])
        self.assertEqual(self.snapshot(), before)

    def test_missing_workspace_and_unknown_host_fail_without_initializing(self):
        with self.assertRaisesRegex(ValueError, "Unknown host"):
            host.check("made-up-host", self.workspace)
        missing = self.workspace / "missing"
        with self.assertRaisesRegex(ValueError, "must already exist"):
            host.check("codex", missing)
        self.assertFalse(missing.exists())

    def test_installation_path_cannot_escape(self):
        with self.assertRaisesRegex(ValueError, "invalid harness file"):
            host.installed_file("../AGENTS.md")

    def test_claude_imports_are_real_files(self):
        text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
        imports = re.findall(r"^@([^\s]+)$", text, re.M)
        self.assertEqual(imports, ["AGENTS.md", "harness/adapters/claude-code.md"])
        self.assertTrue(all((REPO / path).is_file() for path in imports))

    def test_cursor_rule_has_native_frontmatter(self):
        text = (REPO / ".cursor/rules/technical-blog.mdc").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("alwaysApply: true", text.split("---", 2)[1])
        self.assertIn("harness/adapters/cursor.md", text)
        self.assertIn("unrelated coding", text)

    def test_host_cli_lists_and_checks_from_another_directory(self):
        command = [sys.executable, str(REPO / "scripts/host.py")]
        listed = subprocess.run(command + ["--list"], cwd=self.workspace, capture_output=True, text=True)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn("generic", [entry["id"] for entry in json.loads(listed.stdout)])
        checked = subprocess.run(command + ["--host", "claude-code", "--root", str(self.workspace)],
                                 cwd=self.workspace, capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["host"], "claude-code")
        self.assertEqual(self.snapshot(), {})

    def test_shared_policies_do_not_depend_on_codex_tools(self):
        paths = [REPO / "scripts/blog.py", *list((REPO / "harness/policies").glob("*.md")),
                 *list((REPO / "harness/workflows").glob("*.md")), *list((REPO / "harness/stages").glob("*.md"))]
        for path in paths:
            with self.subTest(path=str(path)):
                self.assertNotIn("Codex", path.read_text(encoding="utf-8"))

    def test_manifest_schema_declares_host_contract(self):
        schema = blog.load(REPO / "harness/schemas/manifest.schema.json")
        self.assertIn("hosts", schema["required"])
        self.assertIn("capability_contract", schema["required"])
        self.assertEqual(schema["properties"]["hosts"]["items"]["required"],
                         ["id", "entrypoint", "adapter", "activation"])


if __name__ == "__main__":
    unittest.main()
