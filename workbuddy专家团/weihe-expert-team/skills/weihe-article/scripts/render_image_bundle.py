import argparse
import json
import sys
from datetime import datetime
from html import escape
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json, write_json


WIDTH = 1600
HEIGHT = 900
BG = "#f7f1e8"
INK = "#1f2933"
TEAL = "#0f766e"
ORANGE = "#c65d21"
BLUE = "#2457a5"
OLIVE = "#5f6f52"
CARD = "#fffdf8"
GRID = "#dccfb8"


SUPERVISOR_IMAGE_SPECS = {
    "image-01": {
        "design_key": "agent-chaos-sources",
        "title": "多 Agent 为什么一多就容易乱",
        "purpose": "把角色增多后最常见的 4 类失控来源一次说清。",
    },
    "image-02": {
        "design_key": "supervisor-evolution",
        "title": "数据分析 Skill 如何长出 Supervisor 雏形",
        "purpose": "用第 4 层到第 6 层的演进，说明总控能力是怎么一步步出现的。",
    },
    "image-03": {
        "design_key": "supervisor-vs-others",
        "title": "Supervisor 和 Router / Pipeline / Swarm 有什么不同",
        "purpose": "并列比较四种组织方式的控制逻辑，突出 Supervisor 的中心调度与回收能力。",
    },
    "image-06": {
        "design_key": "supervisor-when-to-use",
        "title": "什么时候该上 Supervisor，什么时候先别上",
        "purpose": "把适用条件和不适用条件做成一眼能判断的决策图。",
    },
}


def svg_header() -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>',
        '<style>',
        'text { font-family: "Source Han Sans SC", "Microsoft YaHei", sans-serif; fill: #1f2933; }',
        '.title { font-size: 42px; font-weight: 700; }',
        '.subtitle { font-size: 20px; fill: #475569; }',
        '.box-title { font-size: 24px; font-weight: 700; }',
        '.body { font-size: 20px; }',
        '.small { font-size: 18px; fill: #475569; }',
        '</style>',
    ]


def svg_footer() -> list[str]:
    return ["</svg>"]


def rect(x: int, y: int, w: int, h: int, fill: str, stroke: str = GRID, radius: int = 24) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'


def text(x: int, y: int, value: str, cls: str = "body", anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(value)}</text>'


def line(x1: int, y1: int, x2: int, y2: int, stroke: str = INK, width: int = 3, marker: bool = False) -> str:
    attrs = ' marker-end="url(#arrow)"' if marker else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}"{attrs}/>'


def defs() -> str:
    return """
<defs>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
    <path d="M0,0 L0,6 L9,3 z" fill="#1f2933"/>
  </marker>
</defs>
"""


def wrap_lines(value: str, line_chars: int = 18) -> list[str]:
    value = value.strip()
    if len(value) <= line_chars:
        return [value]
    lines = []
    for start in range(0, len(value), line_chars):
        lines.append(value[start : start + line_chars])
    return lines


def text_block(x: int, y: int, value: str, cls: str = "body", line_height: int = 28) -> list[str]:
    return [text(x, y + idx * line_height, line, cls) for idx, line in enumerate(wrap_lines(value))]


def image_value(image: dict, key: str, default: str = "") -> str:
    value = image.get(key, default)
    if value is None:
        return default
    return str(value)


def normalize_image_spec(image: dict) -> dict:
    normalized = dict(image)
    topic_id = image_value(image, "topic_id")
    image_id = image_value(image, "image_id")
    if topic_id == "supervisor-mode" and image_id in SUPERVISOR_IMAGE_SPECS:
        normalized.update({k: v for k, v in SUPERVISOR_IMAGE_SPECS[image_id].items() if not normalized.get(k)})
    if not normalized.get("title"):
        normalized["title"] = image_value(image, "target_heading", image_id or "图示")
    if not normalized.get("purpose"):
        normalized["purpose"] = image_value(image, "insert_after_heading", "辅助说明正文关键关系")
    if not normalized.get("design_key"):
        normalized["design_key"] = image_value(image, "kind", "diagram")
    return normalized


