"""Simple user briefs normalized into stable internal intake; never approvals."""
import copy
from datetime import date
import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "harness/schemas/input.schema.json"
LEGACY_SCHEMA = SCHEMA.with_name("input-v1.schema.json")
DEFAULTS = SCHEMA.parents[1] / "config.collection.json"
COUNT_SCOPE = "Body and captions; exclude references and fenced code"


def validate_node(value, rule, location="input"):
    # Implements the keywords used by our schemas, not all of JSON Schema.
    types = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}
    expected = rule.get("type")
    if expected and (not isinstance(value, types[expected]) or (expected == "integer" and isinstance(value, bool))):
        raise ValueError(f"{location}: expected {expected}")
    if "const" in rule and value != rule["const"]:
        raise ValueError(f"{location}: must equal {rule['const']}")
    if "enum" in rule and value not in rule["enum"]:
        raise ValueError(f"{location}: choose from {rule['enum']}")
    if isinstance(value, dict):
        properties = rule.get("properties", {})
        missing = set(rule.get("required", [])) - value.keys()
        if missing:
            raise ValueError(f"{location}: missing {', '.join(sorted(missing))}")
        extra = rule.get("additionalProperties", True)
        unknown = value.keys() - properties.keys()
        if extra is False and unknown:
            raise ValueError(f"{location}: unknown fields {', '.join(sorted(unknown))}")
        for key, item in value.items():
            if key in properties:
                validate_node(item, properties[key], f"{location}.{key}")
            elif isinstance(extra, dict):
                if not key.strip():
                    raise ValueError(f"{location}: names must not be blank")
                validate_node(item, extra, f"{location}.{key}")
    elif isinstance(value, list):
        if len(value) < rule.get("minItems", 0):
            raise ValueError(f"{location}: too few entries")
        for index, item in enumerate(value):
            validate_node(item, rule.get("items", {}), f"{location}[{index}]")
    elif isinstance(value, str):
        if len(value.strip()) < rule.get("minLength", 0):
            raise ValueError(f"{location}: must not be blank")
        if rule.get("format") == "date":
            if len(value) != 10:
                raise ValueError(f"{location}: use YYYY-MM-DD")
            date.fromisoformat(value)
    elif isinstance(value, int) and not isinstance(value, bool):
        if value < rule.get("minimum", value) or value > rule.get("maximum", value):
            raise ValueError(f"{location}: outside allowed range")


def name_key(name):
    return " ".join(name.split()).casefold()


def check_internal(data):
    sources = data.get("sources", [])
    names = [name_key(item["name"]) for item in sources]
    if len(names) != len(set(names)):
        raise ValueError("input.sources: source names must be unique across access modes")
    research = data.get("research", {})
    if research.get("from_date") and research.get("cutoff_date") and research["from_date"] > research["cutoff_date"]:
        raise ValueError("input: from_date must not follow cutoff_date")
    series = data.get("blog", {}).get("series", {})
    if series.get("kind") == "series":
        if "part_number" not in series or "total_parts" not in series or series["total_parts"] < 2:
            raise ValueError("input.series: requires current part and total >= 2")
        if series["part_number"] > series["total_parts"]:
            raise ValueError("input.series: current part exceeds total")
    if series.get("kind") == "single" and (series.get("part_number", 1) != 1 or series.get("total_parts", 1) != 1):
        raise ValueError("input.series: single blogs cannot specify multiple parts")
    parts = [entry["part"] for entry in series.get("roadmap", [])]
    if len(parts) != len(set(parts)) or any(part > series.get("total_parts", 1) for part in parts):
        raise ValueError("input.series: duplicate or out-of-range roadmap part")
    publication = data.get("publication", {})
    destinations = publication.get("cloud_destinations", [])
    if len({name_key(name) for name in destinations}) != len(destinations):
        raise ValueError("input: cloud destinations must be unique")
    if "google_doc" in publication.get("formats", []) and "google docs" not in {name_key(n) for n in destinations}:
        raise ValueError("input.publication: google_doc requires explicit Google Docs destination")
    return data


