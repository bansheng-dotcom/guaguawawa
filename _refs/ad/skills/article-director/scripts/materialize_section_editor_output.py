import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from compiler_lib import build_project_dir, read_json


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _display_path(project_root: Path, path: Path) -> str:
    try:
        value = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        value = path
    return value.as_posix()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _expected_heading(project_dir: Path, section_id: str) -> str:
    manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    for section in manifest.get("sections", []):
        if str(section.get("section_id") or "") == section_id:
            return str(section.get("heading") or section_id)
    return section_id


def _canonical_section(markdown: str, heading: str) -> tuple[str, list[str]]:
    issues: list[str] = []
    text = str(markdown or "").strip()
    if not text:
        return "", ["final_markdown is empty"]
    lines = text.splitlines()
    first = lines[0].strip() if lines else ""
    match = re.match(r"^#{1,3}\s+(.+?)\s*$", first)
    if match:
        actual = _normalize(match.group(1))
        expected = _normalize(heading)
        if actual != expected:
            issues.append(f"heading mismatch: expected '{expected}', got '{actual}'")
        lines[0] = f"## {heading}"
        text = "\n".join(lines).strip()
    else:
        text = f"## {heading}\n\n{text}"
    text = re.sub(r"(?s)<!--\s*writer-contract.*?-->\s*", "", text).strip()
    return text + "\n", issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize section-editor JSON into final section artifacts")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--section-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    section_dir = project_dir / "sections" / args.section_id
    source = section_dir / "section-editor-output.json"
    payload = _read_json(source)
    issues: list[str] = []

    if not payload:
        issues.append(f"missing or invalid section editor output: {source}")

    for key in ("pass", "score", "summary", "scope", "section_id", "ai_tone_audit", "final_markdown"):
        if key not in payload:
            issues.append(f"missing field: {key}")
    if payload.get("scope") != "section":
        issues.append("scope must be section")
    if str(payload.get("section_id") or "") != args.section_id:
        issues.append("section_id mismatch")

    context_path = section_dir / "ai-tone-context-pack.json"
    context = _read_json(context_path)
    audit = payload.get("ai_tone_audit")
    if not isinstance(audit, dict):
        issues.append("ai_tone_audit must be object")
        audit = {}
    else:
        audit.setdefault("pass", bool(payload.get("pass", False)))
        audit.setdefault("score", payload.get("score", 0))
        audit.setdefault("summary", str(payload.get("summary") or ""))
        audit.setdefault("scope", "section")
        audit.setdefault("dimension", "ai_tone")
        for key in ("issues", "blocking_issues", "advisory_issues", "must_fix"):
            audit.setdefault(key, [])
    expected_invocation = context.get("audit_must_include", {}).get("ai_tone_invocation", {}) if context else {}
    invocation = audit.get("ai_tone_invocation") if isinstance(audit.get("ai_tone_invocation"), dict) else {}
    for key in ("topic_id", "section_id", "phase", "idempotency_key", "source_hash"):
        if str(invocation.get(key, "")) != str(expected_invocation.get(key, "")):
            issues.append(f"ai_tone_invocation.{key} mismatch")

    final_markdown, heading_issues = _canonical_section(
        str(payload.get("final_markdown") or ""),
        _expected_heading(project_dir, args.section_id),
    )
    issues.extend(heading_issues)

    terms = payload.get("terms", [])
    if terms is None:
        terms = []
    if not isinstance(terms, list):
        issues.append("terms must be a list")
        terms = []

    materialize_path = section_dir / "section-editor-materialize.json"
    if issues:
        result = {"pass": False, "issues": issues, "file": _display_path(project_root, source)}
        _write_json(materialize_path, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    (section_dir / "final.md").write_text(final_markdown, encoding="utf-8")
    _write_json(section_dir / "review-ai-tone.json", audit)
    _write_json(section_dir / "terms.json", {"terms": terms, "summary": f"{len(terms)} terms collected"})

    result = {
        "pass": True,
        "issues": [],
        "passed": ["section editor output materialized"],
        "file": _display_path(project_root, section_dir / "final.md"),
        "audit_file": _display_path(project_root, section_dir / "review-ai-tone.json"),
        "terms_file": _display_path(project_root, section_dir / "terms.json"),
    }
    _write_json(materialize_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
