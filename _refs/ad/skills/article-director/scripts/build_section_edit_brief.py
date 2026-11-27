import argparse
import json
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


REVIEW_FILES = {
    "ai_tone": "review-ai-tone-findings.json",
    "style_alignment": "review-style.json",
    "logic": "review-logic.json",
    "structure": "review-structure.json",
    "simplify": "review-simplify.json",
}


def _section_meta(project_dir: Path, section_id: str) -> dict[str, Any]:
    manifest = _read_json(project_dir / "section-manifest.json", {"sections": []})
    if not isinstance(manifest, dict):
        return {"heading": section_id}
    for section in manifest.get("sections", []):
        if isinstance(section, dict) and str(section.get("section_id") or "") == section_id:
            return section
    return {"heading": section_id}


def _article_title(project_dir: Path, topic_id: str) -> str:
    profile = _read_json(project_dir / "workflow-profile.json", {})
    if isinstance(profile, dict) and str(profile.get("title") or "").strip():
        return str(profile.get("title") or "").strip()
    requirements = _read_json(project_dir / "article-requirements.json", {})
    if isinstance(requirements, dict) and str(requirements.get("title") or "").strip():
        return str(requirements.get("title") or "").strip()
    return topic_id


def _read_json(path: Path, default: Any) -> Any:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default
    return payload


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


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _collect_review_issues(dimension: str, review: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocking: list[dict[str, Any]] = []
    advisory: list[dict[str, Any]] = []
    for bucket_name, target in (("blocking_issues", blocking), ("must_fix", blocking), ("issues", advisory), ("advisory_issues", advisory)):
        for item in _as_list(review.get(bucket_name)):
            if isinstance(item, dict):
                enriched = dict(item)
            else:
                enriched = {"issue": str(item)}
            enriched.setdefault("dimension", dimension)
            enriched.setdefault("source_bucket", bucket_name)
            target.append(enriched)
    return blocking, advisory


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge parallel section reviews into one edit brief")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--section-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    section_dir = project_dir / "sections" / args.section_id
    output_path = section_dir / "section-edit-brief.json"
    issues: list[str] = []
    passed: list[str] = []

    reviews: dict[str, Any] = {}
    source_files: dict[str, str] = {}
    blocking_issues: list[dict[str, Any]] = []
    advisory_issues: list[dict[str, Any]] = []
    section_meta = _section_meta(project_dir, args.section_id)
    section_heading = str(section_meta.get("heading") or args.section_id)
    article_title = _article_title(project_dir, args.topic_id)

    for dimension, filename in REVIEW_FILES.items():
        path = section_dir / filename
        source_files[dimension] = _display_path(project_root, path)
        review = _read_json(path, {})
        if not isinstance(review, dict) or not review:
            issues.append(f"missing or invalid {filename}")
            review = {}
        else:
            passed.append(f"{dimension} review loaded")
        reviews[dimension] = review
        blocking, advisory = _collect_review_issues(dimension, review)
        blocking_issues.extend(blocking)
        advisory_issues.extend(advisory)

    ai_tone_context = _read_json(section_dir / "ai-tone-context-pack.json", {})
    expected_invocation = {}
    if isinstance(ai_tone_context, dict):
        expected_invocation = ai_tone_context.get("audit_must_include", {}).get("ai_tone_invocation", {})
    if not isinstance(expected_invocation, dict):
        expected_invocation = {}
    ai_tone_review = reviews.get("ai_tone", {}) if isinstance(reviews.get("ai_tone"), dict) else {}
    ai_tone_invocation = ai_tone_review.get("ai_tone_invocation") if isinstance(ai_tone_review.get("ai_tone_invocation"), dict) else {}
    for field in ("topic_id", "section_id", "phase", "idempotency_key", "source_hash"):
        if str(ai_tone_invocation.get(field, "")) != str(expected_invocation.get(field, "")):
            issues.append(f"ai_tone_invocation.{field} mismatch")

    brief = {
        "brief_id": f"{args.topic_id}:{args.section_id}:section-edit-brief",
        "topic_id": args.topic_id,
        "section_id": args.section_id,
        "article_title": article_title,
        "section_heading": section_heading,
        "source_files": {
            **source_files,
            "draft": _display_path(project_root, section_dir / "draft.md"),
            "review_source": _display_path(project_root, section_dir / "review-source.md"),
            "argument_spine": _display_path(project_root, section_dir / "argument-spine.md"),
            "paragraph_tags": _display_path(project_root, section_dir / "paragraph-tags.json"),
            "ai_tone_context": _display_path(project_root, section_dir / "ai-tone-context-pack.json"),
            "ai_tone_scan": _display_path(project_root, section_dir / "ai-tone-scan.json"),
        },
        "edit_contract": {
            "mode": "single_consolidated_rewrite",
            "review_agents_only_advise": True,
            "rewriter_owns_final_tradeoffs": True,
            "requires_supervisor_judgment_before_rewrite": True,
            "preserve_original_meaning": True,
            "do_not_rerun_review_fanout_for_rewrite_failure": True,
            "max_review_rounds": 2,
            "final_pass_order": ["meaning", "logic", "structure", "style", "simplify", "ai_tone"],
        },
        "title_complexity_policy": {
            "supervisor_must_judge": True,
            "simple": {
                "definition": "The heading can be explained in one sentence, centers on one concept, and is unlikely to be confused with adjacent concepts.",
                "editing_strategy": "compress first; avoid extra causal chains, multiple judgments, or dense concept stacking unless the reviews prove they are needed.",
                "logic_load_rules": {
                    "judgment_count": "strict",
                    "causal_chain_length": "strict",
                    "concept_density": "strict",
                },
            },
            "complex": {
                "definition": "The heading mixes multiple concepts, needs prerequisites, requires multiple reasoning steps, or would be confused with other concepts if reasoning is omitted.",
                "editing_strategy": "allow layered reasoning, but separate sub-questions, add intermediate conclusions, and split paragraphs when one paragraph carries several reader tasks.",
                "logic_load_rules": {
                    "judgment_count": "contextual",
                    "causal_chain_length": "contextual",
                    "concept_density": "contextual",
                },
            },
            "decision_order": [
                "judge section heading complexity",
                "choose simple or complex logic-load policy",
                "decide which review findings to apply",
                "rewrite once",
                "apply AI-tone fixes last",
            ],
        },
        "context_snapshot": {
            "draft_chars": len(_read_text(section_dir / "draft.md")),
            "review_source_chars": len(_read_text(section_dir / "review-source.md")),
            "argument_spine_chars": len(_read_text(section_dir / "argument-spine.md")),
            "paragraph_tag_count": len(_as_list(_read_json(section_dir / "paragraph-tags.json", {}).get("paragraphs"))),
        },
        "reviews": reviews,
        "ai_tone": {
            "context_pack": _display_path(project_root, section_dir / "ai-tone-context-pack.json"),
            "scan": _display_path(project_root, section_dir / "ai-tone-scan.json"),
            "review_file": _display_path(project_root, section_dir / "review-ai-tone-findings.json"),
            "ai_tone_invocation": ai_tone_invocation,
            "must_apply_at_final_step": True,
        },
        "edit_items": blocking_issues + advisory_issues,
        "blocking_issues": blocking_issues,
        "advisory_issues": advisory_issues,
        "rewrite_instructions": [
            "Use review findings as inputs, not as independent rewrite passes.",
            "Resolve conflicts by preserving the section thesis and factual scope first.",
            "Apply AI-tone fixes at the end so simplification or structure repair does not reintroduce generic phrasing.",
            "When a review suggestion would change meaning, defer it and explain the deferral in edit_brief_consumed.deferred_items.",
        ],
    }

    result = {
        "pass": not issues,
        "issues": issues,
        "passed": passed,
        "file": _display_path(project_root, output_path),
        "summary": f"merged {len(passed)} review files for section {args.section_id}",
        "edit_brief": brief,
    }
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
