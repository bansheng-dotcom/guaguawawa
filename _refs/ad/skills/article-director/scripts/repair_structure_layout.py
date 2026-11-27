import argparse
import json
import re
from pathlib import Path


PLACEHOLDER_TEXT = "这一段需要回到上游节点补写，目前先保留为空。"


def split_sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^##\s+", text)
    sections: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        heading = f"## {lines[0].strip()}"
        body = "\n".join(lines[1:]).strip()
        sections.append((heading, body))
    return sections


def heading_key(heading: str) -> str:
    return f"## {heading}"


def align_section_bodies(blocks: list[tuple[str, str]], headings: list[str]) -> list[str]:
    aligned: list[str] = []
    cursor = 0
    for heading in headings:
        key = heading_key(heading)
        body = ""
        for index in range(cursor, len(blocks)):
            block_heading, block_body = blocks[index]
            if block_heading == key:
                body = block_body
                cursor = index + 1
                break
        aligned.append(body)
    return aligned


def has_markdown_table(body: str) -> bool:
    lines = [line for line in body.splitlines() if "|" in line]
    return len(lines) >= 2


def count_list_markers(body: str) -> int:
    return len(re.findall(r"(?mi)^\s*(?:[-*]|\d+\.)\s+", body))


def extract_section_lines(meta_text: str, anchor: str) -> list[str]:
    lines = meta_text.splitlines()
    captured: list[str] = []
    in_anchor = False
    stop_markers = {"论点:", "需要解释:", "需要引用:", "待研究:"}
    for raw_line in lines:
        stripped = raw_line.strip()
        if not in_anchor:
            if stripped == anchor:
                in_anchor = True
            continue
        if stripped in stop_markers:
            break
        if stripped.startswith("- "):
            captured.append(stripped[2:].strip())
    return captured


def build_comparison_table(section_heading: str, section_meta: dict) -> str:
    explain_items = extract_section_lines(section_meta.get("body_text", ""), "需要解释:")
    if not explain_items:
        explain_items = extract_section_lines(section_meta.get("body_text", ""), "论点:")
    if len(explain_items) < 2:
        explain_items = [
            f"先看这一节要区分的对象是什么：{section_heading}",
            "再看它们在控制权、责任边界或上下文处理上有什么差别",
            "最后给出这一节真正想让读者带走的判断标准",
        ]
    rows = ["| 比较维度 | 说明 |", "| --- | --- |"]
    for index, item in enumerate(explain_items[:4], start=1):
        rows.append(f"| 第{index}点 | {item} |")
    return "\n".join(rows)


def build_numbered_block(section_meta: dict, minimum: int = 3) -> str:
    items = extract_section_lines(section_meta.get("body_text", ""), "论点:")
    if len(items) < minimum:
        items.extend(extract_section_lines(section_meta.get("body_text", ""), "需要解释:"))
    if not items:
        items = [
            "先把这一节真正要解决的问题说清楚",
            "再把最关键的判断维度拆开",
            "最后收束成读者能直接使用的结论",
        ]
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items[: max(minimum, min(len(items), 5))], start=1))


def build_checklist(section_meta: dict) -> str:
    items = extract_section_lines(section_meta.get("body_text", ""), "需要解释:")
    if not items:
        items = extract_section_lines(section_meta.get("body_text", ""), "论点:")
    if not items:
        items = [
            "先确认这一节要比较或判断的对象",
            "再写清关键边界或限制条件",
            "最后给出读者可直接带走的判断点",
        ]
    return "\n".join(f"- {item}" for item in items[:5])