def compression_callout(summary: dict) -> tuple[int, int, float]:
    case = summary.get("compression_case", {})
    before = int(case.get("qwen_normal", {}).get("tok", 0) or 0)
    after = int(case.get("qwen_caveman", {}).get("tok", 0) or 0)
    if before and after and before > after:
        ratio = (before - after) / before
        return before, after, round(ratio * 100, 1)
    best_before = 0
    best_after = 0
    best_ratio = 0.0
    for item in summary.get("compression", []):
        before = int(item.get("qwen_normal", {}).get("tok", 0) or 0)
        after = int(item.get("qwen_caveman", {}).get("tok", 0) or 0)
        if before and after and before > after:
            ratio = (before - after) / before
            if ratio > best_ratio:
                best_before, best_after, best_ratio = before, after, ratio
    return best_before, best_after, round(best_ratio * 100, 1)


def render_workflow(image: dict) -> list[str]:
    labels = [
        ("数据加载", "低成本模型", 120, 240, OLIVE),
        ("指标计算", "低成本模型", 410, 240, OLIVE),
        ("趋势分析", "平衡模型", 700, 240, BLUE),
        ("维度切片", "平衡模型", 990, 240, BLUE),
        ("异常解释", "强模型", 1280, 240, ORANGE),
        ("图表说明", "低成本模型", 265, 560, TEAL),
        ("报告汇总", "平衡模型", 700, 560, BLUE),
        ("最终审查", "强模型", 1135, 560, ORANGE),
    ]
    lines = svg_header() + [defs(), text(90, 95, image["title"], "title"), text(90, 138, image["purpose"], "subtitle")]
    for name, role, x, y, color in labels:
        lines.append(rect(x, y, 210, 110, CARD, color))
        lines.append(text(x + 28, y + 44, name, "box-title"))
        lines.append(text(x + 28, y + 82, role, "small"))
    arrow_pairs = [
        (330, 295, 410, 295),
        (620, 295, 700, 295),
        (910, 295, 990, 295),
        (1200, 295, 1280, 295),
        (1385, 350, 1385, 470),
        (1240, 615, 1135, 615),
        (910, 615, 700, 615),
        (475, 615, 265, 615),
    ]
    for x1, y1, x2, y2 in arrow_pairs:
        lines.append(line(x1, y1, x2, y2, marker=True))
    lines.extend(text_block(90, 790, "原则：开放式判断交给强模型，重复执行交给平衡/低成本模型，所有关键结论回到强模型复审。", "body"))
    lines.extend(svg_footer())
    return lines


def render_cost_quality(image: dict, summary: dict) -> list[str]:
    baseline = summary.get("baseline", {})
    scenarios = summary.get("scenarios", [])
    best = max(scenarios, key=lambda item: item.get("savings_pct_vs_baseline", -999), default={})
    before, after, ratio = compression_callout(summary)
    lines = svg_header() + [defs(), text(90, 95, image["title"], "title"), text(90, 138, image["purpose"], "subtitle")]
    lines.append(rect(90, 210, 650, 520, CARD, BLUE))
    lines.append(rect(860, 210, 650, 520, CARD, ORANGE))
    lines.append(text(130, 260, "只看单价时", "box-title"))
    lines.append(text(900, 260, "把三因子一起看时", "box-title"))

    left_items = [
        "模型单价更便宜",
        "但输出更长",
        "返工和升级次数上升",
        "总账不一定更省",
    ]
    right_items = [
        "先压输出长度",
        "再做任务分流",
        "最后给失败节点升级",
        "成本和质量更容易一起控制",
    ]
    for idx, item in enumerate(left_items):
        lines.append(text(145, 330 + idx * 80, f"{idx + 1}. {item}", "body"))
    for idx, item in enumerate(right_items):
        lines.append(text(915, 330 + idx * 80, f"{idx + 1}. {item}", "body"))

    lines.append(text(130, 610, f"基线成本: ${baseline.get('total_cost', 0):.4f}", "small"))
    lines.append(text(130, 640, f"最佳混合场景节省: {best.get('savings_pct_vs_baseline', 0):.2f}%", "small"))
    lines.append(text(900, 610, f"压缩案例: {before} -> {after} token", "small"))
    lines.append(text(900, 640, f"同任务 token 压缩比例: {ratio:.1f}%", "small"))
    lines.extend(svg_footer())
    return lines


