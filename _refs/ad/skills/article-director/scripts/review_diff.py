import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json


LEGACY_ROUNDS = {
    "round1_逻辑": "logic",
    "round2_AI味": "ai_tone",
    "round3_人感": "human_feel",
    "round1_logic": "logic",
    "round2_ai_tone": "ai_tone",
    "round3_reader_feel": "human_feel",
}

CURRENT_CONTRACT_FIELDS = {
    "scope",
    "dimension",
    "issues",
}


def read_score(review: dict) -> float:
    value = review.get("score", 0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def has_current_contract(review: dict) -> bool:
    return any(field in review for field in CURRENT_CONTRACT_FIELDS)


def has_legacy_contract(review: dict) -> bool:
    return any(field in review for field in LEGACY_ROUNDS)


def contract_format(review: dict) -> str:
    if has_current_contract(review):
        return "current"
    if has_legacy_contract(review):
        return "legacy-fallback"
    return "missing"


def normalize_issue_items(
    value: object,
    *,
    default_dimension: str = "unknown",
    source_review: str = "",
    source_bucket: str = "",
) -> list[dict]:
    if not isinstance(value, list):
        return []
    normalized: list[dict] = []
    for item in value:
        if isinstance(item, str):
            issue = item.strip()
            if not issue:
                continue
            normalized.append(
                {
                    "issue": issue,
                    "severity": "medium",
                    "dimension": default_dimension,
                    "owner_hint": "manual-triage",
                    "repair_node_hint": "",
                    "package_ids": [],
                    "section_ids": [],
                    "paragraph_ids": [],
                    "paragraph_label": "",
                    "reason_type": "",
                    "why_ai_like": "",
                    "repair_strategy": "",
                    "source_review": source_review,
                    "source_bucket": source_bucket,
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        issue = str(item.get("issue") or item.get("message") or "").strip()
        if not issue:
            continue
        normalized.append(
            {
                "issue": issue,
                "severity": str(item.get("severity") or "medium"),
                "dimension": str(item.get("dimension") or default_dimension or "unknown"),
                "owner_hint": str(item.get("owner_hint") or "manual-triage"),
                "repair_node_hint": str(item.get("repair_node_hint") or ""),
                "package_ids": as_str_list(item.get("package_ids", [])),
                "section_ids": as_str_list(item.get("section_ids", [])),
                "paragraph_ids": as_str_list(item.get("paragraph_ids", [])),
                "paragraph_label": str(item.get("paragraph_label") or ""),
                "reason_type": str(item.get("reason_type") or ""),
                "why_ai_like": str(item.get("why_ai_like") or ""),
                "repair_strategy": str(item.get("repair_strategy") or ""),
                "source_review": source_review,
                "source_bucket": source_bucket,
            }
        )
    return normalized


def legacy_round_issues(review: dict, source_review: str) -> list[dict]:
    items: list[dict] = []
    for round_key, dimension in LEGACY_ROUNDS.items():
        payload = review.get(round_key)
        if not isinstance(payload, dict):
            continue
        if payload.get("pass") is not False:
            continue
        notes = payload.get("notes", [])
        if not isinstance(notes, list):
            notes = []
        items.extend(
            normalize_issue_items(
                notes,
                default_dimension=dimension,
                source_review=source_review,
                source_bucket=f"legacy:{round_key}",
            )
        )
    return items


def collect_review_issues(review: dict, source_review: str) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    default_dimension = str(review.get("dimension") or "unknown")
    blocking = normalize_issue_items(
        review.get("blocking_issues", []),
        default_dimension=default_dimension,
        source_review=source_review,
        source_bucket="blocking_issues",
    )
    must_fix = normalize_issue_items(
        review.get("must_fix", []),
        default_dimension=default_dimension,
        source_review=source_review,
        source_bucket="must_fix",
    )
    advisory = normalize_issue_items(
        review.get("advisory_issues", []),
        default_dimension=default_dimension,
        source_review=source_review,
        source_bucket="advisory_issues",
    )
    issues = normalize_issue_items(
        review.get("issues", []),
        default_dimension=default_dimension,
        source_review=source_review,
        source_bucket="issues",
    )
    if not (blocking or must_fix or advisory or issues):
        issues = legacy_round_issues(review, source_review)
    return blocking, must_fix, advisory, issues


def dedupe_issue_dicts(items: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    result: list[dict] = []
    for item in items:
        key = (
            item.get("issue", ""),
            item.get("dimension", ""),
            item.get("owner_hint", ""),
            tuple(item.get("package_ids", [])),
            tuple(item.get("section_ids", [])),
            tuple(item.get("paragraph_ids", [])),
            item.get("reason_type", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def collect_failing_dimensions(review: dict, issue_items: list[dict]) -> list[str]:
    dimensions: set[str] = set()
    if review.get("pass") is False:
        dimension = str(review.get("dimension") or "").strip()
        if dimension and dimension != "full_article":
            dimensions.add(dimension)
    for item in issue_items:
        dimension = str(item.get("dimension") or "").strip()
        if dimension and dimension != "full_article":
            dimensions.add(dimension)
    for round_key, dimension in LEGACY_ROUNDS.items():
        payload = review.get(round_key)
        if isinstance(payload, dict) and payload.get("pass") is False:
            dimensions.add(dimension)
    return sorted(dimensions)


def infer_section_repair_node(owner_hint: str, dimension: str, section_id: str) -> str:
    if not section_id:
        return ""
    if owner_hint == "writer-package":
        return f"writer-section-{section_id}"
    if owner_hint == "structure-editor" or dimension == "structure":
        return f"revise-structure-{section_id}"
    if owner_hint == "narrative-smoother" and dimension == "logic":
        return f"revise-logic-{section_id}"
    if owner_hint == "narrative-smoother" and dimension == "ai_tone":
        return f"revise-de-ai-{section_id}"
    if dimension == "logic":
        return f"revise-logic-{section_id}"
    if dimension == "ai_tone":
        return f"revise-de-ai-{section_id}"
    return ""


def infer_repair_node(issue: dict, dimension: str) -> str:
    hinted = str(issue.get("repair_node_hint") or "").strip()
    if hinted:
        return hinted

    owner_hint = str(issue.get("owner_hint") or "").strip()
    section_ids = issue.get("section_ids", [])
    if isinstance(section_ids, list) and section_ids:
        section_target = infer_section_repair_node(owner_hint, dimension, str(section_ids[0]))
        if section_target:
            return section_target

    package_ids = issue.get("package_ids", [])
    if isinstance(package_ids, list) and package_ids:
        package_id = str(package_ids[0])
        mapping = {
            "writer-package": f"writer-{package_id}",
            "structure-editor": f"structure-editor-{package_id}",
            "deep-dive-researcher": f"deep-dive-researcher-{package_id}",
            "narrative-smoother": f"narrative-smoother-{package_id}",
            "adversarial-reviewer": f"adversarial-reviewer-{package_id}",
        }
        if owner_hint in mapping:
            return mapping[owner_hint]

    if owner_hint == "style-harmonizer":
        return "style-harmonizer-01"
    if dimension in {"ai_tone", "human_feel", "reader_feel", "style_alignment"}:
        return "style-harmonizer-01"
    return "manual-triage"


def determine_rollback(blocking_items: list[dict], failing_dimensions: list[str], conflicts: list[str]) -> tuple[str, list[str]]:
    if conflicts:
        return "human-review", ["manual-triage"]

    rollback_targets: list[str] = []
    for item in blocking_items:
        dimension = str(item.get("dimension") or "unknown")
        rollback_targets.append(infer_repair_node(item, dimension))

    if not rollback_targets:
        if failing_dimensions and set(failing_dimensions).issubset({"ai_tone", "human_feel", "reader_feel", "style_alignment"}):
            rollback_targets.append("style-harmonizer-01")
        elif failing_dimensions:
            rollback_targets.append("manual-triage")

    deduped: list[str] = []
    for item in rollback_targets:
        if item and item not in deduped:
            deduped.append(item)
    if not deduped:
        deduped = ["manual-triage"]
    return deduped[0], deduped


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge two article reviews into a deterministic diff result")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    review_a_path = project_dir / "article-review-a-01" / "output.json"
    review_b_path = project_dir / "article-review-b-01" / "output.json"
    review_a = read_json(review_a_path, {})
    review_b = read_json(review_b_path, {})

    pass_a = bool(review_a.get("pass"))
    pass_b = bool(review_b.get("pass"))
    score_a = read_score(review_a)
    score_b = read_score(review_b)
    format_a = contract_format(review_a)
    format_b = contract_format(review_b)

    blocking_items_a, must_fix_items_a, advisory_items_a, issues_items_a = collect_review_issues(review_a, "A")
    blocking_items_b, must_fix_items_b, advisory_items_b, issues_items_b = collect_review_issues(review_b, "B")

    blocking_items = dedupe_issue_dicts(blocking_items_a + blocking_items_b + must_fix_items_a + must_fix_items_b)
    advisory_items = dedupe_issue_dicts(advisory_items_a + advisory_items_b + issues_items_a + issues_items_b)
    failing_dimensions = sorted(
        set(
            collect_failing_dimensions(review_a, blocking_items_a + must_fix_items_a + issues_items_a)
            + collect_failing_dimensions(review_b, blocking_items_b + must_fix_items_b + issues_items_b)
        )
    )

    conflicts: list[str] = []
    if format_a == "missing" or format_b == "missing":
        conflicts.append(f"review contract missing: A={format_a}, B={format_b}")
    if pass_a != pass_b:
        conflicts.append("review pass status differs")
    if abs(score_a - score_b) > 15:
        conflicts.append(f"review score gap too large: {score_a:.1f} vs {score_b:.1f}")

    consensus = "approved"
    if conflicts:
        consensus = "human-review"
    elif (not pass_a) or (not pass_b):
        if score_a >= 70 and score_b >= 70:
            consensus = "human-review"
        else:
            consensus = "revise"
    elif blocking_items:
        consensus = "human-review"

    rollback_target, rollback_targets = determine_rollback(blocking_items, failing_dimensions, conflicts)
    revision_required = consensus == "revise"
    human_review_required = consensus == "human-review"

    payload = {
        "pass": consensus == "approved",
        "consensus": consensus,
        "score_a": score_a,
        "score_b": score_b,
        "score_gap": round(abs(score_a - score_b), 2),
        "review_contracts": {"A": format_a, "B": format_b},
        "conflicts": conflicts,
        "review_a_path": str(review_a_path),
        "review_b_path": str(review_b_path),
        "blocking_issues": blocking_items,
        "advisory_issues": advisory_items,
        "must_fix": dedupe_issue_dicts(must_fix_items_a + must_fix_items_b),
        "failing_dimensions": failing_dimensions,
        "rollback_target": rollback_target,
        "rollback_targets": rollback_targets,
        "revision_required": revision_required,
        "human_review_required": human_review_required,
        "summary": f"consensus={consensus}; score_a={score_a:.1f}; score_b={score_b:.1f}; rollback={rollback_target}",
    }
    output_path = project_root / "state" / "reviews" / f"{args.topic_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
