import json
import math
import re
from pathlib import Path

from strategy_profiles import DEFAULT_STRATEGY, get_strategy_profile

IGNORED_SECTION_HEADINGS = {"术语预扫描"}
PRESENTATION_MODES = {
    "prose",
    "numbered-reasons",
    "comparison-table",
    "checklist",
    "problem-solution-blocks",
    "procedural-steps",
}


ARTICLE_SCORE_WEIGHTS = {
    "paragraph": 1.2,
    "claim": 1.6,
    "evidence": 1.4,
    "numeric_claim": 1.5,
    "complexity": 1.8,
    "dependency": 1.3,
    "style": 1.1,
}

IMAGE_SCORE_WEIGHTS = {
    "panel": 2.0,
    "series": 1.6,
    "annotation": 1.3,
    "text_block": 1.1,
    "ui_component": 0.9,
    "precise_numbers": 2.2,
    "layout_density": 1.5,
    "visual_risk": 1.4,
}

TARGET_ARTICLE_PACKAGE_SCORE = 16.0
MAX_ARTICLE_PACKAGES = 6
MIN_ARTICLE_PACKAGES = 2
MAX_IMAGES = 4
MIN_IMAGES = 2
IMAGE_COMPONENT_SPLIT_THRESHOLD = 18.0

FLOW_KEYWORDS = ["流程", "工作流", "路由", "升级", "回退", "编排", "调度"]
COMPARISON_KEYWORDS = ["对比", "比较", "差异", "成本", "省钱", "降本"]
SCREENSHOT_KEYWORDS = ["截图", "界面", "控制台", "面板", "平台"]
NUMBERED_REASON_KEYWORDS = ["原因", "层", "阶段", "步骤", "标准", "原则", "路径", "抓手"]
CHECKLIST_KEYWORDS = ["清单", "检查", "判断", "避坑", "信号", "动作", "规则", "指标"]
PROBLEM_SOLUTION_KEYWORDS = ["问题", "错误做法", "正确做法", "修复", "解决", "纠偏", "症状", "结果差异"]
COMMON_READER_KNOWN_TERMS = [
    "模型",
    "任务",
    "流程",
    "工作流",
    "结果",
    "结论",
    "数据分析",
    "成本",
    "质量",
]
EXCLUDED_ENGLISH_TERMS = {
    "ai",
    "api",
    "cpu",
    "gpu",
    "json",
    "yaml",
    "html",
    "css",
    "js",
    "md",
    "sql",
    "csv",
    "http",
    "https",
    "token",
}
FORBIDDEN_OPENING_PATTERNS = [
    "先给结论",
    "如果只用一句最不绕的话来解释",
    "从这个角度看",
    "换个角度看",
    "可以这样理解",
    "更准确地说",
    "说白了",
    "简单来说",
    "本质上",
]
DISCOURSE_ORDER_MAP = {
    "prose": ["entry-point", "thesis", "mechanism", "evidence", "implication"],
    "numbered-reasons": ["entry-point", "thesis", "numbered-reasons", "takeaway"],
    "comparison-table": ["entry-point", "comparison-axes", "difference", "choice"],
    "checklist": ["entry-point", "diagnosis-or-checklist", "action"],
    "problem-solution-blocks": ["entry-point", "problem", "fix", "result"],
    "procedural-steps": ["entry-point", "goal", "prerequisites", "steps", "verification", "troubleshooting"],
}
ANALOGY_DOMAIN = "data-analysis-workflow"
TEACHING_KEYWORDS = ["教程", "步骤", "怎么做", "如何", "配置", "接入", "安装", "验证", "排查", "复现", "迁移"]
SECTION_MIN_WORDS = 320
SECTION_MAX_WORDS = 900


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff\-_\s]+", "-", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "article-topic"


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return default


def parse_word_budget(value) -> tuple[int, int] | None:
    text = str(value or "").strip()
    if not text:
        return None
    numbers = [int(match) for match in re.findall(r"\d+", text)]
    if not numbers:
        return None
    if len(numbers) == 1:
        number = max(1, numbers[0])
        return number, number
    low, high = sorted(numbers[:2])
    return max(1, low), max(1, high)


