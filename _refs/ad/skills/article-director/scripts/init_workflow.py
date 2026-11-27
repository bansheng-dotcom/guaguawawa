import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from strategy_profiles import build_workflow_profile, get_strategy_profile, infer_strategy, normalize_strategy


RUN_TEMPLATE = """from pathlib import Path

PROJECT_ID = "{project_id}"
TOPIC_ID = "{topic_id}"
TITLE = {title}
BRIEF = {brief}
STRATEGY = {strategy}
ARTICLE_DIRECTOR_WORKFLOW_VERSION = "2026-05-23.stable"
SKILL_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
BOOTSTRAP_INCLUDE_EXPERIMENTS = {include_experiments}
BOOTSTRAP_INCLUDE_TUTORIAL_FACT_GATE = {include_tutorial_fact_gate}
BOOTSTRAP_INCLUDE_IMAGES = {include_images}

NODE_DEFS = [
    dict(
        node_id="topic-architect-01-plan",
        role="{architect_plan_role}",
        skill_file=str(SKILL_ROOT / "{architect_agent_path}"),
        temperature=0.20,
        output_file="skills/article-director/outputs/{project_id}/topic-architect-01-plan/output.md",
        schema_check_id="execution-plan",
        task_prefix={plan_task_prefix},
        provider="codex",
        model_override="",
    ),
    dict(
        node_id="topic-architect-01-exec",
        role="{architect_exec_role}",
        skill_file=str(SKILL_ROOT / "{architect_agent_path}"),
        temperature=0.20,
        output_file="tmp/{topic_id}-detailed-outline.md",
        input_files=["skills/article-director/outputs/{project_id}/topic-architect-01-plan/output.md"],
        schema_check_id="detailed-outline",
        task_prefix={exec_task_prefix},
        provider="codex",
        model_override="",
    ),
    dict(
        node_id="normalize-detailed-outline-01",
        role="normalize-detailed-outline",
        skill_file=str(SKILL_ROOT / "{inspect_agent_path}"),
        temperature=0.00,
        output_file="tmp/{topic_id}-detailed-outline.md",
        schema_check_id="none",
        node_type="script",
        command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\normalize_detailed_outline.py", "--topic-id", "{{topic_id}}"],
    ),
    dict(
        node_id="derive-outline-01",
        role="derive-outline",
        skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
        temperature=0.00,
        output_file="tmp/{topic_id}-outline.md",
        schema_check_id="topic-outline",
        node_type="script",
        command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\derive_outline_from_detailed.py", "--topic-id", "{{topic_id}}"],
    ),
    dict(
        node_id="director-inspect-01",
        role="{inspect_role}",
        skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
        temperature=0.00,
        output_file="skills/article-director/outputs/{project_id}/director-inspect-01/output.md",
        input_files=["tmp/{topic_id}-outline.md", "tmp/{topic_id}-detailed-outline.md"],
        schema_check_id="none",
        task_prefix="只审查大纲完整性、边界和缺口，不代写正文。输出必须是 Markdown，并且至少包含一个一级标题，例如：# 大纲审查。",
        provider="codex",
        model_override="",
    ),
    dict(
        node_id="outline-confirmation-01",
        role="outline-confirmation",
        skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
        temperature=0.00,
        output_file="skills/article-director/outputs/{project_id}/outline-confirmation-01/output.json",
        schema_check_id="none",
        node_type="human-approval",
        env={{
            "approval_key": "outline-confirmation",
            "approval_message": "大纲和细纲已生成并完成检查，请先人工确认后再进入正文分包与写作。",
        }},
    ),
    dict(
        node_id="prepare-article-requirements-01",
        role="prepare-article-requirements",
        skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
        temperature=0.00,
        output_file="skills/article-director/outputs/{project_id}/prepare-article-requirements-01/output.json",
        schema_check_id="code-check-result",
        node_type="script",
        command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\prepare_article_requirements.py", "--topic-id", "{{topic_id}}", "--title", {title}],
    ),
    dict(
        node_id="article-requirements-confirmation-01",
        role="article-requirements-confirmation",
        skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
        temperature=0.00,
        output_file="skills/article-director/outputs/{project_id}/article-requirements-confirmation-01/output.json",
        schema_check_id="none",
        node_type="human-approval",
        env={{
            "approval_key": "article-requirements-confirmation",
            "approval_message": "请先补充并确认 article-requirements.json：字数、篇幅、重点段落、新增需求、个人文风、认知风格和逻辑偏好。确认后再进入 section 写作。"
        }},
    ),
    dict(
        node_id="build-section-manifest-01",
        role="build-section-manifest",
        skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
        temperature=0.00,
        output_file="skills/article-director/outputs/{project_id}/section-manifest.json",
        schema_check_id="section-manifest",
        node_type="script",
        command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\build_section_manifest.py", "--topic-id", "{{topic_id}}"],
    ),
    dict(
        node_id="validate-strategy-manifest-rules-01",
        role="validate-strategy-manifest-rules",
        skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
        temperature=0.00,
        output_file="skills/article-director/outputs/{project_id}/validate-strategy-manifest-rules-01/output.json",
        schema_check_id="code-check-result",
        node_type="script",
        command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\validate_strategy_manifest_rules.py"],
    ),
    *([
        dict(
            node_id="tutorial-research-gate-01",
            role="tutorial-research-gate",
            skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
            temperature=0.00,
            output_file="skills/article-director/outputs/{project_id}/tutorial-research-gate-01/output.json",
            schema_check_id="code-check-result",
            node_type="script",
            command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\prepare_tutorial_research_gate.py", "--topic-id", "{{topic_id}}"],
        ),
    ] if BOOTSTRAP_INCLUDE_TUTORIAL_FACT_GATE else []),
    dict(
        node_id="score-article-workload-01",
        role="score-article-workload",
        skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
        temperature=0.00,
        output_file="skills/article-director/outputs/{project_id}/section-manifest.json",
        schema_check_id="section-manifest",
        node_type="script",
        command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\score_article_workload.py", "--topic-id", "{{topic_id}}"],
    ),
    dict(
        node_id="balance-article-packages-01",
        role="balance-article-packages",
        skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
        temperature=0.00,
        output_file="skills/article-director/outputs/{project_id}/article-packages.json",
        schema_check_id="article-packages",
        node_type="script",
        command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\balance_article_packages.py", "--topic-id", "{{topic_id}}"],
    ),
    *([
        dict(
            node_id="build-image-manifest-01",
            role="build-image-manifest",
            skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
            temperature=0.00,
            output_file="skills/article-director/outputs/{project_id}/image-manifest-source.json",
            schema_check_id="image-manifest-source",
            node_type="script",
            command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\build_image_manifest.py", "--topic-id", "{{topic_id}}"],
        ),
        dict(
            node_id="score-image-workload-01",
            role="score-image-workload",
            skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
            temperature=0.00,
            output_file="skills/article-director/outputs/{project_id}/image-manifest-source.json",
            schema_check_id="image-manifest-source",
            node_type="script",
            command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\score_image_workload.py", "--topic-id", "{{topic_id}}"],
        ),
        dict(
            node_id="build-image-components-01",
            role="build-image-components",
            skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
            temperature=0.00,
            output_file="skills/article-director/outputs/{project_id}/image-component-manifest.json",
            schema_check_id="image-component-manifest",
            node_type="script",
            command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\build_image_components.py", "--topic-id", "{{topic_id}}"],
        ),
        dict(
            node_id="balance-image-packages-01",
            role="balance-image-packages",
            skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
            temperature=0.00,
            output_file="skills/article-director/outputs/{project_id}/image-packages.json",
            schema_check_id="image-packages",
            node_type="script",
            command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\balance_image_packages.py", "--topic-id", "{{topic_id}}"],
        ),
    ] if BOOTSTRAP_INCLUDE_IMAGES else []),
    *([
        dict(
            node_id="prepare-experiment-manifest-01",
            role="prepare-experiment-manifest",
            skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
            temperature=0.00,
            output_file="tmp/multi_model_experiment/rebuilt/experiment_manifest.json",
            schema_check_id="experiment-manifest",
            node_type="script",
            command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\prepare_experiment_manifest.py", "--topic-id", "{{topic_id}}"],
        ),
        dict(
            node_id="run-cost-analysis-experiment-01",
            role="run-cost-analysis-experiment",
            skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
            temperature=0.00,
            output_file="tmp/multi_model_experiment/rebuilt/runs/normalized_runs.json",
            schema_check_id="normalized-runs",
            node_type="script",
            command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\run_cost_analysis_experiment.py", "--topic-id", "{{topic_id}}"],
        ),
        dict(
            node_id="summarize-experiment-results-01",
            role="summarize-experiment-results",
            skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
            temperature=0.00,
            output_file="tmp/multi_model_experiment/rebuilt/summary_table.json",
            schema_check_id="experiment-summary",
            node_type="script",
            command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\summarize_experiment_results.py", "--topic-id", "{{topic_id}}"],
        ),
    ] if BOOTSTRAP_INCLUDE_EXPERIMENTS else []),
    dict(
        node_id="compile-expanded-workflow-01",
        role="compile-expanded-workflow",
        skill_file=str(SKILL_ROOT / "agents/director/SKILL.md"),
        temperature=0.00,
        output_file="skills/article-director/outputs/{project_id}/run_{topic_id}_expanded.py",
        schema_check_id="expanded-workflow",
        node_type="script",
        command=["{{python}}", "{{project_root}}\\\\skills\\\\article-director\\\\scripts\\\\compile_expanded_workflow.py", "--topic-id", "{{topic_id}}", "--title", {title}, "--workflow-mode", {workflow_mode_json}],
    ),
]

EDGE_DEFS = [
    dict(from_node="topic-architect-01-plan", to_node="topic-architect-01-exec"),
    dict(from_node="topic-architect-01-exec", to_node="normalize-detailed-outline-01"),
    dict(from_node="normalize-detailed-outline-01", to_node="derive-outline-01"),
    dict(from_node="derive-outline-01", to_node="director-inspect-01"),
    dict(from_node="director-inspect-01", to_node="outline-confirmation-01"),
    dict(from_node="outline-confirmation-01", to_node="prepare-article-requirements-01"),
    dict(from_node="prepare-article-requirements-01", to_node="article-requirements-confirmation-01"),
    dict(from_node="article-requirements-confirmation-01", to_node="build-section-manifest-01"),
    dict(from_node="build-section-manifest-01", to_node="validate-strategy-manifest-rules-01"),
    *([
        dict(from_node="validate-strategy-manifest-rules-01", to_node="tutorial-research-gate-01"),
        dict(from_node="tutorial-research-gate-01", to_node="score-article-workload-01"),
    ] if BOOTSTRAP_INCLUDE_TUTORIAL_FACT_GATE else [
        dict(from_node="validate-strategy-manifest-rules-01", to_node="score-article-workload-01"),
    ]),
    dict(from_node="score-article-workload-01", to_node="balance-article-packages-01"),
    *([
        dict(from_node="balance-article-packages-01", to_node="build-image-manifest-01"),
        dict(from_node="build-image-manifest-01", to_node="score-image-workload-01"),
        dict(from_node="score-image-workload-01", to_node="build-image-components-01"),
        dict(from_node="build-image-components-01", to_node="balance-image-packages-01"),
    ] if BOOTSTRAP_INCLUDE_IMAGES else []),
    *([
        dict(from_node="balance-image-packages-01", to_node="prepare-experiment-manifest-01"),
        dict(from_node="prepare-experiment-manifest-01", to_node="run-cost-analysis-experiment-01"),
        dict(from_node="run-cost-analysis-experiment-01", to_node="summarize-experiment-results-01"),
        dict(from_node="summarize-experiment-results-01", to_node="compile-expanded-workflow-01"),
    ] if BOOTSTRAP_INCLUDE_EXPERIMENTS else [
        dict(from_node="balance-article-packages-01", to_node="compile-expanded-workflow-01"),
    ]),
]
"""


