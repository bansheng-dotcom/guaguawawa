import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from compiler_lib import build_project_dir, read_json


def _compact(value: object, limit: int = 260) -> str:
    text = str(value or "").strip()
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _bullet_list(values: object) -> list[str]:
    if isinstance(values, list):
        return [_compact(item, 180) for item in values if _compact(item, 180)]
    value = _compact(values, 180)
    return [value] if value else []


def _section_line(section: dict | None) -> str:
    if not section:
        return "无"
    heading = _compact(section.get("heading"), 120)
    claim = _compact(section.get("claim"), 160)
    return f"{heading}｜{claim}" if claim else heading


def _render_spine(
    topic_id: str,
    section: dict,
    previous_section: dict | None,
    next_section: dict | None,
    article_requirements: dict,
) -> str:
    section_id = str(section.get("section_id") or "")
    heading = _compact(section.get("heading"), 160)
    claim = _compact(section.get("claim"), 260)
    explanation = _compact(section.get("explanation"), 360)
    evidence = _compact(section.get("evidence"), 300)
    reader_stuck = _compact(section.get("reader_stuck"), 300)
    upstream_downstream = _compact(section.get("upstream_downstream"), 360)
    logic_difficulty = _compact(section.get("logic_difficulty"), 300)
    example = _compact(section.get("example"), 300)
    prompt_example = _compact(section.get("prompt_example"), 360)
    before_after = _compact(section.get("before_after"), 300)
    writer_actionable = _compact(section.get("writer_actionable"), 360)
    candidate_unit = _compact(section.get("candidate_unit"), 260)
    body_text = _compact(section.get("body_text"), 700)
    target_word_count = section.get("target_word_count", "")
    presentation = _compact(section.get("recommended_presentation"), 80)
    presentation_hint = _compact(section.get("presentation_hint"), 180)
    discourse_order = _bullet_list(section.get("required_discourse_order"))
    must_answer_first = _bullet_list(section.get("must_answer_first"))
    article_goal = _compact(
        article_requirements.get("purpose")
        or article_requirements.get("goal")
        or article_requirements.get("title")
        or "",
        180,
    )

    lines = [
        f"# Argument Spine: {section_id}",
        "",
        "## 基本信息",
        f"- topic_id: {topic_id}",
        f"- section_id: {section_id}",
        f"- heading: {heading}",
        f"- article_goal: {article_goal or '未单独声明，按 article-requirements.json 与细纲执行'}",
        f"- target_word_count: {target_word_count or '未声明'}",
        f"- recommended_presentation: {presentation or '按内容自然选择'}",
        f"- presentation_hint: {presentation_hint or '按细纲内容和读者卡点自然选择'}",
        "",
        "## 上下文承接",
        f"- previous_section: {_section_line(previous_section)}",
        f"- current_claim: {claim or '按细纲 body_text 提取本节主判断'}",
        f"- next_section: {_section_line(next_section)}",
        f"- outline_upstream_downstream: {upstream_downstream or '细纲未声明，按前后 section 和本节材料处理'}",
        "",
        "## 本节要解决的读者卡点",
        f"- {reader_stuck or explanation or '解释本节标题里的核心问题，让小白知道为什么要继续读。'}",
        "",
        "## 本节推理链",
        "- 先承接上一节已经解决的问题，不重新开一个空泛场景。",
        "- 再指出本节的核心判断，并说明这个判断从哪里来。",
        "- 只展开读者理解本节判断所必需的中间推理：前提是什么、为什么会这样、漏掉会发生什么、它对实际操作有什么影响。",
        "- 用本节已有案例、字段、口径、提示词或表格支撑推理，不新增未在细纲出现的新主张。",
        "- 收束到下一步操作、边界或下一节问题，不只写一句总结。",
    ]
    if must_answer_first:
        lines.extend(["", "## 必须先回答"])
        lines.extend([f"- {item}" for item in must_answer_first])
    if discourse_order:
        lines.extend(["", "## 推荐展开顺序"])
        lines.extend([f"- {item}" for item in discourse_order])

    lines.extend(
        [
            "",
            "## 可用材料",
            f"- evidence: {evidence or '按细纲材料和已确认来源处理'}",
            f"- example: {example or '细纲未声明具体案例，writer 不得自行新增关键案例'}",
            f"- prompt_example: {prompt_example or '细纲未声明提示词样例；如正文需要，先标记上游缺口'}",
            f"- before_after: {before_after or '细纲未声明 before/after；如正文需要，先标记上游缺口'}",
            f"- logic_difficulty: {logic_difficulty or '按本节读者卡点处理'}",
            f"- writer_actionable: {writer_actionable or '按细纲主张、示例和边界写作，不新增主结论'}",
            f"- candidate_unit: {candidate_unit or '按本节细纲语义单元做内部候选选择'}",
            f"- detailed_outline_material: {body_text or '读取 tmp/{topic_id}-detailed-outline.md'}",
            "",
            "## 推理深度与压缩标记",
            "- 按本节功能决定推理深度：开篇、定义、过渡、总结、表格、清单用 light；机制、边界、方法用 medium；核心争议或关键判断才用 deep。",
            "- 输出时区分 must_keep 与 compressible：必须保留判断、例子、证据、边界；重复解释、铺垫、旁支背景可压缩。",
            "- 不要求每节固定保留长推理段；只有 medium/deep 且读者不展开就无法理解时，才保留完整自然段推理。",
            "- 不要把同一条必要因果链拆成连续短判断。短句只用于判断、停顿或转向。",
            "- 个人文风和逻辑链优先于去 AI 味；AI 味只是表达约束，不能把必要推理链切碎。",
            "",
            "## 输出边界",
            "- 只写本节，不改标题层级。",
            "- 不新增本节之外的论文、工具或新概念。",
            "- 不输出本 argument-spine 的标签和字段名。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a per-section argument spine for article writing")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--section-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    article_requirements = read_json(project_dir / "article-requirements.json", {})
    sections = [section for section in manifest.get("sections", []) if section.get("section_id")]
    index = next((idx for idx, section in enumerate(sections) if str(section.get("section_id")) == args.section_id), -1)
    if index < 0:
        raise SystemExit(f"section not found: {args.section_id}")

    output_dir = project_dir / "sections" / args.section_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_text = _render_spine(
        args.topic_id,
        sections[index],
        sections[index - 1] if index > 0 else None,
        sections[index + 1] if index + 1 < len(sections) else None,
        article_requirements,
    )
    output_path = output_dir / "argument-spine.md"
    output_path.write_text(output_text, encoding="utf-8")
    print(output_text)


if __name__ == "__main__":
    main()
