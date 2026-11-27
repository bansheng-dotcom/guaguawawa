import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json


def normalize_heading_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def normalize_section_heading_level(block: str) -> str:
    lines = block.splitlines()
    if lines and re.match(r"^#{1,3}\s+", lines[0]):
        lines[0] = re.sub(r"^#{1,3}\s+", "## ", lines[0], count=1)
    return "\n".join(lines).strip()


def canonicalize_section_block(block: str, expected_heading: str, section_id: str) -> tuple[str, bool]:
    expected = normalize_heading_text(expected_heading)
    text = block.lstrip("\ufeff").strip()
    if not text:
        return "", False
    lines = text.splitlines()
    first_line = lines[0].strip() if lines else ""
    heading_match = re.match(r"^#{1,3}\s+(.+?)\s*$", first_line)
    if heading_match:
        actual = normalize_heading_text(heading_match.group(1))
        if actual != expected:
            raise ValueError(f"{section_id}: heading mismatch, expected '{expected}', got '{actual}'")
        lines[0] = f"## {expected_heading}"
        return "\n".join(lines).strip(), False
    return f"## {expected_heading}\n\n{text}", True


def extract_title(topic_id: str, project_root: Path) -> str:
    outline_path = project_root / "tmp" / f"{topic_id}-outline.md"
    if outline_path.exists():
        for line in outline_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return topic_id


def split_section_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        heading_match = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if heading_match:
            if current_heading:
                blocks.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = heading_match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_heading:
        blocks.append((current_heading, "\n".join(current_lines).strip()))
    return blocks


def package_output_path(project_dir: Path, package_id: str) -> Path:
    for stage_name in (
        "final-package-editor",
        "adversarial-reviewer",
        "term-annotator",
        "narrative-smoother",
        "structure-editor",
        "deep-dive-researcher",
        "concept-bridge-rewriter",
        "primer-writer",
        "writer",
    ):
        candidate = project_dir / f"{stage_name}-{package_id}" / "output.md"
        if candidate.exists():
            return candidate
    return project_dir / f"writer-{package_id}" / "output.md"


def section_final_path(project_dir: Path, section_id: str) -> Path:
    return project_dir / "sections" / section_id / "final.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble article draft from package outputs")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    packages = read_json(project_dir / "article-packages.json", {"packages": []})

    assembled_by_id: dict[str, str] = {}
    missing: list[str] = []
    repaired_headings: list[str] = []
    structure_issues: list[str] = []

    for section in manifest.get("sections", []):
        section_id = str(section.get("section_id") or "")
        if not section_id:
            continue
        final_path = section_final_path(project_dir, section_id)
        if final_path.exists():
            try:
                block, repaired = canonicalize_section_block(
                    final_path.read_text(encoding="utf-8"),
                    str(section.get("heading") or section_id),
                    section_id,
                )
                assembled_by_id[section_id] = normalize_section_heading_level(block)
                if repaired:
                    repaired_headings.append(section_id)
            except ValueError as exc:
                structure_issues.append(str(exc))

    if not assembled_by_id:
        for package in packages.get("packages", []):
            output_path = package_output_path(project_dir, package["package_id"])
            if not output_path.exists():
                missing.extend(package.get("section_ids", []))
                continue

            blocks = split_section_blocks(output_path.read_text(encoding="utf-8"))
            expected_ids = package.get("section_ids", [])
            if len(blocks) < len(expected_ids):
                missing.extend(expected_ids[len(blocks) :])

            for index, section_id in enumerate(expected_ids):
                if index >= len(blocks):
                    continue
                _, block = blocks[index]
                section_meta = next(
                    (item for item in manifest.get("sections", []) if item.get("section_id") == section_id),
                    {},
                )
                try:
                    canonical_block, repaired = canonicalize_section_block(
                        block,
                        str(section_meta.get("heading") or section_id),
                        section_id,
                    )
                    assembled_by_id[section_id] = normalize_section_heading_level(canonical_block)
                    if repaired:
                        repaired_headings.append(section_id)
                except ValueError as exc:
                    structure_issues.append(str(exc))

    ordered_sections: list[str] = []
    missing_headings: list[str] = []
    for section in manifest.get("sections", []):
        block = assembled_by_id.get(section["section_id"], "")
        if not block:
            missing_headings.append(section["heading"])
            continue
        ordered_sections.append(block)

    if structure_issues or missing_headings:
        issues = list(structure_issues)
        if missing_headings:
            issues.append(f"missing assembled sections: {', '.join(missing_headings)}")
        payload = {
            "pass": False,
            "passed": [],
            "issues": issues,
            "file": str(project_root / "tmp" / f"{args.topic_id}-draft.md"),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(1)

    profile = read_json(project_dir / "workflow-profile.json", {})
    title = str(profile.get("title") or "").strip() or extract_title(args.topic_id, project_root)
    body = "\n\n".join(ordered_sections).strip() + "\n"
    draft_text = f"# {title}\n\n{body}"
    draft_path = project_root / "tmp" / f"{args.topic_id}-draft.md"
    draft_path.write_text(draft_text, encoding="utf-8")

    payload = {
        "pass": True,
        "passed": [f"assembled {len(ordered_sections)} sections"],
        "issues": [],
        "warnings": [f"inserted canonical headings for sections: {', '.join(repaired_headings)}"] if repaired_headings else [],
        "file": str(draft_path),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
