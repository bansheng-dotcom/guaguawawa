import argparse
import json
import pprint
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from compiler_lib import build_project_dir, read_json
from strategy_profiles import DEFAULT_STRATEGY, get_strategy_profile

AI_TONE_SCRIPT_DIR = Path(r"D:\知识库\skills\内容生产\ai-tone-director\scripts")
if AI_TONE_SCRIPT_DIR.exists() and str(AI_TONE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(AI_TONE_SCRIPT_DIR))

from prewrite_context import build_prewrite_context, render_prewrite_context

AI_TONE_INVOCATION_SCRIPT = r"D:\知识库\skills\内容生产\ai-tone-director\scripts\invocation_log.py"

MICRO_PLAN_VERSION = "2026-05-16.v1"
SECTION_REVIEW_TEMP = 0.0
SECTION_REVISER_TEMP = 0.3
FINAL_REVIEW_A_TEMP = 0.0
FINAL_REVIEW_B_TEMP = 0.15
MAX_PARALLEL_SECTIONS = 3


def _allowed_input(path: str, kind: str = "full_text", **kwargs) -> dict:
    payload = {"path": path, "kind": kind}
    payload.update({key: value for key, value in kwargs.items() if value not in (None, "", [])})
    return payload


def _node(
    node_id: str,
    role: str,
    skill_file: str,
    temperature: float,
    output_file: str,
    schema: str = "none",
    **kwargs,
) -> dict:
    payload = {
        "node_id": node_id,
        "role": role,
        "skill_file": skill_file,
        "temperature": temperature,
        "output_file": output_file,
        "schema_check_id": schema,
    }
    payload.update(kwargs)
    return payload


def _micro_plan_fields(
    micro_plan_id: str,
    micro_plan_file: str,
    micro_plan_mode: str,
    verification_profile: str,
) -> dict:
    return {
        "micro_plan_id": micro_plan_id,
        "micro_plan_file": micro_plan_file,
        "micro_plan_version": MICRO_PLAN_VERSION,
        "micro_plan_mode": micro_plan_mode,
        "verification_profile": verification_profile,
    }


def _node_micro_plan_fields(
    topic_id: str,
    node_id: str,
    micro_plan_mode: str,
    verification_profile: str,
) -> dict:
    return {
        **_micro_plan_fields(
            micro_plan_id=node_id,
            micro_plan_file=f"skills/article-director/outputs/{topic_id}/micro-plan/node-micro-plans.json",
            micro_plan_mode=micro_plan_mode,
            verification_profile=verification_profile,
        ),
        "revision_source": f"skills/article-director/outputs/{topic_id}/micro-plan/revision-plans/{node_id}-rev01.json",
    }


def render_author_style_prewrite_context(section: dict, article_requirements: dict) -> str:
    section_id = str(section.get("section_id") or "")
    heading = str(section.get("heading") or section_id)
    return "\n".join(
        [
            "[author-style-prewrite-context]",
            f"section_id: {section_id}",
            f"heading: {heading}",
            "style_goal:",
            "- 学作者处理问题的方式，不模仿口头禅。",
            "- 先让读者看到真实工作问题，再解释概念。",
            "- 先给判断和可用做法，再补原因和边界。",
            "cognitive_path:",
            "- 从一个具体困惑进入。",
            "- 指出常见误解为什么不好用。",
            "- 抓一个最关键变量，不平均铺开。",
            "- 用例子、字段、口径、提示词或检查清单支撑判断。",
            "rhythm_variation_level: medium",
            "sentence_rhythm:",
            "- 不要把相邻段落写成同一种开头或同一种推进公式。",
            "- 一个写作单元里允许交替出现：短判断句、较长解释句、例子句、停顿句、检查问题。",
            "- 短句只用于判断、停顿或转向，不要连续堆短句。",
            "- 长句只用于解释变量关系，不要每句都长。",
            "- 段落开头不要都用“这/如果/所以/问题在于/你会发现”。",
            "- 每 3-5 个自然段至少出现一次节奏变化：例子、表格、提示词块、检查清单或短判断。",
            "do_not:",
            "- 不写百科定义式开头。",
            "- 不平铺多个方案。",
            "- 不用作者高频词替代具体判断。",
            "- 少写“这是什么逻辑、重点会变化、有价值、不用急着找模板”这类教学旁白，优先写动作句、场景句、后果句。",
            "[/author-style-prewrite-context]",
        ]
    )


def _workflow_mode(profile: dict) -> str:
    for key in ("workflow_mode", "workflow_profile", "profile"):
        value = str(profile.get(key) or "").strip().lower()
        if value:
            return value
    return "standard"