def build_problem_solution(section_heading: str, section_meta: dict) -> str:
    claim_items = extract_section_lines(section_meta.get("body_text", ""), "论点:")
    explain_items = extract_section_lines(section_meta.get("body_text", ""), "需要解释:")
    problem = claim_items[0] if claim_items else f"这一节要处理的问题是：{section_heading}"
    solution = explain_items[0] if explain_items else "先把判断维度拆开，再决定怎么组织后续内容。"
    result = claim_items[1] if len(claim_items) > 1 else "这样更容易让读者看清问题和解法的对应关系。"
    return "\n".join(
        [
            "问题：",
            f"- {problem}",
            "",
            "解决：",
            f"- {solution}",
            "",
            "结果：",
            f"- {result}",
        ]
    )


def repair_body(section_heading: str, body: str, section_meta: dict) -> str:
    mode = section_meta.get("recommended_presentation", "prose")
    cleaned = body.strip()

    if mode == "comparison-table":
        if has_markdown_table(cleaned):
            return cleaned
        table = build_comparison_table(section_heading, section_meta)
        return f"{table}\n\n{cleaned}".strip() if table else cleaned

    if mode == "numbered-reasons":
        minimum = max(2, int(section_meta.get("parallel_point_count", 2) or 2))
        if count_list_markers(cleaned) >= minimum:
            return cleaned
        numbered = build_numbered_block(section_meta, minimum=minimum)
        return f"{numbered}\n\n{cleaned}".strip() if numbered else cleaned

    if mode == "checklist":
        if count_list_markers(cleaned) >= 3:
            return cleaned
        checklist = build_checklist(section_meta)
        return f"{checklist}\n\n{cleaned}".strip() if checklist else cleaned

    if mode == "problem-solution-blocks":
        if ("问题" in cleaned and "解决" in cleaned) or ("错误做法" in cleaned and "正确做法" in cleaned):
            return cleaned
        scaffold = build_problem_solution(section_heading, section_meta)
        return f"{scaffold}\n\n{cleaned}".strip()

    return cleaned


def load_section_manifest(project_root: Path, topic_id: str) -> dict[str, dict]:
    manifest_path = project_root / "skills" / "article-director" / "outputs" / topic_id / "section-manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    return {item["section_id"]: item for item in data["sections"]}


def load_package(project_root: Path, topic_id: str, package_id: str) -> dict:
    packages_path = project_root / "skills" / "article-director" / "outputs" / topic_id / "article-packages.json"
    data = json.loads(packages_path.read_text(encoding="utf-8-sig"))
    for pkg in data["packages"]:
        if pkg["package_id"] == package_id:
            return pkg
    raise ValueError(f"package not found: {package_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministically repair structure layout for a package output")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--stage", default="structure-editor")
    parser.add_argument("--fallback-stage", default="deep-dive-researcher")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    base_dir = project_root / "skills" / "article-director" / "outputs" / args.topic_id
    output_path = base_dir / f"{args.stage}-{args.package_id}" / "output.md"
    fallback_path = base_dir / f"{args.fallback_stage}-{args.package_id}" / "output.md"

    package = load_package(project_root, args.topic_id, args.package_id)
    section_meta = load_section_manifest(project_root, args.topic_id)

    current_sections = split_sections(output_path.read_text(encoding="utf-8")) if output_path.exists() else []
    fallback_sections = split_sections(fallback_path.read_text(encoding="utf-8")) if fallback_path.exists() else []
    current_bodies = align_section_bodies(current_sections, package["section_headings"])
    fallback_bodies = align_section_bodies(fallback_sections, package["section_headings"])

    repaired_blocks: list[str] = []
    for index, heading in enumerate(package["section_headings"]):
        key = heading_key(heading)
        section_id = package["section_ids"][index]
        body = current_bodies[index]
        if not body or body.strip() == PLACEHOLDER_TEXT:
            body = fallback_bodies[index]
        if not body:
            body = PLACEHOLDER_TEXT
        repaired = repair_body(heading, body, section_meta.get(section_id, {}))
        repaired_blocks.append(f"{key}\n\n{repaired}".strip())

    output_path.write_text("\n\n".join(repaired_blocks).strip() + "\n", encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
