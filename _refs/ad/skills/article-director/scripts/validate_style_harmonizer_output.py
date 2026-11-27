import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
AI_TONE_SCRIPT_DIR = Path(r"D:\知识库\skills\内容生产\ai-tone-director\scripts")
if str(AI_TONE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(AI_TONE_SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json, write_json
from scan_ai_tone import scan_text


FORBIDDEN_TAIL_PATTERNS = [
    "如果你要",
    "我下一步可以",
    "我可以继续",
    "你要的话",
    "如果需要我可以",
    "接下来我可以",
]


def normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def format_blocking_hits(scan: dict, limit: int = 8) -> list[str]:
    rows: list[str] = []
    for hit in scan.get("hits", []):
        if hit.get("severity") != "blocking":
            continue
        rows.append(
            f"line {hit.get('line')}: {hit.get('family')} -> {hit.get('quote')}"
        )
        if len(rows) >= limit:
            break
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate style harmonizer full-draft output")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--input-node", default="style-harmonizer-01")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    output_path = project_dir / args.input_node / "output.md"

    issues: list[str] = []
    passed: list[str] = []
    text = output_path.read_text(encoding="utf-8") if output_path.exists() else ""

    if not text.strip():
        issues.append("style harmonizer output is empty")

    expected_headings = [normalize_heading(section.get("heading", "")) for section in manifest.get("sections", [])]
    actual_headings = [normalize_heading(match.group(1)) for match in re.finditer(r"^##\s+(.*)$", text, flags=re.MULTILINE)]

    missing = [heading for heading in expected_headings if heading and heading not in actual_headings]
    tail_hits = [pattern for pattern in FORBIDDEN_TAIL_PATTERNS if pattern in text]

    if missing:
        issues.append(f"missing harmonized sections: {', '.join(missing)}")
    else:
        passed.append(f"validated {len(expected_headings)} harmonized sections")

    if len(actual_headings) != len(expected_headings):
        issues.append(f"unexpected harmonized section count: expected={len(expected_headings)} actual={len(actual_headings)}")

    if not missing and len(actual_headings) == len(expected_headings) and actual_headings != expected_headings:
        issues.append("harmonized section order does not match section-manifest order")

    if "[...truncated...]" in text:
        issues.append("style harmonizer output contains truncation marker")

    if tail_hits:
        issues.append(f"style harmonizer output contains assistant-tail patterns: {', '.join(tail_hits)}")
    else:
        passed.append("no assistant-tail patterns detected")

    ai_tone_scan = scan_text(text)
    blocking_hit_count = int(ai_tone_scan.get("blocking_hit_count", 0) or 0)
    if blocking_hit_count:
        hit_summary = " | ".join(format_blocking_hits(ai_tone_scan))
        issues.append(
            f"final body contains {blocking_hit_count} blocking AI-tone/filler pattern hits"
            + (f": {hit_summary}" if hit_summary else "")
        )
    else:
        passed.append("no blocking AI-tone/filler patterns detected")

    payload = {
        "pass": not issues,
        "passed": passed,
        "issues": issues,
        "file": str(output_path),
        "expected_section_count": len(expected_headings),
        "actual_section_count": len(actual_headings),
        "ai_tone_scan": {
            "hit_count": ai_tone_scan.get("hit_count", 0),
            "blocking_hit_count": ai_tone_scan.get("blocking_hit_count", 0),
            "advisory_hit_count": ai_tone_scan.get("advisory_hit_count", 0),
            "pattern_counts": ai_tone_scan.get("pattern_counts", {}),
            "hits": ai_tone_scan.get("hits", []),
        },
    }
    write_json(project_dir / "style-harmonizer-check-01" / "output.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload["pass"] else 1)


if __name__ == "__main__":
    main()
