#!/usr/bin/env python3
"""Local state/evidence/export support; the host agent performs research and writing."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import html
import json
import mimetypes
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse

from intake import draft_settings as input_draft_settings, missing_fields, read_input, validate as normalize_input

ROOT = Path(__file__).resolve().parents[1]
STAGES = ("COLLECTION", "DRAFT", "REVISE", "PREPARE")


def now():
    return datetime.now(timezone.utc).isoformat()


def fail(message):
    raise ValueError(message)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root, name, folder=None):
    path = (root / name).resolve()
    boundary = (root / folder).resolve() if folder else root.resolve()
    if not path.is_relative_to(boundary):
        fail(f"Path must stay inside {boundary}")
    return path


def required(path):
    if not path.is_file() or not path.stat().st_size:
        fail(f"Missing or empty file: {path}")
    return path


def record(state, action):
    state.setdefault("history", []).append({"at": now(), "action": action})


def require_stage(state, *allowed):
    if state["stage"] not in allowed:
        fail(f"Requires stage {' or '.join(allowed)}; current: {state['stage']}")


def invalidate(state):
    state.pop("completed_at", None)
    state.pop("delivery_sha256", None)


def approved(root, state):
    approval = state.get("approval") or fail("No approved revision")
    path = required(inside(root, approval["file"], "outputs/revised_draft"))
    if sha(path) != approval["sha256"]:
        fail("Approved revision changed. Reopen REVISE and obtain fresh approval.")


def title_ready(state):
    selection = state.get("title_selection")
    if state.get("require_title_selection") and not selection:
        fail("Suggest titles in PREPARE and obtain user selection before publishing or choosing a hero.")
    if selection and selection.get("revision_sha256", state["approval"]["sha256"]) != state["approval"]["sha256"]:
        fail("Title selection predates the approved revision; suggest/reconfirm titles in PREPARE.")


def word_count(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text))


def image_asset(root, src):
    parsed = urlparse(src)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        fail(f"Images must be local assets, not URLs: {src}")
    path = required(inside(root, Path("outputs/blog") / unquote(parsed.path), "outputs/blog/assets"))
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"}:
        fail(f"Unsupported image format: {path}")
    return path


def render_html(root, text, title):
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        fail("Install export dependencies: python3 -m pip install -r requirements-export.txt")
    if re.search(r"^\s*(`{3,}|~{3,})\s*mermaid\b", text, re.M | re.I):
        fail("Render Mermaid to local SVG/PNG before export.")
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = md.parse(text)
    used_assets = set()
    for token in tokens:
        for child in token.children or []:
            if child.type == "image":
                path = image_asset(root, child.attrGet("src") or "")
                used_assets.add(str(path.relative_to(root)))
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                child.attrSet("src", f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode())
    hero = load(root / "project.json").get("hero", {})
    if hero.get("decision") == "selected":
        path = required(inside(root, hero["file"], "outputs/blog/assets"))
        if sha(path) != hero["sha256"]:
            fail("Selected hero changed; ask user to select again.")
        if hero["file"] not in used_assets:
            fail("Include the user-selected hero in outputs/blog/article.md before exporting.")
    body = md.renderer.render(tokens, md.options, {})
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src 'none'">
<title>{html.escape(title)}</title><style>
@page {{ size: A4; margin: 20mm; }}
body {{ font: 17px/1.65 system-ui, sans-serif; max-width: 850px; margin: 2rem auto; padding: 0 1rem; color: #182230; }}
h1,h2,h3 {{ line-height: 1.25; break-after: avoid; }}
img {{ max-width: 100%; height: auto; }}
pre {{ background: #f3f5f7; padding: 1rem; white-space: pre-wrap; overflow-wrap: anywhere; }}
code {{ font-size: .88em; }}
table {{ border-collapse: collapse; width: 100%; font-size: .9em; }}
th,td {{ border: 1px solid #ccd2da; padding: .4em; overflow-wrap: break-word; word-break: normal; }}
main > table:first-of-type {{ table-layout: fixed; }}
main > table:first-of-type th:first-child,
main > table:first-of-type td:first-child {{ width: 24%; }}
main > table:first-of-type th:nth-child(2),
main > table:first-of-type td:nth-child(2),
main > table:first-of-type th:nth-child(3),
main > table:first-of-type td:nth-child(3) {{ width: 38%; }}
a {{ color: #1759a7; overflow-wrap: anywhere; }}
blockquote {{ border-left: 3px solid #ccd2da; padding-left: 1rem; }}
@media print {{
  body {{ margin: 0; max-width: none; padding: 0; }}
  pre,figure,img,tr {{ break-inside: avoid; page-break-inside: avoid; }}
  thead {{ display: table-header-group; break-inside: avoid; break-after: avoid; }}
}}
</style></head><body><main>{body}</main></body></html>'''


def delivery(root, state):
    files = {}
    for path in sorted((root / "outputs/blog").rglob("*")):
        if path.is_file() and path.name != "delivery.json":
            files[str(path.relative_to(root))] = sha(path)
    return {"generated_at": now(), "approved_revision": state.get("approval"),
            "hero": state.get("hero"), "google_doc": state.get("google_doc"),
            "source_plan": state.get("source_plan"), "title_selection": state.get("title_selection"),
            "mcp_decisions": state.get("mcp_decisions", []), "files": files}


def startup(root, input_file=None):
    """Read-only routing: saved runs win over newly supplied input files."""
    guide = ROOT / "input/README.md"
    policy = ROOT / "harness/policies/input.md"
    required(guide)
    required(policy)
    result = {"input_guide": str(guide), "input_policy": str(policy),
              "workflow": str(ROOT / "harness/workflows/technical-blog.md"),
              "titles_stage": "PREPARE", "read_only": True}
    state_path = root / "project.json"
    if state_path.is_file():
        state = load(state_path)
        result.update({"action": "await_explicit_resume" if state.get("workflow_stopped") else "resume_saved_run",
                       "stage": state.get("stage"), "state_file": str(state_path),
                       "decision_log": str(root / "outputs/decisions.md"),
                       "input_snapshot": str(root / "outputs/input.json"),
                       "supplied_input_ignored": input_file is not None,
                       "next_step": "Read saved state and latest decisions; do not initialize or reapply input."})
        return result
    path = (root / (input_file or "input/blog.json")).resolve()
    if input_file is not None or path.is_file():
        data = read_input(path)
        result.update({"action": "new_intake", "input_file": str(path), "input_validated": True,
                       "preferences": load(path), "missing_fields": missing_fields(data),
                       "next_step": "Prefill this brief; ask only for missing/conflicting information and required approvals."})
    else:
        result.update({"action": "ask_for_input_or_missing_preferences", "input_file": str(path),
                       "input_validated": False, "missing_fields": missing_fields(normalize_input({})),
                       "next_step": "Ask for a brief or missing preferences; never substitute a sample."})
    return result


def run(args):
    root = Path(args.root).resolve()
    state_path = root / "project.json"
    cmd = args.command
    if cmd == "startup":
        print(json.dumps(startup(root, args.input), indent=2, ensure_ascii=False))
        return
    if cmd == "inspect-input":
        path = (root / args.file).resolve()
        data = read_input(path)
        print(json.dumps({"file": str(path), "preferences": load(path), "missing_fields": missing_fields(data),
                          "proposed_defaults": {"drafts": data.get("draft", {}).get("versions"),
                                                "series": data.get("blog", {}).get("series", {"kind": "single"}),
                                                "follow": data.get("navigation", {}).get("mode")},
                          "notice": "Preferences/default proposals only; confirm scope before collection. Titles are suggested in PREPARE."}, indent=2))
        return
    if cmd == "migrate-decisions":
        old, new = root / "decisions.md", root / "outputs/decisions.md"
        if not old.exists():
            print("No legacy decisions.md to migrate; use outputs/decisions.md.")
            return
        if new.exists():
            fail("Both decision logs exist; reconcile them explicitly without overwriting either.")
        new.parent.mkdir(parents=True, exist_ok=True)
        old.rename(new)
        print("Moved decisions.md to outputs/decisions.md without changing its contents.")
        return
    root.mkdir(parents=True, exist_ok=True)
    if cmd == "init":
        if state_path.exists():
            fail("Project already exists; resume it or use a separate workspace.")
        input_path = (root / args.input).resolve() if args.input else root / "input/blog.json"
        preferences = read_input(input_path) if args.input or input_path.is_file() else None
        provided = preferences.get("blog", {}) if preferences else {}
        audience = "; ".join(provided.get("audience", []))
        if (args.topic and provided.get("topic") and args.topic != provided["topic"]) or (args.audience and audience and args.audience != audience):
            fail("CLI topic/audience conflicts with input; reconcile before initialization.")
        topic, audience = args.topic or provided.get("topic"), args.audience or audience
        if not topic or not audience:
            fail("Provide topic and audience via --input or --topic/--audience; ask only for missing fields.")
        for folder in ("outputs/data/raw", "outputs/data/normalized", "outputs/data/assets", "outputs/draft/assets", "outputs/revised_draft/assets", "outputs/blog/assets"):
            (root / folder).mkdir(parents=True, exist_ok=True)
        state = {"schema_version": 1, "topic": topic, "audience": audience,
                 "stage": "COLLECTION", "created_at": now(), "history": [], "require_title_selection": True, "editorial_contract_version": 1}
        if preferences:
            state["intake"] = preferences
            state["input_origin"] = {"file": str(input_path), "sha256": sha(input_path), "at": now()}
            save(root / "outputs/input.json", load(input_path))
            settings = input_draft_settings(preferences)
            if settings:
                state["draft_settings"] = settings
        record(state, "Initialized project; input preferences are not workflow approvals")
        save(state_path, state)
        save(root / "outputs/data/catalog.json", [])
        decisions = root / "outputs/decisions.md"
        if not decisions.exists():
            decisions.write_text("# Decisions and approvals\n\nRecord dated user answers, source scope, confidentiality, approvals and blockers here.\n", encoding="utf-8")
        print("Initialized COLLECTION. Read input preferences; confirm source/navigation/storage scope together before searching.")
        return
    if not state_path.exists():
        if cmd == "status":
            print("No project. Run startup with the user's input path to validate/prefill intake; ask only for missing information and required approvals.")
            return
        fail("Initialize a project first.")
    state = load(state_path)
    if cmd == "status":
        print(json.dumps(state, indent=2, ensure_ascii=False))
        if (root / "decisions.md").exists():
            print("Legacy decisions.md detected; run migrate-decisions before continuing. Use outputs/decisions.md.")
        for folder in ("outputs/draft", "outputs/revised_draft"):
            for path in sorted((root / folder).glob("*.md")):
                print(f"{path.relative_to(root)}: ~{word_count(path.read_text(encoding='utf-8'))} words (fenced code excluded)")
        return
    if cmd == "resume":
        state.pop("workflow_stopped", None)
        record(state, "User explicitly requested resume; unresolved MCP access must be rechecked")
        save(state_path, state)
        print("Resumed. Check MCP access before continuing; prior accepted skips remain in effect.")
        return
    if state.get("workflow_stopped"):
        fail("Workflow stopped by user after an MCP failure. Resume only on explicit user request.")
    if cmd == "import-input":
        require_stage(state, "COLLECTION")
        if state.get("intake") or (root / "outputs/input.json").exists():
            fail("Input already saved. Do not overwrite run preferences; discuss later changes and record them in outputs/decisions.md.")
        path = (root / args.file).resolve()
        data = read_input(path)
        blog = data.get("blog", {})
        if (blog.get("topic") and blog["topic"] != state["topic"]) or (blog.get("audience") and "; ".join(blog["audience"]) != state["audience"]):
            fail("Input conflicts with the existing topic/audience; resolve explicitly without replacing the project.")
        state["intake"] = data
        state["input_origin"] = {"file": str(path), "sha256": sha(path), "at": now()}
        settings = input_draft_settings(data)
        if settings and not state.get("draft_settings"):
            state["draft_settings"] = settings
        save(root / "outputs/input.json", load(path))
        record(state, "Imported preferences; existing source/collection state and approvals were not changed")
        save(state_path, state)
        return
    if cmd == "apply-input":
        require_stage(state, "COLLECTION")
        data = state.get("intake") or fail("Initialize/import an input file first.")
        if not data.get("sources"):
            fail("Input lacks selected sources; ask the user and use select-sources.")
        if state.get("source_plan"):
            fail("Source selection already exists; do not overwrite it from input on resume.")
        state["source_plan"] = {"sources": [{"name": " ".join(s["name"].split()), "mode": s["mode"]} for s in data["sources"]],
                                "destinations": data.get("publication", {}).get("cloud_destinations", []), "updated_at": now()}
        state["intake_confirmed_at"] = now()
        record(state, "User confirmed supplied intake summary; missing fields remain questions and no later approvals are implied")
        save(state_path, state)
        return
    if cmd == "titles":
        require_stage(state, "PREPARE")
        approved(root, state)
        path = required(inside(root, args.file, "outputs/blog"))
        options = load(path)
        if not isinstance(options, list) or not 3 <= len(options) <= 7:
            fail("Provide 3–7 title options, each with id, title and angle.")
        ids, names = set(), set()
        for option in options:
            if not isinstance(option, dict) or any(not isinstance(option.get(key), str) or not option[key].strip() for key in ("id", "title", "angle")):
                fail("Each title option needs nonempty id, title and angle strings.")
            if "\n" in option["title"] or option["id"] in ids or option["title"].casefold() in names:
                fail("Title options must be unique single-line headlines with unique IDs.")
            ids.add(option["id"])
            names.add(option["title"].casefold())
        state["title_options"] = {"file": str(path.relative_to(root)), "sha256": sha(path), "options": options,
                                  "revision_sha256": state["approval"]["sha256"]}
        record(state, "Presented evidence-grounded title choices; awaiting user selection")
        save(state_path, state)
        return
    if cmd == "select-title":
        require_stage(state, "PREPARE")
        approved(root, state)
        options = state.get("title_options") or fail("Suggest/register title options in PREPARE before asking for selection.")
        if options.get("revision_sha256") != state["approval"]["sha256"]:
            fail("Title suggestions predate the approved revision; present current options first.")
        if sha(required(inside(root, options["file"], "outputs"))) != options["sha256"]:
            fail("Title options changed; present and register the current options first.")
        if args.custom:
            title = args.custom.strip()
        else:
            title = next((o["title"] for o in options["options"] if o["id"] == args.id), None)
        if not title or "\n" in title:
            fail("Select a real option ID or a nonempty single-line custom title.")
        previous = state.get("title_selection", {})
        if previous.get("title") != title or previous.get("revision_sha256") != state["approval"]["sha256"]:
            for key in ("hero", "google_doc", "export"):
                state.pop(key, None)
        state["title_selection"] = {"title": title, "at": now(), "option_id": args.id,
                                    "options_sha256": options["sha256"], "revision_sha256": state["approval"]["sha256"]}
        invalidate(state)
        record(state, "User selected publication title in PREPARE; keep approved body unchanged and use this H1 in packaging")
        save(state_path, state)
        return
    if cmd == "select-sources":
        sources = []
        seen = set()
        for mode, names in (("mcp", args.mcp), ("manual", args.manual)):
            for name in names:
                name = " ".join(name.split())
                if not name or name.casefold() in seen:
                    fail("Source names must be nonempty and unique across access modes.")
                seen.add(name.casefold())
                sources.append({"name": name, "mode": mode})
        if not sources:
            fail("Select at least one source (use --manual for files/pasted content).")
        destinations = []
        for name in args.destination:
            name = " ".join(name.split())
            if not name or name.casefold() in {d.casefold() for d in destinations}:
                fail("Destination names must be nonempty and unique.")
            destinations.append(name)
        state["source_plan"] = {"sources": sources, "destinations": destinations, "updated_at": now()}
        invalidate(state)
        record(state, "User selected source plan; only selected MCP sources/destinations require access checks")
        save(state_path, state)
        print("Saved source selection. Do not warn about unselected or manual-only integrations.")
        return
    if cmd == "mcp-decision":
        plan = state.get("source_plan") or fail("Ask the user to select sources before MCP warnings.")
        allowed = {s["name"].casefold() for s in plan["sources"] if s["mode"] == "mcp"}
        allowed.update(name.casefold() for name in plan["destinations"])
        if any(" ".join(name.split()).casefold() not in allowed for name in args.connector):
            fail("MCP warnings/decisions are allowed only for explicitly selected MCP sources or destinations.")
        entry = {"connectors": args.connector, "capability": args.capability,
                 "source_plan_at": plan["updated_at"],
                 "reason": args.reason, "decision": args.decision,
                 "stage": state["stage"], "at": now()}
        state.setdefault("mcp_decisions", []).append(entry)
        invalidate(state)
        if args.decision == "exit":
            state["workflow_stopped"] = True
        record(state, f"User chose {args.decision} after MCP warning: {', '.join(args.connector)}")
        save(state_path, state)
        print("Proceed with available sources; skip the recorded MCP failures." if args.decision == "proceed"
              else "Workflow stopped. Progress preserved; end the agent workflow now.")
        return
    if cmd == "source":
        require_stage(state, "COLLECTION", "DRAFT", "REVISE")
        path = required(inside(root, args.file, "outputs/data"))
        if not path.is_relative_to((root / "outputs/data/normalized").resolve()):
            fail("Register readable evidence under outputs/data/normalized/.")
        catalog_path = root / "outputs/data/catalog.json"
        catalog = load(catalog_path)
        entry = {"id": f"S{len(catalog) + 1:03d}", "kind": args.kind, "title": args.title,
                 "locator": args.locator, "version": args.version, "limitations": args.limitations,
                 "confidentiality": args.confidentiality, "retrieved_at": now(),
                 "file": str(path.relative_to(root)), "sha256": sha(path)}
        catalog.append(entry)
        save(catalog_path, catalog)
        record(state, f"Registered evidence {entry['id']}")
        print(entry["id"])
    elif cmd == "advance":
        current = state["stage"]
        if (current, args.to) not in {("COLLECTION", "DRAFT"), ("DRAFT", "REVISE")}:
            fail("Only COLLECTION→DRAFT and DRAFT→REVISE use advance.")
        if current == "COLLECTION":
            catalog = load(root / "outputs/data/catalog.json")
            if not catalog:
                fail("Register at least one real source first.")
            for entry in catalog:
                if sha(required(inside(root, entry["file"], "outputs/data/normalized"))) != entry["sha256"]:
                    fail(f"Evidence changed: {entry['id']}; preserve the original and register a new version.")
            for name in ("research-brief.md", "claims.md", "search-log.md"):
                required(root / "outputs/data" / name)
        else:
            settings = state.get("draft_settings") or fail("Ask for draft length and version count first.")
            for i in range(1, settings["versions"] + 1):
                required(root / f"outputs/draft/version-{i:02d}.md")
            required(root / "outputs/draft/comparison.md")
            required(root / "outputs/draft/evidence-map.md")
            required(root / "outputs/draft/diagram-notes.md")
            from editorial import require_quality
            require_quality(root, state, [f"outputs/draft/version-{i:02d}.md" for i in range(1, settings["versions"] + 1)])
        state["stage"] = args.to
        record(state, f"User confirmed {current}→{args.to}")
    elif cmd == "draft-settings":
        require_stage(state, "DRAFT")
        if args.words < 1:
            fail("Word count must be positive.")
        state["draft_settings"] = {"words": args.words, "versions": args.versions, "count_scope": args.count_scope}
        record(state, "Recorded user draft settings")
    elif cmd == "approve":
        require_stage(state, "REVISE")
        path = required(inside(root, args.file, "outputs/revised_draft"))
        if not re.fullmatch(r"revision-\d{3,}\.md", path.name):
            fail("Approve a revision-NNN.md file, not notes or a draft.")
        required(path.with_name(path.stem + "-notes.md"))
        from editorial import require_quality
        quality = require_quality(root, state, [str(path.relative_to(root))])
        digest = sha(path)
        if state.get("title_selection", {}).get("revision_sha256") != digest:
            state.pop("title_selection", None)
            state.pop("title_options", None)
        state["approval"] = {"file": str(path.relative_to(root)), "sha256": digest, "at": now()}
        if quality:
            state["approval"]["quality_fingerprint"] = quality["fingerprint"]
        state["stage"] = "PREPARE"
        for key in ("hero", "google_doc", "export"):
            state.pop(key, None)
        invalidate(state)
        record(state, f"User explicitly satisfied with {path.name}; entering PREPARE")
    elif cmd == "reopen":
        require_stage(state, "PREPARE")
        state["stage"] = "REVISE"
        state.pop("approval", None)
        invalidate(state)
        record(state, "Reopened revision: " + args.reason)
    elif cmd == "hero":
        require_stage(state, "PREPARE")
        approved(root, state)
        title_ready(state)
        if args.skip:
            state["hero"] = {"decision": "skip", "at": now()}
        else:
            if not args.alt:
                fail("Provide meaningful --alt text.")
            path = required(inside(root, args.file, "outputs/blog/assets"))
            state["hero"] = {"decision": "selected", "file": str(path.relative_to(root)),
                             "alt": args.alt, "sha256": sha(path), "at": now()}
        invalidate(state)
        state.pop("export", None)
        record(state, "User hero decision: " + state["hero"]["decision"])
    elif cmd == "export":
        require_stage(state, "PREPARE")
        approved(root, state)
        title_ready(state)
        if not state.get("hero"):
            fail("Ask the user to select a hero image or explicitly skip first.")
        invalidate(state)
        state.pop("export", None)
        save(state_path, state)
        pdf = root / "outputs/blog/article.pdf"
        pdf.unlink(missing_ok=True)
        text = required(root / "outputs/blog/article.md").read_text(encoding="utf-8")
        heading = re.search(r"^#\s+(.+?)\s*$", text, re.M)
        document_title = heading.group(1) if heading else state["topic"]
        if state.get("title_selection") and document_title != state["title_selection"]["title"]:
            fail("Final Markdown title differs from the user's selection.")
        markup = render_html(root, text, document_title)
        (root / "outputs/blog/article.html").write_text(markup, encoding="utf-8")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    page = browser.new_page()
                    page.route("**/*", lambda route: route.abort())
                    page.set_content(markup, wait_until="load")
                    page.pdf(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True)
                finally:
                    browser.close()
        except Exception as exc:
            pdf.unlink(missing_ok=True)
            fail(f"HTML ready; PDF blocked: {exc}. Install Playwright and its Chromium browser; rerun export.")
        exported_files = {f"outputs/blog/article.{ext}": sha(root / f"outputs/blog/article.{ext}") for ext in ("md", "html", "pdf")}
        for asset in (root / "outputs/blog/assets").rglob("*"):
            if asset.is_file():
                inside(root, asset, "outputs/blog/assets")
                exported_files[str(asset.relative_to(root))] = sha(asset)
        state["export"] = {"at": now(), "files": exported_files}
        save(root / "outputs/blog/delivery.json", delivery(root, state))
        print("Created outputs/blog/article.html and outputs/blog/article.pdf. Inspect both before delivery.")
    elif cmd == "google-doc":
        require_stage(state, "PREPARE")
        approved(root, state)
        title_ready(state)
        match = re.fullmatch(r"https://docs\.google\.com/document/d/([A-Za-z0-9_-]+)/?(?:edit)?(?:[?#].*)?", args.url)
        if not match:
            fail("Provide the real Google Docs document URL.")
        state["google_doc"] = {"url": args.url, "document_id": match.group(1), "verified_at": now(),
                               "article_sha256": sha(required(root / "outputs/blog/article.md"))}
        save(root / "outputs/blog/article.gdoc", {"url": args.url, "doc_id": match.group(1)})
        save(root / "outputs/blog/google-doc.json", state["google_doc"])
        invalidate(state)
        record(state, "User authorized Google Doc; host agent attested readback verification")
    elif cmd == "complete":
        require_stage(state, "PREPARE")
        approved(root, state)
        title_ready(state)
        hero = state.get("hero") or fail("Missing user hero decision.")
        if hero["decision"] == "selected":
            if sha(required(inside(root, hero["file"], "outputs/blog/assets"))) != hero["sha256"]:
                fail("Selected hero changed; ask user to select again.")
        exports = state.get("export") or fail("Run export successfully first.")
        for name, digest in exports["files"].items():
            if sha(required(root / name)) != digest:
                fail(f"Export changed: {name}; rerun export and verify the Google Doc.")
        doc = state.get("google_doc") or fail("Google Doc is still blocked/unverified.")
        if sha(root / "outputs/blog/article.md") != doc["article_sha256"]:
            fail("Google Doc verification predates current Markdown; verify it again.")
        for name in ("article.gdoc", "google-doc.json", "verification.md"):
            required(root / "outputs/blog" / name)
        if load(root / "outputs/blog/google-doc.json") != doc or load(root / "outputs/blog/article.gdoc").get("url") != doc["url"]:
            fail("Google Doc pointer/metadata changed; re-verify the document.")
        if any(p.is_file() for p in (root / "outputs/blog/assets").rglob("*")):
            required(root / "outputs/blog/assets/manifest.json")
        save(root / "outputs/blog/delivery.json", delivery(root, state))
        state["completed_at"] = now()
        state["delivery_sha256"] = sha(root / "outputs/blog/delivery.json")
        record(state, "User accepted all four verified publication formats")
        print("Complete. Deliverables and checksums: outputs/blog/delivery.json")
    save(state_path, state)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=str(ROOT), help="Workspace root (default: repository root)")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("startup", help="Read-only input validation/new-or-resume routing; never replays input into a saved run")
    s.add_argument("--input", help="Input brief for a new run; ignored when project.json already exists")
    s = sub.add_parser("init")
    s.add_argument("--topic")
    s.add_argument("--audience")
    s.add_argument("--input", help="Validated JSON preferences; default: input/blog.json if present (never the sample)")
    for command in ("inspect-input", "import-input"):
        s = sub.add_parser(command)
        s.add_argument("--file", default="input/blog.json")
    s = sub.add_parser("apply-input")
    s.add_argument("--user-confirmed", action="store_true", required=True)
    sub.add_parser("migrate-decisions")
    s = sub.add_parser("titles")
    s.add_argument("--file", required=True)
    s = sub.add_parser("select-title")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--id")
    g.add_argument("--custom")
    s.add_argument("--user-confirmed", action="store_true", required=True)
    sub.add_parser("status")
    s = sub.add_parser("resume")
    s.add_argument("--user-confirmed", action="store_true", required=True)
    s = sub.add_parser("select-sources")
    s.add_argument("--mcp", action="append", default=[], help="Selected MCP research source; repeat as needed")
    s.add_argument("--manual", action="append", default=[], help="Selected source supplied via local files/paste")
    s.add_argument("--destination", action="append", default=[], help="Explicitly selected cloud publication target")
    s.add_argument("--user-confirmed", action="store_true", required=True)
    s = sub.add_parser("mcp-decision")
    s.add_argument("--connector", action="append", required=True)
    s.add_argument("--capability", required=True)
    s.add_argument("--reason", required=True, help="Sanitized issue summary; never credentials")
    s.add_argument("--decision", choices=("proceed", "exit"), required=True)
    s.add_argument("--user-confirmed", action="store_true", required=True)
    s = sub.add_parser("source")
    for name in ("file", "kind", "title", "locator", "confidentiality"):
        s.add_argument("--" + name, required=True)
    s.add_argument("--version", default="unknown")
    s.add_argument("--limitations", default="none recorded; verify coverage")
    s = sub.add_parser("advance")
    s.add_argument("--to", choices=("DRAFT", "REVISE"), required=True)
    s.add_argument("--user-confirmed", action="store_true", required=True)
    s = sub.add_parser("draft-settings")
    s.add_argument("--words", type=int, required=True)
    s.add_argument("--versions", type=int, choices=(2, 3), required=True)
    s.add_argument("--count-scope", required=True)
    s = sub.add_parser("approve")
    s.add_argument("--file", required=True)
    s.add_argument("--user-confirmed", action="store_true", required=True)
    s = sub.add_parser("reopen")
    s.add_argument("--reason", required=True)
    s = sub.add_parser("hero")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--skip", action="store_true")
    s.add_argument("--alt")
    s.add_argument("--user-confirmed", action="store_true", required=True)
    sub.add_parser("export")
    s = sub.add_parser("google-doc")
    s.add_argument("--url", required=True)
    s.add_argument("--verified", action="store_true", required=True)
    s.add_argument("--user-confirmed", action="store_true", required=True)
    s = sub.add_parser("complete")
    s.add_argument("--user-confirmed", action="store_true", required=True)
    return p


if __name__ == "__main__":
    try:
        run(parser().parse_args())
    except (ValueError, OSError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