EXECUTION_MODES = {
    "simple-production": {
        "label": "简单生产",
        "description": "优先最短可交付路径，不默认拉起图片、实验和额外增强链。",
    },
    "enhanced-production": {
        "label": "增强生产",
        "description": "保留增强生产偏好，但当前默认主链仍不会自动展开图片和实验，后续可人工追加增强链。",
    },
}

INTERACTION_PREFERENCES = {
    "speed-first": {
        "label": "速度优先",
        "description": "更看重尽快看到可确认的大纲、细纲和正文骨架。",
    },
    "balanced": {
        "label": "平衡模式",
        "description": "兼顾速度、可读性和稳定性。",
    },
    "quality-first": {
        "label": "完整性优先",
        "description": "更看重表达完整、逻辑稳和终稿质量。",
    },
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff\-_\s]+", "-", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "article-topic"


def _is_interactive_session(disabled: bool) -> bool:
    return not disabled and hasattr(sys.stdin, "isatty") and sys.stdin.isatty()


def _prompt_choice(question: str, options: list[tuple[str, str, str]], default_value: str) -> str:
    print(f"\n{question}")
    for index, (_, label, description) in enumerate(options, start=1):
        print(f"{index}. {label}：{description}")
    default_index = next((idx for idx, (value, _, _) in enumerate(options, start=1) if value == default_value), 1)
    raw = input(f"请选择 [{default_index}]: ").strip()
    if not raw:
        return default_value
    if raw.isdigit():
        index = int(raw)
        if 1 <= index <= len(options):
            return options[index - 1][0]
    normalized = raw.strip().lower()
    for value, label, _ in options:
        if normalized in {value.lower(), label.lower()}:
            return value
    print("输入无法识别，使用默认选项。")
    return default_value


