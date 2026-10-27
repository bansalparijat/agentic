import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import blog
from editorial_fixtures import pass_quality

HAS_MARKDOWN = importlib.util.find_spec("markdown_it") is not None


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.call("init", "--topic", "Event ingestion", "--audience", "Engineers")

    def call(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            blog.run(blog.parser().parse_args(["--root", str(self.root), *args]))
        return output.getvalue()

    def put(self, name, text="Evidence-backed content"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def state(self):
        return blog.load(self.root / "project.json")

    def source(self):
        self.put("outputs/data/normalized/source.md", "A queue buffers events.\n")
        return self.call("source", "--file", "outputs/data/normalized/source.md", "--kind", "local",
                         "--title", "Design", "--locator", "user-upload#queue", "--confidentiality", "internal")

    def draft_stage(self):
        self.source()
        for name in ("research-brief.md", "claims.md", "search-log.md"):
            self.put("outputs/data/" + name)
        self.call("advance", "--to", "DRAFT", "--user-confirmed")

    def revise_stage(self):
        self.draft_stage()
        self.call("draft-settings", "--words", "1000", "--versions", "2", "--count-scope", "body")
        for name in ("version-01.md", "version-02.md", "comparison.md", "evidence-map.md", "diagram-notes.md"):
            self.put("outputs/draft/" + name, "# Working heading\n\nEvidence-backed content.")
        pass_quality(self.root, [f"outputs/draft/version-{i:02d}.md" for i in (1, 2)])
        self.call("advance", "--to", "REVISE", "--user-confirmed")

    def prepare_stage(self):
        self.revise_stage()
        self.put("outputs/revised_draft/revision-001.md", "# Event ingestion\n\nA queue buffers events.\n")
        self.put("outputs/revised_draft/revision-001-notes.md", "User satisfied after checking claims.")
        pass_quality(self.root, ["outputs/revised_draft/revision-001.md"])
        self.call("approve", "--file", "outputs/revised_draft/revision-001.md", "--user-confirmed")
        self.put("outputs/blog/title-options.json", json.dumps([
            {"id": "T1", "title": "Event ingestion", "angle": "Architecture"},
            {"id": "T2", "title": "Buffering events", "angle": "Mechanisms"},
            {"id": "T3", "title": "Reliable ingestion", "angle": "Operations"}]))
        self.call("titles", "--file", "outputs/blog/title-options.json")
        self.call("select-title", "--id", "T1", "--user-confirmed")
        self.call("hero", "--skip", "--user-confirmed")
        self.put("outputs/blog/article.md", "# Event ingestion\n\nA queue buffers events.\n")

    def fake_verified_outputs(self):
        # Test local integrity gates, not PDF rendering or remote document existence.
        self.put("outputs/blog/article.html", "<!doctype html><h1>Event ingestion</h1>")
        self.put("outputs/blog/article.pdf", "%PDF-1.7\nTEST FIXTURE ONLY")
        state = self.state()
        state["export"] = {"at": blog.now(), "files": {
            f"outputs/blog/article.{ext}": blog.sha(self.root / f"outputs/blog/article.{ext}") for ext in ("md", "html", "pdf")}}
        blog.save(self.root / "project.json", state)
        self.call("google-doc", "--url", "https://docs.google.com/document/d/test_fixture_only/edit",
                  "--verified", "--user-confirmed")
        self.put("outputs/blog/verification.md", "TEST FIXTURE: local gates only, no real remote document.")

    def test_initialized_and_resume(self):
        self.assertEqual(self.state()["stage"], "COLLECTION")
        self.assertIn("COLLECTION", self.call("status"))
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.call("init", "--topic", "Overwrite", "--audience", "Nobody")

    def test_stage_directories_are_under_outputs(self):
        for stage in ("data", "draft", "revised_draft", "blog"):
            self.assertTrue((self.root / "outputs" / stage / "assets").is_dir())
            self.assertFalse((self.root / stage).exists())
        self.assertTrue((self.root / "outputs/data/raw").is_dir())
        self.assertTrue((self.root / "outputs/data/normalized").is_dir())
        self.assertTrue((self.root / "project.json").is_file())
        self.assertTrue((self.root / "outputs/decisions.md").is_file())
        self.assertFalse((self.root / "decisions.md").exists())

    def test_status_reads_drafts_under_outputs(self):
        self.put("outputs/draft/version-01.md", "Two words")
        self.put("outputs/revised_draft/revision-001.md", "Three simple words")
        status = self.call("status")
        self.assertIn("outputs/draft/version-01.md: ~2 words", status)
        self.assertIn("outputs/revised_draft/revision-001.md: ~3 words", status)

    def test_legacy_source_path_is_rejected(self):
        self.put("data/normalized/legacy.md", "Old location")
        with self.assertRaisesRegex(ValueError, "inside"):
            self.call("source", "--file", "data/normalized/legacy.md", "--kind", "local",
                      "--title", "Legacy", "--locator", "local", "--confidentiality", "internal")

    def test_cannot_skip_stages(self):
        with self.assertRaisesRegex(ValueError, "Only"):
            self.call("advance", "--to", "REVISE", "--user-confirmed")
        with self.assertRaisesRegex(ValueError, "Requires stage"):
            self.call("approve", "--file", "outputs/draft/version-01.md", "--user-confirmed")

    def test_collection_requires_evidence(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            self.call("advance", "--to", "DRAFT", "--user-confirmed")

    def test_source_hash_and_ids(self):
        self.assertEqual(self.source().strip(), "S001")
        catalog = blog.load(self.root / "outputs/data/catalog.json")
        self.assertEqual(catalog[0]["file"], "outputs/data/normalized/source.md")
        self.assertEqual(catalog[0]["sha256"], blog.sha(self.root / "outputs/data/normalized/source.md"))
        self.assertIn("retrieved_at", catalog[0])

    def test_changed_evidence_blocks_collection_completion(self):
        self.source()
        self.put("outputs/data/normalized/source.md", "Silently changed evidence")
        with self.assertRaisesRegex(ValueError, "Evidence changed"):
            self.call("advance", "--to", "DRAFT", "--user-confirmed")

    def test_path_traversal_and_symlink(self):
        with self.assertRaisesRegex(ValueError, "inside"):
            blog.inside(self.root, "../outside.md", "outputs/data")
        (self.root / "outputs/data/normalized/escape").symlink_to(self.root.parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "inside"):
            blog.inside(self.root, "outputs/data/normalized/escape/private.md", "outputs/data/normalized")

    def test_settings_and_required_drafts(self):
        self.draft_stage()
        with self.assertRaisesRegex(ValueError, "length"):
            self.call("advance", "--to", "REVISE", "--user-confirmed")
        with self.assertRaisesRegex(ValueError, "positive"):
            self.call("draft-settings", "--words", "0", "--versions", "2", "--count-scope", "body")
        self.call("draft-settings", "--words", "1000", "--versions", "3", "--count-scope", "body")
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.call("advance", "--to", "REVISE", "--user-confirmed")

    def test_approved_revision_is_pinned(self):
        self.prepare_stage()
        self.put("outputs/revised_draft/revision-001.md", "An unapproved change")
        with self.assertRaisesRegex(ValueError, "revision changed"):
            self.call("hero", "--skip", "--user-confirmed")

    def test_reopen_invalidates_approval(self):
        self.prepare_stage()
        self.call("reopen", "--reason", "Technical correction")
        self.assertEqual(self.state()["stage"], "REVISE")
        self.assertNotIn("approval", self.state())

    def test_missing_google_doc_blocks_completion(self):
        self.prepare_stage()
        self.fake_verified_outputs()
        state = self.state()
        state.pop("google_doc")
        blog.save(self.root / "project.json", state)
        with self.assertRaisesRegex(ValueError, "Google Doc"):
            self.call("complete", "--user-confirmed")

    def test_complete_and_invalidate(self):
        self.prepare_stage()
        self.fake_verified_outputs()
        self.call("complete", "--user-confirmed")
        self.assertIn("completed_at", self.state())
        self.assertEqual(blog.sha(self.root / "outputs/blog/delivery.json"), self.state()["delivery_sha256"])
        self.call("hero", "--skip", "--user-confirmed")
        self.assertNotIn("completed_at", self.state())

    def test_stale_export_and_doc(self):
        self.prepare_stage()
        self.fake_verified_outputs()
        self.put("outputs/blog/article.md", "New unverified packaging")
        with self.assertRaisesRegex(ValueError, "Export changed"):
            self.call("complete", "--user-confirmed")
        state = self.state()
        state["export"]["files"]["outputs/blog/article.md"] = blog.sha(self.root / "outputs/blog/article.md")
        blog.save(self.root / "project.json", state)
        with self.assertRaisesRegex(ValueError, "predates"):
            self.call("complete", "--user-confirmed")

    def test_invalid_doc_url(self):
        self.prepare_stage()
        with self.assertRaisesRegex(ValueError, "real Google"):
            self.call("google-doc", "--url", "https://example.com/document", "--verified", "--user-confirmed")

    def test_asset_url_validation(self):
        for src in ("https://example.com/a.png", "data:image/png;base64,AA", "../private.png", "/tmp/private.png"):
            with self.assertRaises(ValueError):
                blog.image_asset(self.root, src)
        self.put("outputs/blog/assets/test.png", "fixture")
        self.assertEqual(blog.image_asset(self.root, "assets/test.png"), self.root / "outputs/blog/assets/test.png")

    def test_pdf_failure_removes_stale_output(self):
        self.prepare_stage()
        self.put("outputs/blog/article.pdf", "STALE")
        with patch.object(blog, "render_html", return_value="<h1>Fixture</h1>"), patch.dict(sys.modules, {"playwright.sync_api": None}):
            with self.assertRaisesRegex(ValueError, "PDF blocked"):
                self.call("export")
        self.assertFalse((self.root / "outputs/blog/article.pdf").exists())
        self.assertTrue((self.root / "outputs/blog/article.html").exists())
        self.assertNotIn("export", self.state())

    def test_export_writes_and_records_outputs_paths(self):
        self.prepare_stage()
        api = MagicMock()
        page = api.sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value.new_page.return_value
        page.pdf.side_effect = lambda **kwargs: Path(kwargs["path"]).write_bytes(b"%PDF-1.7\nMOCK")
        with patch.object(blog, "render_html", return_value="<h1>Fixture</h1>"), patch.dict(sys.modules, {"playwright.sync_api": api}):
            self.call("export")
        expected = {f"outputs/blog/article.{ext}" for ext in ("md", "html", "pdf")}
        self.assertEqual(set(self.state()["export"]["files"]), expected)
        manifest = blog.load(self.root / "outputs/blog/delivery.json")
        self.assertEqual(set(manifest["files"]), expected | {"outputs/blog/title-options.json"})
        self.assertTrue(all((self.root / name).is_file() for name in expected))
        self.assertFalse((self.root / "blog").exists())

    @unittest.skipUnless(HAS_MARKDOWN, "optional markdown-it-py not installed")
    def test_html_embeds_assets_escapes_html_and_has_tables(self):
        self.prepare_stage()
        self.put("outputs/blog/assets/chart.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
        result = blog.render_html(self.root, '# Title\n<script>alert(1)</script>\n\n![Chart](assets/chart.svg)\n\n| A | B |\n|---|---|\n| 1 | 2 |', "Test & title")
        self.assertIn("data:image/svg+xml;base64,", result)
        self.assertNotIn("<script>", result)
        self.assertIn("<table>", result)
        self.assertIn("Test &amp; title", result)

    @unittest.skipUnless(HAS_MARKDOWN, "optional markdown-it-py not installed")
    def test_mermaid_and_remote_images_rejected(self):
        self.prepare_stage()
        for text in ("```mermaid\ngraph TD; A-->B\n```", "~~~mermaid\ngraph TD; A-->B\n~~~", "![Remote](https://example.com/x.png)"):
            with self.assertRaises(ValueError):
                blog.render_html(self.root, text, "Title")

    @unittest.skipUnless(HAS_MARKDOWN, "optional markdown-it-py not installed")
    def test_selected_hero_must_be_included_and_unchanged(self):
        self.prepare_stage()
        self.put("outputs/blog/assets/hero.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.call("hero", "--file", "outputs/blog/assets/hero.svg", "--alt", "An original abstract queue", "--user-confirmed")
        with self.assertRaisesRegex(ValueError, "Include"):
            blog.render_html(self.root, "# No hero", "Title")
        self.put("outputs/blog/assets/hero.svg", '<svg xmlns="http://www.w3.org/2000/svg"><title>Changed</title></svg>')
        with self.assertRaisesRegex(ValueError, "hero changed"):
            blog.render_html(self.root, "![Hero](assets/hero.svg)", "Title")


if __name__ == "__main__":
    unittest.main()