def render_experiment_chart(image: dict, summary: dict) -> list[str]:
    baseline = summary.get("baseline", {})
    scenarios = summary.get("scenarios", [])
    bars = [baseline, *scenarios]
    max_cost = max([float(item.get("total_cost", 0) or 0) for item in bars] or [1.0])
    lines = svg_header() + [defs(), text(90, 95, image["title"], "title"), text(90, 138, image["purpose"], "subtitle")]
    lines.append(rect(90, 180, 1420, 650, CARD, TEAL))
    chart_x = 170
    chart_y = 720
    chart_h = 430
    bar_w = 120
    gap = 55
    lines.append(line(chart_x, 260, chart_x, chart_y, GRID, 2))
    lines.append(line(chart_x, chart_y, 1420, chart_y, GRID, 2))
    for idx, item in enumerate(bars):
        label = item.get("experiment", "baseline")
        cost = float(item.get("total_cost", 0) or 0)
        tokens = int(item.get("total_tokens", 0) or 0)
        bar_h = 0 if max_cost == 0 else int(cost / max_cost * chart_h)
        x = chart_x + 70 + idx * (bar_w + gap)
        y = chart_y - bar_h
        fill = ORANGE if label == "A3" else TEAL if label in {"baseline", ""} else BLUE
        lines.append(rect(x, y, bar_w, bar_h, fill, fill, 14))
        lines.append(text(x + bar_w / 2, chart_y + 40, label or "A1", "body", "middle"))
        lines.append(text(x + bar_w / 2, y - 14, f"${cost:.4f}", "small", "middle"))
        lines.append(text(x + bar_w / 2, y + bar_h + 70, f"{tokens} tok", "small", "middle"))
    lines.append(text(170, 240, "成本（美元）", "small"))
    before, after, ratio = compression_callout(summary)
    lines.append(text(980, 250, f"补充：同任务压缩 {before} -> {after} token，下降 {ratio:.1f}%", "body"))
    lines.extend(svg_footer())
    return lines


def render_routing(image: dict) -> list[str]:
    lines = svg_header() + [defs(), text(90, 95, image["title"], "title"), text(90, 138, image["purpose"], "subtitle")]
    nodes = [
        ("请求进入", 150, 250, TEAL),
        ("难度评分", 430, 250, BLUE),
        ("证据要求", 710, 250, BLUE),
        ("结构化程度", 990, 250, BLUE),
        ("低成本模型", 250, 560, OLIVE),
        ("平衡模型", 710, 560, TEAL),
        ("强模型", 1170, 560, ORANGE),
    ]
    for label, x, y, color in nodes:
        lines.append(rect(x, y, 220, 110, CARD, color))
        lines.append(text(x + 28, y + 62, label, "box-title"))
    for pair in [(370, 305, 430, 305), (650, 305, 710, 305), (930, 305, 990, 305)]:
        lines.append(line(*pair, marker=True))
    for pair in [(1100, 360, 1260, 560), (1080, 360, 820, 560), (1020, 360, 360, 560)]:
        lines.append(line(*pair, marker=True))
    lines.append(line(360, 615, 1170, 615, ORANGE, 3, True))
    lines.append(text(380, 665, "失败信号：缺引用、JSON 不合法、超字数、审查未过、事实校验失败 -> 升级", "body"))
    lines.extend(svg_footer())
    return lines


def render_agent_chaos(image: dict) -> list[str]:
    lines = svg_header() + [defs(), text(90, 95, image["title"], "title"), text(90, 138, image["purpose"], "subtitle")]
    lines.append(rect(90, 190, 1420, 620, CARD, ORANGE))
    cards = [
        ("任务边界不清", "同一个总任务，被不同角色各自理解成不同版本。", 140, 280),
        ("上下文乱传", "摘要替代原始事实，约束在交接中被压缩或丢失。", 790, 280),
        ("步骤失控", "前一步的小偏差，会被后面几步继续放大和包装。", 140, 520),
        ("失败没人兜底", "每个局部都像是对的，但没人停下来重查路线。", 790, 520),
    ]
    for title_value, body_value, x, y in cards:
        lines.append(rect(x, y, 560, 170, "#fffaf3", BLUE if x < 700 else TEAL))
        lines.append(text(x + 32, y + 50, title_value, "box-title"))
        lines.extend(text_block(x + 32, y + 96, body_value, "body"))
    lines.append(text(140, 760, "关键提醒：角色变多带来的不只是并行能力，还会带来更多交接点、状态转换和误差传播路径。", "body"))
    lines.extend(svg_footer())
    return lines


