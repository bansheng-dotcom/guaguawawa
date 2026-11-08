import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from article_quality_gates import split_section_blocks
from compiler_lib import build_project_dir, read_json, write_json


OPTIONAL_FINAL_HEADINGS = {
    "标题",
    "读者画像",
    "读者已有基础",
    "读者读完想得到什么",
    "主要读者",
    "常见误解",
    "误解 1：Handoff 就是把任务分配给另一个 Agent",
    "误解 2：Handoff 就是把上下文转发过去",
    "误解 3：有了 Supervisor 就等于有了 Handoff",
    "误解 4：Handoff 和 Router 是一回事",
    "误解 5：模型足够强就不怕交接失败",
    "误解 6：多 Agent + Handoff 一定比单 Agent 高级",
    "上游知识",
    "横向对比对象",
    "下游可延伸主题",
    "可补充的图表/附表建议（仅作为写作钩子，不展开正文）",
    "名词预扫描",
}

ALLOWED_FINAL_ONLY_HEADINGS = {
    "通过脚本设计 Handoff：真正落地时要写哪些东西",
    "如何用提示词和 AI 说明建立 Handoff",
    "常见误解：为什么很多系统“看起来像交接”，其实不是",
}


def normalize_heading(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def is_appendix_heading(heading: str) -> bool:
    normalized = normalize_heading(heading)
    without_number = re.sub(r"^\d+[.、]\s*", "", normalized)
    return without_number.startswith(("附录", "延伸阅读", "参考资料"))


def strip_heading(block: str) -> str:
    lines = block.splitlines()
    if lines and re.match(r"^#{1,3}\s+", lines[0]):
        lines = lines[1:]
    return "\n".join(lines).strip()


def split_h2_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        heading_match = re.match(r"^##\s+(.+?)\s*$", line)
        if heading_match:
            if current_heading:
                blocks.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = heading_match.group(1).strip()
            current_lines = [line]
        elif current_heading:
            current_lines.append(line)
    if current_heading:
        blocks.append((current_heading, "\n".join(current_lines).strip()))
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate that the finalized draft covers every planned section")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--stage", default="finalize-draft")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    draft_path = project_root / "tmp" / f"{args.topic_id}-draft.md"
    draft_text = draft_path.read_text(encoding="utf-8") if draft_path.exists() else ""

    body_text = re.sub(r"\A\s*#\s+.*(?:\r?\n)+", "", draft_text, count=1)
    all_blocks = split_section_blocks(body_text)
    all_headings = [normalize_heading(heading) for heading, _ in all_blocks]
    actual_blocks = split_h2_blocks(body_text)
    actual_headings = [normalize_heading(heading) for heading, _ in actual_blocks]
    expected_headings = [
        heading
        for heading in (normalize_heading(section.get("heading", "")) for section in manifest.get("sections", []))
        if heading and not is_appendix_heading(heading) and heading not in OPTIONAL_FINAL_HEADINGS
    ]
    appendix_index = next((index for index, heading in enumerate(actual_headings) if is_appendix_heading(heading)), len(actual_headings))
    actual_main_headings = actual_headings[:appendix_index]
    all_appendix_index = next((index for index, heading in enumerate(all_headings) if is_appendix_heading(heading)), len(all_headings))
    appendix_headings = all_headings[all_appendix_index:]
    actual_main_blocks = actual_blocks[:appendix_index]

    missing = [heading for heading in expected_headings if heading and heading not in actual_main_headings]
    unexpected_main = [
        heading
        for heading in actual_main_headings
        if heading and heading not in expected_headings and heading not in ALLOWED_FINAL_ONLY_HEADINGS
    ]
    issues: list[str] = []
    passed: list[str] = []

    if missing:
        issues.append(f"missing finalized sections: {', '.join(missing)}")
    else:
        passed.append(f"validated {len(expected_headings)} finalized sections")

    if unexpected_main:
        issues.append(f"unexpected main sections: {', '.join(unexpected_main)}")

    if not missing and not unexpected_main and actual_main_headings != expected_headings:
        issues.append("finalized section order does not match section-manifest order")

    empty_sections = [
        heading
        for heading, block in actual_main_blocks
        if normalize_heading(heading) in expected_headings and not strip_heading(block)
    ]
    if empty_sections:
        issues.append(f"empty finalized sections: {', '.join(empty_sections)}")

    if "[...truncated...]" in draft_text:
        issues.append("finalized draft still contains truncation marker")

    output_path = project_dir / "final-draft-integrity-01" / "output.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pass": not issues,
        "passed": passed,
        "issues": issues,
        "file": str(draft_path),
        "expected_main_section_count": len(expected_headings),
        "actual_main_section_count": len(actual_main_headings),
        "appendix_heading_count": len(appendix_headings),
        "actual_total_heading_count": len(all_headings),
        "stage": args.stage,
    }
    write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload["pass"] else 1)


if __name__ == "__main__":
    main()
