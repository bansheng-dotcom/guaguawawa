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

from compiler_lib import build_project_dir


LABEL_MARKERS = {
    "problem_entry": ["问题", "现象", "困惑", "真实", "背景", "为什么", "如果你"],
    "misconception": ["误区", "很多人", "大部分", "常规", "套公式", "只看", "以为"],
    "judgment": ["真正的问题", "关键", "本质", "不是", "而是", "不能简单", "阶段性结论"],
    "evidence": ["数据", "案例", "例如", "比如", "证明", "可以看到", "结果"],
    "mechanism": ["背后", "机制", "原因", "影响", "导致", "对应", "业务含义"],
    "transition": ["到这里", "接下来", "再往下", "继续", "回过头", "下一步"],
    "action": ["看板", "专项", "复盘", "预警", "策略", "资源配置", "跟踪", "动作"],
    "boundary": ["不意味着", "解决不了", "不能把", "只适用", "还不能", "边界"],
    "summary": ["总结", "所以", "因此", "以上", "最后", "简单来说"],
}

EXPECTED_FUNCTION = {
    "problem_entry": "提出真实问题、现象、困惑或业务背景",
    "misconception": "指出常见误区、模板拆法或 AI 式理解",
    "judgment": "给出作者判断、取舍或阶段结论",
    "evidence": "提供数据、案例、事实或观察来支撑判断",
    "mechanism": "解释因果、业务机制或系统关系",
    "transition": "从上一层问题推进到下一层分析",
    "action": "落到策略、看板、专项、复盘或资源配置",
    "boundary": "限制外推、说明未验证点或承认不可解问题",
    "summary": "阶段性收束、回扣主线或引出下一步",
}

REVIEW_CHECKS = {
    "problem_entry": ["real_problem_entry", "avoid百科定义", "reader_context"],
    "misconception": ["misconception_is_specific", "misconception_supports_later_judgment"],
    "judgment": ["judgment_is_clear", "judgment_has_path", "fact_inference_action_boundary"],
    "evidence": ["evidence_supports_judgment", "metric_to_scene", "avoid_data_dump"],
    "mechanism": ["causal_chain_visible", "business_mechanism_explained"],
    "transition": ["transition_has_logical_work", "next_layer_is_clear"],
    "action": ["action_is_controllable", "object_action_metric_cadence"],
    "boundary": ["scope_limited", "unverified_points_visible"],
    "summary": ["stage_summary", "next_step_or_boundary"],
}


def split_paragraphs(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        if stripped.startswith("## "):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        current.append(line.rstrip())
    if current:
        blocks.append("\n".join(current).strip())
    return [block for block in blocks if block]


def marker_scores(text: str) -> dict[str, int]:
    return {
        label: sum(1 for marker in markers if marker in text)
        for label, markers in LABEL_MARKERS.items()
    }


def infer_label(text: str, index: int, total: int) -> tuple[str, list[str], dict[str, int]]:
    scores = marker_scores(text)
    stripped = text.strip()
    if stripped.startswith("```"):
        return "evidence", ["mechanism"], scores
    if stripped.endswith("：") and ("写" in stripped or "看" in stripped or "版本" in stripped or "改成" in stripped):
        return "transition", ["evidence"], scores
    if stripped.startswith("如果你想") and ("就要" in stripped or "不要只写" in stripped):
        secondary = ["summary"]
        if "下一节" in stripped:
            secondary.append("transition")
        return "action", secondary, scores
    if "下一节" in stripped and ("先看" in stripped or "进入" in stripped or "目标" in stripped):
        return "transition", ["summary"], scores
    if stripped.startswith("所以") and ("不要只问" in stripped or "还要问" in stripped):
        return "action", ["summary"], scores
    if index <= 2 and scores["problem_entry"] == 0:
        scores["problem_entry"] += 1
    if index >= max(1, total - 1) and scores["summary"] == 0:
        scores["summary"] += 1

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    positive = [(label, score) for label, score in ranked if score > 0]
    if not positive:
        return "mechanism", [], scores
    primary = positive[0][0]
    secondary = [label for label, score in positive[1:3] if score > 0]
    return primary, secondary, scores


def infer_confidence(label: str, secondary: list[str], scores: dict[str, int]) -> float:
    top_score = scores.get(label, 0)
    if top_score <= 0:
        return 0.35
    confidence = 0.45 + min(top_score, 3) * 0.15
    if secondary:
        confidence -= 0.1
    return round(max(0.35, min(0.95, confidence)), 2)


def chain_coverage(paragraphs: list[dict]) -> dict:
    required = [
        "problem_entry",
        "misconception",
        "judgment",
        "mechanism",
        "evidence",
        "action",
        "boundary",
    ]
    present = {item["label"] for item in paragraphs}
    for item in paragraphs:
        present.update(item.get("secondary_labels", []))
    missing = [label for label in required if label not in present]
    return {
        "required_chain": required,
        "present_labels": sorted(present),
        "missing_labels": missing,
        "chain_complete": not missing,
        "note": "Missing labels are cross-paragraph review hints, not proof that every paragraph must contain them.",
    }


def _display_path(project_root: Path, path: Path) -> str:
    try:
        value = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        value = path
    return value.as_posix()


def tag_section(topic_id: str, section_id: str, project_root: Path, input_path: Path | None = None) -> dict:
    project_dir = build_project_dir(project_root, topic_id)
    section_dir = project_dir / "sections" / section_id
    draft_path = section_dir / "draft.md"
    review_source_path = section_dir / "review-source.md"
    source_path = input_path or (review_source_path if review_source_path.exists() else draft_path if draft_path.exists() else section_dir / "writer.md")
    text = source_path.read_text(encoding="utf-8-sig") if source_path.exists() else ""
    blocks = split_paragraphs(text)
    paragraphs = []
    total = len(blocks)
    for index, block in enumerate(blocks, start=1):
        label, secondary, scores = infer_label(block, index, total)
        paragraphs.append(
            {
                "paragraph_id": f"p{index:02d}",
                "label": label,
                "secondary_labels": secondary,
                "tagging_method": "marker_heuristic",
                "marker_based": True,
                "confidence": infer_confidence(label, secondary, scores),
                "expected_function": EXPECTED_FUNCTION[label],
                "review_checks": REVIEW_CHECKS[label],
                "char_count": len(block),
                "marker_scores": scores,
                "text_preview": block[:240],
            }
        )
    return {
        "pass": bool(text),
        "topic_id": topic_id,
        "section_id": section_id,
        "source": _display_path(project_root, source_path),
        "tagging_method": "marker_heuristic",
        "marker_based": True,
        "confidence_note": "Paragraph labels are review hints. Review agents may override low-confidence or obviously wrong labels.",
        "paragraph_count": len(paragraphs),
        "paragraphs": paragraphs,
        "chain_coverage": chain_coverage(paragraphs),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tag paragraph functions for section review")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--section-id", required=True)
    parser.add_argument("--input", default="")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    input_path = Path(args.input) if args.input else None
    if input_path and not input_path.is_absolute():
        input_path = project_root / input_path
    payload = tag_section(args.topic_id, args.section_id, project_root, input_path)
    output_path = (
        build_project_dir(project_root, args.topic_id)
        / "sections"
        / args.section_id
        / "paragraph-tags.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
