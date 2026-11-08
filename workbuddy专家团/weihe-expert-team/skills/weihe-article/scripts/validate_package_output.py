import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from article_quality_gates import (
    evaluate_discourse_flaws,
    evaluate_reader_accessibility,
    evaluate_structure_mismatch,
    package_output_path,
    resolve_package_sections,
    split_section_blocks,
)
from compiler_lib import build_project_dir, read_json


MIN_CHAR_RATIO = 0.05
MAX_CHAR_RATIO = 2.60


def clean_length(text: str) -> int:
    return len(re.sub(r"[\s#>*`\-\[\]\(\)\|]", "", text))


def evaluate_tutorial_contract(block: str, section: dict) -> list[str]:
    issues: list[str] = []
    warnings: list[str] = []
    mode = section.get("recommended_presentation", "none")
    if mode != "procedural-steps":
        return issues
    required_markers = ["前提", "操作", "预期", "失败", "排查", "下一步"]
    marker_hits = sum(1 for marker in required_markers if marker in block)
    if marker_hits < 2 and "|" not in block:
        issues.append(f"tutorial step structure too weak: {section['heading']}")
    return issues


def validate_article_package(project_root: Path, topic_id: str, package_id: str) -> dict:
    project_dir = build_project_dir(project_root, topic_id)
    packages = read_json(project_dir / "article-packages.json", {"packages": []})
    manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    workflow_profile = read_json(project_dir / "workflow-profile.json", {"strategy": ""})
    package_output = package_output_path(project_root, topic_id, package_id)

    package = next((item for item in packages.get("packages", []) if item.get("package_id") == package_id), None)
    if package is None:
        return {
            "pass": False,
            "passed": [],
            "issues": [f"package not found: {package_id}"],
            "file": str(package_output),
        }
    if not package_output.exists():
        return {
            "pass": False,
            "passed": [],
            "issues": [f"package output missing: {package_output}"],
            "file": str(package_output),
        }

    text = package_output.read_text(encoding="utf-8")
    blocks = split_section_blocks(text)
    issues: list[str] = []
    warnings: list[str] = []
    passed: list[str] = []
    section_map = {section["section_id"]: section for section in manifest.get("sections", [])}
    expected_ids = package.get("section_ids", [])

    if len(blocks) < len(expected_ids):
        issues.append(f"section block count too small: actual={len(blocks)} expected={len(expected_ids)}")

    for index, section_id in enumerate(expected_ids):
        section = section_map.get(section_id)
        if not section:
            issues.append(f"unknown section id: {section_id}")
            continue
        if index >= len(blocks):
            issues.append(f"missing section block for: {section['heading']}")
            continue

        observed_heading, block = blocks[index]
        actual_chars = clean_length(block)
        target_chars = int(section.get("target_word_count", 0) or 0)
        if target_chars and "附录" not in section["heading"]:
            ratio = actual_chars / max(target_chars, 1)
            if ratio < MIN_CHAR_RATIO or ratio > MAX_CHAR_RATIO:
                warnings.append(
                    f"section length out of range: expected={section['heading']} observed={observed_heading} actual={actual_chars} target={target_chars} ratio={ratio:.2f}"
                )
        if workflow_profile.get("strategy") == "teaching-playbook":
            issues.extend(evaluate_tutorial_contract(block, section))
        passed.append(f"validated: expected={section['heading']} observed={observed_heading}")

    package_sections, _ = resolve_package_sections(project_root, topic_id, package_id)
    accessibility_passed, accessibility_issues = evaluate_reader_accessibility(text, package_sections)
    structure_passed, structure_issues = evaluate_structure_mismatch(text, package_sections)
    discourse_passed, discourse_issues = evaluate_discourse_flaws(text, package_sections)
    passed.extend(accessibility_passed)
    passed.extend(structure_passed)
    passed.extend(discourse_passed)
    warnings.extend(accessibility_issues)
    warnings.extend(structure_issues)
    warnings.extend(discourse_issues)

    return {
        "pass": not issues,
        "passed": passed,
        "issues": issues,
        "warnings": warnings,
        "file": str(package_output),
        "package_id": package_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate deterministic package outputs")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--mode", default="article")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    if args.mode != "article":
        payload = {
            "pass": False,
            "passed": [],
            "issues": [f"unsupported mode: {args.mode}"],
            "file": "",
        }
    else:
        payload = validate_article_package(project_root, args.topic_id, args.package_id)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload["pass"] else 1)


if __name__ == "__main__":
    main()
