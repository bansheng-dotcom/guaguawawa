import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from compiler_lib import build_project_dir, read_json


LOGIC_MARKERS = (
    "因为",
    "原因",
    "导致",
    "如果",
    "当",
    "缺少",
    "漏掉",
    "前提",
    "口径",
    "证据",
    "判断",
    "边界",
    "落到",
    "影响",
    "意味着",
    "不能",
    "需要",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_lines: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## "):
            if current_heading:
                sections.append((current_heading, current_lines))
            current_heading = line[3:].strip()
            current_lines = []
        elif current_heading:
            current_lines.append(line)
    if current_heading:
        sections.append((current_heading, current_lines))
    return [(heading, "\n".join(lines).strip()) for heading, lines in sections]


def _prose_paragraphs(section_text: str) -> list[str]:
    paragraphs: list[str] = []
    buffer: list[str] = []
    in_code = False
    for raw_line in section_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer = []
            continue
        if in_code:
            continue
        if not stripped:
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer = []
            continue
        if stripped.startswith("|") or re.match(r"^[-*+]\s+", stripped) or re.match(r"^\d+[\.、]\s*", stripped):
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer = []
            continue
        if stripped.startswith("#"):
            continue
        buffer.append(stripped)
    if buffer:
        paragraphs.append(" ".join(buffer).strip())
    return [paragraph for paragraph in paragraphs if paragraph]


def _visible_len(text: str) -> int:
    cleaned = re.sub(r"`[^`]*`", "", text)
    cleaned = re.sub(r"\[[^\]]+\]\([^)]+\)", "", cleaned)
    cleaned = re.sub(r"[#>*_\-\s，。！？；：、“”‘’（）()《》【】\[\]|]", "", cleaned)
    return len(cleaned)


def _has_logic_marker(text: str) -> bool:
    return any(marker in text for marker in LOGIC_MARKERS)


def _normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _is_appendix_heading(heading: str) -> bool:
    normalized = _normalize_heading(heading)
    without_number = re.sub(r"^\d+[.、]\s*", "", normalized)
    return without_number.startswith(("附录", "延伸阅读", "参考资料"))


def _expected_headings(manifest: dict) -> list[str]:
    headings: list[str] = []
    for section in manifest.get("sections", []):
        heading = _normalize_heading(section.get("heading", ""))
        if heading and not _is_appendix_heading(heading):
            headings.append(heading)
    return headings


def _manifest_by_heading(manifest: dict) -> dict[str, dict]:
    mapping: dict[str, dict] = {}
    for section in manifest.get("sections", []):
        heading = str(section.get("heading") or "").strip()
        if heading:
            mapping[heading] = section
            normalized = re.sub(r"^\d+\.\s*", "", heading)
            mapping[normalized] = section
    return mapping


def validate(markdown: str, manifest: dict | None = None) -> dict:
    manifest = manifest or {}
    manifest_map = _manifest_by_heading(manifest)
    expected_headings = _expected_headings(manifest)
    issues: list[str] = []
    warnings: list[str] = []
    section_results: list[dict] = []
    actual_headings: list[str] = []

    for heading, section_text in _split_sections(markdown):
        if _is_appendix_heading(heading):
            continue
        actual_headings.append(_normalize_heading(heading))
        paragraphs = _prose_paragraphs(section_text)
        lengths = [_visible_len(paragraph) for paragraph in paragraphs]
        section_meta = manifest_map.get(heading) or manifest_map.get(re.sub(r"^\d+\.\s*", "", heading), {})
        target_word_count = int(section_meta.get("target_word_count") or 0)
        require_long_logic = target_word_count >= 380 or len(paragraphs) >= 4
        long_reasoning = [
            idx
            for idx, paragraph in enumerate(paragraphs, start=1)
            if _visible_len(paragraph) >= 95 and (_has_logic_marker(paragraph) or _visible_len(paragraph) >= 130)
        ]

        max_short_run = 0
        current_run = 0
        for length in lengths:
            if length <= 42:
                current_run += 1
                max_short_run = max(max_short_run, current_run)
            else:
                current_run = 0
        short_ratio = (sum(1 for length in lengths if length <= 42) / len(lengths)) if lengths else 0.0

        result = {
            "heading": heading,
            "paragraph_count": len(paragraphs),
            "long_reasoning_count": len(long_reasoning),
            "max_short_run": max_short_run,
            "short_ratio": round(short_ratio, 2),
        }
        section_results.append(result)

        if require_long_logic and not long_reasoning:
            warnings.append(f"{heading}: 未检测到长推理段；如本节是机制/边界/方法/核心判断，请确认中间推理没有被压掉")
        if max_short_run >= 4:
            issues.append(f"{heading}: 连续短气口段落过多（max_short_run={max_short_run}）")
        elif short_ratio >= 0.70 and len(paragraphs) >= 4:
            warnings.append(f"{heading}: 短段落占比偏高（short_ratio={short_ratio:.2f}）")

    if expected_headings:
        missing = [heading for heading in expected_headings if heading not in actual_headings]
        unexpected = [heading for heading in actual_headings if heading not in expected_headings]
        if missing:
            issues.append(f"missing argument-flow sections: {', '.join(missing)}")
        if unexpected:
            issues.append(f"unexpected argument-flow sections: {', '.join(unexpected)}")
        if not missing and not unexpected and actual_headings != expected_headings:
            issues.append("argument-flow section order does not match section-manifest order")

    return {
        "pass": not issues,
        "passed": ["argument flow check passed"] if not issues else [],
        "issues": issues,
        "warnings": warnings,
        "section_results": section_results,
        "expected_section_count": len(expected_headings),
        "actual_section_count": len(actual_headings),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate long logic and paragraph breath in article drafts")
    parser.add_argument("path")
    parser.add_argument("--topic-id", default="")
    parser.add_argument("--section-manifest", default="")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    article_path = Path(args.path)
    if not article_path.is_absolute():
        article_path = project_root / article_path
    if not article_path.exists():
        payload = {"pass": False, "passed": [], "issues": [f"file not found: {article_path}"], "warnings": []}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    manifest: dict = {}
    manifest_path: Path | None = Path(args.section_manifest) if args.section_manifest else None
    if args.topic_id and manifest_path is None:
        manifest_path = build_project_dir(project_root, args.topic_id) / "section-manifest.json"
    if manifest_path:
        if not manifest_path.is_absolute():
            manifest_path = project_root / manifest_path
        if manifest_path.exists():
            manifest = read_json(manifest_path, {})

    payload = validate(_read_text(article_path), manifest)
    payload["file"] = str(article_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload["pass"] else 1)


if __name__ == "__main__":
    main()