def _confirm_continue(default_yes: bool = True) -> bool:
    prompt = "确认继续生成 workflow 吗？[Y/n]: " if default_yes else "确认继续生成 workflow 吗？[y/N]: "
    raw = input(prompt).strip().lower()
    if not raw:
        return default_yes
    return raw in {"y", "yes", "1"}


def _collect_startup_preferences(
    title: str,
    brief: str,
    explicit_strategy: str,
    explicit_mode: str,
    explicit_preference: str,
    interactive: bool,
    auto_confirm: bool,
) -> dict:
    inferred_strategy = infer_strategy(title, brief, explicit_strategy)
    strategy = normalize_strategy(explicit_strategy) if explicit_strategy and explicit_strategy.lower() not in {"", "auto"} else inferred_strategy
    execution_mode = explicit_mode or "simple-production"
    interaction_preference = explicit_preference or "balanced"
    answers_source = "cli"

    if interactive:
        answers_source = "interactive"
        strategy_options = [
            ("knowledge-explainer", "知识解释", "适合“是什么 / 为什么 / 原理 / 机制 / 边界”这类知识科普。"),
            ("teaching-playbook", "教学步骤", "适合“如何做 / 怎么接入 / 如何验证 / 如何排查”这类教程文章。"),
        ]
        mode_options = [
            ("simple-production", EXECUTION_MODES["simple-production"]["label"], EXECUTION_MODES["simple-production"]["description"]),
            ("enhanced-production", EXECUTION_MODES["enhanced-production"]["label"], EXECUTION_MODES["enhanced-production"]["description"]),
        ]
        preference_options = [
            ("speed-first", INTERACTION_PREFERENCES["speed-first"]["label"], INTERACTION_PREFERENCES["speed-first"]["description"]),
            ("balanced", INTERACTION_PREFERENCES["balanced"]["label"], INTERACTION_PREFERENCES["balanced"]["description"]),
            ("quality-first", INTERACTION_PREFERENCES["quality-first"]["label"], INTERACTION_PREFERENCES["quality-first"]["description"]),
        ]
        strategy = _prompt_choice("执行前先确认本次写作策略", strategy_options, strategy)
        execution_mode = _prompt_choice("执行前先确认本次流程强度", mode_options, execution_mode)
        interaction_preference = _prompt_choice("执行前先确认本次交互偏好", preference_options, interaction_preference)

    return {
        "strategy": strategy,
        "execution_mode": execution_mode,
        "interaction_preference": interaction_preference,
        "answers_source": answers_source,
        "inferred_strategy": inferred_strategy,
        "auto_confirm": auto_confirm,
    }