def apply_article_word_budget(manifest: dict, requirements: dict) -> dict:
    budget = parse_word_budget(requirements.get("target_word_count"))
    sections = manifest.get("sections") or []
    if not budget or not sections:
        return manifest

    low, high = budget
    target_total = round((low + high) / 2)
    priority_headings = [str(item) for item in requirements.get("priority_sections", [])]
    weights = []
    for section in sections:
        heading = str(section.get("heading") or "")
        base = max(1, int(section.get("target_word_count", 0) or 1))
        is_priority = any(heading in item or item in heading for item in priority_headings)
        weights.append(base * (1.25 if is_priority else 0.85))

    total_weight = sum(weights) or len(sections)
    section_min = min(SECTION_MIN_WORDS, max(220, low // max(1, len(sections) + 3)))
    section_max = max(SECTION_MAX_WORDS, high // max(1, len(sections) - 1))
    scaled: list[int] = []
    for weight in weights:
        words = int(round((target_total * weight / total_weight) / 10) * 10)
        words = max(section_min, min(section_max, words))
        scaled.append(words)

    def _adjust(delta: int) -> None:
        if delta == 0:
            return
        step = 10 if delta > 0 else -10
        remaining = abs(delta)
        while remaining >= 10:
            changed = False
            order = range(len(scaled)) if step > 0 else reversed(range(len(scaled)))
            for idx in order:
                candidate = scaled[idx] + step
                if section_min <= candidate <= section_max:
                    scaled[idx] = candidate
                    remaining -= 10
                    changed = True
                    if remaining < 10:
                        return
            if not changed:
                return

    _adjust(target_total - sum(scaled))

    for section, words in zip(sections, scaled):
        section["target_word_count"] = words
        section["target_paragraph_count"] = max(2, min(5, round(words / 180)))
    manifest["word_budget"] = {
        "source": "article-requirements.json",
        "requested_range": [low, high],
        "target_total": target_total,
        "allocated_total": sum(scaled),
    }
    return manifest


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def split_points(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = [part.strip() for part in re.split(r"[；;、,，]\s*", text) if part.strip()]
    return parts or [text]


def normalize_presentation_mode(value: str) -> str:
    raw = value.strip()
    lowered = raw.lower()
    if lowered in PRESENTATION_MODES:
        return lowered
    if any(token in lowered for token in ["before/after", "before-after", "table"]) or any(
        token in raw for token in ["对照", "对比", "表格", "字段表"]
    ):
        return "comparison-table"
    if any(token in lowered for token in ["checklist", "check list"]) or "清单" in raw:
        return "checklist"
    if any(token in lowered for token in ["step", "procedure"]) or any(token in raw for token in ["步骤", "流程"]):
        return "procedural-steps"
    if any(token in raw for token in ["问题-方案", "问题/方案", "问题和方案"]):
        return "problem-solution-blocks"
    if any(token in raw for token in ["编号", "分点"]):
        return "numbered-reasons"
    if any(token in lowered for token in ["prose", "paragraph"]) or any(token in raw for token in ["自然段", "叙述"]):
        return "prose"
    return ""


def presentation_from_strategy_rules(title: str, manifest_rules: dict) -> tuple[str, str]:
    for rule in manifest_rules.get("presentation_rules", []):
        mode = normalize_presentation_mode(str(rule.get("mode", "")))
        if not mode:
            continue
        keywords = [str(item).strip() for item in rule.get("heading_keywords", []) if str(item).strip()]
        if any(keyword in title for keyword in keywords):
            return mode, str(rule.get("reason") or "strategy_presentation_rule")
    return "", ""


def has_explicit_step_contract(body: str, explicit_step_markers: list[str]) -> bool:
    marker_hits = sum(1 for marker in explicit_step_markers if marker and marker in body)
    return marker_hits >= 2


def infer_argument_complexity(title: str, body: str) -> int:
    score = 1
    joined = f"{title} {body}"
    for keyword in ["为什么", "如何", "机制", "理论", "设计", "证明", "实验", "路由", "质量", "成本"]:
        if keyword in joined:
            score += 1
    return max(1, min(score, 5))


def infer_style_sensitivity(title: str) -> int:
    if any(keyword in title for keyword in ["开头", "结论", "收束", "标题"]):
        return 4
    if any(keyword in title for keyword in ["理论", "框架", "设计"]):
        return 3
    return 2


def infer_cross_section_dependencies(body: str) -> int:
    count = 0
    for keyword in ["上文", "前文", "下文", "后文", "总结", "回到", "承接"]:
        if keyword in body:
            count += 1
    return count


def infer_parallel_point_count(claims: list[str], explanation: list[str], body: str) -> int:
    numbered_markers = re.findall(r"(?:^|\n)\s*(?:\d+[\.、]|[一二三四五六七八九十]+、)", body)
    counts = [len(claims), len(explanation), len(numbered_markers)]
    return max(1, min(6, max(counts)))


def infer_recommended_presentation(
    title: str,
    body: str,
    claims: list[str],
    explanation: list[str],
    strategy: str = DEFAULT_STRATEGY,
) -> tuple[str, int, str]:
    joined = f"{title} {body}"
    parallel_point_count = infer_parallel_point_count(claims, explanation, body)
    tutorial_intro_keywords = ["目标与结果", "目标用户", "适用边界", "基础概念", "名词预扫描"]
    tutorial_route_keywords = ["执行路径总览", "直连路径", "兼容路径"]

    strategy_profile = get_strategy_profile(strategy)
    manifest_rules = strategy_profile.get("manifest_rules", {})
    explicit_step_markers = manifest_rules.get(
        "explicit_step_markers",
        ["前提:", "操作:", "预期结果:", "失败现象:", "排查:", "下一步:"],
    )
    procedural_keywords = manifest_rules.get("procedural_keywords", TEACHING_KEYWORDS)
    strategy_mode, strategy_reason = presentation_from_strategy_rules(title, manifest_rules)
    if strategy_mode:
        return strategy_mode, max(2, parallel_point_count), strategy_reason
    if strategy == "teaching-playbook":
        if any(keyword in title for keyword in tutorial_intro_keywords):
            return "checklist", max(2, parallel_point_count), "teaching_intro_or_boundary_content"
        if any(keyword in title for keyword in tutorial_route_keywords):
            return "comparison-table", max(2, parallel_point_count), "teaching_route_choice_content"
    if manifest_rules.get("prefer_procedural_steps") and (
        has_explicit_step_contract(body, explicit_step_markers)
        or any(keyword in title for keyword in procedural_keywords if keyword in {"执行步骤", "配置步骤", "验证步骤", "排查步骤"})
    ):
        return "procedural-steps", max(2, parallel_point_count), f"{strategy_profile['strategy']}_execution_contract"

    if any(keyword in joined for keyword in COMPARISON_KEYWORDS + ["优缺点", "更适合", "不一定", "区别", "差别", "选择"]):
        return "comparison-table", parallel_point_count, "comparison_or_choice_content"
    if any(keyword in joined for keyword in PROBLEM_SOLUTION_KEYWORDS):
        return "problem-solution-blocks", parallel_point_count, "problem_and_fix_content"
    if any(keyword in joined for keyword in CHECKLIST_KEYWORDS):
        return "checklist", parallel_point_count, "diagnostic_or_operational_content"
    if 2 <= parallel_point_count <= 4 and (
        any(keyword in joined for keyword in NUMBERED_REASON_KEYWORDS)
        or parallel_point_count >= 3
    ):
        return "numbered-reasons", parallel_point_count, "parallel_reasons_or_stages"
    return "prose", parallel_point_count, "default_prose"


def infer_requires_image(title: str, body: str, numeric_claim_count: int) -> bool:
    joined = f"{title} {body}"
    if numeric_claim_count >= 1:
        return True
    keywords = FLOW_KEYWORDS + COMPARISON_KEYWORDS + SCREENSHOT_KEYWORDS + ["实验", "数据", "图", "矩阵"]
    return any(keyword in joined for keyword in keywords)


def infer_image_kind(title: str, body: str, numeric_claim_count: int) -> str:
    joined = f"{title} {body}"
    if any(keyword in joined for keyword in SCREENSHOT_KEYWORDS):
        return "screenshot"
    if any(keyword in joined for keyword in FLOW_KEYWORDS):
        return "diagram"
    if any(keyword in joined for keyword in COMPARISON_KEYWORDS):
        return "comparison"
    if numeric_claim_count >= 2 or "实验" in joined or "数据" in joined:
        return "chart"
    return "diagram"


def infer_reader_unknown_terms(title: str, body: str) -> list[str]:
    text = f"{title}\n{body}"
    candidates: list[str] = []
    seen: set[str] = set()
    pattern = re.compile(r"\b([A-Za-z][A-Za-z0-9+/.\-]{1,})(?:\s*(?:模式|工程|框架|机制|系统|运行时|runtime|Runtime|Agent|agent|Workflow|workflow))?")
    for match in pattern.finditer(text):
        phrase = match.group(0).strip()
        token = match.group(1).lower()
        if token in EXCLUDED_ENGLISH_TERMS:
            continue
        if len(token) <= 1:
            continue
        if phrase.lower() in seen:
            continue
        seen.add(phrase.lower())
        candidates.append(phrase)
    return candidates[:8]


def infer_must_answer_first(title: str, recommended_presentation: str) -> list[str]:
    if "是什么" in title:
        return ["这个概念到底是什么", "它解决什么问题"]
    if "为什么" in title:
        return ["先交代读者会遇到的现象", "再解释原因或机制"]
    if "如何" in title or "怎么" in title:
        return ["先说要解决的任务", "再给做法或步骤"]
    if recommended_presentation == "procedural-steps":
        return ["先说这一步要完成什么", "再说为什么要这样做"]
    if recommended_presentation == "comparison-table":
        return ["先说比较对象是什么", "再说为什么要比较"]
    return ["先说读者会遇到的具体问题", "再说本节结论"]


def infer_comparison_terms(title: str, body: str, unknown_terms: list[str]) -> list[str]:
    joined = f"{title} {body}"
    if not any(keyword in joined for keyword in COMPARISON_KEYWORDS + ["区别", "差别", "更适合", "不适合"]):
        return []
    return unknown_terms[:4]


def infer_reader_contract(title: str, body: str, recommended_presentation: str, strategy: str) -> dict:
    unknown_terms = infer_reader_unknown_terms(title, body)
    profile = get_strategy_profile(strategy)
    return {
        "reader_contract_version": "2026-05-21.v1",
        "reader_level": "beginner-public",
        "reader_knows_terms": COMMON_READER_KNOWN_TERMS,
        "reader_unknown_terms": unknown_terms,
        "concept_explainer_required": bool(unknown_terms),
        "must_explain_terms": unknown_terms[:3],
        "concept_explanation_policy": profile["concept_policy"]["rule"],
        "must_answer_first": infer_must_answer_first(title, recommended_presentation),
        "comparison_terms": infer_comparison_terms(title, body, unknown_terms),
        "forbidden_opening_patterns": FORBIDDEN_OPENING_PATTERNS,
        "required_discourse_order": DISCOURSE_ORDER_MAP.get(
            recommended_presentation,
            DISCOURSE_ORDER_MAP["prose"],
        ),
        "allowed_analogy_domain": ANALOGY_DOMAIN,
        "human_entry_required": True,
    }


def read_workflow_profile(project_root: Path, topic_id: str) -> dict:
    profile_path = build_project_dir(project_root, topic_id) / "workflow-profile.json"
    if not profile_path.exists():
        return get_strategy_profile(DEFAULT_STRATEGY)
    payload = read_json(profile_path, {})
    strategy = payload.get("strategy", DEFAULT_STRATEGY)
    profile = get_strategy_profile(strategy)
    profile["workflow_profile"] = payload
    for key in (
        "workflow_family",
        "workflow_family_version",
        "strategy_display_name",
        "strategy_version",
        "strategy_contract_path",
        "content_contract",
        "prompt_contracts",
        "title",
        "brief",
    ):
        if key in payload:
            profile[key] = payload[key]
    return profile


def build_project_dir(project_root: Path, topic_id: str) -> Path:
    return project_root / "skills" / "article-director" / "outputs" / topic_id


def parse_detailed_outline(path: Path, topic_id: str, strategy: str = DEFAULT_STRATEGY) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    sections = []
    current = None
    counter = 0
    profile = get_strategy_profile(strategy)

    def flush_current():
        nonlocal current
        if not current:
            return
        if current["heading"] in IGNORED_SECTION_HEADINGS:
            current = None
            return
        body_text = "\n".join(current["body_lines"]).strip()
        claim_text = current.get("claim", "")
        evidence_text = current.get("evidence", "")
        reader_stuck_text = current.get("reader_stuck", "")
        upstream_downstream_text = current.get("upstream_downstream", "")
        logic_difficulty_text = current.get("logic_difficulty", "")
        example_text = current.get("example", "")
        before_after_text = current.get("before_after", "")
        writer_actionable_text = current.get("writer_actionable", "")
        candidate_unit_text = current.get("candidate_unit", "")
        explanation_text = current.get("explanation", "")
        research_text = current.get("research", "")
        concept_text = current.get("concepts", "")
        prerequisites_text = current.get("prerequisites", "")
        actions_text = current.get("actions", "")
        expected_text = current.get("expected_result", "")
        failure_text = current.get("failure_signals", "")
        troubleshooting_text = current.get("troubleshooting", "")
        next_text = current.get("next_transition", "")
        handoff_text = current.get("handoff_from_previous", "")
        output_text = current.get("section_output", "")
        next_gate_text = current.get("next_section_gate", "")
        code_example_text = current.get("code_example", "")
        prompt_example_text = current.get("prompt_example", "")
        presentation_hint_text = current.get("presentation", "")
        explicit_presentation = normalize_presentation_mode(presentation_hint_text)
        claims = split_points(claim_text)
        evidence = split_points(evidence_text)
        explanation = split_points(explanation_text)
        numeric_claim_count = len(re.findall(r"\d+(?:\.\d+)?%?", body_text))
        if any(word in body_text for word in ["成本", "token", "实验", "比例", "降本", "质量"]) and numeric_claim_count == 0:
            numeric_claim_count = 1
        complexity = infer_argument_complexity(current["heading"], body_text)
        dependencies = infer_cross_section_dependencies(body_text)
        style = infer_style_sensitivity(current["heading"])
        inferred_presentation, parallel_point_count, presentation_reason = infer_recommended_presentation(
            current["heading"],
            body_text,
            claims,
            explanation,
            strategy,
        )
        recommended_presentation = explicit_presentation or inferred_presentation
        if explicit_presentation:
            presentation_reason = "detailed_outline_presentation"
        target_paragraph_count = max(2, min(6, len(claims) + max(1, len(explanation) // 2) + math.ceil(complexity / 2)))
        target_word_count = target_paragraph_count * 220 + len(evidence) * 40 + numeric_claim_count * 30
        requires_image = infer_requires_image(current["heading"], body_text, numeric_claim_count)
        if profile.get("manifest_rules", {}).get("prefer_procedural_steps") and (actions_text or expected_text or failure_text):
            target_paragraph_count = max(target_paragraph_count, 4)
            target_word_count = max(target_word_count, 900)
        reader_contract = infer_reader_contract(current["heading"], body_text, recommended_presentation, strategy)
        sections.append(
            {
                "section_id": f"section-{len(sections) + 1:02d}",
                "heading": current["heading"],
                "level": current["level"],
                "strategy": strategy,
                "claim": claim_text,
                "explanation": explanation_text,
                "evidence": evidence_text,
                "reader_stuck": reader_stuck_text,
                "upstream_downstream": upstream_downstream_text,
                "logic_difficulty": logic_difficulty_text,
                "example": example_text,
                "before_after": before_after_text,
                "writer_actionable": writer_actionable_text,
                "candidate_unit": candidate_unit_text,
                "research": research_text,
                "concepts": concept_text,
                "prerequisites": prerequisites_text,
                "actions": actions_text,
                "expected_result": expected_text,
                "failure_signals": failure_text,
                "troubleshooting": troubleshooting_text,
                "next_transition": next_text,
                "handoff_from_previous": handoff_text,
                "section_output": output_text,
                "next_section_gate": next_gate_text,
                "code_example": code_example_text,
                "prompt_example": prompt_example_text,
                "presentation_hint": presentation_hint_text,
                "body_text": body_text,
                "recommended_presentation": recommended_presentation,
                "parallel_point_count": parallel_point_count,
                "presentation_reason": presentation_reason,
                "step_fields_required": profile.get("required_step_fields", []),
                "step_boundary_rule": profile.get("step_boundary_rules", {}).get("summary_rule", ""),
                "claim_count": max(1, len(claims)) if claim_text else 1,
                "evidence_count": len(evidence),
                "numeric_claim_count": numeric_claim_count,
                "cross_section_dependency_count": dependencies,
                "argument_complexity": complexity,
                "style_sensitivity": style,
                "target_paragraph_count": target_paragraph_count,
                "target_word_count": target_word_count,
                "requires_image": requires_image,
                "requires_fact_verification": len(evidence) > 0 or numeric_claim_count > 0,
                "image_kind_candidate": infer_image_kind(current["heading"], body_text, numeric_claim_count),
                **reader_contract,
            }
        )
        current = None

    for raw_line in lines:
        clean_line = raw_line.lstrip("\ufeff")
        line = clean_line.strip()
        if re.match(r"^#\s", line):
            continue
        if re.match(r"^###\s", line):
            if current is not None:
                current["body_lines"].append(clean_line)
            continue
        if re.match(r"^##\s", line):
            flush_current()
            counter += 1
            current = {
                "heading": re.sub(r"^#+\s*", "", line).strip(),
                "level": line.count("#"),
                "claim": "",
                "explanation": "",
                "evidence": "",
                "research": "",
                "presentation": "",
                "concepts": "",
                "prerequisites": "",
                "actions": "",
                "expected_result": "",
                "failure_signals": "",
                "troubleshooting": "",
                "next_transition": "",
                "handoff_from_previous": "",
                "section_output": "",
                "next_section_gate": "",
                "code_example": "",
                "prompt_example": "",
                "body_lines": [],
            }
            continue
        if current is None:
            continue
        current["body_lines"].append(clean_line)
        if line.startswith("论点:"):
            current["claim"] = line.split(":", 1)[1].strip()
        elif line.startswith("读者卡点:"):
            current["reader_stuck"] = line.split(":", 1)[1].strip()
        elif line.startswith("上下游承接:"):
            current["upstream_downstream"] = line.split(":", 1)[1].strip()
        elif line.startswith("逻辑难点:"):
            current["logic_difficulty"] = line.split(":", 1)[1].strip()
        elif line.startswith("需要解释:"):
            current["explanation"] = line.split(":", 1)[1].strip()
        elif line.startswith("需要引用:"):
            current["evidence"] = line.split(":", 1)[1].strip()
        elif line.startswith("需要案例:"):
            current["example"] = line.split(":", 1)[1].strip()
        elif line.startswith("待研究:"):
            current["research"] = line.split(":", 1)[1].strip()
        elif line.startswith("规范化前后:"):
            current["before_after"] = line.split(":", 1)[1].strip()
        elif line.startswith("writer可执行信息:") or line.startswith("写作执行信息:"):
            current["writer_actionable"] = line.split(":", 1)[1].strip()
        elif line.startswith("候选写作单元:"):
            current["candidate_unit"] = line.split(":", 1)[1].strip()
        elif line.startswith("展示方式:"):
            current["presentation"] = line.split(":", 1)[1].strip()
        elif line.startswith("推荐呈现:") or line.startswith("推荐呈现方式:"):
            current["presentation"] = line.split(":", 1)[1].strip()
        elif line.startswith("概念解释:"):
            current["concepts"] = line.split(":", 1)[1].strip()
        elif line.startswith("前提:"):
            current["prerequisites"] = line.split(":", 1)[1].strip()
        elif line.startswith("操作:"):
            current["actions"] = line.split(":", 1)[1].strip()
        elif line.startswith("预期结果:"):
            current["expected_result"] = line.split(":", 1)[1].strip()
        elif line.startswith("失败现象:"):
            current["failure_signals"] = line.split(":", 1)[1].strip()
        elif line.startswith("排查:"):
            current["troubleshooting"] = line.split(":", 1)[1].strip()
        elif line.startswith("下一步:"):
            current["next_transition"] = line.split(":", 1)[1].strip()
        elif line.startswith("上文承接:"):
            current["handoff_from_previous"] = line.split(":", 1)[1].strip()
        elif line.startswith("本节产出:"):
            current["section_output"] = line.split(":", 1)[1].strip()
        elif line.startswith("进入下一节条件:"):
            current["next_section_gate"] = line.split(":", 1)[1].strip()
        elif line.startswith("代码样例:"):
            current["code_example"] = line.split(":", 1)[1].strip()
        elif line.startswith("提示词样例:"):
            current["prompt_example"] = line.split(":", 1)[1].strip()

    flush_current()
    return {
        "topic_id": topic_id,
        "strategy": strategy,
        "strategy_profile": {
            "display_name": profile["display_name"],
            "primary_goal": profile["primary_goal"],
            "section_intent": profile["section_intent"],
            "concept_policy": profile["concept_policy"],
            "step_boundary_rules": profile["step_boundary_rules"],
            "required_step_fields": profile["required_step_fields"],
        },
        "section_count": len(sections),
        "sections": sections,
    }


def score_article_sections(manifest: dict) -> dict:
    for section in manifest["sections"]:
        quantity_score = (
            ARTICLE_SCORE_WEIGHTS["paragraph"] * section["target_paragraph_count"]
            + ARTICLE_SCORE_WEIGHTS["claim"] * section["claim_count"]
            + ARTICLE_SCORE_WEIGHTS["evidence"] * section["evidence_count"]
            + ARTICLE_SCORE_WEIGHTS["numeric_claim"] * section["numeric_claim_count"]
        )
        quality_score = (
            ARTICLE_SCORE_WEIGHTS["complexity"] * section["argument_complexity"]
            + ARTICLE_SCORE_WEIGHTS["dependency"] * section["cross_section_dependency_count"]
            + ARTICLE_SCORE_WEIGHTS["style"] * section["style_sensitivity"]
        )
        section["quantity_score"] = round(quantity_score, 2)
        section["quality_score"] = round(quality_score, 2)
        section["total_score"] = round(quantity_score + quality_score, 2)
        section["risk_tier"] = (
            "high"
            if section["requires_fact_verification"] and section["argument_complexity"] >= 4
            else "medium"
            if section["requires_fact_verification"] or section["argument_complexity"] >= 3
            else "low"
        )
    manifest["total_score"] = round(sum(section["total_score"] for section in manifest["sections"]), 2)
    return manifest


def _balance_items(items: list[dict], target_score: float, min_packages: int, max_packages: int) -> list[dict]:
    total = sum(item["total_score"] for item in items)
    package_count = max(min_packages, min(max_packages, math.ceil(total / target_score) if total else min_packages))
    packages = [
        {"package_id": f"package-{idx + 1:02d}", "package_order": idx + 1, "items": [], "total_score": 0.0}
        for idx in range(package_count)
    ]
    for item in sorted(items, key=lambda value: value["total_score"], reverse=True):
        package = min(packages, key=lambda value: value["total_score"])
        package["items"].append(item)
        package["total_score"] += item["total_score"]
    for package in packages:
        package["total_score"] = round(package["total_score"], 2)
    return packages


def _single_section_packages(items: list[dict]) -> list[dict]:
    packages = []
    for idx, item in enumerate(items, start=1):
        packages.append(
            {
                "package_id": f"package-{idx:02d}",
                "package_order": idx,
                "items": [item],
                "total_score": round(item["total_score"], 2),
            }
        )
    return packages


def _contiguous_items(items: list[dict], target_score: float, min_packages: int, max_packages: int) -> list[dict]:
    if not items:
        return []
    total = sum(item["total_score"] for item in items)
    package_count = max(min_packages, min(max_packages, math.ceil(total / target_score) if total else min_packages))
    if package_count >= len(items):
        return _single_section_packages(items)

    packages: list[dict] = []
    current_items: list[dict] = []
    current_score = 0.0
    remaining_slots = package_count

    for index, item in enumerate(items):
        remaining_items = len(items) - index
        must_split = remaining_items == remaining_slots
        if current_items and (current_score >= target_score or must_split):
            packages.append(
                {
                    "package_id": f"package-{len(packages) + 1:02d}",
                    "package_order": len(packages) + 1,
                    "items": current_items,
                    "total_score": round(current_score, 2),
                }
            )
            remaining_slots -= 1
            current_items = []
            current_score = 0.0
        current_items.append(item)
        current_score += item["total_score"]

    if current_items:
        packages.append(
            {
                "package_id": f"package-{len(packages) + 1:02d}",
                "package_order": len(packages) + 1,
                "items": current_items,
                "total_score": round(current_score, 2),
            }
        )
    return packages


def build_article_packages(manifest: dict) -> dict:
    if manifest.get("sections") and "total_score" not in manifest["sections"][0]:
        manifest = score_article_sections(manifest)
    strategy = manifest.get("strategy", DEFAULT_STRATEGY)
    strategy_profile = manifest.get("strategy_profile", {}) or {}
    manifest_rules = strategy_profile.get("manifest_rules", {}) or {}
    package_mode = str(manifest_rules.get("package_mode", "") or "").strip().lower()

    if strategy == "teaching-playbook" or package_mode == "single-section":
        packages = _single_section_packages(manifest["sections"])
    else:
        packages = _contiguous_items(
            manifest["sections"],
            target_score=TARGET_ARTICLE_PACKAGE_SCORE,
            min_packages=MIN_ARTICLE_PACKAGES,
            max_packages=MAX_ARTICLE_PACKAGES,
        )
    payload = {"topic_id": manifest["topic_id"], "package_count": len(packages), "packages": []}
    for package in packages:
        sections = package["items"]
        payload["packages"].append(
            {
                "package_id": package["package_id"],
                "package_order": package["package_order"],
                "package_score": package["total_score"],
                "section_ids": [section["section_id"] for section in sections],
                "section_headings": [section["heading"] for section in sections],
                "target_word_count": sum(section["target_word_count"] for section in sections),
                "target_paragraph_count": sum(section["target_paragraph_count"] for section in sections),
                "risk_tier": "high" if any(section["risk_tier"] == "high" for section in sections) else "medium",
                "requires_fact_verification": any(section["requires_fact_verification"] for section in sections),
            }
        )
    return payload


def build_image_manifest_source(section_manifest: dict) -> dict:
    candidates = []
    for section in section_manifest["sections"]:
        if not section["requires_image"]:
            continue
        kind = section["image_kind_candidate"]
        panel_count = 2 if kind == "comparison" else 1
        data_series_count = max(1, min(4, section["numeric_claim_count"] + (1 if kind == "chart" else 0)))
        node_count = section["claim_count"] + section["cross_section_dependency_count"] + (2 if kind == "diagram" else 0)
        annotation_count = max(1, min(6, section["evidence_count"] + section["numeric_claim_count"]))
        text_block_count = max(1, min(5, section["target_paragraph_count"]))
        ui_component_count = panel_count + annotation_count + (2 if kind in {"chart", "comparison"} else 1)
        candidates.append(
            {
                "image_id": f"image-{len(candidates) + 1:02d}",
                "target_section_id": section["section_id"],
                "target_heading": section["heading"],
                "kind": kind,
                "panel_count": panel_count,
                "data_series_count": data_series_count,
                "node_count": node_count,
                "annotation_count": annotation_count,
                "text_block_count": text_block_count,
                "ui_component_count": ui_component_count,
                "requires_precise_numbers": section["numeric_claim_count"] > 0,
                "layout_density": min(5, panel_count + text_block_count + math.ceil(annotation_count / 2)),
                "visual_risk_tier": 3 if section["risk_tier"] == "high" else 2 if section["risk_tier"] == "medium" else 1,
                "insert_after_heading": section["heading"],
                "source": section["section_id"],
            }
        )
    if len(candidates) < MIN_IMAGES and section_manifest["sections"]:
        fallback_sections = [section for section in section_manifest["sections"] if section["section_id"] not in {c["target_section_id"] for c in candidates}]
        for section in fallback_sections[: MIN_IMAGES - len(candidates)]:
            candidates.append(
                {
                    "image_id": f"image-{len(candidates) + 1:02d}",
                    "target_section_id": section["section_id"],
                    "target_heading": section["heading"],
                    "kind": "diagram",
                    "panel_count": 1,
                    "data_series_count": 1,
                    "node_count": max(3, section["claim_count"] + 1),
                    "annotation_count": 2,
                    "text_block_count": 2,
                    "ui_component_count": 4,
                    "requires_precise_numbers": False,
                    "layout_density": 2,
                    "visual_risk_tier": 1,
                    "insert_after_heading": section["heading"],
                    "source": section["section_id"],
                }
            )
    candidates = sorted(
        candidates,
        key=lambda item: (item["requires_precise_numbers"], item["visual_risk_tier"], item["annotation_count"]),
        reverse=True,
    )[:MAX_IMAGES]
    return {"topic_id": section_manifest["topic_id"], "images": candidates}


def score_image_manifest(manifest: dict) -> dict:
    for image in manifest["images"]:
        quantity_score = (
            IMAGE_SCORE_WEIGHTS["panel"] * image["panel_count"]
            + IMAGE_SCORE_WEIGHTS["series"] * image["data_series_count"]
            + IMAGE_SCORE_WEIGHTS["annotation"] * image["annotation_count"]
            + IMAGE_SCORE_WEIGHTS["text_block"] * image["text_block_count"]
            + IMAGE_SCORE_WEIGHTS["ui_component"] * image["ui_component_count"]
        )
        quality_score = (
            IMAGE_SCORE_WEIGHTS["precise_numbers"] * (1 if image["requires_precise_numbers"] else 0)
            + IMAGE_SCORE_WEIGHTS["layout_density"] * image["layout_density"]
            + IMAGE_SCORE_WEIGHTS["visual_risk"] * image["visual_risk_tier"]
        )
        image["quantity_score"] = round(quantity_score, 2)
        image["quality_score"] = round(quality_score, 2)
        image["total_score"] = round(quantity_score + quality_score, 2)
    manifest["total_score"] = round(sum(image["total_score"] for image in manifest["images"]), 2)
    return manifest


def expand_image_components(image_manifest: dict) -> dict:
    if image_manifest.get("images") and "total_score" not in image_manifest["images"][0]:
        image_manifest = score_image_manifest(image_manifest)
    component_templates = {
        "chart": ["frame", "axes", "series", "legend", "labels", "notes"],
        "diagram": ["frame", "nodes", "connectors", "callouts", "numbering"],
        "comparison": ["frame", "left-panel", "right-panel", "diff-highlights", "labels"],
        "screenshot": ["crop", "focus-mask", "callouts", "caption"],
        "cover": ["frame", "title-block", "accent-shapes", "badge"],
    }
    components = []
    for image in image_manifest["images"]:
        template = component_templates[image["kind"]]
        for idx, name in enumerate(template, start=1):
            components.append(
                {
                    "component_id": f"{image['image_id']}-component-{idx:02d}",
                    "image_id": image["image_id"],
                    "component_parent": image["image_id"],
                    "kind": image["kind"],
                    "component_name": name,
                    "package_hint": image["image_id"],
                    "workload_score": round(image["total_score"] / len(template), 2),
                    "split_required": image["total_score"] > IMAGE_COMPONENT_SPLIT_THRESHOLD,
                }
            )
    return {"topic_id": image_manifest["topic_id"], "components": components}


def build_image_packages(image_manifest: dict) -> dict:
    if image_manifest.get("images") and "total_score" not in image_manifest["images"][0]:
        image_manifest = score_image_manifest(image_manifest)
    packages = _balance_items(image_manifest["images"], target_score=18.0, min_packages=1, max_packages=max(1, len(image_manifest["images"])))
    return {
        "topic_id": image_manifest["topic_id"],
        "package_count": len(packages),
        "packages": [
            {
                "package_id": package["package_id"],
                "package_order": package["package_order"],
                "package_score": package["total_score"],
                "image_ids": [image["image_id"] for image in package["items"]],
                "kinds": [image["kind"] for image in package["items"]],
            }
            for package in packages
        ],
    }