def validate(data):
    if isinstance(data, dict) and data.get("schema_version") == 1:
        validate_node(data, json.loads(LEGACY_SCHEMA.read_text(encoding="utf-8")))
        result = copy.deepcopy(data)
        # Historical snapshots stay untouched on disk. Old headline hints never
        # drive new title suggestions/selection, which now belong to PREPARE.
        result.pop("title_preferences", None)
        return check_internal(result)
    validate_node(data, json.loads(SCHEMA.read_text(encoding="utf-8")))
    result = {"schema_version": 1, "blog": {"series": {"kind": "single"}},
              "draft": {"versions": data.get("drafts", 2), "count_scope": data.get("count_scope", COUNT_SCOPE),
                        "technical_depth": data.get("depth", "Practical technical detail"),
                        "tone": data.get("tone", "Clear, engaging and technically precise")},
              "research": {}, "privacy": {}, "sources": []}
    blog = result["blog"]
    for key, target in (("topic", "topic"), ("goal", "purpose"), ("publication", "publication"),
                        ("keywords", "keywords"), ("cover", "required_coverage"), ("exclude", "exclusions")):
        if key in data:
            blog[target] = copy.deepcopy(data[key])
    if "audience" in data:
        blog["audience"] = [data["audience"]]
    if "words" in data:
        result["draft"]["target_words"] = data["words"]
    for key in ("from_date", "cutoff_date", "questions"):
        if key in data:
            result["research"][key] = copy.deepcopy(data[key])
    if "notes" in data:
        result["research"]["source_notes"] = data["notes"]  # internal v1 storage only
    if "series" in data:
        series = data["series"]
        blog["series"] = {"kind": "series", "part_number": series["part"], "total_parts": series["total"],
                          "roadmap": [{"part": i + 1, "focus": text} for i, text in enumerate(series.get("roadmap", []))]}
    scopes = {name_key(k): value for k, value in data.get("source_scopes", {}).items()}
    settings = {name_key(k): value for k, value in data.get("source_settings", {}).items()}
    for mode, groups in (("mcp", data.get("sources", {})), ("manual", data.get("manual_sources", {}))):
        for name, links in groups.items():
            entry = {"name": " ".join(name.split()), "mode": mode, "links": list(links)}
            if "scope" in data:
                entry["scope_notes"] = data["scope"]
            result["sources"].append(entry)
    if data.get("files"):
        result["sources"].append({"name": "Local files", "mode": "manual", "links": list(data["files"]),
                                  "scope_notes": data.get("scope", "Only the supplied local files")})
    for entry in result["sources"]:
        if name_key(entry["name"]) in scopes:
            entry["scope_notes"] = scopes[name_key(entry["name"])]
        entry.update(settings.get(name_key(entry["name"]), {}))
    source_names = {name_key(s["name"]) for s in result["sources"]}
    if (scopes.keys() | settings.keys()) - source_names:
        raise ValueError("input: source_scopes/source_settings must refer only to selected sources")
    result["navigation"] = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    result["navigation"].pop("sources")
    result["navigation"].update(data.get("limits", {}))
    result["navigation"].update({"mode": data.get("follow", "both"), "max_depth": data.get("max_depth", 2)})
    if "store_confidential_locally" in data:
        result["privacy"]["store_confidential_locally"] = data["store_confidential_locally"]
    formats = data.get("outputs", ["markdown", "html", "pdf"])
    destinations = list(data.get("cloud_destinations", []))
    # Explicit google_doc output selects only that publication destination,
    # never a Google research source or upload authorization.
    if "google_doc" in formats and "google docs" not in {name_key(n) for n in destinations}:
        destinations.append("Google Docs")
    result["publication"] = {"formats": list(formats), "cloud_destinations": destinations}
    return check_internal(result)


def read_input(path):
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))


def missing_fields(data):
    needed = (("blog", "topic", "topic"), ("blog", "audience", "audience"),
              ("blog", "publication", "publication"), ("draft", "target_words", "words"),
              ("privacy", "store_confidential_locally", "store_confidential_locally"))
    missing = [label for section, key, label in needed if key not in data.get(section, {})]
    if not data.get("sources"):
        missing.append("sources or files")
    return missing


def draft_settings(data):
    draft = data.get("draft", {})
    if not all(key in draft for key in ("target_words", "versions", "count_scope")):
        return None
    return {"words": draft["target_words"], "versions": draft["versions"], "count_scope": draft["count_scope"]}