def _print_execution_preview(topic_id: str, title: str, startup: dict) -> None:
    strategy = startup["strategy"]
    execution_mode = startup["execution_mode"]
    interaction_preference = startup["interaction_preference"]
    strategy_profile = get_strategy_profile(strategy)
    print("\n================ 启动前确认 ================")
    print(f"主题ID：{topic_id}")
    print(f"标题：{title}")
    print(f"写作策略：{strategy_profile['display_name']} ({strategy})")
    print(f"流程强度：{EXECUTION_MODES[execution_mode]['label']} ({execution_mode})")
    print(f"交互偏好：{INTERACTION_PREFERENCES[interaction_preference]['label']} ({interaction_preference})")
    print("默认初始化链：选题规划 -> 细纲 -> 规范化 -> 大纲 -> 大纲检查 -> 人工确认 -> 工作量评分 -> 分包 -> 编译扩展工作流")
    print("默认正文主链：分包写作 -> 主审查修订 -> 全文合并 -> 全文终审 -> 最终文章确认")
    if execution_mode == "enhanced-production":
        print("增强说明：当前会记录增强生产偏好，但默认仍不会自动启动图片链和实验链，需后续人工追加。")
    print("===========================================")


def generate_run_script(
    project_id: str,
    topic_id: str,
    title: str,
    brief: str = "",
    strategy: str = "knowledge-explainer",
    execution_mode: str = "simple-production",
    interaction_preference: str = "balanced",
    workflow_mode: str = "standard",
) -> str:
    strategy = infer_strategy(title, brief, strategy)
    profile = get_strategy_profile(strategy)
    include_experiments = False
    include_tutorial_fact_gate = strategy == "teaching-playbook"
    include_images = False
    workflow_mode = (workflow_mode or "standard").strip()
    architect_agent_path = "agents/topic-architect/SKILL.md"
    inspect_agent_path = "agents/topic-architect/SKILL.md" if workflow_mode == "lean-v1" else "agents/director/SKILL.md"
    architect_plan_role = "topic-architect-plan"
    architect_exec_role = "topic-architect-exec"
    inspect_role = "topic-architect-inspect" if workflow_mode == "lean-v1" else "director-inspect"
    manifest_rules = profile.get("manifest_rules", {})
    outline_backbone = manifest_rules.get("outline_backbone", [])
    detailed_outline_labels = manifest_rules.get("detailed_outline_required_labels", [])
    step_chain_requirements = manifest_rules.get("step_chain_requirements", [])
    plan_task_prefix = (
        "[Bootstrap/Plan] 只做选题理解、读者误区、知识结构和大小纲规划，不写正文。"
        "输出必须使用以下固定 Markdown 标题：\\n# 选题规划\\n## 执行计划\\n## 任务拆解\\n"
        "在“执行计划”里说明这篇文章要如何组织知识；在“任务拆解”里至少列出 3 条规划任务。"
        f"{profile['topic_architect_plan_suffix']}"
    )
    exec_task_prefix = (
        "只产出 detailed outline，不要把多个文件包装在一个回复里。"
        "优先为每个 section 写出这些固定标签：论点:、需要解释:、需要引用:、待研究:。"
        "本阶段重点是行文逻辑和知识点边界正确，不追求严格机器格式；方案先给人确认。"
        f"{profile['topic_architect_exec_suffix']}"
    )
    if execution_mode == "simple-production":
        plan_task_prefix += "\\n本次走简单生产模式：优先最短可交付路径，不默认拉起图片、实验和额外增强链。"
    else:
        plan_task_prefix += "\\n本次走增强生产模式：先跑默认主链，后续是否追加增强链由人工确认，不自动扩面。"
    if interaction_preference == "speed-first":
        exec_task_prefix += "\\n本次交互偏好是速度优先：先给出最可确认的结构方案，不在这个阶段追求过度展开。"
    elif interaction_preference == "quality-first":
        exec_task_prefix += "\\n本次交互偏好是完整性优先：在可确认前提下尽量把结构边界、论证顺序和潜在缺口提前说清。"
    else:
        exec_task_prefix += "\\n本次交互偏好是平衡模式：兼顾速度、可确认性和后续正文稳定性。"
    if manifest_rules.get("prefer_procedural_steps"):
        if outline_backbone:
            plan_task_prefix += (
                "\\n教程类文章默认骨架："
                + " -> ".join(outline_backbone)
                + "。大纲先写结果和路径，再写步骤，不先写概念综述。"
            )
        if detailed_outline_labels:
            exec_task_prefix += (
                "\\n教程细纲必须覆盖这些标签："
                + "、".join(detailed_outline_labels)
                + "。"
            )
        if step_chain_requirements:
            exec_task_prefix += (
                "\\n执行步骤额外要求："
                + "；".join(step_chain_requirements)
                + "。"
            )
    return RUN_TEMPLATE.format(
        project_id=project_id,
        topic_id=topic_id,
        title=json.dumps(title, ensure_ascii=False),
        brief=json.dumps(brief, ensure_ascii=False),
        strategy=json.dumps(strategy, ensure_ascii=False),
        include_experiments="True" if include_experiments else "False",
        include_tutorial_fact_gate="True" if include_tutorial_fact_gate else "False",
        include_images="True" if include_images else "False",
        architect_agent_path=architect_agent_path,
        inspect_agent_path=inspect_agent_path,
        architect_plan_role=architect_plan_role,
        architect_exec_role=architect_exec_role,
        inspect_role=inspect_role,
        workflow_mode_json=json.dumps(workflow_mode, ensure_ascii=False),
        plan_task_prefix=json.dumps(plan_task_prefix, ensure_ascii=False),
        exec_task_prefix=json.dumps(exec_task_prefix, ensure_ascii=False),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize bootstrap workflow for article-director")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--brief", default="")
    parser.add_argument("--strategy", default="auto")
    parser.add_argument("--mode", default="")
    parser.add_argument("--interaction-preference", default="")
    parser.add_argument("--workflow-mode", default="standard", choices=["standard", "lean-v1"])
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parent.parent
    topic_id = slugify(args.topic_id)
    project_dir = skill_root / "outputs" / topic_id
    project_dir.mkdir(parents=True, exist_ok=True)
    interactive = _is_interactive_session(args.non_interactive or args.yes)
    startup = _collect_startup_preferences(
        title=args.title,
        brief=args.brief,
        explicit_strategy=args.strategy,
        explicit_mode=args.mode,
        explicit_preference=args.interaction_preference,
        interactive=interactive,
        auto_confirm=args.yes,
    )
    _print_execution_preview(topic_id, args.title, startup)
    if interactive and not args.yes:
        if not _confirm_continue(default_yes=True):
            raise SystemExit("用户取消了 workflow 初始化。")

    strategy = startup["strategy"]
    workflow_profile = build_workflow_profile(strategy, args.title, args.brief)
    workflow_profile["workflow_mode"] = args.workflow_mode
    workflow_profile["startup_contract"] = {
        "execution_mode": startup["execution_mode"],
        "interaction_preference": startup["interaction_preference"],
        "answers_source": startup["answers_source"],
        "inferred_strategy": startup["inferred_strategy"],
        "asked_at": datetime.now().isoformat(timespec="seconds"),
        "pre_execution_questions": [
            "写作策略",
            "流程强度",
            "交互偏好",
        ],
        "default_chain_preview": {
            "bootstrap": [
                "选题规划",
                "细纲",
                "规范化",
                "大纲",
                "大纲检查",
                "人工确认",
                "文章期望模板",
                "文章期望确认",
                "工作量评分",
                "正文分包",
                "编译扩展工作流",
            ],
            "body": [
                "二级章节并行写作（最多3个）",
                "lean-v1：单节 writer + 单节 editor" if args.workflow_mode == "lean-v1" else "四步审查",
                "lean-v1：脚本保留 AI 味审计与回归" if args.workflow_mode == "lean-v1" else "四步修改",
                "全文合并",
                "确定性校验",
                "最终文章确认",
            ],
        },
    }
    (project_dir / "workflow-profile.json").write_text(
        json.dumps(workflow_profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    script_path = project_dir / f"run_{topic_id}.py"
    script_path.write_text(
        generate_run_script(
            topic_id,
            topic_id,
            args.title,
            args.brief,
            strategy,
            startup["execution_mode"],
            startup["interaction_preference"],
            args.workflow_mode,
        ),
        encoding="utf-8",
    )
    print(script_path)


if __name__ == "__main__":
    main()
