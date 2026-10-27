import contextlib
import copy
import io
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import blog
import editorial
from editorial_fixtures import pass_quality, passing_packet


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.blog("init", "--topic", "Queue architecture", "--audience", "Engineers")
        state = self.state()
        state["stage"] = "DRAFT"
        state["draft_settings"] = {"words": 700, "versions": 2, "count_scope": "Body"}
        blog.save(self.root / "project.json", state)
        self.targets = [f"outputs/draft/version-{i:02d}.md" for i in (1, 2)]
        for name in self.targets:
            self.put(name, "# Provisional\n\nA queue buffers work; consumers process it independently.\n")
        self.packet = passing_packet(self.root, self.targets)

    def state(self):
        return blog.load(self.root / "project.json")

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def blog(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            blog.run(blog.parser().parse_args(["--root", str(self.root), *args]))

    def cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return editorial.run(editorial.parser().parse_args(["--root", str(self.root), *args]))

    def persist(self, refresh_reviews=False):
        if refresh_reviews:
            for review in self.packet["reviews"]:
                review["sha256"] = blog.sha(self.root / review["file"])
        blog.save(self.root / editorial.PACKET, self.packet)

    def evaluate(self):
        self.persist()
        return editorial.evaluate(self.root, self.state(), self.targets)

    def messages(self, report):
        return "\n".join(f["location"] + ": " + f["message"] for f in report["findings"])

    def measured(self, status="supported"):
        statement = "Mean latency fell from 4 ms to 2 ms."
        item = {"id": "C1", "statement": statement, "status": status, "sources": ["S001"],
                **{key: "Synthetic test condition: " + key for key in editorial.MEASUREMENT_FIELDS},
                "provenance": "experiment", "causality": "descriptive", "limitations": ["Synthetic fixture only"]}
        self.packet["measurements"]["items"] = [item]
        for name in self.targets:
            self.put(name, "# Provisional\n\n" + statement + "\n")
        self.persist(refresh_reviews=True)
        return item

    def figure(self, kind="chart"):
        asset = self.put("outputs/draft/assets/chart.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
        data = self.put("outputs/data/chart.csv", "workload,latency\nA,4\nB,2\n")
        figure = {"id": "F1", "kind": kind, "label": "Figure 1", "caption": "Figure 1: Comparison under the recorded workload.",
                  "alt": "A measured workload comparison", "sources": ["S001"], "used_in": self.targets,
                  "rendered_file": str(asset.relative_to(self.root))}
        if kind == "chart":
            figure["measurement_ids"] = ["C_chart"]
            self.packet["measurements"]["items"] = [{"id": "C_chart", "statement": figure["caption"], "status": "supported", "sources": ["S001"],
                                                       **{key: "Synthetic CSV chart condition for " + key for key in editorial.MEASUREMENT_FIELDS},
                                                       "provenance": "experiment", "causality": "descriptive"}]
            figure["data"] = {"file": str(data.relative_to(self.root)), "x": "workload", "y": "latency",
                              "units": "milliseconds", "baseline": "Workload A", "aggregation": "Recorded synthetic fixture values", "conditions": "Same fixture environment"}
        self.packet["figures"]["items"] = [figure]
        for name in self.targets:
            self.put(name, "# Provisional\n\nSee Figure 1 for the comparison.\n\n![A measured workload comparison](assets/chart.svg)\n\n" + figure["caption"] + "\n")
        self.persist(refresh_reviews=True)
        return figure

    def executable(self, status="not-run"):
        disclosure = "These commands are illustrative and have not been run here."
        self.packet["reproducibility"] = {
            "applicable": True, "reason": "A bounded tutorial example.",
            **{key: "Synthetic test explanation for " + key for key in ("prerequisites", "versions", "permissions", "cost", "verification", "cleanup", "troubleshooting")},
            "steps": [{"instruction": "touch " + str(self.root / "NEVER_EXECUTE"), "expected": "A file would be created if explicitly run"}],
            "execution": {"status": status, "reason": "Execution was not authorized", "disclosure": disclosure}}
        for name in self.targets:
            self.put(name, "# Provisional\n\n```sh\nprintf example\n```\n\n" + disclosure + "\n")
        self.persist(refresh_reviews=True)

    def test_six_blueprints_infer_and_can_be_overridden_by_agent(self):
        examples = {"A hands-on tutorial": "tutorial", "Migrating a database": "migration-journey",
                    "CPU latency optimization": "performance-investigation", "Reinforcement learning experiment": "ml-experiment",
                    "Introducing a new feature": "technical-introduction", "Queue architecture": "architecture-case-study"}
        for topic, expected in examples.items():
            self.assertEqual(editorial.infer({"topic": topic})[0], expected)
        self.assertEqual(editorial.infer({"topic": "Migration"}, "tutorial")[0], "tutorial")
        self.assertEqual(len(editorial.load(editorial.BLUEPRINTS)["types"]), 6)

    def test_scaffold_is_incomplete_not_an_automatic_review(self):
        (self.root / editorial.PACKET).unlink()
        self.cli("scaffold")
        packet = blog.load(self.root / editorial.PACKET)
        self.assertTrue(all(r["technical"]["status"] == "blocked" for r in packet["reviews"]))
        report = editorial.evaluate(self.root, self.state(), self.targets)
        self.assertEqual(report["status"], "blocked")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.cli("scaffold")

    def test_passing_report_still_discloses_limits_and_has_no_numeric_score(self):
        report = self.evaluate()
        self.assertEqual(report["status"], "pass")
        self.assertIn("not proof", report["limitations"])
        self.assertNotIn("score", report)
        self.assertTrue(all(f["origin"] == "automatic" for f in report["findings"]))

    def test_required_coverage_and_blueprint_budgets_are_enforced(self):
        state = self.state()
        state["intake"] = {"blog": {"required_coverage": ["Alternatives"]}, "research": {"questions": ["Why not a database?"]}}
        blog.save(self.root / "project.json", state)
        self.packet["plan"]["outlines"][0]["sections"].pop()
        self.packet["plan"]["outlines"][1]["sections"][0]["words"] = 5000
        report = self.evaluate()
        messages = self.messages(report)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("Alternatives", messages)
        self.assertIn("Why not a database?", messages)
        self.assertIn("slot missing", messages)
        self.assertIn("budgets", messages)

    def test_pending_coverage_and_duplicate_draft_angles_block(self):
        self.packet["plan"]["coverage"][0]["status"] = "pending"
        self.packet["plan"]["outlines"][1]["angle"] = self.packet["plan"]["outlines"][0]["angle"]
        report = self.evaluate()
        self.assertIn("Unresolved required coverage", self.messages(report))
        self.assertIn("distinct substantive angles", self.messages(report))

    def test_qualified_omission_is_visible_as_warning_not_silent_pass(self):
        row = self.packet["plan"]["coverage"][0]
        row.update({"status": "omitted", "sources": [], "sections": [], "note": "Evidence does not establish this mechanism; user must see the limitation."})
        report = self.evaluate()
        self.assertEqual(report["status"], "pass")
        self.assertIn("Disclose this to the user", self.messages(report))

    def test_source_ids_and_original_source_checksums_are_checked(self):
        self.packet["plan"]["coverage"][0]["sources"] = ["DOES_NOT_EXIST"]
        report = self.evaluate()
        self.assertIn("Unknown source ID", self.messages(report))
        source = blog.load(self.root / "outputs/data/catalog.json")[0]["file"]
        self.put(source, "Unregistered altered source")
        self.assertIn("Registered evidence changed", self.messages(self.evaluate()))

    def test_supported_measurement_requires_protocol_and_source_classification(self):
        item = self.measured()
        self.assertEqual(self.evaluate()["status"], "pass")
        item["baseline"] = "unknown"
        item["window"] = ""
        self.assertEqual(self.evaluate()["status"], "blocked")
        item["baseline"], item["window"] = "Prior implementation", "A recorded test window"
        item["provenance"] = "simulation"
        self.assertIn("must be qualified", self.messages(self.evaluate()))

    def test_qualified_measurements_need_visible_qualification(self):
        item = self.measured("qualified")
        item["qualification"] = "This is a simulation, not a production measurement."
        item["provenance"] = "simulation"
        self.assertIn("exact qualification", self.messages(self.evaluate()))
        for name in self.targets:
            self.put(name, (self.root / name).read_text() + "\n" + item["qualification"])
        self.persist(refresh_reviews=True)
        self.assertEqual(self.evaluate()["status"], "pass")

    def test_measurement_candidates_cannot_hide_behind_unrelated_record(self):
        self.measured()
        self.put(self.targets[0], (self.root / self.targets[0]).read_text() + "\nCPU fell by 25%.\n")
        self.persist(refresh_reviews=True)
        self.assertIn("unclassified: 25%", self.messages(self.evaluate()))

    def test_configuration_numbers_need_a_reason_instead_of_fake_benchmarks(self):
        for name in self.targets:
            self.put(name, "# Provisional\n\nThe configured timeout is 30 seconds.\n")
        self.persist(refresh_reviews=True)
        self.assertIn("unclassified", self.messages(self.evaluate()))
        self.packet["measurements"]["non_result_numbers"] = [{"text": "30 seconds", "reason": "A configured timeout, not a measured outcome."}]
        self.assertEqual(self.evaluate()["status"], "pass")

    def test_ml_experiment_needs_dataset_split_leakage_and_model_context(self):
        self.packet = passing_packet(self.root, self.targets, "ml-experiment")
        item = self.measured()
        self.assertIn("ml_dataset", self.messages(self.evaluate()))
        item["ml_context"] = {key: "Synthetic fixture context for " + key for key in editorial.ML_FIELDS}
        self.assertEqual(self.evaluate()["status"], "pass")

    def test_code_requires_reproducibility_and_not_run_is_honest(self):
        for name in self.targets:
            self.put(name, "# Provisional\n\n```python\nprint('example')\n```\n")
        self.persist(refresh_reviews=True)
        self.assertIn("reproducibility record", self.messages(self.evaluate()))
        self.executable()
        report = self.evaluate()
        self.assertEqual(report["status"], "pass")
        self.assertIn("Examples were not run", self.messages(report))
        self.assertFalse((self.root / "NEVER_EXECUTE").exists())
        self.packet["reproducibility"]["execution"]["disclosure"] = "An undisclosed status"
        self.assertEqual(self.evaluate()["status"], "blocked")

    def test_verified_execution_needs_real_local_record_but_helper_never_executes(self):
        self.executable("verified")
        execution = self.packet["reproducibility"]["execution"]
        execution.update({"permission_record": "TEST FIXTURE only; exercises permission-attestation field", "environment": "Isolated fixture"})
        with self.assertRaises(ValueError):
            self.evaluate()
        path = self.put("outputs/data/verification.txt", "TEST FIXTURE: synthetic transcript presence, not proof of real execution.")
        execution["evidence_file"] = str(path.relative_to(self.root))
        self.assertEqual(self.evaluate()["status"], "pass")
        self.assertFalse((self.root / "NEVER_EXECUTE").exists())

    def test_tutorial_cannot_claim_reproducibility_is_irrelevant(self):
        self.packet = passing_packet(self.root, self.targets, "tutorial")
        self.assertIn("Tutorials/code examples", self.messages(self.evaluate()))

    def test_mermaid_is_not_mistaken_for_executable_code(self):
        self.assertFalse(editorial.has_code("```mermaid\ngraph TD; A-->B\n```\n"))
        self.assertTrue(editorial.has_code("```mermaid\ngraph TD; A-->B\n```\n```python\nprint(1)\n```"))
        self.assertFalse(editorial.has_code("Plain text without a fenced example."))

    def test_chart_provenance_csv_columns_and_numeric_values(self):
        figure = self.figure()
        self.assertEqual(self.evaluate()["status"], "pass")
        figure["data"]["y"] = "missing"
        self.assertIn("columns do not exist", self.messages(self.evaluate()))
        figure["data"]["y"] = "latency"
        self.put("outputs/data/chart.csv", "workload,latency\nA,NaN\n")
        self.assertIn("finite numeric", self.messages(self.evaluate()))

    def test_chart_cannot_be_unproven_decoration(self):
        figure = self.figure()
        figure.pop("data")
        self.assertIn("Charts need data provenance", self.messages(self.evaluate()))

    def test_figures_need_captions_cross_references_and_alt_text(self):
        self.figure()
        self.put(self.targets[0], "# Provisional\n\n![](assets/chart.svg)\n")
        self.persist(refresh_reviews=True)
        messages = self.messages(self.evaluate())
        self.assertIn("caption and a prose cross-reference", messages)
        self.assertIn("meaningful alt text", messages)

    def test_unregistered_remote_and_traversing_assets_fail_without_network(self):
        self.put(self.targets[0], "# Provisional\n\n![Remote](https://example.invalid/a.png)\n")
        self.persist(refresh_reviews=True)
        self.assertIn("not remote/data URLs", self.messages(self.evaluate()))
        self.packet["figures"]["items"] = [{"id": "F1", "kind": "screenshot", "label": "Figure 1", "caption": "Figure 1: Snapshot", "alt": "A snapshot", "sources": ["S001"], "used_in": self.targets,
                                             "rendered_file": "../private.svg", "permission_basis": "Unverified"}]
        with self.assertRaisesRegex(ValueError, "inside outputs"):
            self.evaluate()

    def test_equations_and_screenshots_have_type_specific_requirements(self):
        figure = self.figure("equation")
        messages = self.messages(self.evaluate())
        self.assertIn("expression", messages)
        self.assertIn("Define equation variables", messages)
        figure.update({"expression": "cost = requests * unit_price", "variables": {"requests": "Number of requests", "unit_price": "Price per request", "cost": "Total price"}})
        self.assertEqual(self.evaluate()["status"], "pass")
        figure["kind"] = "screenshot"
        figure.pop("expression")
        figure.pop("variables")
        self.assertIn("permission_basis", self.messages(self.evaluate()))

    def test_chart_must_link_its_measurement_proof(self):
        figure = self.figure()
        figure["measurement_ids"] = ["C_missing"]
        self.assertIn("Charts must link", self.messages(self.evaluate()))

    def test_editable_mermaid_registry_is_allowed_before_final_rendering(self):
        source = self.put("outputs/draft/assets/flow.mmd", "graph TD; A-->B\n")
        caption = "Figure 1: Conceptual flow, not an observed deployment."
        self.packet["figures"]["items"] = [{"id": "F1", "kind": "flow", "label": "Figure 1", "caption": caption,
                                              "alt": "Conceptual A to B flow", "sources": [], "conceptual": True,
                                              "source_file": str(source.relative_to(self.root)), "used_in": self.targets}]
        for name in self.targets:
            self.put(name, "# Provisional\n\nSee Figure 1.\n\n```mermaid\ngraph TD; A-->B\n```\n\n" + caption)
        self.persist(refresh_reviews=True)
        self.assertEqual(self.evaluate()["status"], "pass")

    def test_resolved_asset_symlinks_cannot_escape_outputs(self):
        self.figure()
        outside = self.put("private.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
        link = self.root / "outputs/draft/assets/outside.svg"
        link.symlink_to(outside)
        self.packet["figures"]["items"][0]["rendered_file"] = str(link.relative_to(self.root))
        with self.assertRaisesRegex(ValueError, "inside outputs"):
            self.evaluate()

    def test_omitted_measurement_cannot_remain_in_article(self):
        self.measured("omitted")
        self.assertIn("omitted measurement statement still appears", self.messages(self.evaluate()))

    def test_stale_reviews_and_reported_blockers_cannot_be_hidden_by_pass(self):
        self.packet["reviews"][0]["sha256"] = "stale"
        self.assertIn("Missing/stale sequential reviews", self.messages(self.evaluate()))
        self.persist(refresh_reviews=True)
        self.packet["reviews"][0]["technical"]["findings"] = [{"severity": "blocker", "message": "Mechanism contradicts the source."}]
        report = self.evaluate()
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(any(f["origin"] == "agent-review" for f in report["findings"]))

    def test_schema_and_placeholders_block(self):
        self.packet["unexpected"] = True
        self.assertIn("unknown fields", self.messages(self.evaluate()))
        self.packet.pop("unexpected")
        self.put(self.targets[0], "# Provisional\n\nTBD: required mechanism.\n")
        self.persist(refresh_reviews=True)
        self.assertIn("placeholder", self.messages(self.evaluate()))

    def test_cli_writes_reports_and_archives_and_returns_failure_for_blockers(self):
        self.persist()
        self.assertEqual(self.cli("check"), 0)
        self.assertTrue((self.root / "outputs/draft/quality-report.md").is_file())
        self.assertTrue(list((self.root / "outputs/draft/quality-reports").glob("*.json")))
        self.packet["plan"]["thesis"] = ""
        self.persist()
        self.assertEqual(self.cli("check"), 1)
        self.assertEqual(blog.load(self.root / editorial.REPORT)["status"], "blocked")

    def test_new_workflow_gate_requires_all_drafts_and_fresh_report(self):
        for name in ("comparison.md", "evidence-map.md", "diagram-notes.md"):
            self.put("outputs/draft/" + name, "Fixture supporting document")
        with self.assertRaisesRegex(ValueError, "Missing/empty"):
            self.blog("advance", "--to", "REVISE", "--user-confirmed")
        self.persist()
        self.cli("check", "--file", self.targets[0])
        with self.assertRaisesRegex(ValueError, "stale editorial quality"):
            self.blog("advance", "--to", "REVISE", "--user-confirmed")
        self.cli("check")
        self.put("outputs/decisions.md", "A new scope decision changes the review fingerprint")
        with self.assertRaisesRegex(ValueError, "stale editorial quality"):
            self.blog("advance", "--to", "REVISE", "--user-confirmed")
        self.cli("check")
        self.blog("advance", "--to", "REVISE", "--user-confirmed")
        self.assertEqual(self.state()["stage"], "REVISE")

    def test_revision_approval_pins_quality_fingerprint(self):
        state = self.state()
        state["stage"] = "REVISE"
        blog.save(self.root / "project.json", state)
        revision = "outputs/revised_draft/revision-001.md"
        self.put(revision, "# Provisional\n\nAn explanatory fixture.")
        self.put("outputs/revised_draft/revision-001-notes.md", "Feedback addressed")
        with self.assertRaisesRegex(ValueError, "Missing/empty"):
            self.blog("approve", "--file", revision, "--user-confirmed")
        report = pass_quality(self.root, [revision])
        self.blog("approve", "--file", revision, "--user-confirmed")
        self.assertEqual(self.state()["approval"]["quality_fingerprint"], report["fingerprint"])
        self.assertEqual(self.state()["stage"], "PREPARE")
        self.assertNotIn("title_selection", self.state())

    def test_legacy_runs_are_not_retroactively_invalidated_and_can_adopt(self):
        state = self.state()
        state.pop("editorial_contract_version")
        blog.save(self.root / "project.json", state)
        editorial.require_quality(self.root, state, self.targets)
        self.cli("adopt", "--user-confirmed")
        self.assertEqual(self.state()["editorial_contract_version"], 1)
        with self.assertRaises(ValueError):
            editorial.require_quality(self.root, self.state(), self.targets)

    def test_stopped_or_prepare_runs_cannot_run_editorial_mutations(self):
        state = self.state()
        state["workflow_stopped"] = True
        blog.save(self.root / "project.json", state)
        with self.assertRaisesRegex(ValueError, "Workflow stopped"):
            self.cli("check")
        state.pop("workflow_stopped")
        state["stage"] = "PREPARE"
        blog.save(self.root / "project.json", state)
        with self.assertRaisesRegex(ValueError, "require DRAFT or REVISE"):
            self.cli("adopt", "--user-confirmed")


if __name__ == "__main__":
    unittest.main()
