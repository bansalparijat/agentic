"""Synthetic local-contract fixtures, NOT factual/editorial review of real articles."""
from pathlib import Path

import blog
import editorial


def passing_packet(root, targets, kind="architecture-case-study"):
    root = Path(root)
    state = blog.load(root / "project.json")
    if not state.get("draft_settings"):
        state["draft_settings"] = {"words": 1000, "versions": 2, "count_scope": "Body"}
        blog.save(root / "project.json", state)
    catalog_path = root / "outputs/data/catalog.json"
    catalog = blog.load(catalog_path) if catalog_path.exists() else []
    if not catalog:
        source = root / "outputs/data/normalized/editorial-fixture.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("TEST FIXTURE ONLY: synthetic explanatory evidence for local gate tests.\n", encoding="utf-8")
        catalog = [{"id": "S001", "file": str(source.relative_to(root)), "sha256": blog.sha(source)}]
        blog.save(catalog_path, catalog)
    for name in ("outputs/data/claims.md", "outputs/data/research-brief.md", "outputs/decisions.md"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("TEST FIXTURE ONLY: contract test, not production publication approval.\n", encoding="utf-8")
    source = catalog[0]["id"]
    slots = editorial.load(editorial.BLUEPRINTS)["types"][kind]["slots"]
    words = state["draft_settings"]["words"]
    requirements = [*state.get("intake", {}).get("blog", {}).get("required_coverage", []),
                    *state.get("intake", {}).get("research", {}).get("questions", [])] or ["Explain the fixture mechanism"]
    packet = {"schema_version": 1, "plan": {
        "article_type": kind, "selection_reason": "TEST FIXTURE: local gate behavior only.",
        "thesis": "A synthetic example exercises the local contract.", "reader_outcomes": ["Understand the fixture mechanism"],
        "coverage": [{"requirement": r, "status": "covered", "sources": [source], "sections": [slots[0].title()], "note": "Fixture mapping"} for r in dict.fromkeys(requirements)],
        "outlines": [{"file": name, "angle": "TEST FIXTURE angle " + str(i),
                      "sections": [{"heading": slot.title(), "purpose": slot, "words": words // len(slots) + (j < words % len(slots)), "sources": [source]}
                                   for j, slot in enumerate(slots)]} for i, name in enumerate(targets)]},
        "measurements": {"items": [], "non_result_numbers": [], "not_applicable_reason": "Fixture has no quantitative result claims."},
        "reproducibility": {"applicable": False, "reason": "Fixture contains explanatory prose without code or execution steps.", "execution": {"status": "not-run", "reason": "No executable example"}},
        "figures": {"items": [], "not_applicable_reason": "Fixture has no technical illustrations."},
        "reviews": [{"file": name, "sha256": blog.sha(root / name), **{role: {"status": "pass", "notes": "TEST FIXTURE: simulates agent attestation, not a real factual/editorial review.", "findings": []} for role in editorial.ROLES}} for name in targets]}
    blog.save(root / editorial.PACKET, packet)
    return packet


def pass_quality(root, targets):
    passing_packet(root, targets)
    report = editorial.evaluate(root, blog.load(root / "project.json"), sorted(targets))
    if report["status"] != "pass":
        raise AssertionError(report["findings"])
    blog.save(root / editorial.REPORT, report)
    return report
