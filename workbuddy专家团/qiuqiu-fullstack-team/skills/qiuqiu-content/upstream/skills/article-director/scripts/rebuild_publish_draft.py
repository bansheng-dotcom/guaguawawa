import argparse
import re
from pathlib import Path


SECTION_ORDER = [
    "标题",
    "读者画像",
    "读者已有基础",
    "读者读完想得到什么",
    "一、这篇文章到底在回答什么问题：为什么“Handoff”值得单独讲？",
    "二、Handoff 的最小定义是什么：到底转移了什么？",
    "三、Handoff 和 Supervisor、Router、Tool Calling 到底有什么区别？",
    "误解 1：Handoff 就是把任务分配给另一个 Agent",
    "误解 2：Handoff 就是把上下文转发过去",
    "误解 3：有了 Supervisor 就等于有了 Handoff",
    "误解 4：Handoff 和 Router 是一回事",
    "误解 5：模型足够强就不怕交接失败",
    "误解 6：多 Agent + Handoff 一定比单 Agent 高级",
    "四、为什么 Handoff 难：交接不是“发消息”，而是状态和责任的迁移",
    "五、一个好的 Handoff 机制应当长什么样？",
    "六、真实系统里 Handoff 常见怎么失败？",
    "七、什么场景适合 Handoff，什么场景不适合？",
    "八、如果把 Supervisor 看作“指挥”，那 Handoff 更像什么？",
    "九、文章收束：一句话怎么定义 Handoff，以及读者该带走什么判断框架？",
    "上下游知识连接",
    "附表 1：相邻概念判别矩阵",
    "附表 2：Handoff 最小信息清单",
    "附表 3：Handoff 失败模式清单",
]

DROP_HEADINGS = {
    "上游知识",
    "横向对比对象",
    "下游可延伸主题",
    "常见误解",
    "名词预扫描",
    "可补充的图表/附表建议（仅作为写作钩子，不展开正文）",
    "附录",
    "主要读者",
    "标题",
}

DROP_PATTERNS = [
    r"(?m)^问题：\s*$",
    r"(?m)^解决：\s*$",
    r"(?m)^结果：\s*$",
    r"(?m)^问题：\s*-\s*.*$",
    r"(?m)^解决：\s*-\s*.*$",
    r"(?m)^结果：\s*-\s*.*$",
    r"(?m)^-\s+这一节要处理的问题是：.*$",
    r"(?m)^-\s+先把判断维度拆开，再决定怎么组织后续内容。*$",
    r"(?m)^-\s+这样更容易让读者看清问题和解法的对应关系。*$",
    r"(?m)^这一段需要回到上游.*$",
    r"(?m)^> 按用户要求不扩写正文.*$",
    r"(?m)^-\s+先确认这一节要比较或判断的对象.*$",
    r"(?m)^-\s+再写清关键边界或限制条件.*$",
    r"(?m)^-\s+最后给出读者可直接带走的判断点.*$",
]


def split_sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^##\s+", text)
    sections: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        sections.append((heading, body))
    return sections


def clean_body(body: str) -> str:
    cleaned = body
    for pattern in DROP_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned)
    cleaned = re.sub(r"(?m)^-\s+任务目标\s*$", "", cleaned)
    cleaned = re.sub(r"(?m)^-\s+交接触发条件\s*$", "", cleaned)
    cleaned = cleaned.replace(
        "近年的 agent 研究和工程实践反复指向同一个判断：",
        "从不少 agent 实现的演化方向看，可以观察到一个共同趋势：",
    )
    cleaned = cleaned.replace(
        "很多开源框架的演化方向也一致：",
        "不少开源框架的演化方向也比较一致：",
    )
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def transform_section(heading: str, body: str) -> str:
    cleaned = clean_body(body)
    if heading == "三、Handoff 和 Supervisor、Router、Tool Calling 到底有什么区别？":
        replacement = """| 概念 | 谁做决定 | 谁持有控制权 | 是否切换处理主体 | 谁对结果负责 |
| --- | --- | --- | --- | --- |
| Supervisor | 上层协调者 | 仍在总控一侧 | 不一定 | 总控或其所在系统 |
| Router | 路由规则或分类器 | 被选中的处理路径 | 通常没有 | 实际处理者 |
| Tool Calling | 当前主体 | 当前主体 | 否 | 当前主体 |
| Handoff | 当前主体或控制系统 | 接手方 | 是 | 接手方 |"""
        cleaned = re.sub(
            r"(?ms)^\| 比较维度 \| 说明 \|.*?\n\n",
            replacement + "\n\n",
            cleaned,
            count=1,
        )
    if heading.startswith("误解 "):
        cleaned = re.sub(
            r"(?ms)^很多人读到这里时，真正卡住的往往不是结论对不对，而是眼前这个问题到底该怎么判断。\n\n",
            "",
            cleaned,
            count=1,
        )
    if heading in {"附表 1：相邻概念判别矩阵", "附表 2：Handoff 最小信息清单", "附表 3：Handoff 失败模式清单"}:
        cleaned = re.sub(
            r"(?ms)^很多人读到这里时，真正卡住的往往不是结论对不对，而是眼前这个问题到底该怎么判断。\n\n",
            "",
            cleaned,
            count=1,
        )
        cleaned = re.sub(
            r"(?ms)^这里先把这几个词说清楚：.*?\n\n",
            "",
            cleaned,
            count=2,
        )
    return cleaned


def extract_title_from_sections(section_map: dict[str, str]) -> str:
    raw = section_map.get("标题", "").strip()
    if not raw:
        return "上一篇讲了 Supervisor，这一篇讲 Handoff：AI 之间到底怎么交接任务"
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return lines[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild a publish-ready article draft from final package outputs")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    output_root = project_root / "skills" / "article-director" / "outputs" / args.topic_id

    section_map: dict[str, str] = {}
    for idx in range(1, 7):
        path = output_root / f"final-package-editor-package-0{idx}" / "output.md"
        if not path.exists():
            continue
        for heading, body in split_sections(path.read_text(encoding="utf-8")):
            if heading in DROP_HEADINGS:
                continue
            section_map.setdefault(heading, transform_section(heading, body))

    title = extract_title_from_sections(section_map)

    ordered_blocks: list[str] = []
    for heading in SECTION_ORDER:
        if heading == "标题":
            continue
        body = section_map.get(heading, "").strip()
        if not body:
            continue
        ordered_blocks.append(f"## {heading}\n\n{body}".strip())

    final_text = f"# {title}\n\n" + "\n\n".join(ordered_blocks).strip() + "\n"
    draft_path = project_root / "tmp" / f"{args.topic_id}-draft.md"
    draft_path.write_text(final_text, encoding="utf-8")
    print(draft_path)


if __name__ == "__main__":
    main()
