import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import blog
import collection


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = {"stage": "COLLECTION", "source_plan": {
            "sources": [{"name": "Confluence", "mode": "mcp"}, {"name": "Jira", "mode": "mcp"},
                        {"name": "Files", "mode": "manual"}], "destinations": []}}
        self.config = blog.load(REPO / "harness/config.collection.json")
        self.config["sources"] = {
            "Confluence": {"backend": "shared", "scope_prefixes": ["https://example.test/team"]},
            "Jira": {"backend": "shared", "scope_prefixes": ["https://example.test/issues"]},
            "Files": {"backend": "local", "scope_prefixes": ["file:///tmp/research"]}}
        blog.save(self.root / "project.json", self.project)
        blog.save(self.root / "outputs/data/collection-config.json", self.config)
        self.call("configure", "--config", "outputs/data/collection-config.json", "--user-confirmed")

    def call(self, *args, clock=100):
        with contextlib.redirect_stdout(io.StringIO()) as output, patch.object(collection.time, "time", return_value=clock):
            collection.run(collection.parser().parse_args(["--root", str(self.root), *args]))
        return json.loads(output.getvalue())

    def state(self):
        return blog.load(self.root / collection.STATE)

    def save_state(self, state):
        blog.save(self.root / collection.STATE, state)

    def add(self, suffix, parent=None, relation="child"):
        args = ["add", "--source", "Confluence", "--url", "https://example.test/team/" + suffix]
        if parent:
            args += ["--parent", parent, "--relation", relation, "--reason", "Resolves the architecture question"]
        return self.call(*args)

    def finish(self, value="useful"):
        node = self.call("next")
        self.call("finish", "--key", node["key"], "--value", value, "--summary", "Evidence assessed")
        return node["key"]

    def test_canonicalization_and_cycles(self):
        first = self.add("root")
        duplicate = self.call("add", "--source", "Confluence", "--url", "https://EXAMPLE.test:443/team/root/?utm_source=x#section")
        self.assertEqual(duplicate, {"decision": "duplicate", "key": first["key"]})
        self.finish()
        child = self.add("child", first["key"])
        self.finish()
        back = self.add("root", child["key"])
        self.assertEqual(back["decision"], "duplicate")
        self.assertEqual(len(self.state()["nodes"]), 2)
        self.assertIn("version=2", collection.canonical("https://example.test/team/a?version=2#x"))

    def test_depth_limit(self):
        self.add("root")
        root = self.finish()
        self.add("one", root)
        one = self.finish()
        self.add("two", one)
        two = self.finish()
        with self.assertRaisesRegex(ValueError, "depth"):
            self.add("three", two)

    def test_mode_and_relevance_required(self):
        self.add("root")
        key = self.finish()
        state = self.state()
        state["config"]["mode"] = "none"
        self.save_state(state)
        with self.assertRaisesRegex(ValueError, "recursion mode"):
            self.add("child", key)
        state["config"]["mode"] = "children"
        self.save_state(state)
        with self.assertRaisesRegex(ValueError, "recursion mode"):
            self.add("link", key, "link")
        with self.assertRaisesRegex(ValueError, "relevance reason"):
            self.call("add", "--source", "Confluence", "--url", "https://example.test/team/child",
                      "--parent", key, "--relation", "child")

    def test_scope_and_encoded_traversal(self):
        for url in ("https://evil.test/team/a", "https://example.test/teammate/a",
                    "https://example.test/team/%2e%2e/private", "https://example.test/team/%252e%252e/private",
                    "https://example.test/team/a?access_token=SECRET"):
            with self.assertRaises(ValueError):
                self.call("add", "--source", "Confluence", "--url", url)
        self.assertEqual(self.state()["nodes"], {})

    def test_low_value_branch_and_global_stop(self):
        self.add("root")
        key = self.finish("low-value")
        self.add("one", key)
        one = self.finish("low-value")
        with self.assertRaisesRegex(ValueError, "branch pruned"):
            self.add("two", one)
        state = self.state()
        state["low_value_streak"] = state["config"]["global_low_value_limit"]
        self.save_state(state)
        with self.assertRaisesRegex(ValueError, "little value"):
            self.call("next")

    def test_breadth_first_and_one_active_item(self):
        self.add("a")
        self.add("b")
        a = self.finish()
        self.add("a-child", a)
        b = self.call("next")
        self.assertEqual(b["url"], "https://example.test/team/b")
        with self.assertRaisesRegex(ValueError, "active item"):
            self.call("next")

    def test_item_and_fanout_budgets(self):
        self.add("root")
        key = self.finish()
        state = self.state()
        state["config"]["max_links_per_item"] = 1
        self.save_state(state)
        self.add("child", key)
        with self.assertRaisesRegex(ValueError, "fan-out"):
            self.add("other", key)
        state = self.state()
        state["config"]["max_items_per_source"] = 2
        self.save_state(state)
        with self.assertRaisesRegex(ValueError, "Item budget"):
            self.add("another-root")

    def test_shared_backend_pacing_and_single_inflight(self):
        self.call("request", "--source", "Confluence")
        with self.assertRaisesRegex(ValueError, "in flight"):
            self.call("request", "--source", "Jira", clock=105)
        self.call("result", "--outcome", "success", clock=105)
        with self.assertRaisesRegex(ValueError, "WAIT 2"):
            self.call("request", "--source", "Jira", clock=105)
        self.call("request", "--source", "Jira", clock=107)
        self.assertEqual(self.state()["requests"], 2)
        self.assertEqual(self.state()["backends"]["shared"]["requests"], 2)

    def test_retry_after_and_circuit(self):
        self.call("request", "--source", "Confluence")
        self.call("result", "--outcome", "retry", "--retry-after", "60")
        with self.assertRaisesRegex(ValueError, "WAIT"):
            self.call("request", "--source", "Confluence", clock=159)
        self.call("request", "--source", "Confluence", clock=160)
        self.call("result", "--outcome", "retry", clock=160)
        self.call("request", "--source", "Confluence", clock=170)
        self.call("result", "--outcome", "retry", clock=170)
        with self.assertRaisesRegex(ValueError, "circuit"):
            self.call("request", "--source", "Jira", clock=200)
        self.assertEqual(self.state()["requests"], 3)

    def test_resource_error_does_not_disable_healthy_backend(self):
        self.call("request", "--source", "Confluence")
        self.call("result", "--outcome", "resource-error")
        self.assertFalse(self.state()["backends"]["shared"]["open"])
        self.call("request", "--source", "Jira", clock=102)
        self.assertEqual(self.state()["requests"], 2)

    def test_elapsed_and_request_budgets(self):
        with self.assertRaisesRegex(ValueError, "time budget"):
            self.call("next", clock=1300)
        state = self.state()
        state["requests"] = state["config"]["max_requests_total"]
        self.save_state(state)
        with self.assertRaisesRegex(ValueError, "Request budget"):
            self.call("request", "--source", "Confluence")

    def test_no_reconfigure_or_unselected_calls(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.call("configure", "--config", "outputs/data/collection-config.json", "--user-confirmed")
        for source in ("Slack", "Files"):
            with self.assertRaisesRegex(ValueError, "only for selected"):
                self.call("request", "--source", source)
        self.project["workflow_stopped"] = True
        blog.save(self.root / "project.json", self.project)
        with self.assertRaisesRegex(ValueError, "Workflow stopped"):
            self.call("request", "--source", "Confluence")

    def test_overlapping_controller_calls_fail_closed(self):
        lock = self.root / "outputs/data/.collection.lock"
        lock.write_text("another writer", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "controller busy"):
            self.call("request", "--source", "Confluence")
        self.assertEqual(self.state()["requests"], 0)
        self.assertTrue(lock.exists())
        lock.unlink()
        self.call("request", "--source", "Confluence")
        self.assertFalse(lock.exists())

    def test_backend_budget_independent_of_global_budget(self):
        state = self.state()
        state["backends"]["shared"] = {"requests": state["config"]["max_requests_per_backend"],
                                         "next_at": 0, "retries": 0, "open": False}
        self.save_state(state)
        with self.assertRaisesRegex(ValueError, "Request budget"):
            self.call("request", "--source", "Confluence")
        self.assertFalse((self.root / "outputs/data/.collection.lock").exists())

    def test_invalid_policy(self):
        for key, value in (("min_interval_seconds", 0), ("max_depth", -1), ("max_retries", True)):
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ValueError):
                collection.validate(config, self.project)