def render_supervisor_evolution(image: dict) -> list[str]:
    lines = svg_header() + [defs(), text(90, 95, image["title"], "title"), text(90, 138, image["purpose"], "subtitle")]
    stages = [
        ("第 4 层", "主 Agent + 副 Agent + Harness", ["开始分工", "有人验收"], 120, 250, OLIVE),
        ("第 5 层", "大脑 Agent + Plan 接口", ["先定框架", "再派任务"], 560, 250, BLUE),
        ("第 6 层", "异常发现后继续追问", ["会回看", "会补证据", "会迭代"], 1000, 250, ORANGE),
    ]
    lines.append(line(430, 395, 560, 395, marker=True))
    lines.append(line(870, 395, 1000, 395, marker=True))
    for stage_no, stage_title, bullets, x, y, color in stages:
        lines.append(rect(x, y, 340, 300, CARD, color))
        lines.append(text(x + 32, y + 54, stage_no, "small"))
        lines.append(text(x + 32, y + 102, stage_title, "box-title"))
        for idx, bullet in enumerate(bullets):
            lines.append(text(x + 36, y + 170 + idx * 42, f"{idx + 1}. {bullet}", "body"))
    lines.append(text(120, 700, "演进重点：不是角色越来越多，而是中心控制、结构化派活、硬校验和闭环追问逐步补齐。", "body"))
    lines.extend(svg_footer())
    return lines


def render_supervisor_comparison(image: dict) -> list[str]:
    lines = svg_header() + [defs(), text(90, 95, image["title"], "title"), text(90, 138, image["purpose"], "subtitle")]
    columns = [
        ("01 Router", "#3B82F6", "入口分流", "先判断给谁做"),
        ("02 Pipeline", "#10B981", "固定顺序", "按既定步骤直走"),
        ("03 Swarm", "#F59E0B", "分散协作", "角色彼此接力推进"),
        ("04 Supervisor", "#7C3AED", "中心调度", "能改派、回收、重规划"),
    ]
    start_x = 90
    width = 320
    gap = 25
    for idx, (name, color, label_a, label_b) in enumerate(columns):
        x = start_x + idx * (width + gap)
        lines.append(rect(x, 215, width, 520, CARD, color))
        lines.append(text(x + 28, 265, name, "box-title"))
        lines.append(text(x + 28, 310, label_a, "body"))
        lines.append(text(x + 28, 342, label_b, "small"))
        if idx == 0:
            lines.append(rect(x + 90, 405, 140, 56, "#eff6ff", color, 14))
            lines.append(text(x + 108, 440, "Input -> 路由规则", "small"))
            lines.append(line(x + 160, 461, x + 95, 545, color, 3, True))
            lines.append(line(x + 160, 461, x + 225, 545, color, 3, True))
        elif idx == 1:
            for step in range(3):
                box_x = x + 50 + step * 70
                lines.append(rect(box_x, 430, 90, 56, "#ecfdf5", color, 14))
                lines.append(text(box_x + 18, 465, f"步骤 {step + 1}", "small"))
                if step < 2:
                    lines.append(line(box_x + 90, 458, box_x + 118, 458, color, 3, True))
        elif idx == 2:
            points = [(x + 80, 430), (x + 200, 410), (x + 150, 545), (x + 255, 545)]
            for px, py in points:
                lines.append(rect(px, py, 72, 50, "#fffbeb", color, 12))
            lines.append(line(x + 116, 455, x + 205, 435, color, 3, True))
            lines.append(line(x + 220, 460, x + 186, 545, color, 3, True))
            lines.append(line(x + 150, 570, x + 255, 570, color, 3, True))
        else:
            lines.append(rect(x + 100, 385, 120, 62, "#f5f3ff", color, 16))
            lines.append(text(x + 120, 425, "Supervisor", "small"))
            worker_points = [(x + 45, 545), (x + 125, 605), (x + 210, 545)]
            for px, py in worker_points:
                lines.append(rect(px, py, 86, 52, "#faf5ff", color, 12))
                lines.append(line(x + 160, 447, px + 43, py, color, 3, True))
                lines.append(line(px + 43, py + 52, x + 160, 447, GRID, 2, False))
            lines.append(text(x + 46, 682, "持续收结果，再决定下一步", "small"))
    lines.append(text(90, 800, "读图方式：差别不在“有没有多个 Agent”，而在“谁在持续掌握全局状态并决定下一步”。", "body"))
    lines.extend(svg_footer())
    return lines