def compile_nodes_lean(topic_id: str, project_root: Path) -> tuple[list[dict], list[dict]]:
    project_dir = build_project_dir(project_root, topic_id)
    section_manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    article_requirements = read_json(project_dir / "article-requirements.json", {})
    workflow_profile = read_json(project_dir / "workflow-profile.json", {"strategy": DEFAULT_STRATEGY})
    strategy = workflow_profile.get("strategy", DEFAULT_STRATEGY)
    strategy_profile = get_strategy_profile(strategy)
    prompt_contracts = strategy_profile.get("prompt_contracts", {})

    def _contract(key: str) -> str:
        return str(prompt_contracts.get(key, "")).strip()

    skill_root_expr = 'str(SKILL_ROOT / "{path}")'
    nodes: list[dict] = []
    edges: list[dict] = []
    sections = [section for section in section_manifest.get("sections", []) if section.get("section_id")]
    section_manifest_path = f"skills/article-director/outputs/{topic_id}/section-manifest.json"
    article_requirements_path = f"skills/article-director/outputs/{topic_id}/article-requirements.json"
    detailed_outline_path = f"tmp/{topic_id}-detailed-outline.md"
    ai_tone_contract_input = _allowed_input("D:/知识库/skills/内容生产/ai-tone-director/workflows/article-director-integration.md", "full_text", max_chars=12000)
    ai_tone_schema_input = _allowed_input("D:/知识库/skills/内容生产/ai-tone-director/schemas/ai-tone-audit.schema.json", "full_text", max_chars=12000)
    author_soul_writer_contract_path = "skills/article-director/style-profiles/author-soul-writer-contract.md"
    author_soul_writer_contract_input = _allowed_input(author_soul_writer_contract_path, "full_text", max_chars=6000)
    style_allowed_inputs = [
        _allowed_input("skills/article-director/style-profiles/style-guide.md", "full_text", max_chars=12000),
        _allowed_input("skills/article-director/style-profiles/cognitive-style-guide.md", "full_text", max_chars=12000),
        _allowed_input("skills/article-director/style-profiles/author-soul.md", "full_text", max_chars=8000),
        _allowed_input("skills/article-director/style-profiles/anti-patterns.json", "full_text", max_chars=8000),
        _allowed_input("skills/report-style-analyzer/references/weihestyle-profile.md", "full_text", max_chars=12000),
        _allowed_input("skills/report-style-analyzer/references/weihestyle-paragraph-rhythm.md", "full_text", max_chars=12000),
        _allowed_input("skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md", "full_text", max_chars=12000),
    ]
    style_reference_paths = [
        "skills/article-director/style-profiles/style-guide.md",
        "skills/article-director/style-profiles/cognitive-style-guide.md",
        "skills/article-director/style-profiles/author-soul.md",
        "skills/article-director/style-profiles/anti-patterns.json",
        "skills/report-style-analyzer/references/weihestyle-profile.md",
        "skills/report-style-analyzer/references/weihestyle-paragraph-rhythm.md",
        "skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md",
    ]
    common_inputs = [
        section_manifest_path,
        article_requirements_path,
        detailed_outline_path,
        "skills/article-director/style-profiles/style-guide.md",
        "skills/article-director/style-profiles/cognitive-style-guide.md",
        "skills/article-director/style-profiles/author-soul.md",
        "skills/article-director/style-profiles/anti-patterns.json",
        "skills/report-style-analyzer/references/weihestyle-profile.md",
        "skills/report-style-analyzer/references/weihestyle-paragraph-rhythm.md",
        "skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md",
        "D:/知识库/skills/内容生产/ai-tone-director/workflows/article-director-integration.md",
        "D:/知识库/skills/内容生产/ai-tone-director/schemas/ai-tone-audit.schema.json",
    ]

    nodes.append(
        _node(
            node_id="build-node-micro-plans-01",
            role="micro-plan-builder",
            skill_file=skill_root_expr.format(path="agents/topic-architect/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/micro-plan/node-micro-plans.json",
            schema="none",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\build_node_micro_plans.py",
                "--topic-id",
                topic_id,
            ],
        )
    )
    nodes.append(
        _node(
            node_id="seed-longform-memory-01",
            role="seed-longform-memory",
            skill_file=skill_root_expr.format(path="agents/topic-architect/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/memory/term-registry.json",
            schema="none",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\seed_longform_article_memory.py",
                "--topic-id",
                topic_id,
            ],
        )
    )
    edges.append({"from_node": "build-node-micro-plans-01", "to_node": "seed-longform-memory-01"})

    section_complete_nodes: list[str] = []
    argument_spine_inputs: list[str] = []

    for order, section in enumerate(sections, start=1):
        section_id = str(section.get("section_id"))
        heading = str(section.get("heading") or section_id)
        section_dir = f"skills/article-director/outputs/{topic_id}/sections/{section_id}"
        argument_spine_path = f"{section_dir}/argument-spine.md"
        writer_context_path = f"{section_dir}/writer-context-window.json"
        draft_path = f"{section_dir}/draft.md"
        review_source_path = f"{section_dir}/review-source.md"
        tag_path = f"{section_dir}/paragraph-tags.json"
        ai_tone_context_path = f"{section_dir}/ai-tone-context-pack.json"
        ai_tone_scan_path = f"{section_dir}/ai-tone-scan.json"
        review_ai_tone_findings_path = f"{section_dir}/review-ai-tone-findings.json"
        review_style_path = f"{section_dir}/review-style.json"
        review_logic_path = f"{section_dir}/review-logic.json"
        review_structure_path = f"{section_dir}/review-structure.json"
        review_simplify_path = f"{section_dir}/review-simplify.json"
        section_edit_brief_path = f"{section_dir}/section-edit-brief.json"
        paragraph_rewrite_design_path = f"{section_dir}/paragraph-rewrite-design.json"
        editor_output_path = f"{section_dir}/section-editor-output.json"
        section_rewrite_gate_path = f"{section_dir}/section-rewrite-gate.json"
        final_path = f"{section_dir}/final.md"
        review_ai_tone_path = f"{section_dir}/review-ai-tone.json"
        ai_tone_audit_gate_path = f"{section_dir}/ai-tone-audit-gate.json"
        ai_tone_repair_plan_path = f"{section_dir}/ai-tone-repair-plan.md"
        ai_tone_regression_path = f"{section_dir}/ai-tone-regression.json"
        ai_tone_log_dir = f"skills/article-director/outputs/{topic_id}/logs"
        argument_spine_inputs.append(argument_spine_path)
        section_manifest_input = _allowed_input(section_manifest_path, "section_manifest", section_id=section_id)
        article_requirements_input = _allowed_input(article_requirements_path, "full_text", max_chars=12000)
        argument_spine_input = _allowed_input(argument_spine_path, "full_text", max_chars=8000)
        writer_context_input = _allowed_input(writer_context_path, "full_text", max_chars=12000)
        draft_input = _allowed_input(draft_path, "full_text", max_chars=22000)
        review_source_input = _allowed_input(review_source_path, "full_text", max_chars=22000)
        tag_input = _allowed_input(tag_path, "full_text", max_chars=12000)

        def _section_node(
            node_id: str,
            role: str,
            skill_path: str,
            temperature: float,
            output_name: str,
            schema: str,
            input_files: list[str],
            task_prefix: str,
            node_type: str = "agent",
            command: list[str] | None = None,
            allowed_inputs: list[dict] | None = None,
            section_group_name: str | None = None,
            component_parent: str = "",
            max_retries: int | None = None,
        ) -> dict:
            node = _node(
                node_id=node_id,
                role=role,
                skill_file=skill_root_expr.format(path=skill_path),
                temperature=temperature,
                output_file=f"{section_dir}/{output_name}",
                schema=schema,
                input_files=input_files,
                task_prefix=task_prefix,
                node_type=node_type,
                parallel=node_type == "agent",
                provider="codex",
                package_type="section",
                package_order=order,
                risk_tier=str(section.get("risk_tier") or "medium"),
                section_group=section_group_name or section_id,
                component_parent=component_parent,
                command=command or [],
                allowed_inputs=allowed_inputs or [],
                **_node_micro_plan_fields(topic_id, node_id, "lean-section-loop", "standard"),
            )
            if max_retries is not None:
                node["max_retries"] = max_retries
            return node

        build_argument_spine_id = f"build-argument-spine-{section_id}"
        nodes.append(
            _section_node(
                build_argument_spine_id,
                "build-argument-spine",
                "agents/topic-architect/SKILL.md",
                0.0,
                "argument-spine.md",
                "none",
                [section_manifest_path, article_requirements_path, detailed_outline_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\build_argument_spine.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )

        writer_context_id = f"build-writer-context-window-{section_id}"
        nodes.append(
            _section_node(
                writer_context_id,
                "build-writer-context-window",
                "agents/topic-architect/SKILL.md",
                0.0,
                "writer-context-window.json",
                "none",
                [section_manifest_path, article_requirements_path, argument_spine_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\build_writer_context_window.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )
        edges.append({"from_node": build_argument_spine_id, "to_node": writer_context_id})

        ai_tone_prewrite_context = render_prewrite_context(build_prewrite_context(section, article_requirements))
        author_style_prewrite_context = render_author_style_prewrite_context(section, article_requirements)
        writer_id = f"section-writer-{section_id}"
        nodes.append(
            _section_node(
                writer_id,
                "section-writer",
                "agents/section-writer/SKILL.md",
                0.35,
                "draft.md",
                "none",
                common_inputs + [argument_spine_path, writer_context_path, author_soul_writer_contract_path],
                (
                    f"[lean-v1:section-writer] Write only section_id={section_id}; heading={heading}. "
                    "Use writer-context-window.json, argument-spine.md, author-soul.md, author-soul-writer-contract.md, style references, and the prewrite contexts below. "
                    "Apply author-soul-writer-contract.md as a light prewrite constraint: choose one primary author move and concrete anchor, but do not force every paragraph into a full soul checklist. "
                    "Build a concise reader-use-contract in an HTML comment, then draft the section body. "
                    "Keep exactly one ## heading and do not write other sections.\n\n"
                    f"{ai_tone_prewrite_context}\n\n{author_style_prewrite_context}\n\n"
                    + (f" {_contract('writer_contract_suffix')}" if _contract("writer_contract_suffix") else "")
                ),
                allowed_inputs=[
                    section_manifest_input,
                    article_requirements_input,
                    argument_spine_input,
                    writer_context_input,
                ]
                + style_allowed_inputs
                + [author_soul_writer_contract_input, ai_tone_contract_input],
            )
        )
        edges.append({"from_node": writer_context_id, "to_node": writer_id})

        review_source_id = f"prepare-section-review-source-{section_id}"
        nodes.append(
            _section_node(
                review_source_id,
                "prepare-section-review-source",
                "agents/director/SKILL.md",
                0.0,
                "review-source.md",
                "none",
                [draft_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\prepare_section_review_source.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )
        edges.append({"from_node": writer_id, "to_node": review_source_id})

        tag_id = f"tag-paragraphs-{section_id}"
        nodes.append(
            _section_node(
                tag_id,
                "paragraph-function-tagger",
                "agents/director/SKILL.md",
                0.0,
                "paragraph-tags.json",
                "none",
                [review_source_path, "skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md"],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\tag_paragraph_functions.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                    "--input",
                    f"{{project_root}}\\{review_source_path}",
                ],
            )
        )
        edges.append({"from_node": review_source_id, "to_node": tag_id})

        prepare_ai_tone_id = f"prepare-ai-tone-call-{section_id}"
        nodes.append(
            _section_node(
                prepare_ai_tone_id,
                "prepare-ai-tone-call",
                "agents/director/SKILL.md",
                0.0,
                "ai-tone-context-pack.json",
                "ai-tone-context-pack",
                [review_source_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    AI_TONE_INVOCATION_SCRIPT,
                    "prepare",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                    "--input",
                    f"{{project_root}}\\{review_source_path}",
                    "--context-output",
                    f"{{project_root}}\\{ai_tone_context_path}",
                    "--scan-output",
                    f"{{project_root}}\\{ai_tone_scan_path}",
                    "--log-dir",
                    f"{{project_root}}\\{ai_tone_log_dir}",
                ],
            )
        )
        edges.append({"from_node": tag_id, "to_node": prepare_ai_tone_id})

        review_specs = [
            (
                "review-ai-tone",
                "ai_tone",
                "review-ai-tone-findings.json",
                "Review AI-tone risks using ai-tone-context-pack.json and ai-tone-scan.json. Do not rewrite the draft.",
            ),
            (
                "review-style",
                "style_alignment",
                "review-style.json",
                "Review author style, author-soul posture, cognitive path, rhythm, and whether the section sounds like a lecture, over-polished, or generic. Do not rewrite the draft.",
            ),
            (
                "review-logic",
                "logic",
                "review-logic.json",
                "Review argument chain, causality, missing middle reasoning, evidence support, and fit with argument-spine.md. Do not rewrite the draft.",
            ),
            (
                "review-structure",
                "structure",
                "review-structure.json",
                "Review paragraphing, bullets, tables, examples, and whether structure helps the reader scan. Do not rewrite the draft.",
            ),
            (
                "review-simplify",
                "simplify",
                "review-simplify.json",
                "Review over-complex explanation, abstract filler, low-information bridge sentences, and places that should be shorter. Do not rewrite the draft.",
            ),
        ]
        review_output_paths: list[str] = []
        review_node_ids: list[str] = []
        for review_prefix, dimension, output_name, instruction in review_specs:
            review_node_id = f"{review_prefix}-{section_id}"
            review_role = f"section-review-{review_prefix.removeprefix('review-')}"
            review_output_path = f"{section_dir}/{output_name}"
            review_input_files = [section_manifest_path, argument_spine_path, review_source_path, tag_path]
            allowed_review_inputs = [
                section_manifest_input,
                review_source_input,
                argument_spine_input,
                tag_input,
            ]
            if dimension == "ai_tone":
                review_input_files += [
                    ai_tone_context_path,
                    ai_tone_scan_path,
                    "D:/知识库/skills/内容生产/ai-tone-director/workflows/article-director-integration.md",
                    "D:/知识库/skills/内容生产/ai-tone-director/schemas/ai-tone-audit.schema.json",
                ]
                allowed_review_inputs += [
                    _allowed_input(ai_tone_context_path, "full_text", max_chars=12000),
                    _allowed_input(ai_tone_scan_path, "full_text", max_chars=12000),
                    ai_tone_contract_input,
                    ai_tone_schema_input,
                ]
            elif dimension == "style_alignment":
                review_input_files += style_reference_paths
                allowed_review_inputs += style_allowed_inputs
            elif dimension in {"logic", "structure", "simplify"}:
                review_input_files += [
                    "skills/article-director/style-profiles/cognitive-style-guide.md",
                    "skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md",
                ]
                allowed_review_inputs += [
                    _allowed_input("skills/article-director/style-profiles/cognitive-style-guide.md", "full_text", max_chars=12000),
                    _allowed_input("skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md", "full_text", max_chars=12000),
                ]
            nodes.append(
                _section_node(
                    review_node_id,
                    review_role,
                    "agents/section-reviewer/SKILL.md",
                    SECTION_REVIEW_TEMP,
                    output_name,
                    "section-review-result",
                    review_input_files,
                    (
                        f"[lean-v1:section-review:{dimension}] Review only section_id={section_id}; heading={heading}. "
                        f"{instruction} Output strict JSON only with pass, score, summary, scope='section', "
                        f"dimension='{dimension}', issues, blocking_issues, advisory_issues, and must_fix. "
                        "For AI-tone review, include ai_tone_invocation exactly matching the context pack. "
                        "Review findings are advisory inputs for section-rewriter; do not edit final_markdown here."
                    ),
                    allowed_inputs=allowed_review_inputs,
                    section_group_name=f"{section_id}:{dimension}",
                    component_parent=section_id,
                    max_retries=2,
                )
            )
            edges.append({"from_node": prepare_ai_tone_id, "to_node": review_node_id})
            review_output_paths.append(review_output_path)
            review_node_ids.append(review_node_id)

        brief_id = f"merge-edit-brief-{section_id}"
        nodes.append(
            _section_node(
                brief_id,
                "merge-section-edit-brief",
                "agents/director/SKILL.md",
                0.0,
                "section-edit-brief.json",
                "code-check-result",
                review_output_paths + [draft_path, argument_spine_path, tag_path, ai_tone_context_path, ai_tone_scan_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\build_section_edit_brief.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )
        for review_node_id in review_node_ids:
            edges.append({"from_node": review_node_id, "to_node": brief_id})

        rewrite_design_id = f"paragraph-rewrite-designer-{section_id}"
        nodes.append(
            _section_node(
                rewrite_design_id,
                "paragraph-rewrite-designer",
                "agents/paragraph-rewrite-designer/SKILL.md",
                0.35,
                "paragraph-rewrite-design.json",
                "paragraph-rewrite-design",
                common_inputs
                + [
                    argument_spine_path,
                    review_source_path,
                    tag_path,
                    ai_tone_context_path,
                    ai_tone_scan_path,
                    section_edit_brief_path,
                    review_ai_tone_findings_path,
                    review_style_path,
                    review_logic_path,
                    review_structure_path,
                    review_simplify_path,
                ],
                (
                    f"[lean-v1:paragraph-rewrite-designer:v2] Design judged rewrite units for section_id={section_id}; heading={heading}. "
                    "Consume section-edit-brief.json plus all five review JSON files, paragraph-tags.json, argument-spine.md, style references, and author-soul.md. "
                    "Do not output final section Markdown. Do not merely prioritize review comments. "
                    "Every reader-facing body paragraph must receive at least a micro_polish instruction; only non-body blocks may be preserved. "
                    "Group prose into rewrite_units when a local rewrite, unit redesign, or section bridge is needed. "
                    "For unit_redesign, target a complete 200-400 Chinese character semantic unit when possible, generate 2-4 usable candidate drafts, score them with the exact rubric, and select one. "
                    "Use this exact rubric: meaning_and_fact_preservation=20, review_absorption=20, de_ai_tone=15, reader_readability=15, workflow_scene=10, author_judgment_and_light_soul=10, section_connection=10. "
                    "Output strict JSON only with pass, summary, section_id, rewrite_mode='paragraph_rewrite_design_v2', section_rewrite_intent, judge_rubric, coverage, rewrite_units, paragraph_micro_edits, preserved_non_body_blocks, not_used_review_pressure, and handoff_to_rewriter. "
                    "coverage.covered_paragraph_ids must include every reader-facing id in coverage.body_paragraph_ids. "
                    "handoff_to_rewriter must tell section-rewriter not to re-judge candidates; it should assemble selected drafts, apply micro edits, smooth connections, and preserve facts and scope."
                ),
                allowed_inputs=[
                    section_manifest_input,
                    review_source_input,
                    argument_spine_input,
                    tag_input,
                    _allowed_input(ai_tone_context_path, "full_text", max_chars=12000),
                    _allowed_input(ai_tone_scan_path, "full_text", max_chars=12000),
                    _allowed_input(section_edit_brief_path, "full_text", max_chars=18000),
                    _allowed_input(review_ai_tone_findings_path, "full_text", max_chars=12000),
                    _allowed_input(review_style_path, "full_text", max_chars=12000),
                    _allowed_input(review_logic_path, "full_text", max_chars=12000),
                    _allowed_input(review_structure_path, "full_text", max_chars=12000),
                    _allowed_input(review_simplify_path, "full_text", max_chars=12000),
                    ai_tone_contract_input,
                ]
                + style_allowed_inputs,
                max_retries=2,
            )
        )
        edges.append({"from_node": brief_id, "to_node": rewrite_design_id})

        editor_id = f"section-editor-{section_id}"
        nodes.append(
            _section_node(
                editor_id,
                "section-rewriter",
                "agents/section-rewriter/SKILL.md",
                0.30,
                "section-editor-output.json",
                "section-editor-result",
                common_inputs
                + [
                    argument_spine_path,
                    review_source_path,
                    tag_path,
                    ai_tone_context_path,
                    ai_tone_scan_path,
                    section_edit_brief_path,
                    paragraph_rewrite_design_path,
                    review_ai_tone_findings_path,
                    review_style_path,
                    review_logic_path,
                    review_structure_path,
                    review_simplify_path,
                ],
                (
                    f"[lean-v1:section-rewriter] Edit only section_id={section_id}; heading={heading}. "
                    "Consume paragraph-rewrite-design.json, section-edit-brief.json, and all review JSON files. "
                    "Use paragraph-rewrite-design.json as the primary rewrite design: assemble selected rewrite_units, apply paragraph_micro_edits, and preserve the designer's judge result unless doing so would break facts, scope, or reader flow. "
                    "Before rewriting, act as the local supervisor: read article_title, section_heading, and title_complexity_policy from section-edit-brief.json; "
                    "judge whether the heading is simple or complex; choose the matching logic-load policy; then decide which review findings to apply, defer, or ignore. "
                    "Output this decision as supervisor_judgment before final_markdown. "
                    "The review fan-out, rewrite unit generation, and designer judge have already run; do not rerun reviews, invent new review dimensions, generate new candidates, or choose a different candidate. "
                    "Make one consolidated rewrite that preserves the original meaning, uses selected drafts, lightly adjusts links between paragraphs, "
                    "applies micro edits across all body prose, repairs light author-soul posture before surface polishing, and applies AI-tone repair as the final editing pass. "
                    "Return strict JSON only. Include ai_tone_audit with ai_tone_invocation exactly matching the context pack. "
                    "Include paragraph_rewrite_design_consumed with design_summary, covered_paragraph_ids, used_units, adapted_units, micro_edits_applied, bridge_edits, and deferred_items. "
                    "Include edit_brief_consumed with brief_id, review_sources, applied_items, deferred_items, and final_gate_notes. "
                    "In final_markdown, output the revised section with exactly one ## heading and remove writer-contract comments."
                ),
                allowed_inputs=[
                    section_manifest_input,
                    review_source_input,
                    argument_spine_input,
                    tag_input,
                    _allowed_input(ai_tone_context_path, "full_text", max_chars=12000),
                    _allowed_input(ai_tone_scan_path, "full_text", max_chars=12000),
                    _allowed_input(section_edit_brief_path, "full_text", max_chars=18000),
                    _allowed_input(paragraph_rewrite_design_path, "full_text", max_chars=32000),
                    _allowed_input(review_ai_tone_findings_path, "full_text", max_chars=12000),
                    _allowed_input(review_style_path, "full_text", max_chars=12000),
                    _allowed_input(review_logic_path, "full_text", max_chars=12000),
                    _allowed_input(review_structure_path, "full_text", max_chars=12000),
                    _allowed_input(review_simplify_path, "full_text", max_chars=12000),
                    ai_tone_contract_input,
                    ai_tone_schema_input,
                ]
                + style_allowed_inputs,
                max_retries=2,
            )
        )
        edges.append({"from_node": rewrite_design_id, "to_node": editor_id})

        rewrite_gate_id = f"section-rewrite-gate-{section_id}"
        nodes.append(
            _section_node(
                rewrite_gate_id,
                "section-rewrite-gate",
                "agents/director/SKILL.md",
                0.0,
                "section-rewrite-gate.json",
                "code-check-result",
                [editor_output_path, section_edit_brief_path, paragraph_rewrite_design_path, review_source_path, ai_tone_context_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\validate_section_rewrite_gate.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
                max_retries=2,
            )
        )
        edges.append({"from_node": editor_id, "to_node": rewrite_gate_id})

        materialize_id = f"materialize-section-editor-{section_id}"
        nodes.append(
            _section_node(
                materialize_id,
                "materialize-section-editor",
                "agents/director/SKILL.md",
                0.0,
                "section-editor-materialize.json",
                "code-check-result",
                [editor_output_path, section_rewrite_gate_path, ai_tone_context_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\materialize_section_editor_output.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )
        edges.append({"from_node": rewrite_gate_id, "to_node": materialize_id})

        audit_gate_id = f"validate-ai-tone-audit-{section_id}"
        nodes.append(
            _section_node(
                audit_gate_id,
                "validate-ai-tone-audit",
                "agents/director/SKILL.md",
                0.0,
                "ai-tone-audit-gate.json",
                "code-check-result",
                [ai_tone_context_path, ai_tone_scan_path, review_ai_tone_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    AI_TONE_INVOCATION_SCRIPT,
                    "validate-audit",
                    "--context",
                    f"{{project_root}}\\{ai_tone_context_path}",
                    "--audit",
                    f"{{project_root}}\\{review_ai_tone_path}",
                    "--gate-output",
                    f"{{project_root}}\\{ai_tone_audit_gate_path}",
                ],
            )
        )
        edges.append({"from_node": materialize_id, "to_node": audit_gate_id})

        repair_plan_id = f"build-ai-tone-repair-plan-{section_id}"
        nodes.append(
            _section_node(
                repair_plan_id,
                "build-ai-tone-repair-plan",
                "agents/director/SKILL.md",
                0.0,
                "ai-tone-repair-plan.md",
                "none",
                [ai_tone_context_path, review_ai_tone_path, ai_tone_audit_gate_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    AI_TONE_INVOCATION_SCRIPT,
                    "repair-plan",
                    "--context",
                    f"{{project_root}}\\{ai_tone_context_path}",
                    "--audit",
                    f"{{project_root}}\\{review_ai_tone_path}",
                    "--output",
                    f"{{project_root}}\\{ai_tone_repair_plan_path}",
                ],
            )
        )
        edges.append({"from_node": audit_gate_id, "to_node": repair_plan_id})

        regression_id = f"ai-tone-regression-{section_id}"
        nodes.append(
            _section_node(
                regression_id,
                "ai-tone-regression",
                "agents/director/SKILL.md",
                0.0,
                "ai-tone-regression.json",
                "code-check-result",
                [ai_tone_context_path, review_ai_tone_path, review_source_path, final_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    AI_TONE_INVOCATION_SCRIPT,
                    "regression",
                    "--context",
                    f"{{project_root}}\\{ai_tone_context_path}",
                    "--audit",
                    f"{{project_root}}\\{review_ai_tone_path}",
                    "--before",
                    f"{{project_root}}\\{review_source_path}",
                    "--after",
                    f"{{project_root}}\\{final_path}",
                    "--output",
                    f"{{project_root}}\\{ai_tone_regression_path}",
                ],
            )
        )
        edges.append({"from_node": repair_plan_id, "to_node": regression_id})

        complete_id = f"section-complete-{section_id}"
        nodes.append(
            _section_node(
                complete_id,
                "section-complete",
                "agents/director/SKILL.md",
                0.0,
                "complete.json",
                "code-check-result",
                [final_path, ai_tone_audit_gate_path, ai_tone_regression_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\complete_section_lean.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )
        edges.append({"from_node": regression_id, "to_node": complete_id})
        edges.append({"from_node": "seed-longform-memory-01", "to_node": build_argument_spine_id})
        section_complete_nodes.append(complete_id)

    nodes.append(
        _node(
            node_id="draft-assembler-01",
            role="draft-assembler",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/draft-assembler-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\assemble_draft.py",
                "--topic-id",
                topic_id,
            ],
        )
    )
    for complete_id in section_complete_nodes:
        edges.append({"from_node": complete_id, "to_node": "draft-assembler-01"})

    final_integrator_inputs = [
        f"tmp/{topic_id}-draft.md",
        article_requirements_path,
        section_manifest_path,
    ] + common_inputs + argument_spine_inputs
    nodes.append(
        _node(
            node_id="final-integrator-01",
            role="final-integrator",
            skill_file=skill_root_expr.format(path="agents/final-integrator/SKILL.md"),
            temperature=0.20,
            output_file=f"skills/article-director/outputs/{topic_id}/final-integrator-01/output.md",
            schema="none",
            input_files=final_integrator_inputs,
            task_prefix=(
                "[lean-v1:final-integrator] Integrate the assembled draft without rewriting from scratch. "
                "Preserve every ## section heading from section-manifest in order. "
                "Fix cross-section repetition, continuity, author rhythm, and obvious assistant-tail phrasing. "
                "Use author-soul.md to remove lecture-like posture and keep the article in the author's experience-and-tradeoff voice. "
                "Remove low-information bridge sentences that only announce continuity, including shells like "
                "'继续往下走', '很好理解', '把这件事分清楚', '下一步很自然', '卡住的点很具体', "
                "'差别会变得很清楚', '选择题很具体', '判断标准很简单', and '优先级应该很清楚'. "
                "Do not add new claims or delete tables, prompt blocks, checklists, or examples. "
                "Output Markdown body only, without the top-level # title and without appendix."
            ),
            provider="codex",
            package_type="final-integration",
            risk_tier="high",
            max_input_tokens=22000,
            max_output_tokens=12000,
            allowed_inputs=[
                _allowed_input(f"tmp/{topic_id}-draft.md", "full_text", max_chars=60000),
                _allowed_input(article_requirements_path, "full_text", max_chars=12000),
                _allowed_input(section_manifest_path, "section_manifest_summary", max_chars=20000),
            ]
            + style_allowed_inputs
            + [_allowed_input(path, "full_text", max_chars=8000) for path in argument_spine_inputs],
        )
    )
    edges.append({"from_node": "draft-assembler-01", "to_node": "final-integrator-01"})

    nodes.append(
        _node(
            node_id="style-harmonizer-check-01",
            role="style-harmonizer-check",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/style-harmonizer-check-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\validate_style_harmonizer_output.py",
                "--topic-id",
                topic_id,
                "--input-node",
                "final-integrator-01",
            ],
        )
    )
    edges.append({"from_node": "final-integrator-01", "to_node": "style-harmonizer-check-01"})

    nodes.append(
        _node(
            node_id="source-map-repair-01",
            role="source-map-repair",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/memory/source-map.md",
            schema="none",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\repair_source_map_from_draft.py",
                "--topic-id",
                topic_id,
            ],
        )
    )
    nodes.append(
        _node(
            node_id="appendix-agent-01",
            role="appendix-builder",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/appendix-agent-01/output.md",
            schema="none",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\build_longform_appendix.py",
                "--topic-id",
                topic_id,
            ],
        )
    )
    edges.append({"from_node": "style-harmonizer-check-01", "to_node": "source-map-repair-01"})
    edges.append({"from_node": "source-map-repair-01", "to_node": "appendix-agent-01"})

    nodes.append(
        _node(
            node_id="finalize-draft-01",
            role="finalize-draft",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/finalize-draft-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\finalize_draft.py",
                "--topic-id",
                topic_id,
                "--body-node",
                "final-integrator-01",
            ],
        )
    )
    edges.append({"from_node": "appendix-agent-01", "to_node": "finalize-draft-01"})

    nodes.append(
        _node(
            node_id="final-draft-integrity-01",
            role="final-draft-integrity",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/final-draft-integrity-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\validate_full_draft_integrity.py",
                "--topic-id",
                topic_id,
                "--stage",
                "workflow-gate",
            ],
        )
    )
    edges.append({"from_node": "finalize-draft-01", "to_node": "final-draft-integrity-01"})

    nodes.append(
        _node(
            node_id="argument-flow-check-01",
            role="argument-flow-check",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/argument-flow-check-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\validate_argument_flow.py",
                f"tmp\\{topic_id}-draft.md",
                "--topic-id",
                topic_id,
            ],
        )
    )
    edges.append({"from_node": "final-draft-integrity-01", "to_node": "argument-flow-check-01"})

    nodes.append(
        _node(
            node_id="code-check-01",
            role="code-check",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/code-check-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\scripts\\check_article.py",
                f"tmp\\{topic_id}-draft.md",
                "--topic-id",
                topic_id,
            ],
        )
    )
    edges.append({"from_node": "argument-flow-check-01", "to_node": "code-check-01"})

    nodes.append(
        _node(
            node_id="human-approval-01",
            role="human-approval",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/human-approval-01/output.json",
            schema="none",
            node_type="human-approval",
            env={
                "approval_key": "final-article-approval",
                "approval_message": "全文终审完成，请人工确认最终文章是否通过。",
            },
        )
    )
    edges.append({"from_node": "code-check-01", "to_node": "human-approval-01"})
    return nodes, edges


def compile_nodes(topic_id: str, project_root: Path) -> tuple[list[dict], list[dict]]:
    project_dir = build_project_dir(project_root, topic_id)
    section_manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    article_requirements = read_json(project_dir / "article-requirements.json", {})
    workflow_profile = read_json(project_dir / "workflow-profile.json", {"strategy": DEFAULT_STRATEGY})
    if _workflow_mode(workflow_profile) in {"lean", "lean-v1", "compact"}:
        return compile_nodes_lean(topic_id, project_root)
    strategy = workflow_profile.get("strategy", DEFAULT_STRATEGY)
    strategy_profile = get_strategy_profile(strategy)
    is_teaching_playbook = strategy == "teaching-playbook"
    prompt_contracts = strategy_profile.get("prompt_contracts", {})

    def _contract(key: str) -> str:
        return str(prompt_contracts.get(key, "")).strip()

    skill_root_expr = 'str(SKILL_ROOT / "{path}")'
    nodes: list[dict] = []
    edges: list[dict] = []
    sections = [section for section in section_manifest.get("sections", []) if section.get("section_id")]
    author_style_inputs = [
        "skills/article-director/style-profiles/style-guide.md",
        "skills/article-director/style-profiles/cognitive-style-guide.md",
        "skills/article-director/style-profiles/author-soul.md",
        "skills/article-director/style-profiles/anti-patterns.json",
    ]
    ai_tone_contract_inputs = [
        "D:/知识库/skills/内容生产/ai-tone-director/SKILL.md",
        "D:/知识库/skills/内容生产/ai-tone-director/agents/director/SKILL.md",
        "D:/知识库/skills/内容生产/ai-tone-director/workflows/article-director-integration.md",
        "D:/知识库/skills/内容生产/ai-tone-director/schemas/ai-tone-audit.schema.json",
        "D:/知识库/skills/内容生产/ai-tone-director/schemas/ai-tone-context-pack.schema.json",
        "D:/知识库/skills/内容生产/ai-tone-director/schemas/ai-tone-regression.schema.json",
        "D:/知识库/skills/内容生产/ai-tone-director/templates/ai-tone-repair-plan.md",
        "D:/知识库/skills/内容生产/ai-tone-director/scripts/invocation_log.py",
    ]
    author_core_inputs = author_style_inputs + ai_tone_contract_inputs
    author_exemplar_inputs = [
        "skills/article-director/style-profiles/exemplars/opening-patterns.md",
        "skills/article-director/style-profiles/exemplars/transition-patterns.md",
        "skills/article-director/style-profiles/exemplars/evidence-patterns.md",
        "skills/article-director/style-profiles/exemplars/closing-patterns.md",
    ]
    report_style_inputs = [
        "skills/report-style-analyzer/references/weihestyle-profile.md",
        "skills/report-style-analyzer/references/weihestyle-language-bank.md",
        "skills/report-style-analyzer/references/weihestyle-paragraph-rhythm.md",
        "skills/report-style-analyzer/references/weihestyle-review-rubric.md",
        "skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md",
    ]
    argument_spine_inputs: list[str] = []
    nodes.append(
        _node(
            node_id="build-node-micro-plans-01",
            role="micro-plan-builder",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/micro-plan/node-micro-plans.json",
            node_type="script",
            input_files=[
                f"skills/article-director/outputs/{topic_id}/section-manifest.json",
            ],
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\build_node_micro_plans.py",
                "--topic-id",
                topic_id,
            ],
            package_type="micro-plan",
            risk_tier="low",
        )
    )
    nodes.append(
        _node(
            node_id="seed-longform-memory-01",
            role="seed-longform-memory",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/memory/term-registry.json",
            schema="none",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\seed_longform_article_memory.py",
                "--topic-id",
                topic_id,
            ],
            package_type="memory",
            risk_tier="low",
        )
    )

    for order, section in enumerate(sections, start=1):
        section_id = str(section["section_id"])
        heading = str(section.get("heading") or section_id)
        section_dir = f"skills/article-director/outputs/{topic_id}/sections/{section_id}"
        argument_spine_path = f"{section_dir}/argument-spine.md"
        writer_context_window_path = f"{section_dir}/writer-context-window.json"
        writer_control_log_path = f"{section_dir}/writer-control-log.json"
        argument_spine_inputs.append(argument_spine_path)
        base_section_inputs = [
            f"skills/article-director/outputs/{topic_id}/article-requirements.json",
            f"skills/article-director/outputs/{topic_id}/section-manifest.json",
            f"tmp/{topic_id}-detailed-outline.md",
        ]
        article_requirements_path = f"skills/article-director/outputs/{topic_id}/article-requirements.json"
        section_manifest_path = f"skills/article-director/outputs/{topic_id}/section-manifest.json"
        detailed_outline_path = f"tmp/{topic_id}-detailed-outline.md"
        section_manifest_input = _allowed_input(section_manifest_path, "section_manifest", section_id=section_id)
        manifest_summary_input = _allowed_input(section_manifest_path, "section_manifest_summary", max_chars=12000)
        section_outline_input = _allowed_input(
            detailed_outline_path,
            "markdown_sections",
            section_headings=[heading],
            max_chars=18000,
        )
        article_requirements_input = _allowed_input(article_requirements_path, "full_text", max_chars=10000)
        argument_spine_input = _allowed_input(argument_spine_path, "full_text", max_chars=10000)
        writer_context_input = _allowed_input(writer_context_window_path, "full_text", max_chars=12000)
        writer_control_input = _allowed_input(writer_control_log_path, "full_text", max_chars=12000)
        style_allowed_inputs = [
            _allowed_input("skills/article-director/style-profiles/style-guide.md", "full_text", max_chars=12000),
            _allowed_input("skills/article-director/style-profiles/cognitive-style-guide.md", "full_text", max_chars=12000),
            _allowed_input("skills/article-director/style-profiles/author-soul.md", "full_text", max_chars=8000),
            _allowed_input("skills/article-director/style-profiles/anti-patterns.json", "full_text", max_chars=8000),
            _allowed_input("skills/report-style-analyzer/references/weihestyle-profile.md", "full_text", max_chars=12000),
            _allowed_input("skills/report-style-analyzer/references/weihestyle-paragraph-rhythm.md", "full_text", max_chars=12000),
        ]
        review_protocol_input = _allowed_input(
            "skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md",
            "full_text",
            max_chars=12000,
        )
        ai_tone_contract_input = _allowed_input(
            "D:/知识库/skills/内容生产/ai-tone-director/workflows/article-director-integration.md",
            "full_text",
            max_chars=12000,
        )
        ai_tone_schema_input = _allowed_input(
            "D:/知识库/skills/内容生产/ai-tone-director/schemas/ai-tone-audit.schema.json",
            "full_text",
            max_chars=12000,
        )
        writer_planning_inputs = [
            article_requirements_input,
            section_manifest_input,
            section_outline_input,
            argument_spine_input,
            writer_context_input,
        ] + style_allowed_inputs + [ai_tone_contract_input]
        writer_body_inputs = writer_planning_inputs + [writer_control_input]
        common_inputs = base_section_inputs + author_core_inputs + report_style_inputs
        writer_controller_inputs = (
            base_section_inputs
            + [argument_spine_path, writer_context_window_path]
            + author_style_inputs
            + ai_tone_contract_inputs
            + report_style_inputs
            + author_exemplar_inputs
        )
        writer_inputs = (
            base_section_inputs
            + [argument_spine_path, writer_context_window_path, writer_control_log_path]
            + author_style_inputs
            + ai_tone_contract_inputs
            + report_style_inputs
            + author_exemplar_inputs
        )
        ai_tone_prewrite_context = render_prewrite_context(
            build_prewrite_context(section, article_requirements)
        )
        author_style_prewrite_context = render_author_style_prewrite_context(section, article_requirements)

        def _section_node(
            node_id: str,
            role: str,
            skill_path: str,
            temperature: float,
            output_name: str,
            schema: str,
            input_files: list[str],
            task_prefix: str,
            node_type: str = "agent",
            command: list[str] | None = None,
            allowed_inputs: list[dict] | None = None,
        ) -> dict:
            return _node(
                node_id=node_id,
                role=role,
                skill_file=skill_root_expr.format(path=skill_path),
                temperature=temperature,
                output_file=f"{section_dir}/{output_name}",
                schema=schema,
                input_files=input_files,
                task_prefix=task_prefix,
                node_type=node_type,
                parallel=node_type == "agent",
                provider="codex",
                package_type="section",
                package_order=order,
                risk_tier=str(section.get("risk_tier") or "medium"),
                section_group=section_id,
                command=command or [],
                allowed_inputs=allowed_inputs or [],
                **_node_micro_plan_fields(topic_id, node_id, "section-loop", "standard"),
            )

        build_argument_spine_id = f"build-argument-spine-{section_id}"
        nodes.append(
            _section_node(
                build_argument_spine_id,
                "build-argument-spine",
                "agents/director/SKILL.md",
                0.0,
                "argument-spine.md",
                "none",
                base_section_inputs,
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\build_argument_spine.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )

        writer_context_id = f"build-writer-context-window-{section_id}"
        nodes.append(
            _section_node(
                writer_context_id,
                "build-writer-context-window",
                "agents/director/SKILL.md",
                0.0,
                "writer-context-window.json",
                "none",
                base_section_inputs + [argument_spine_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\build_writer_context_window.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )
        edges.append({"from_node": build_argument_spine_id, "to_node": writer_context_id})

        writer_control_id = f"plan-writer-controller-{section_id}"
        nodes.append(
            _section_node(
                writer_control_id,
                "writer-controller",
                "agents/writer-research/SKILL.md",
                0.2,
                "writer-control-log.json",
                "none",
                writer_controller_inputs,
                (
                    f"[writer-controller] Plan writing for section_id={section_id}; heading={heading}. "
                    "Do not write the article body yet. Read writer-context-window.json first. "
                    "Use previous_block and next_block only as context; do not rewrite or depend on generated drafts from other sections. "
                    "Read the ai-tone-prewrite-context below before creating reader_use_contract. "
                    "Copy its avoid_before_writing items into reader_use_contract.must_not_do, adapted to this section, and do not downgrade them to optional style advice. "
                    "If an avoided sentence family seems useful for the argument, keep the reasoning but choose a different expression. "
                    "Read author-style-prewrite-context as style guidance after the de-AI expression constraints are preserved. "
                    "Generate strict JSON with keys: context_map, reader_use_contract, deliberation_log, write_readiness, upstream_issue, downstream_issue, self_check. "
                    "context_map must state previous_solved, current_job, next_dependency, and risks. "
                    "reader_use_contract must state reader_state_before, reader_state_after, concrete_anchor, writing_move, reasoning_depth, compressible_items, and must_not_do; keep paragraph_role, abstraction_budget, and continuity_rule only when they are genuinely useful. "
                    "deliberation_log should contain one concise decision round by default and at most two rounds when there is context conflict, missing material, or scope risk; stop as soon as the section is ready to draft. "
                    "Record missing context as upstream_issue or downstream_issue instead of hiding it. "
                    "Output JSON only."
                    f"\n\n{ai_tone_prewrite_context}\n\n{author_style_prewrite_context}\n"
                ),
                allowed_inputs=writer_planning_inputs,
            )
        )
        edges.append({"from_node": writer_context_id, "to_node": writer_control_id})

        writer_id = f"writer-section-{section_id}"
        draft_path = f"{section_dir}/draft.md"
        nodes.append(
            _section_node(
                writer_id,
                "writer-section",
                "agents/writer-research/SKILL.md",
                0.35,
                "draft.md",
                "none",
                writer_inputs,
                (
                    f"[段落写作] 只写 section_id={section_id}，标题《{heading}》。"
                    "必须读取 article-requirements.json，遵守字数、重点段落、新需求和个人风格要求。"
                    "必须先读取 argument-spine.md，它是本节逻辑链和气口的上游契约。"
                    "必须读取 writer-context-window.json 和 writer-control-log.json；前者给上一节/本节/下一节上下文，后者是本节写作契约和决策日志。"
                    "必须读取 style-guide.md、cognitive-style-guide.md 与 author-soul.md；学习作者从真实困惑进入、给判断、展示推理、做取舍的写法，并避免老师讲课式姿态。"
                    "写每个段落前先读取 ai-tone-prewrite-context 小上下文；它是写前表达约束，不是写后审查。"
                    "不能用它删掉逻辑链，但必须换掉 avoid_before_writing 命中的模板句式。"
                    "只输出本章节 Markdown，保留一个 ## 标题，不写其他章节。"
                    f"\n\n{ai_tone_prewrite_context}\n"
                    + (f" {_contract('writer_contract_suffix')}" if _contract("writer_contract_suffix") else "")
                ),
                allowed_inputs=writer_body_inputs,
            )
        )

        nodes[-1]["task_prefix"] = (
            f"[section-writing] Write only section_id={section_id}; heading={heading}. "
            "Read article-requirements.json and follow target length, priority sections, new requirements, "
            "and personal style notes. Read argument-spine.md first; it is the upstream contract for this "
            "section's must-keep reasoning, compressible explanation, and paragraph breath. Read writer-context-window.json and writer-control-log.json before drafting; writer-control-log.json is the local controller contract and decision log for this section. Read style-guide.md, cognitive-style-guide.md, and author-soul.md; follow the author's "
            "0-to-1 understanding path: real confusion -> judgment -> reasoning -> example/boundary -> next step. "
            "Use author-soul.md to write from the author's experience-and-tradeoff posture instead of a lecture or tutorial posture. "
            "Use previous_block and next_block from writer-context-window.json only to understand continuity; do not modify them, do not invent fake continuity if they are missing, and do not make section execution sequential. "
            "Write from the final reader_use_contract in writer-control-log.json. If write_readiness is blocked, preserve the section scope and surface the missing setup in the draft with the least disruptive wording rather than silently jumping. "
            "Before drafting the current writing unit, apply the compact ai-tone-prewrite-context and "
            "author-style-prewrite-context blocks below as writing input, not as post-review nodes. "
            "The reader_use_contract.must_not_do list must already contain the ai-tone avoid_before_writing constraints; obey them while preserving must-keep information from the argument-spine. "
            "Do not treat ai-tone-prewrite-context as second-priority or optional. If a listed AI-like sentence family appears tempting, keep the idea and rewrite the expression instead of using that shell. "
            "Use author-style-prewrite-context to control cognitive path and rhythm variation; do not copy catchphrases. "
            "Use weihestyle-profile.md and weihestyle-paragraph-rhythm.md as the default report-writing style assets. "
            "Match reasoning depth to the section: light for opening, definition, transition, summary, table, or checklist sections; medium for mechanism, boundary, or method sections; deep only for core disputes or key judgments. Do not force every section to contain a long reasoning paragraph. Mark material that can later be compressed instead of making the draft final-short. "
            "Use exemplars as style references without copying their topics. Output Markdown for this section only. Keep exactly one ## heading. "
            "Do not write other sections. "
            f"\n\n{ai_tone_prewrite_context}\n\n{author_style_prewrite_context}\n\n"
            + (f" {_contract('writer_contract_suffix')}" if _contract("writer_contract_suffix") else "")
        )
        edges.append({"from_node": writer_control_id, "to_node": writer_id})
        edges.append({"from_node": build_argument_spine_id, "to_node": writer_id})

        tag_id = f"tag-paragraphs-{section_id}"
        tag_path = f"{section_dir}/paragraph-tags.json"
        ai_tone_context_path = f"{section_dir}/ai-tone-context-pack.json"
        ai_tone_scan_path = f"{section_dir}/ai-tone-scan.json"
        ai_tone_audit_gate_path = f"{section_dir}/ai-tone-audit-gate.json"
        ai_tone_repair_plan_path = f"{section_dir}/ai-tone-repair-plan.md"
        ai_tone_regression_path = f"{section_dir}/ai-tone-regression.json"
        ai_tone_log_dir = f"skills/article-director/outputs/{topic_id}/logs"
        nodes.append(
            _section_node(
                tag_id,
                "paragraph-function-tagger",
                "agents/director/SKILL.md",
                0.0,
                "paragraph-tags.json",
                "none",
                [draft_path, "skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md"],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\tag_paragraph_functions.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )
        edges.append({"from_node": writer_id, "to_node": tag_id})

        prepare_ai_tone_id = f"prepare-ai-tone-call-{section_id}"
        nodes.append(
            _section_node(
                prepare_ai_tone_id,
                "prepare-ai-tone-call",
                "agents/director/SKILL.md",
                0.0,
                "ai-tone-context-pack.json",
                "ai-tone-context-pack",
                [draft_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    AI_TONE_INVOCATION_SCRIPT,
                    "prepare",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                    "--input",
                    f"{{project_root}}\\{draft_path}",
                    "--context-output",
                    f"{{project_root}}\\{ai_tone_context_path}",
                    "--scan-output",
                    f"{{project_root}}\\{ai_tone_scan_path}",
                    "--log-dir",
                    f"{{project_root}}\\{ai_tone_log_dir}",
                ],
            )
        )
        edges.append({"from_node": tag_id, "to_node": prepare_ai_tone_id})

        review_specs = [
            ("review-ai-tone", "ai_tone", "Review AI tone using ai-tone-director. Output JSON compatible with ai-tone-audit.schema.json and do not rewrite the draft."),
            ("review-logic", "logic", "Review arguments, causality, jumps, and whether evidence supports claims."),
            ("review-structure", "structure", "Review whether paragraphs, bullets, tables, lists, or steps are needed."),
            ("extract-terms", "terms", "Extract proper nouns, key concepts, and terms that may need explanation."),
        ]
        previous = prepare_ai_tone_id
        review_outputs: list[str] = []
        for prefix, dimension, instruction in review_specs:
            node_id = f"{prefix}-{section_id}"
            output_name = "terms.json" if prefix == "extract-terms" else f"{prefix.replace('review-', 'review-')}.json"
            schema = "term-extraction-result" if prefix == "extract-terms" else "section-review-result"
            review_input_files = common_inputs + [argument_spine_path, draft_path, tag_path]
            if prefix == "review-ai-tone":
                review_input_files += [ai_tone_context_path, ai_tone_scan_path]
            task = (
                f"[段落审查:{dimension}] 只审 section_id={section_id}《{heading}》。{instruction}"
                "审查 agent 温度固定为0，只输出 JSON，不改正文。"
                "JSON 至少包含 pass, score, summary；普通问题放 issues，阻断问题放 blocking_issues。"
                if prefix != "extract-terms"
                else (
                    f"[专有名词提取] 只处理 section_id={section_id}《{heading}》。"
                    "输出 JSON：terms 数组和 summary。terms 每项包含 term, explanation_needed, reason。不得改正文。"
                )
            )
            nodes.append(
                _section_node(
                    node_id,
                    prefix,
                    "agents/article-review/SKILL.md",
                    SECTION_REVIEW_TEMP,
                    output_name,
                    schema,
                    review_input_files,
                    task,
                )
            )
            if prefix == "extract-terms":
                nodes[-1]["task_prefix"] = (
                    f"[term-extraction] Process only section_id={section_id}; heading={heading}. "
                    "Output JSON only with terms and summary. Each term should include term, explanation_needed, "
                    "and reason. Do not rewrite article text."
                )
            else:
                ai_tone_contract = ""
                if prefix == "review-ai-tone":
                    ai_tone_contract = (
                        "This is an independent ai-tone-director invocation for this section. "
                        "You must read ai-tone-context-pack.json and ai-tone-scan.json. "
                        "Do not reuse another section's judgment. "
                        "The output must include ai_tone_invocation exactly matching ai-tone-context-pack.json: "
                        "topic_id, section_id, phase, idempotency_key, and source_hash. "
                        "If deterministic scan has hits but you judge them acceptable, add deterministic_evidence_acknowledged=true "
                        "and false_positive_notes explaining why. "
                    )
                style_posture_contract = ""
                if prefix in {"review-logic", "review-structure"}:
                    style_posture_contract = (
                        "Use cognitive-style-guide.md and author-soul.md to judge whether the section matches the author's reasoning path and speaking posture. "
                    )
                nodes[-1]["task_prefix"] = (
                    f"[section-review:{dimension}] Review only section_id={section_id}; heading={heading}. {instruction} "
                    f"{ai_tone_contract}"
                    f"{style_posture_contract}"
                    "Use paragraph-tags.json and paragraph-tagging-review-protocol.md as marker-based hints: first respect each paragraph's function label, "
                    "then review only the checks relevant to that label; do not require every paragraph to contain problem, evidence, action, and boundary. "
                    "If a paragraph tag looks wrong or low confidence, report tag uncertainty and judge by the paragraph's actual function. "
                    "For logic review, read argument-spine.md and explicitly check for viewpoint stringing, missing middle reasoning, and excessive short-breath paragraphs. "
                    "Report cross-paragraph chain gaps separately. "
                    "Review temperature is fixed at 0.00. Output JSON only and do not rewrite article text. "
                    "JSON must include pass, score, summary, scope, dimension, issues, blocking_issues, advisory_issues, and must_fix. "
                    "For AI-tone issues, include reason_type, why_ai_like, and repair_strategy when possible."
                )
            draft_input = _allowed_input(draft_path, "full_text", max_chars=18000)
            tag_input = _allowed_input(tag_path, "full_text", max_chars=16000)
            if prefix == "review-ai-tone":
                allowed_review_inputs = [
                    section_manifest_input,
                    draft_input,
                    tag_input,
                    _allowed_input(ai_tone_context_path, "full_text", max_chars=12000),
                    _allowed_input(ai_tone_scan_path, "full_text", max_chars=12000),
                    ai_tone_contract_input,
                    ai_tone_schema_input,
                ]
            elif prefix == "review-logic":
                allowed_review_inputs = [
                    section_manifest_input,
                    draft_input,
                    argument_spine_input,
                    tag_input,
                    _allowed_input("skills/article-director/style-profiles/cognitive-style-guide.md", "full_text", max_chars=12000),
                    _allowed_input("skills/article-director/style-profiles/author-soul.md", "full_text", max_chars=8000),
                    review_protocol_input,
                ]
            elif prefix == "review-structure":
                allowed_review_inputs = [
                    section_manifest_input,
                    draft_input,
                    argument_spine_input,
                    tag_input,
                    _allowed_input("skills/article-director/style-profiles/cognitive-style-guide.md", "full_text", max_chars=12000),
                    _allowed_input("skills/article-director/style-profiles/author-soul.md", "full_text", max_chars=8000),
                    review_protocol_input,
                ]
            else:
                allowed_review_inputs = [
                    section_manifest_input,
                    draft_input,
                    tag_input,
                ]
            edges.append({"from_node": previous, "to_node": node_id})
            nodes[-1]["allowed_inputs"] = allowed_review_inputs
            previous = node_id
            review_outputs.append(f"{section_dir}/{output_name}")
            if prefix == "review-ai-tone":
                audit_gate_id = f"validate-ai-tone-audit-{section_id}"
                nodes.append(
                    _section_node(
                        audit_gate_id,
                        "validate-ai-tone-audit",
                        "agents/director/SKILL.md",
                        0.0,
                        "ai-tone-audit-gate.json",
                        "code-check-result",
                        [ai_tone_context_path, ai_tone_scan_path, f"{section_dir}/review-ai-tone.json"],
                        "",
                        node_type="script",
                        command=[
                            "{python}",
                            AI_TONE_INVOCATION_SCRIPT,
                            "validate-audit",
                            "--context",
                            f"{{project_root}}\\{ai_tone_context_path}",
                            "--audit",
                            f"{{project_root}}\\{section_dir}\\review-ai-tone.json",
                            "--gate-output",
                            f"{{project_root}}\\{ai_tone_audit_gate_path}",
                        ],
                    )
                )
                edges.append({"from_node": node_id, "to_node": audit_gate_id})
                repair_plan_id = f"build-ai-tone-repair-plan-{section_id}"
                nodes.append(
                    _section_node(
                        repair_plan_id,
                        "build-ai-tone-repair-plan",
                        "agents/director/SKILL.md",
                        0.0,
                        "ai-tone-repair-plan.md",
                        "none",
                        [ai_tone_context_path, f"{section_dir}/review-ai-tone.json", ai_tone_audit_gate_path],
                        "",
                        node_type="script",
                        command=[
                            "{python}",
                            AI_TONE_INVOCATION_SCRIPT,
                            "repair-plan",
                            "--context",
                            f"{{project_root}}\\{ai_tone_context_path}",
                            "--audit",
                            f"{{project_root}}\\{section_dir}\\review-ai-tone.json",
                            "--output",
                            f"{{project_root}}\\{ai_tone_repair_plan_path}",
                        ],
                    )
                )
                edges.append({"from_node": audit_gate_id, "to_node": repair_plan_id})
                previous = repair_plan_id

        context_id = f"build-section-review-context-{section_id}"
        nodes.append(
            _section_node(
                context_id,
                "build-section-review-context",
                "agents/director/SKILL.md",
                0.0,
                "section-review-context.json",
                "section-review-context",
                review_outputs + [argument_spine_path, tag_path, ai_tone_context_path, ai_tone_scan_path, ai_tone_audit_gate_path, ai_tone_repair_plan_path],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\build_section_review_context.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )
        edges.append({"from_node": previous, "to_node": context_id})

        revision_specs = [
            ("revise-structure", "agents/structure-editor/SKILL.md", "revision-structure.md", "Improve paragraphing and bullet structure while preserving claims and evidence."),
            ("revise-de-ai", "agents/narrative-smoother/SKILL.md", "revision-de-ai.md", "Apply ai-tone-director audit/repair-plan items for this section only; do not use local AI-tone rules."),
            ("revise-personal-style", "agents/style-harmonizer/SKILL.md", "revision-personal-style.md", "Inject the user's personal style, cognitive path, logic, prioritization, tone, and expression habits."),
            ("revise-logic", "agents/narrative-smoother/SKILL.md", "revision-logic.md", "Improve logical transitions, causality, and argument closure."),
        ]
        previous = context_id
        current_input = draft_path
        revision_dimensions = {
            "revise-structure": "structure",
            "revise-de-ai": "ai_tone",
            "revise-personal-style": "ai_tone, style_alignment, human_feel",
            "revise-logic": "logic",
        }
        for prefix, skill_path, output_name, instruction in revision_specs:
            node_id = f"{prefix}-{section_id}"
            relevant_dimensions = revision_dimensions[prefix]
            revision_input = current_input
            extra_revision_inputs = []
            if prefix == "revise-de-ai":
                extra_revision_inputs = [
                    ai_tone_context_path,
                    ai_tone_scan_path,
                    f"{section_dir}/review-ai-tone.json",
                    ai_tone_audit_gate_path,
                    ai_tone_repair_plan_path,
                ]
            current_revision_input = _allowed_input(current_input, "full_text", max_chars=22000)
            review_context_input = _allowed_input(
                f"{section_dir}/section-review-context.json",
                "full_text",
                max_chars=18000,
            )
            tag_input = _allowed_input(tag_path, "full_text", max_chars=12000)
            if prefix == "revise-structure":
                allowed_revision_inputs = [
                    section_manifest_input,
                    current_revision_input,
                    review_context_input,
                    tag_input,
                    argument_spine_input,
                    review_protocol_input,
                ]
            elif prefix == "revise-de-ai":
                allowed_revision_inputs = [
                    section_manifest_input,
                    current_revision_input,
                    review_context_input,
                    _allowed_input(ai_tone_context_path, "full_text", max_chars=12000),
                    _allowed_input(ai_tone_scan_path, "full_text", max_chars=12000),
                    _allowed_input(f"{section_dir}/review-ai-tone.json", "full_text", max_chars=12000),
                    _allowed_input(ai_tone_repair_plan_path, "full_text", max_chars=12000),
                    ai_tone_contract_input,
                ]
            elif prefix == "revise-personal-style":
                allowed_revision_inputs = [
                    section_manifest_input,
                    current_revision_input,
                    review_context_input,
                    argument_spine_input,
                ] + style_allowed_inputs
            else:
                allowed_revision_inputs = [
                    section_manifest_input,
                    current_revision_input,
                    review_context_input,
                    argument_spine_input,
                    _allowed_input("skills/article-director/style-profiles/cognitive-style-guide.md", "full_text", max_chars=12000),
                    _allowed_input("skills/article-director/style-profiles/author-soul.md", "full_text", max_chars=8000),
                ]
            revision_contract_zh = {
                "revise-structure": "必须消费 section-review-context.json、paragraph-tags.json、argument-spine.md 和段落标注审查协议。",
                "revise-de-ai": "必须消费 ai-tone-context-pack.json、review-ai-tone.json、ai-tone-repair-plan.md 和 ai-tone-director 接入契约；不要复制本地去 AI 规则。",
                "revise-personal-style": "必须消费 style-guide.md、cognitive-style-guide.md、author-soul.md 和 section-review-context.json，修正作者站位后再做表层文风。",
                "revise-logic": "必须消费 cognitive-style-guide.md、author-soul.md、argument-spine.md 和 section-review-context.json。",
            }[prefix]
            revision_contract_en = {
                "revise-structure": "Consume section-review-context.json, paragraph-tags.json, argument-spine.md, and the paragraph tagging review protocol.",
                "revise-de-ai": "Consume ai-tone-context-pack.json, review-ai-tone.json, ai-tone-repair-plan.md, and the ai-tone-director integration contract; do not duplicate local AI-tone rules.",
                "revise-personal-style": "Consume style-guide.md, cognitive-style-guide.md, author-soul.md, and section-review-context.json; repair author-soul posture before surface style.",
                "revise-logic": "Consume cognitive-style-guide.md, author-soul.md, argument-spine.md, and section-review-context.json.",
            }[prefix]
            nodes.append(
                _section_node(
                    node_id,
                    prefix,
                    skill_path,
                    SECTION_REVISER_TEMP,
                    output_name,
                    "none",
                    common_inputs
                    + (author_exemplar_inputs if prefix == "revise-personal-style" else [])
                    + extra_revision_inputs
                    + [argument_spine_path, current_input, f"{section_dir}/section-review-context.json", tag_path],
                    (
                        f"[段落修改:{prefix}] 只修改 section_id={section_id}《{heading}》。{instruction}"
                        "修改 agent 温度固定为0.30。必须消费 section-review-context.json。"
                        f"{revision_contract_zh}"
                        "只输出修订后的本章节 Markdown，保留 ## 标题，不输出解释。"
                    ),
                    allowed_inputs=allowed_revision_inputs,
                )
            )
            nodes[-1]["task_prefix"] = (
                f"[section-revision:{prefix}] Revise only section_id={section_id}; heading={heading}. {instruction} "
                f"Revision temperature is fixed at 0.30. {revision_contract_en} Preserve facts and section scope. "
                "Use paragraph tags to repair only the paragraph's assigned function; do not turn every paragraph into a full mini-report. "
                "Preserve necessary reasoning from argument-spine.md, but compress overlong explanation and do not force a long reasoning paragraph when the section only needs light depth. "
                f"Relevant review dimensions for this node: {relevant_dimensions}. If section-review-context.json has no blocking_issues "
                "or advisory_issues for those dimensions, output the current input unchanged except for obvious typos. "
                "For revise-de-ai, ai-tone-context-pack.json, review-ai-tone.json, and ai-tone-repair-plan.md are mandatory; "
                "if the audit has issues, do not output an unchanged copy. "
                "Output the revised Markdown section only. Keep one ## heading and do not output explanations."
            )
            edges.append({"from_node": previous, "to_node": node_id})
            previous = node_id
            current_input = f"{section_dir}/{output_name}"
            if prefix == "revise-de-ai":
                regression_id = f"ai-tone-regression-{section_id}"
                nodes.append(
                    _section_node(
                        regression_id,
                        "ai-tone-regression",
                        "agents/director/SKILL.md",
                        0.0,
                        "ai-tone-regression.json",
                        "code-check-result",
                        [
                            ai_tone_context_path,
                            f"{section_dir}/review-ai-tone.json",
                            revision_input,
                            current_input,
                        ],
                        "",
                        node_type="script",
                        command=[
                            "{python}",
                            AI_TONE_INVOCATION_SCRIPT,
                            "regression",
                            "--context",
                            f"{{project_root}}\\{ai_tone_context_path}",
                            "--audit",
                            f"{{project_root}}\\{section_dir}\\review-ai-tone.json",
                            "--before",
                            f"{{project_root}}\\{revision_input}",
                            "--after",
                            f"{{project_root}}\\{current_input}",
                            "--output",
                            f"{{project_root}}\\{ai_tone_regression_path}",
                        ],
                    )
                )
                edges.append({"from_node": node_id, "to_node": regression_id})
                previous = regression_id

        complete_id = f"section-complete-{section_id}"
        nodes.append(
            _section_node(
                complete_id,
                "section-complete",
                "agents/director/SKILL.md",
                0.0,
                "complete.json",
                "code-check-result",
                [f"{section_dir}/revision-logic.md"],
                "",
                node_type="script",
                command=[
                    "{python}",
                    "{project_root}\\skills\\article-director\\scripts\\complete_section.py",
                    "--topic-id",
                    topic_id,
                    "--section-id",
                    section_id,
                ],
            )
        )
        edges.append({"from_node": previous, "to_node": complete_id})
        edges.append({"from_node": "seed-longform-memory-01", "to_node": build_argument_spine_id})

    nodes.append(
        _node(
            node_id="draft-assembler-01",
            role="draft-assembler",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/draft-assembler-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\assemble_draft.py",
                "--topic-id",
                topic_id,
            ],
        )
    )
    for section in sections:
        edges.append({"from_node": f"section-complete-{section['section_id']}", "to_node": "draft-assembler-01"})

    edges.append({"from_node": "build-node-micro-plans-01", "to_node": "seed-longform-memory-01"})

    nodes.append(
        _node(
            node_id="style-harmonizer-01",
            role="style-harmonizer",
            skill_file=skill_root_expr.format(path="agents/style-harmonizer/SKILL.md"),
            temperature=0.10,
            output_file=f"skills/article-director/outputs/{topic_id}/style-harmonizer-01/output.md",
            schema="none",
            input_files=[
                f"tmp/{topic_id}-draft.md",
                f"skills/article-director/outputs/{topic_id}/article-requirements.json",
                f"skills/article-director/outputs/{topic_id}/section-manifest.json",
            ]
            + author_core_inputs
            + argument_spine_inputs
            + author_exemplar_inputs
            + report_style_inputs,
            task_prefix=(
                "[full-draft-style-harmonizer] This is not a rewrite from scratch. "
                "Read the assembled draft plus style-guide.md, cognitive-style-guide.md, author-soul.md, anti-patterns.json, "
                "all section argument-spine.md files, "
                "ai-tone-director integration contract, weihestyle-profile.md, weihestyle-paragraph-rhythm.md, "
                "and paragraph-tagging-review-protocol.md. "
                "Preserve every ## section heading and all facts, evidence, "
                "tables, steps, and source direction. Harmonize tone and align "
                "the whole article to the author's cognitive path and author-soul posture: real confusion -> judgment -> reasoning -> "
                "example/boundary -> next step. Check the full article chain without forcing every paragraph "
                "to contain every element. Preserve necessary reasoning from argument spines while protecting readability; do not turn one required causal chain into short viewpoint strings, but also do not keep overlong reasoning solely because it exists. Apply AI-tone repair only when an ai-tone-repair-plan is provided, "
                "Remove low-information bridge sentences that only announce continuity and add no new judgment, example, boundary, or action. "
                "and do not copy AI-tone rules into this node. Output the complete Markdown article only."
            ),
            provider="codex",
            package_type="full-draft-style",
            risk_tier="medium",
            allowed_inputs=[
                _allowed_input(f"tmp/{topic_id}-draft.md", "full_text", max_chars=60000),
                _allowed_input(f"skills/article-director/outputs/{topic_id}/article-requirements.json", "full_text", max_chars=12000),
                _allowed_input(f"skills/article-director/outputs/{topic_id}/section-manifest.json", "section_manifest_summary", max_chars=20000),
                _allowed_input("skills/article-director/style-profiles/style-guide.md", "full_text", max_chars=12000),
                _allowed_input("skills/article-director/style-profiles/cognitive-style-guide.md", "full_text", max_chars=12000),
                _allowed_input("skills/article-director/style-profiles/author-soul.md", "full_text", max_chars=8000),
                _allowed_input("skills/report-style-analyzer/references/weihestyle-profile.md", "full_text", max_chars=12000),
                _allowed_input("skills/report-style-analyzer/references/weihestyle-paragraph-rhythm.md", "full_text", max_chars=12000),
                _allowed_input("skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md", "full_text", max_chars=12000),
                _allowed_input("D:/知识库/skills/内容生产/ai-tone-director/workflows/article-director-integration.md", "full_text", max_chars=12000),
            ]
            + [_allowed_input(argument_spine_path, "full_text", max_chars=8000) for argument_spine_path in argument_spine_inputs],
        )
    )

    nodes.append(
        _node(
            node_id="style-harmonizer-check-01",
            role="style-harmonizer-check",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/style-harmonizer-check-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\validate_style_harmonizer_output.py",
                "--topic-id",
                topic_id,
            ],
        )
    )

    nodes.append(
        _node(
            node_id="source-map-repair-01",
            role="source-map-repair",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/memory/source-map.md",
            schema="none",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\repair_source_map_from_draft.py",
                "--topic-id",
                topic_id,
            ],
        )
    )
    nodes.append(
        _node(
            node_id="appendix-agent-01",
            role="appendix-builder",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/appendix-agent-01/output.md",
            schema="none",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\build_longform_appendix.py",
                "--topic-id",
                topic_id,
            ],
        )
    )
    edges.append({"from_node": "draft-assembler-01", "to_node": "style-harmonizer-01"})
    edges.append({"from_node": "style-harmonizer-01", "to_node": "style-harmonizer-check-01"})
    edges.append({"from_node": "style-harmonizer-check-01", "to_node": "source-map-repair-01"})
    edges.append({"from_node": "source-map-repair-01", "to_node": "appendix-agent-01"})

    nodes.append(
        _node(
            node_id="finalize-draft-01",
            role="finalize-draft",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/finalize-draft-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\finalize_draft.py",
                "--topic-id",
                topic_id,
            ],
        )
    )
    edges.append({"from_node": "appendix-agent-01", "to_node": "finalize-draft-01"})

    nodes.append(
        _node(
            node_id="final-draft-integrity-01",
            role="final-draft-integrity",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/final-draft-integrity-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\validate_full_draft_integrity.py",
                "--topic-id",
                topic_id,
                "--stage",
                "workflow-gate",
            ],
        )
    )
    edges.append({"from_node": "finalize-draft-01", "to_node": "final-draft-integrity-01"})

    nodes.append(
        _node(
            node_id="argument-flow-check-01",
            role="argument-flow-check",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/argument-flow-check-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\validate_argument_flow.py",
                f"tmp\\{topic_id}-draft.md",
                "--topic-id",
                topic_id,
            ],
        )
    )
    edges.append({"from_node": "final-draft-integrity-01", "to_node": "argument-flow-check-01"})

    final_review_inputs = [
        f"tmp/{topic_id}-draft.md",
        f"skills/article-director/outputs/{topic_id}/article-requirements.json",
        f"skills/article-director/outputs/{topic_id}/section-manifest.json",
        f"skills/article-director/outputs/{topic_id}/style-harmonizer-01/output.md",
    ]
    final_review_inputs += [
        f"skills/article-director/outputs/{topic_id}/sections/{section['section_id']}/section-review-context.json"
        for section in sections
        if section.get("section_id")
    ]
    final_review_inputs += author_core_inputs + argument_spine_inputs + report_style_inputs
    final_review_allowed_inputs = [
        _allowed_input(f"tmp/{topic_id}-draft.md", "full_text", max_chars=60000),
        _allowed_input(f"skills/article-director/outputs/{topic_id}/article-requirements.json", "full_text", max_chars=12000),
        _allowed_input(f"skills/article-director/outputs/{topic_id}/section-manifest.json", "section_manifest_summary", max_chars=20000),
        _allowed_input(f"skills/article-director/outputs/{topic_id}/style-harmonizer-01/output.md", "full_text", max_chars=60000),
    ]
    final_review_allowed_inputs += [
        _allowed_input(
            f"skills/article-director/outputs/{topic_id}/sections/{section['section_id']}/section-review-context.json",
            "full_text",
            max_chars=12000,
        )
        for section in sections
        if section.get("section_id")
    ]
    final_review_allowed_inputs += [
        _allowed_input(argument_spine_path, "full_text", max_chars=8000)
        for argument_spine_path in argument_spine_inputs
    ]
    final_review_allowed_inputs += [
        _allowed_input("skills/article-director/style-profiles/style-guide.md", "full_text", max_chars=12000),
        _allowed_input("skills/article-director/style-profiles/cognitive-style-guide.md", "full_text", max_chars=12000),
        _allowed_input("skills/article-director/style-profiles/author-soul.md", "full_text", max_chars=8000),
        _allowed_input("skills/report-style-analyzer/references/weihestyle-review-rubric.md", "full_text", max_chars=12000),
        _allowed_input("skills/report-style-analyzer/references/paragraph-tagging-review-protocol.md", "full_text", max_chars=12000),
        _allowed_input("D:/知识库/skills/内容生产/ai-tone-director/workflows/article-director-integration.md", "full_text", max_chars=12000),
    ]

    final_review_contract = (
        "Output strict JSON using the current article-review contract only. "
        "Top-level fields must include pass, score, summary, scope, dimension, issues, "
        "blocking_issues, advisory_issues, and must_fix. Set scope='full-article' and dimension='full_article'. "
        "Each issue object should include issue, severity, dimension, owner_hint, repair_node_hint, "
        "section_ids, paragraph_ids when available, reason_type, why_ai_like, and repair_strategy. "
        "Do not output legacy round1_逻辑/round2_AI味/round3_人感 fields."
    )

    nodes.append(
        _node(
            node_id="article-review-a-01",
            role="article-review",
            skill_file=skill_root_expr.format(path="agents/article-review/SKILL.md"),
            temperature=FINAL_REVIEW_A_TEMP,
            output_file=f"skills/article-director/outputs/{topic_id}/article-review-a-01/output.json",
            schema="article-review-result",
            input_files=final_review_inputs,
            task_prefix=(
                "[full-article-review:A] Strict final semantic review after section revisions and style harmonization. "
                "Read section argument-spine.md files. Focus on whole-article logic, unsupported claims, cross-section gaps, source/appendix boundaries, "
                "viewpoint stringing, short-breath paragraphs, "
                "and whether local section fixes introduced global drift. "
                + final_review_contract
            ),
            parallel=True,
            provider="codex",
            package_type="final-review",
            risk_tier="high",
            max_input_tokens=18000,
            max_output_tokens=6000,
            allowed_inputs=final_review_allowed_inputs,
        )
    )
    nodes.append(
        _node(
            node_id="article-review-b-01",
            role="article-review",
            skill_file=skill_root_expr.format(path="agents/article-review/SKILL.md"),
            temperature=FINAL_REVIEW_B_TEMP,
            output_file=f"skills/article-director/outputs/{topic_id}/article-review-b-01/output.json",
            schema="article-review-result",
            input_files=final_review_inputs,
            task_prefix=(
                "[full-article-review:B] Reader-experience final semantic review after section revisions and style harmonization. "
                "Focus on reader comprehension, concrete scenes, AI-tone issues under the ai-tone-director audit contract, "
                "opening/ending effectiveness, long-thinking rhythm, and tutorial prerequisites or stop conditions when relevant. "
                + final_review_contract
            ),
            parallel=True,
            provider="codex",
            package_type="final-review",
            risk_tier="high",
            max_input_tokens=18000,
            max_output_tokens=6000,
            allowed_inputs=final_review_allowed_inputs,
        )
    )
    edges.append({"from_node": "argument-flow-check-01", "to_node": "article-review-a-01"})
    edges.append({"from_node": "argument-flow-check-01", "to_node": "article-review-b-01"})

    nodes.append(
        _node(
            node_id="review-diff-01",
            role="review-diff",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"state/reviews/{topic_id}.json",
            schema="review-diff-result",
            node_type="script",
            input_files=[
                f"skills/article-director/outputs/{topic_id}/article-review-a-01/output.json",
                f"skills/article-director/outputs/{topic_id}/article-review-b-01/output.json",
            ],
            command=[
                "{python}",
                "{project_root}\\skills\\article-director\\scripts\\review_diff.py",
                "--topic-id",
                topic_id,
            ],
            package_type="review-merge",
            risk_tier="high",
        )
    )
    edges.append({"from_node": "article-review-a-01", "to_node": "review-diff-01"})
    edges.append({"from_node": "article-review-b-01", "to_node": "review-diff-01"})

    nodes.append(
        _node(
            node_id="code-check-01",
            role="code-check",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/code-check-01/output.json",
            schema="code-check-result",
            node_type="script",
            command=[
                "{python}",
                "{project_root}\\scripts\\check_article.py",
                f"tmp\\{topic_id}-draft.md",
                "--topic-id",
                topic_id,
            ],
        )
    )
    edges.append({"from_node": "review-diff-01", "to_node": "code-check-01"})

    nodes.append(
        _node(
            node_id="human-approval-01",
            role="human-approval",
            skill_file=skill_root_expr.format(path="agents/director/SKILL.md"),
            temperature=0.0,
            output_file=f"skills/article-director/outputs/{topic_id}/human-approval-01/output.json",
            schema="none",
            node_type="human-approval",
            env={
                "approval_key": "final-article-approval",
                "approval_message": "全文终审完成，请人工确认最终文章是否通过。",
            },
        )
    )
    edges.append({"from_node": "code-check-01", "to_node": "human-approval-01"})
    return nodes, edges


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile expanded article workflow")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--workflow-mode", default="")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    topic_id = args.topic_id
    project_dir = build_project_dir(project_root, topic_id)
    if args.workflow_mode:
        workflow_profile_path = project_dir / "workflow-profile.json"
        workflow_profile = read_json(workflow_profile_path, {"strategy": DEFAULT_STRATEGY})
        workflow_profile["workflow_mode"] = args.workflow_mode
        workflow_profile_path.write_text(json.dumps(workflow_profile, ensure_ascii=False, indent=2), encoding="utf-8")
    nodes, edges = compile_nodes(topic_id, project_root)
    run_script = project_dir / f"run_{topic_id}_expanded.py"
    title = args.title or topic_id
    workflow_profile = read_json(project_dir / "workflow-profile.json", {"strategy": DEFAULT_STRATEGY})
    strategy = workflow_profile.get("strategy", DEFAULT_STRATEGY)
    workflow_mode = _workflow_mode(workflow_profile)

    content = [
        "from pathlib import Path",
        "",
        f'PROJECT_ID = "{topic_id}"',
        f'TOPIC_ID = "{topic_id}"',
        f'TITLE = {json.dumps(title, ensure_ascii=False)}',
        'BRIEF = ""',
        f'STRATEGY = {json.dumps(strategy, ensure_ascii=False)}',
        f'WORKFLOW_MODE = {json.dumps(workflow_mode, ensure_ascii=False)}',
        f'ARTICLE_DIRECTOR_WORKFLOW_VERSION = "2026-06-25.{workflow_mode}"',
        "SKILL_ROOT = Path(__file__).resolve().parents[2]",
        "PROJECT_ROOT = Path(__file__).resolve().parents[4]",
        "",
        f"NODE_DEFS = {pprint.pformat(nodes, width=120, sort_dicts=False)}",
        "",
        f"EDGE_DEFS = {pprint.pformat(edges, width=120, sort_dicts=False)}",
        "",
    ]
    run_script.write_text("\n".join(content), encoding="utf-8")
    print(run_script.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
