import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from assemble_draft import extract_title
from article_quality_gates import split_section_blocks
from compiler_lib import build_project_dir, read_json


APPENDIX_HEADING_RE = re.compile(
    r"(?m)^(#{2,3})\s*(?:\d+[.、]\s*)?(?:附录|参考资料|延伸阅读)\b.*$"
)


def strip_title(text: str) -> str:
    stripped = text.lstrip("\ufeff").strip()
    if stripped.startswith("# "):
        parts = stripped.splitlines()
        return "\n".join(parts[1:]).strip()
    return stripped


def strip_legacy_appendix(text: str) -> str:
    match = APPENDIX_HEADING_RE.search(text)
    if not match:
        return text.strip()
    return text[: match.start()].strip()


def strip_appendix_placeholder(text: str) -> str:
    blocks = split_section_blocks(text)

    if not blocks:
        return text.strip()

    last_heading, last_block = blocks[-1]
    compact = last_block.replace(" ", "")
    if "附录" in last_heading and ("占位" in compact or "后续appendix" in compact.lower() or len(compact) < 220):
        blocks = blocks[:-1]
    return "\n\n".join(block for _, block in blocks).strip()


def expected_main_section_count(project_dir: Path) -> int:
    manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    count = 0
    for section in manifest.get("sections", []):
        heading = str(section.get("heading", "")).strip()
        if heading and not heading.startswith(("附录", "参考资料", "延伸阅读")):
            count += 1
    return count


def has_full_section_coverage(path: Path, expected_count: int) -> bool:
    if not path.exists():
        return False
    text = strip_appendix_placeholder(strip_legacy_appendix(strip_title(path.read_text(encoding="utf-8"))))
    return len(split_section_blocks(text)) >= expected_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize article draft with appendix")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--body-node", default="style-harmonizer-01")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)

    style_path = project_dir / args.body_node / "output.md"
    appendix_path = project_dir / "appendix-agent-01" / "output.md"
    assembled_path = project_root / "tmp" / f"{args.topic_id}-draft.md"

    expected_count = expected_main_section_count(project_dir)
    body_source = style_path if has_full_section_coverage(style_path, expected_count) else assembled_path
    if not body_source.exists():
        payload = {
            "pass": False,
            "passed": [],
            "issues": [f"body source missing: {body_source}"],
            "file": str(assembled_path),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(1)

    body_text = strip_appendix_placeholder(strip_legacy_appendix(strip_title(body_source.read_text(encoding="utf-8"))))
    appendix_text = appendix_path.read_text(encoding="utf-8").strip() if appendix_path.exists() else ""
    profile = read_json(project_dir / "workflow-profile.json", {})
    title = str(profile.get("title") or "").strip() or extract_title(args.topic_id, project_root)

    parts = [f"# {title}", body_text]
    if appendix_text:
        parts.append(appendix_text)

    final_text = "\n\n".join(part.strip() for part in parts if part and part.strip()) + "\n"
    assembled_path.write_text(final_text, encoding="utf-8")

    payload = {
        "pass": True,
        "passed": [
            f"finalized draft from {body_source.name}",
            "appendix appended" if appendix_text else "appendix missing, body only",
        ],
        "issues": [],
        "file": str(assembled_path),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
