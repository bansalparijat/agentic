"""JSON-only adapter to actual pure Python helpers; no eval, source calls or run writes."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import blog
import collection
import editorial
import intake


def dispatch(request):
    op = request["op"]
    if op == "normalize":
        value = intake.validate(request["value"])
        return {"normalized": value, "missing": intake.missing_fields(value)}
    if op == "canonical":
        return collection.canonical(request["url"])
    if op == "in_scope":
        return collection.in_scope(request["url"], request["prefixes"])
    if op == "blueprint":
        return editorial.infer(request["state"], request.get("type", "auto"))[0]
    if op == "has_code":
        return editorial.has_code(request["text"])
    if op == "word_count":
        return blog.word_count(request["text"])
    if op == "targets":
        return editorial.targets_for(request["state"], request.get("files", []))
    if op == "inside":
        return str(blog.inside(Path(request["root"]), request["name"], request.get("folder")))
    raise ValueError("Unknown test operation")


if __name__ == "__main__":
    try:
        print(json.dumps({"ok": True, "result": dispatch(json.load(sys.stdin))}))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        sys.exit(1)