def render_supervisor_usage(image: dict) -> list[str]:
    lines = svg_header() + [defs(), text(90, 95, image["title"], "title"), text(90, 138, image["purpose"], "subtitle")]
    lines.append(rect(90, 210, 650, 560, CARD, TEAL))
    lines.append(rect(860, 210, 650, 560, CARD, ORANGE))
    lines.append(text(130, 270, "适合上 Supervisor", "box-title"))
    lines.append(text(900, 270, "可以先不上", "box-title"))
    left_items = ["长流程，多次交接", "多角色、多工具一起协作", "中间结果必须检查", "经常要回退或重规划"]
    right_items = ["简单单步任务", "固定顺序就能稳定解决", "角色边界本来就不清", "加调度层只会抬高成本"]
    for idx, item in enumerate(left_items):
        lines.append(text(140, 360 + idx * 86, f"{idx + 1}. {item}", "body"))
    for idx, item in enumerate(right_items):
        lines.append(text(910, 360 + idx * 86, f"{idx + 1}. {item}", "body"))
    lines.append(text(130, 690, "判断方法：先看会不会偏航，再看偏航后代价大不大。", "small"))
    lines.append(text(900, 690, "成本提醒：多一层监督，不会自动省 token，只有减少返工时才划算。", "small"))
    lines.extend(svg_footer())
    return lines


def render_svg(image: dict, summary: dict) -> list[str]:
    image = normalize_image_spec(image)
    design_key = image.get("design_key", "")
    if design_key == "agent-chaos-sources":
        return render_agent_chaos(image)
    if design_key == "supervisor-evolution":
        return render_supervisor_evolution(image)
    if design_key == "supervisor-vs-others":
        return render_supervisor_comparison(image)
    if design_key == "supervisor-when-to-use":
        return render_supervisor_usage(image)
    if design_key == "data-analysis-workflow":
        return render_workflow(image)
    if design_key == "cost-quality-rework":
        return render_cost_quality(image, summary)
    if design_key == "experiment-comparison":
        return render_experiment_chart(image, summary)
    return render_routing(image)


def filename_for(image: dict) -> str:
    image = normalize_image_spec(image)
    mapping = {
        "data-analysis-workflow": "data-analysis-workflow-allocation.svg",
        "cost-quality-rework": "cost-quality-rework-triangle.svg",
        "experiment-comparison": "experiment-cost-comparison.svg",
        "routing-escalation": "routing-escalation-mechanism.svg",
        "agent-chaos-sources": "agent-chaos-sources.svg",
        "supervisor-evolution": "supervisor-evolution.svg",
        "supervisor-vs-others": "supervisor-vs-others.svg",
        "supervisor-when-to-use": "supervisor-when-to-use.svg",
    }
    return mapping.get(image.get("design_key", ""), f"{image['image_id']}.svg")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render deterministic image assets from image manifest")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--image-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    manifest = read_json(project_dir / "image-manifest-source.json", {"images": []})
    summary = read_json(project_root / "tmp" / "multi_model_experiment" / "rebuilt" / "summary_table.json", {})
    image = next((item for item in manifest.get("images", []) if item.get("image_id") == args.image_id), None)
    if image is None:
        raise SystemExit(f"image not found: {args.image_id}")
    image = normalize_image_spec({**image, "topic_id": args.topic_id})

    asset_dir = project_root / "assets" / "publish-ready" / args.topic_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    filename = filename_for(image)
    asset_path = asset_dir / filename
    asset_path.write_text("\n".join(render_svg(image, summary)), encoding="utf-8")

    output_dir = project_dir / f"image-compositor-{args.image_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "pass": True,
        "passed": [f"rendered {filename}"],
        "issues": [],
        "file": str(asset_path),
        "image_id": args.image_id,
        "filename": filename,
        "kind": image.get("kind", ""),
        "insert_after_heading": image.get("insert_after_heading", ""),
        "source": image.get("source", ""),
        "components": [component for component in read_json(project_dir / "image-component-manifest.json", {"components": []}).get("components", []) if component.get("image_id") == args.image_id],
        "design_notes": image.get("purpose", ""),
        "generated_at": datetime.now().isoformat(),
        "width": WIDTH,
        "height": HEIGHT,
    }
    write_json(output_dir / "output.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
