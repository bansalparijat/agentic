import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import blog
import intake
from editorial_fixtures import pass_quality


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.raw = blog.load(REPO / "input/input_sample.json")
        self.data = intake.validate(self.raw)

    def put_input(self, data=None, name="input/blog.json"):
        path = self.root / name
        blog.save(path, self.raw if data is None else data)
        return path

    def call(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            blog.run(blog.parser().parse_args(["--root", str(self.root), *args]))
        return output.getvalue()

    def state(self):
        return blog.load(self.root / "project.json")

    def stage(self, stage):
        state = self.state()
        state["stage"] = stage
        blog.save(self.root / "project.json", state)

    def options(self):
        blog.save(self.root / "outputs/blog/title-options.json", [
            {"id": "T1", "title": "Sandbox architecture", "angle": "Architecture"},
            {"id": "T2", "title": "The cost of isolation", "angle": "Trade-offs"},
            {"id": "T3", "title": "Building a customer sandbox", "angle": "Production journey"}])
        self.call("titles", "--file", "outputs/blog/title-options.json")

    def prepare(self):
        self.call("init", "--topic", "Sandbox", "--audience", "Engineers")
        self.stage("REVISE")
        path = self.root / "outputs/revised_draft/revision-001.md"
        path.write_text("# Provisional heading\n\nEvidence-backed body.\n", encoding="utf-8")
        path.with_name("revision-001-notes.md").write_text("Requested changes addressed.", encoding="utf-8")
        pass_quality(self.root, [str(path.relative_to(self.root))])
        self.call("approve", "--file", str(path.relative_to(self.root)), "--user-confirmed")
        return path

    def test_all_samples_are_simple_valid_and_title_free(self):
        manifest = blog.load(REPO / "harness/manifest.json")
        self.assertEqual(len(manifest["input_samples"]), 5)
        for name in manifest["input_samples"]:
            with self.subTest(sample=name):
                raw = blog.load(REPO / name)
                normalized = intake.validate(raw)
                self.assertEqual(intake.missing_fields(normalized), [])
                self.assertNotIn("title_preferences", raw)
                self.assertNotIn("research", raw)
                self.assertNotIn("source_notes", raw)
                self.assertNotIn("blog", raw)
                self.assertIn("words", raw)
                self.assertIn("audience", normalized["blog"])
        self.assertEqual(self.data["draft"]["target_words"], 2000)
        self.assertEqual(self.data["blog"]["series"]["total_parts"], 3)
        self.assertEqual(self.data["research"]["cutoff_date"], "2025-12-31")
        self.assertNotIn("rippling.atlassian.net", json.dumps(self.raw))

    def test_small_brief_defaults_and_missing_essentials(self):
        raw = {"topic": "Queues", "audience": "Backend developers", "words": 1200,
               "publication": "public", "sources": {"GitHub": []}}
        data = intake.validate(raw)
        self.assertEqual(data["blog"]["series"], {"kind": "single"})
        self.assertEqual(data["draft"]["versions"], 2)
        self.assertEqual(data["publication"], {"formats": ["markdown", "html", "pdf"], "cloud_destinations": []})
        self.assertEqual(data["navigation"]["mode"], "both")
        self.assertEqual(data["navigation"]["max_depth"], 2)
        self.assertEqual(intake.missing_fields(data), ["store_confidential_locally"])
        self.assertNotIn("store_confidential_locally", data["privacy"])

    def test_series_is_opt_in_and_roadmap_preserved(self):
        single = intake.read_input(REPO / "input/sample_single.json")
        self.assertEqual(single["blog"]["series"]["kind"], "single")
        series = self.data["blog"]["series"]
        self.assertEqual((series["part_number"], series["total_parts"]), (1, 3))
        self.assertEqual([p["focus"] for p in series["roadmap"]], self.raw["series"]["roadmap"])

    def test_optional_information_is_not_lost_during_normalization(self):
        raw = copy.deepcopy(self.raw)
        raw.update({"drafts": 3, "tone": "Plain English", "count_scope": "Body only", "from_date": "2025-01-01",
                    "questions": ["Why this design?"], "source_scopes": {"GitHub": "Only repository deployment code"},
                    "source_settings": {"GitHub": {"backend": "shared-github", "scope_prefixes": ["https://github.com/example"]}},
                    "limits": {"max_requests_total": 40, "min_interval_seconds": 4}})
        data = intake.validate(raw)
        self.assertEqual(data["blog"]["required_coverage"], raw["cover"])
        self.assertEqual(data["blog"]["exclusions"], raw["exclude"])
        self.assertEqual(data["draft"]["count_scope"], "Body only")
        self.assertEqual(data["draft"]["tone"], "Plain English")
        self.assertEqual(data["research"]["from_date"], "2025-01-01")
        self.assertEqual(data["research"]["questions"], raw["questions"])
        self.assertEqual(data["research"]["source_notes"], raw["notes"])
        gh = next(s for s in data["sources"] if s["name"] == "GitHub")
        self.assertEqual(gh["scope_notes"], raw["source_scopes"]["GitHub"])
        self.assertEqual(gh["backend"], "shared-github")
        self.assertEqual(data["navigation"]["max_requests_total"], 40)
        self.assertEqual(data["navigation"]["min_interval_seconds"], 4)

    def test_local_and_custom_manual_sources_need_no_mcp(self):
        data = intake.validate({"files": ["notes.pdf"], "manual_sources": {"Word exports": ["design.docx"]}, "follow": "none"})
        self.assertEqual({s["name"] for s in data["sources"]}, {"Local files", "Word exports"})
        self.assertTrue(all(s["mode"] == "manual" for s in data["sources"]))
        self.put_input({"topic": "Queues", "audience": "Engineers", "files": ["notes.md"]})
        self.call("init")
        self.call("apply-input", "--user-confirmed")
        self.assertEqual(self.state()["source_plan"]["destinations"], [])
        with self.assertRaisesRegex(ValueError, "only for explicitly selected"):
            self.call("mcp-decision", "--connector", "Google Docs", "--capability", "read", "--reason", "Missing",
                      "--decision", "exit", "--user-confirmed")

    def test_inspect_displays_original_simple_brief_without_writes(self):
        self.put_input()
        result = json.loads(self.call("inspect-input"))
        self.assertEqual(result["preferences"], self.raw)
        self.assertNotIn("blog", result["preferences"])
        self.assertEqual(result["missing_fields"], [])
        self.assertFalse((self.root / "project.json").exists())
        self.assertFalse((self.root / "outputs").exists())

    def test_init_normalizes_internally_but_snapshots_original(self):
        path = self.put_input()
        self.call("init")
        state = self.state()
        self.assertEqual(state["topic"], self.raw["topic"])
        self.assertEqual(state["draft_settings"]["words"], 2000)
        self.assertEqual(state["input_origin"]["sha256"], blog.sha(path))
        self.assertEqual(state["intake"], self.data)
        self.assertEqual(blog.load(self.root / "outputs/input.json"), self.raw)
        for field in ("source_plan", "approval", "hero", "title_selection", "google_doc"):
            self.assertNotIn(field, state)
        self.assertTrue((self.root / "outputs/decisions.md").is_file())
        self.assertFalse((self.root / "decisions.md").exists())

    def test_no_sample_is_automatically_used(self):
        self.put_input(name="input/input_sample.json")
        self.put_input(name="input/sample_single.json")
        self.call("init", "--topic", "Manual topic", "--audience", "Engineers")
        self.assertNotIn("intake", self.state())

    def test_apply_input_requires_confirmation_and_cannot_replay(self):
        self.put_input()
        self.call("init")
        self.call("apply-input", "--user-confirmed")
        state = self.state()
        self.assertEqual([s["name"] for s in state["source_plan"]["sources"]], list(self.raw["sources"]))
        self.assertEqual(state["source_plan"]["destinations"], ["Google Docs"])
        self.assertNotIn("approval", state)
        self.assertFalse((self.root / "outputs/data/collection-state.json").exists())
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.call("apply-input", "--user-confirmed")
        self.stage("PREPARE")
        with self.assertRaisesRegex(ValueError, "Requires stage"):
            self.call("apply-input", "--user-confirmed")

    def test_removed_fields_approval_fields_and_bad_types_are_rejected(self):
        for field in ("title_preferences", "title", "source_notes", "research", "approved", "authentication_token"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                intake.validate({field: "Not supported"})
        for field, value in (("words", 0), ("words", True), ("drafts", 4), ("follow", "unlimited")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                intake.validate({field: value})

    def test_cross_validation(self):
        bad = [
            {"series": {"part": 4, "total": 3}},
            {"series": {"part": 1, "total": 1}},
            {"series": {"part": 1, "total": 2, "roadmap": ["A", "B", "C"]}},
            {"from_date": "2026-01-01", "cutoff_date": "2025-01-01"},
            {"sources": {"Teams": []}, "manual_sources": {"teams": []}},
            {"sources": {"Confluence": []}, "source_scopes": {"Slack": "Not selected"}},
            {"sources": {"GitHub": "not a list"}},
        ]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(ValueError):
                intake.validate(data)

    def test_legacy_input_preserved_except_ignored_headline_hints(self):
        legacy = copy.deepcopy(self.data)
        legacy["title_preferences"] = {"seed_title": "Old title", "candidate_count": 5}
        original = copy.deepcopy(legacy)
        normalized = intake.validate(legacy)
        self.assertNotIn("title_preferences", normalized)
        self.assertEqual(normalized["sources"], legacy["sources"])
        self.assertEqual(legacy, original)
        self.put_input(legacy)
        self.call("init")
        self.assertEqual(blog.load(self.root / "outputs/input.json"), legacy)
        self.assertNotIn("title_selection", self.state())

    def test_cli_conflict_and_saved_input_edits_do_not_replace_run(self):
        self.put_input()
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.call("init", "--topic", "Different topic")
        self.assertFalse((self.root / "outputs").exists())
        self.call("init")
        altered = copy.deepcopy(self.raw)
        altered["words"] = 3000
        self.put_input(altered)
        self.call("status")
        self.assertEqual(self.state()["draft_settings"]["words"], 2000)
        with self.assertRaisesRegex(ValueError, "already saved"):
            self.call("import-input")

    def test_import_preserves_current_source_and_draft_settings(self):
        self.call("init", "--topic", self.raw["topic"], "--audience", self.raw["audience"])
        self.call("select-sources", "--manual", "Local notes", "--user-confirmed")
        state = self.state()
        state["draft_settings"] = {"words": 2500, "versions": 2, "count_scope": "Body"}
        original_plan = copy.deepcopy(state["source_plan"])
        blog.save(self.root / "project.json", state)
        self.put_input()
        self.call("import-input")
        self.assertEqual(self.state()["source_plan"], original_plan)
        self.assertEqual(self.state()["draft_settings"]["words"], 2500)
        self.assertEqual(blog.load(self.root / "outputs/input.json"), self.raw)

    def test_decision_migration_preserves_bytes_and_refuses_conflict(self):
        old = self.root / "decisions.md"
        content = b"# Decisions\r\nApproval: unchanged.\n"
        old.write_bytes(content)
        self.call("migrate-decisions")
        new = self.root / "outputs/decisions.md"
        self.assertEqual(new.read_bytes(), content)
        self.assertFalse(old.exists())
        old.write_bytes(b"Another log")
        with self.assertRaisesRegex(ValueError, "Both decision logs"):
            self.call("migrate-decisions")
        self.assertEqual(new.read_bytes(), content)

    def test_title_commands_are_prepare_only_and_body_approval_is_independent(self):
        self.call("init", "--topic", "Sandbox", "--audience", "Engineers")
        for stage in ("DRAFT", "REVISE"):
            self.stage(stage)
            with self.assertRaisesRegex(ValueError, "Requires stage PREPARE"):
                self.call("select-title", "--custom", "Early title", "--user-confirmed")
        # Body approval no longer requires choosing a headline first.
        path = self.root / "outputs/revised_draft/revision-001.md"
        path.write_text("# Provisional\n\nApproved body.", encoding="utf-8")
        path.with_name("revision-001-notes.md").write_text("Body approved", encoding="utf-8")
        pass_quality(self.root, [str(path.relative_to(self.root))])
        self.call("approve", "--file", str(path.relative_to(self.root)), "--user-confirmed")
        self.assertEqual(self.state()["stage"], "PREPARE")
        self.assertNotIn("title_selection", self.state())
        with self.assertRaisesRegex(ValueError, "Suggest titles in PREPARE"):
            self.call("hero", "--skip", "--user-confirmed")

    def test_prepare_title_selection_keeps_approved_revision_pinned(self):
        path = self.prepare()
        original = path.read_bytes()
        approval = copy.deepcopy(self.state()["approval"])
        with self.assertRaisesRegex(ValueError, "Suggest/register"):
            self.call("select-title", "--custom", "My title", "--user-confirmed")
        self.options()
        self.assertNotIn("title_selection", self.state())
        self.call("select-title", "--id", "T2", "--user-confirmed")
        self.call("hero", "--skip", "--user-confirmed")
        self.assertEqual(self.state()["stage"], "PREPARE")
        self.assertEqual(self.state()["title_selection"]["title"], "The cost of isolation")
        self.assertEqual(self.state()["title_selection"]["revision_sha256"], approval["sha256"])
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(self.state()["approval"], approval)

    def test_title_change_invalidates_title_dependent_artifacts_without_revising_body(self):
        path = self.prepare()
        self.options()
        self.call("select-title", "--id", "T1", "--user-confirmed")
        self.call("hero", "--skip", "--user-confirmed")
        state = self.state()
        state.update({"export": {"files": {}}, "google_doc": {"url": "test-only"}, "completed_at": "test-only"})
        blog.save(self.root / "project.json", state)
        digest = blog.sha(path)
        self.call("select-title", "--custom", "An edited publication title", "--user-confirmed")
        for key in ("hero", "export", "google_doc", "completed_at"):
            self.assertNotIn(key, self.state())
        self.assertEqual(self.state()["approval"]["sha256"], digest)
        self.assertEqual(self.state()["stage"], "PREPARE")

    def test_changed_title_options_and_revision_require_current_choices(self):
        path = self.prepare()
        self.options()
        options_path = self.root / "outputs/blog/title-options.json"
        options = blog.load(options_path)
        options[0]["title"] = "Changed option"
        blog.save(options_path, options)
        with self.assertRaisesRegex(ValueError, "options changed"):
            self.call("select-title", "--id", "T1", "--user-confirmed")
        self.call("titles", "--file", "outputs/blog/title-options.json")
        self.call("select-title", "--id", "T1", "--user-confirmed")
        self.call("reopen", "--reason", "Body correction")
        path.write_text("# Provisional\n\nCorrected approved body.", encoding="utf-8")
        pass_quality(self.root, [str(path.relative_to(self.root))])
        self.call("approve", "--file", str(path.relative_to(self.root)), "--user-confirmed")
        self.assertNotIn("title_selection", self.state())
        self.assertNotIn("title_options", self.state())

    def test_export_accepts_selected_publication_title_without_changing_approved_body(self):
        revision = self.prepare()
        original = revision.read_bytes()
        self.options()
        self.call("select-title", "--id", "T2", "--user-confirmed")
        self.call("hero", "--skip", "--user-confirmed")
        article = "# The cost of isolation\n\nEvidence-backed body.\n"
        (self.root / "outputs/blog/article.md").write_text(article, encoding="utf-8")
        api = MagicMock()
        page = api.sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value.new_page.return_value
        page.pdf.side_effect = lambda **kwargs: Path(kwargs["path"]).write_bytes(b"%PDF-1.7\\nMOCK")
        with patch.object(blog, "render_html", return_value="<h1>The cost of isolation</h1>") as render, patch.dict(sys.modules, {"playwright.sync_api": api}):
            self.call("export")
        render.assert_called_once_with(self.root, article, "The cost of isolation")
        self.assertEqual(revision.read_bytes(), original)
        self.assertEqual(self.state()["approval"]["sha256"], blog.sha(revision))
        self.assertTrue((self.root / "outputs/blog/article.pdf").is_file())

    def test_final_heading_must_match_prepare_selection(self):
        self.prepare()
        self.options()
        self.call("select-title", "--id", "T1", "--user-confirmed")
        self.call("hero", "--skip", "--user-confirmed")
        (self.root / "outputs/blog/article.md").write_text("# Wrong title\n\nEvidence-backed body.", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "title differs"):
            self.call("export")


if __name__ == "__main__":
    unittest.main()
