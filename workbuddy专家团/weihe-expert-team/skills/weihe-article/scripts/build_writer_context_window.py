import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from compiler_lib import build_project_dir, read_json, write_json


KEEP_SECTION_KEYS = (
    "section_id",
    "heading",
    "strategy",
    "body_text",
    "claim",
    "explanation",
    "evidence",
    "reader_stuck",
    "upstream_downstream",
    "logic_difficulty",
    "example",
    "before_after",
    "writer_actionable",
    "candidate_unit",
    "concepts",
    "actions",
    "expected_result",
    "failure_signals",
    "troubleshooting",
    "handoff_from_previous",
    "section_output",
    "next_section_gate",
    "prompt_example",
    "presentation_hint",
    "recommended_presentation",
    "target_paragraph_count",
    "target_word_count",
    "must_answer_first",
    "required_discourse_order",
    "reader_level",
    "reader_knows_terms",
    "reader_unknown_terms",
    "must_explain_terms",
    "concept_explanation_policy",
    "forbidden_opening_patterns",
)


def _compact_text(value: object, limit: int = 1800) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _section_block(section: dict | None) -> dict | None:
    if not section:
        return None
    block: dict[str, object] = {}
    for key in KEEP_SECTION_KEYS:
        value = section.get(key)
        if value in ("", [], {}, None):
            continue
        if isinstance(value, str):
            block[key] = _compact_text(value)
        else:
            block[key] = value
    return block


def _base_prompt(article_requirements: dict, manifest: dict) -> dict:
    strategy_profile = manifest.get("strategy_profile") or {}
    return {
        "title": article_requirements.get("title") or manifest.get("title") or "",
        "purpose": article_requirements.get("purpose") or article_requirements.get("goal") or "",
        "audience": article_requirements.get("audience") or article_requirements.get("reader") or "",
        "target_word_count": article_requirements.get("target_word_count") or "",
        "priority_sections": article_requirements.get("priority_sections") or [],
        "new_requirements": article_requirements.get("new_requirements") or [],
        "strategy": manifest.get("strategy") or "",
        "strategy_primary_goal": strategy_profile.get("primary_goal") or "",
        "concept_policy": strategy_profile.get("concept_policy") or {},
    }


def build_context_window(topic_id: str, section_id: str, project_root: Path) -> dict:
    project_dir = build_project_dir(project_root, topic_id)
    manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    article_requirements = read_json(project_dir / "article-requirements.json", {})
    sections = [section for section in manifest.get("sections", []) if section.get("section_id")]
    index = next((idx for idx, section in enumerate(sections) if str(section.get("section_id")) == section_id), -1)
    if index < 0:
        raise SystemExit(f"section not found: {section_id}")

    section_dir = project_dir / "sections" / section_id
    argument_spine_path = section_dir / "argument-spine.md"
    argument_spine = argument_spine_path.read_text(encoding="utf-8-sig") if argument_spine_path.exists() else ""

    return {
        "version": "2026-06-23.writer-context-window.v1",
        "topic_id": topic_id,
        "section_id": section_id,
        "order": index + 1,
        "source_files": {
            "section_manifest": str(project_dir / "section-manifest.json"),
            "article_requirements": str(project_dir / "article-requirements.json"),
            "argument_spine": str(argument_spine_path),
        },
        "context_policy": {
            "previous_block_is_optional": True,
            "next_block_is_optional": True,
            "previous_and_next_are_context_only": True,
            "writer_must_not_modify_previous_or_next": True,
            "do_not_force_sequential_section_execution": True,
            "if_previous_or_next_missing": "write from current_block and explicitly avoid fake continuity",
        },
        "base_prompt": _base_prompt(article_requirements, manifest),
        "previous_block": _section_block(sections[index - 1] if index > 0 else None),
        "current_block": {
            **(_section_block(sections[index]) or {}),
            "argument_spine": _compact_text(argument_spine, 2600),
        },
        "next_block": _section_block(sections[index + 1] if index + 1 < len(sections) else None),
        "writer_controller_required_output": {
            "context_map": [
                "previous_solved",
                "current_job",
                "next_dependency",
                "risk",
            ],
            "reader_use_contract": [
                "paragraph_role",
                "reader_state_before",
                "reader_state_after",
                "concrete_anchor",
                "writing_move",
                "abstraction_budget",
                "continuity_rule",
                "must_not_do",
            ],
            "deliberation_log": "2-3 rounds of decision logs, not hidden chain of thought",
            "write_readiness": "ready / blocked",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build previous/current/next context window for writer-controller")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--section-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    payload = build_context_window(args.topic_id, args.section_id, project_root)
    output_dir = build_project_dir(project_root, args.topic_id) / "sections" / args.section_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "writer-context-window.json"
    write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
