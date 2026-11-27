import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from compiler_lib import build_project_dir


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _display_path(project_root: Path, path: Path) -> str:
    try:
        value = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        value = path
    return value.as_posix()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _brief_payload(wrapper: dict[str, Any]) -> dict[str, Any]:
    brief = wrapper.get("edit_brief")
    return brief if isinstance(brief, dict) else {}


def _expected_invocation(context: dict[str, Any]) -> dict[str, Any]:
    payload = context.get("audit_must_include", {})
    if not isinstance(payload, dict):
        return {}
    invocation = payload.get("ai_tone_invocation", {})
    return invocation if isinstance(invocation, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate consolidated section rewriter output")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--section-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    section_dir = project_dir / "sections" / args.section_id
    output_path = section_dir / "section-rewrite-gate.json"

    editor_output_path = section_dir / "section-editor-output.json"
    brief_path = section_dir / "section-edit-brief.json"
    design_path = section_dir / "paragraph-rewrite-design.json"
    context_path = section_dir / "ai-tone-context-pack.json"
    draft_path = section_dir / "draft.md"
    review_source_path = section_dir / "review-source.md"

    editor = _read_json(editor_output_path)
    brief_wrapper = _read_json(brief_path)
    brief = _brief_payload(brief_wrapper)
    design = _read_json(design_path)
    context = _read_json(context_path)
    draft_text = _normalize(_read_text(review_source_path) or _read_text(draft_path))

    issues: list[str] = []
    passed: list[str] = []

    if not editor:
        issues.append("missing or invalid section-editor-output.json")
    if not brief:
        issues.append("missing edit_brief in section-edit-brief.json")
    if not design:
        issues.append("missing or invalid paragraph-rewrite-design.json")
    if str(editor.get("scope") or "") != "section":
        issues.append("section-editor-output.scope must be section")
    if str(editor.get("section_id") or "") != args.section_id:
        issues.append("section-editor-output.section_id mismatch")

    supervisor = editor.get("supervisor_judgment")
    if not isinstance(supervisor, dict):
        issues.append("missing supervisor_judgment")
        supervisor = {}
    title_complexity = str(supervisor.get("title_complexity") or "").strip().lower()
    if title_complexity not in {"simple", "complex"}:
        issues.append("supervisor_judgment.title_complexity must be simple or complex")
    for field in ("section_heading", "complexity_reason", "rewrite_strategy"):
        if not str(supervisor.get(field) or "").strip():
            issues.append(f"supervisor_judgment.{field} is required")
    logic_policy = supervisor.get("logic_load_policy")
    if not isinstance(logic_policy, dict):
        issues.append("supervisor_judgment.logic_load_policy must be object")
        logic_policy = {}
    expected_policy = "strict" if title_complexity == "simple" else "contextual" if title_complexity == "complex" else ""
    for field in ("judgment_count", "causal_chain_length", "concept_density"):
        value = str(logic_policy.get(field) or "").strip().lower()
        if value not in {"strict", "contextual"}:
            issues.append(f"supervisor_judgment.logic_load_policy.{field} must be strict or contextual")
        elif expected_policy and value != expected_policy:
            issues.append(f"supervisor_judgment.logic_load_policy.{field} must be {expected_policy} for {title_complexity} heading")
    plan = supervisor.get("review_application_plan")
    if not isinstance(plan, list) or not plan:
        issues.append("supervisor_judgment.review_application_plan must be a non-empty list")

    final_markdown = str(editor.get("final_markdown") or "").strip()
    if not final_markdown:
        issues.append("final_markdown is empty")
    elif not re.search(r"(?m)^##\s+", final_markdown):
        issues.append("final_markdown must contain a ## section heading")
    else:
        passed.append("final_markdown has a section heading")
    if "<!--" in final_markdown and "writer-contract" in final_markdown:
        issues.append("writer-contract comment was not removed")

    audit = editor.get("ai_tone_audit")
    if not isinstance(audit, dict):
        issues.append("ai_tone_audit must be object")
        audit = {}
    expected = _expected_invocation(context)
    actual = audit.get("ai_tone_invocation") if isinstance(audit.get("ai_tone_invocation"), dict) else {}
    for key in ("topic_id", "section_id", "phase", "idempotency_key", "source_hash"):
        if str(actual.get(key, "")) != str(expected.get(key, "")):
            issues.append(f"ai_tone_audit.ai_tone_invocation.{key} mismatch")
    if expected and not any(item.startswith("ai_tone_audit.ai_tone_invocation") for item in issues):
        passed.append("ai_tone_invocation matches context pack")

    consumed = editor.get("edit_brief_consumed")
    if not isinstance(consumed, dict):
        issues.append("missing edit_brief_consumed")
        consumed = {}
    expected_brief_id = str(brief.get("brief_id") or "")
    if expected_brief_id and str(consumed.get("brief_id") or "") != expected_brief_id:
        issues.append("edit_brief_consumed.brief_id mismatch")
    review_sources = consumed.get("review_sources")
    if not isinstance(review_sources, list) or len(review_sources) < 5:
        issues.append("edit_brief_consumed.review_sources must list all five review sources")
    else:
        passed.append("edit brief consumption is logged")

    rewrite_mode = str(design.get("rewrite_mode") or "")
    design_consumed = editor.get("paragraph_rewrite_design_consumed")
    if not isinstance(design_consumed, dict):
        issues.append("missing paragraph_rewrite_design_consumed")
        design_consumed = {}
    else:
        if not str(design_consumed.get("design_summary") or "").strip():
            issues.append("paragraph_rewrite_design_consumed.design_summary is required")
        passed.append("paragraph rewrite design consumption is logged")

    design_requires_change = False
    if rewrite_mode == "paragraph_rewrite_design_v2":
        coverage = design.get("coverage") if isinstance(design.get("coverage"), dict) else {}
        body_ids = coverage.get("body_paragraph_ids")
        covered_ids = coverage.get("covered_paragraph_ids")
        if not isinstance(body_ids, list) or not body_ids:
            issues.append("paragraph-rewrite-design.coverage.body_paragraph_ids must be a non-empty list")
            body_ids = []
        if not isinstance(covered_ids, list) or not covered_ids:
            issues.append("paragraph-rewrite-design.coverage.covered_paragraph_ids must be a non-empty list")
            covered_ids = []
        missing_coverage = sorted(set(map(str, body_ids)) - set(map(str, covered_ids)))
        if missing_coverage:
            issues.append(f"paragraph-rewrite-design coverage missing body paragraphs: {', '.join(missing_coverage)}")

        rewrite_units = design.get("rewrite_units")
        if not isinstance(rewrite_units, list):
            issues.append("paragraph-rewrite-design.rewrite_units must be list")
            rewrite_units = []
        micro_edits = design.get("paragraph_micro_edits")
        if not isinstance(micro_edits, list):
            issues.append("paragraph-rewrite-design.paragraph_micro_edits must be list")
            micro_edits = []
        unit_source_ids: set[str] = set()
        redesign_unit_ids: set[str] = set()
        for item in rewrite_units:
            if not isinstance(item, dict):
                continue
            unit_id = str(item.get("unit_id") or "")
            source_ids = item.get("source_paragraph_ids")
            if isinstance(source_ids, list):
                unit_source_ids.update(map(str, source_ids))
            if str(item.get("rewrite_intensity") or "") == "unit_redesign":
                if unit_id:
                    redesign_unit_ids.add(unit_id)
                if not str(item.get("selected_draft") or "").strip():
                    issues.append(f"unit_redesign {unit_id or '<missing>'} missing selected_draft")
        micro_ids = {
            str(item.get("paragraph_id") or "")
            for item in micro_edits
            if isinstance(item, dict) and str(item.get("paragraph_id") or "")
        }
        actual_covered = unit_source_ids | micro_ids
        missing_actual_coverage = sorted(set(map(str, body_ids)) - actual_covered)
        if missing_actual_coverage:
            issues.append(f"body paragraphs lack rewrite unit or micro edit coverage: {', '.join(missing_actual_coverage)}")

        consumed_covered = design_consumed.get("covered_paragraph_ids")
        used_units = design_consumed.get("used_units")
        adapted_units = design_consumed.get("adapted_units")
        micro_applied = design_consumed.get("micro_edits_applied")
        bridge_edits = design_consumed.get("bridge_edits")
        deferred_items = design_consumed.get("deferred_items")
        for field_name, value in (
            ("covered_paragraph_ids", consumed_covered),
            ("used_units", used_units),
            ("adapted_units", adapted_units),
            ("micro_edits_applied", micro_applied),
            ("bridge_edits", bridge_edits),
            ("deferred_items", deferred_items),
        ):
            if not isinstance(value, list):
                issues.append(f"paragraph_rewrite_design_consumed.{field_name} must be list")
        if isinstance(consumed_covered, list):
            missing_consumed_coverage = sorted(set(map(str, body_ids)) - set(map(str, consumed_covered)))
            if missing_consumed_coverage:
                issues.append(f"paragraph_rewrite_design_consumed.covered_paragraph_ids missing body paragraphs: {', '.join(missing_consumed_coverage)}")
        if redesign_unit_ids and isinstance(used_units, list) and isinstance(adapted_units, list):
            consumed_unit_ids = {
                str(item.get("unit_id") or item.get("id") or "")
                for item in used_units + adapted_units
                if isinstance(item, dict)
            }
            missing_units = sorted(redesign_unit_ids - consumed_unit_ids)
            if missing_units:
                issues.append(f"unit_redesign items were not used or adapted: {', '.join(missing_units)}")
        if micro_edits and isinstance(micro_applied, list) and not micro_applied:
            issues.append("paragraph_micro_edits exist but none were applied")
        if body_ids:
            design_requires_change = True
        passed.append("paragraph rewrite design v2 coverage is checked")
    elif rewrite_mode == "paragraph_rewrite_design":
        designs = design.get("designs") if isinstance(design, dict) else None
        if not isinstance(designs, list) or not designs:
            issues.append("paragraph-rewrite-design.designs must be a non-empty list")
            designs = []
        used_designs = design_consumed.get("used_designs")
        adapted_designs = design_consumed.get("adapted_designs")
        ignored_designs = design_consumed.get("ignored_designs")
        if not isinstance(used_designs, list):
            issues.append("paragraph_rewrite_design_consumed.used_designs must be list")
        if not isinstance(adapted_designs, list):
            issues.append("paragraph_rewrite_design_consumed.adapted_designs must be list")
        if not isinstance(ignored_designs, list):
            issues.append("paragraph_rewrite_design_consumed.ignored_designs must be list")
        if isinstance(used_designs, list) and isinstance(adapted_designs, list):
            if designs and not used_designs and not adapted_designs and not all(str(item.get("rewrite_scope") or "") == "keep" for item in designs if isinstance(item, dict)):
                issues.append("non-keep paragraph rewrite designs exist but none were used or adapted")
        non_keep_designs = [
            item
            for item in designs
            if isinstance(item, dict) and str(item.get("rewrite_scope") or "") != "keep"
        ]
        design_requires_change = bool(non_keep_designs)
    else:
        issues.append("paragraph-rewrite-design.rewrite_mode must be paragraph_rewrite_design_v2 or paragraph_rewrite_design")

    blocking_items = brief.get("blocking_issues") if isinstance(brief.get("blocking_issues"), list) else []
    must_fix_items = []
    reviews = brief.get("reviews") if isinstance(brief.get("reviews"), dict) else {}
    for review in reviews.values():
        if isinstance(review, dict) and isinstance(review.get("must_fix"), list):
            must_fix_items.extend(review.get("must_fix"))
    if (blocking_items or must_fix_items) and _normalize(final_markdown) == draft_text:
        issues.append("blocking or must_fix items exist but final_markdown is unchanged")
    if design_requires_change and _normalize(final_markdown) == draft_text:
        issues.append("paragraph rewrite design requires body edits but final_markdown is unchanged")

    result = {
        "pass": not issues,
        "issues": issues,
        "passed": passed,
        "file": _display_path(project_root, editor_output_path),
        "rollback_target": f"section-editor-{args.section_id}",
        "rollback_targets": [f"section-editor-{args.section_id}", f"section-rewrite-gate-{args.section_id}"],
        "summary": "section rewrite gate passed" if not issues else "section rewrite gate failed; rerun only rewriter/gate, not review fan-out",
    }
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