class HarnessContractTests(unittest.TestCase):
    def test_manifest_paths_and_stage_contracts(self):
        manifest = blog.load(REPO / "harness/manifest.json")
        paths = [manifest[k] for k in ("entrypoint", "workflow", "defaults", "git_guard")]
        paths += manifest["policies"] + manifest["runtime"]["commands"]
        paths += [s["guide"] for s in manifest["stages"]]
        for path in paths:
            self.assertTrue((REPO / path).is_file(), path)
        self.assertEqual([s["id"] for s in manifest["stages"]], list(blog.STAGES))
        for stage in manifest["stages"]:
            self.assertTrue(stage["inputs"] and stage["gate"])
            self.assertTrue(all(path.startswith("outputs/") for path in stage["outputs"]))
        self.assertEqual(manifest["schema_version"], 1)

    def test_harness_references_are_not_stale(self):
        old = ("harness/workflow.md", "harness/sources.md", "harness/mcp.md",
               "harness/editorial.md", "harness/publishing.md")
        docs = [REPO / "AGENTS.md", REPO / "README.md", *list((REPO / "harness").rglob("*.md"))]
        for path in docs:
            text = path.read_text(encoding="utf-8")
            for stale in old:
                self.assertNotIn(stale, text, str(path))


if __name__ == "__main__":
    unittest.main()
