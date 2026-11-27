import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import read_json, write_json
from build_node_micro_plans import (
    SCHEMA_VERSION,
    build_package_scope,
    build_section_lookup,
    detect_role,
    infer_package_id,
    load_topic_payloads,
    now_iso,
)


PACKAGE_ROLE_CHAIN = [
    "writer-package",
    "adversarial-reviewer",
    "package-check",
]


def next_revision_target(project_dir: Path, node_id: str) -> tuple[str, Path]:
    revision_dir = project_dir / "micro-plan" / "revision-plans"
    revision_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{node_id}-rev"
    numbers: list[int] = []
    for path in revision_dir.glob(f"{node_id}-rev*.json"):
        suffix = path.stem.replace(prefix, "", 1)
        if suffix.isdigit():
            numbers.append(int(suffix))
    next_number = (max(numbers) if numbers else 0) + 1
    revision_id = f"{node_id}-rev{next_number:02d}"
    return revision_id, revision_dir / f"{revision_id}.json"


def expected_output_file(topic_id: str, node_id: str, role: str) -> str:
    if role in {
        "writer-package",
        "adversarial-reviewer",
    }:
        return f"skills/article-director/outputs/{topic_id}/{node_id}/output.md"
    return f"skills/article-director/outputs/{topic_id}/{node_id}/output.json"


def build_upstream_inputs(topic_id: str, node_id: str, role: str, package_id: str | None) -> list[str]:
    if role == "writer-package":
        return [
            f"tmp/{topic_id}-detailed-outline.md",
            f"skills/article-director/outputs/{topic_id}/article-packages.json",
            f"skills/article-director/outputs/{topic_id}/section-manifest.json",
        ]
    if role == "adversarial-reviewer" and package_id:
        return [
            f"skills/article-director/outputs/{topic_id}/writer-{package_id}/output.md",
            f"tmp/{topic_id}-detailed-outline.md",
            f"skills/article-director/outputs/{topic_id}/section-manifest.json",
        ]
    if role == "package-check" and package_id:
        return [
            f"skills/article-director/outputs/{topic_id}/adversarial-reviewer-{package_id}/output.md",
            f"skills/article-director/outputs/{topic_id}/article-packages.json",
            f"skills/article-director/outputs/{topic_id}/section-manifest.json",
        ]
    if node_id == "article-review-a-01" or node_id == "article-review-b-01":
        return [
            f"tmp/{topic_id}-draft.md",
            f"skills/article-director/outputs/{topic_id}/section-manifest.json",
        ]
    if node_id == "review-diff-01":
        return [
            f"skills/article-director/outputs/{topic_id}/article-review-a-01/output.json",
            f"skills/article-director/outputs/{topic_id}/article-review-b-01/output.json",
        ]
    return [f"skills/article-director/outputs/{topic_id}/section-manifest.json"]


def build_downstream_nodes(node_id: str, role: str, package_id: str | None) -> list[str]:
    if role in PACKAGE_ROLE_CHAIN and package_id:
        role_index = PACKAGE_ROLE_CHAIN.index(role)
        if role_index < len(PACKAGE_ROLE_CHAIN) - 1:
            next_role = PACKAGE_ROLE_CHAIN[role_index + 1]
            next_id_map = {
                "writer-package": f"writer-{package_id}",
                "primer-writer": f"primer-writer-{package_id}",
                "deep-dive-researcher": f"deep-dive-researcher-{package_id}",
                "structure-editor": f"structure-editor-{package_id}",
                "narrative-smoother": f"narrative-smoother-{package_id}",
                "adversarial-reviewer": f"adversarial-reviewer-{package_id}",
                "package-check": f"package-check-{package_id}",
            }
            if next_role == "package-check":
                return [next_id_map[next_role], "draft-assembler-01"]
            return [next_id_map[next_role]]
        return ["draft-assembler-01"]
    if node_id in {"article-review-a-01", "article-review-b-01"}:
        return ["review-diff-01"]
    if node_id == "review-diff-01":
        return ["code-check-01"]
    return []


def build_must_preserve(role: str, package_scope: dict | None) -> list[str]:
    preserves = [
        "Keep the repair scoped to the current node contract.",
        "Preserve stable claims unless the reason explicitly requires correction.",
    ]
    if package_scope:
        preserves.append(f"Keep package boundary fixed to: {', '.join(package_scope.get('section_ids', []))}.")
    role_specific = {
        "writer-package": [
            "Preserve section ordering and package thesis.",
            "Preserve evidence anchors needed by later passes.",
        ],
        "adversarial-reviewer": [
            "Preserve body-ready Markdown output.",
            "Preserve package-local scope while fixing logic or style issues.",
        ],
        "package-check": [
            "Preserve validator target and package identity.",
        ],
        "article-review": [
            "Preserve strict review JSON contract.",
        ],
        "review-diff": [
            "Preserve merged review JSON contract.",
        ],
    }
    return preserves + role_specific.get(role, [])


def build_revision_goals(role: str, reason: str) -> list[str]:
    goals = [f"Resolve the reported issue: {reason}"]
    role_specific = {
        "writer-package": "Rebuild missing or weak section coverage without spilling into other packages.",
        "adversarial-reviewer": "Patch unsupported claims, jargon gaps, or AI-flavored phrasing in the body.",
        "package-check": "Restore package readiness so assembly can trust this gate.",
        "article-review": "Produce a cleaner review payload with clearer, actionable findings.",
        "review-diff": "Merge the two review streams into one stable and actionable review result.",
    }
    if role in role_specific:
        goals.append(role_specific[role])
    goals.append("Minimize collateral impact on downstream nodes.")
    return goals


def build_repair_actions(topic_id: str, node_id: str, role: str, package_scope: dict | None) -> list[dict]:
    actions = [
        {
            "order": 1,
            "status": "pending",
            "action": "Re-read the current node output, the upstream inputs, and the reported reason before editing.",
        },
        {
            "order": 2,
            "status": "pending",
            "action": "Map the issue to the smallest affected sections, paragraphs, or review fields.",
        },
        {
            "order": 3,
            "status": "pending",
            "action": "Apply a role-scoped repair without expanding to unrelated package content.",
        },
        {
            "order": 4,
            "status": "pending",
            "action": "Re-check node contract and record whether downstream nodes need rerun.",
        },
    ]
    if package_scope and package_scope.get("fact_sections"):
        actions.append(
            {
                "order": 5,
                "status": "pending",
                "action": "Confirm fact-sensitive sections still retain support after the repair.",
            }
        )
    if role == "package-check":
        actions.append(
            {
                "order": 6,
                "status": "pending",
                "action": "Rerun or re-evaluate the package gate against the adversarial reviewer output.",
            }
        )
    if node_id in {"article-review-a-01", "article-review-b-01"}:
        actions.append(
            {
                "order": 6,
                "status": "pending",
                "action": "Confirm the repaired review output is still strict JSON and still actionable for review-diff.",
            }
        )
    return actions


def build_validation_checks(role: str, package_scope: dict | None) -> list[str]:
    checks = [
        "Repair stays inside the current node boundary.",
        "Expected output format still matches this node type.",
    ]
    if package_scope:
        checks.append("Owned section IDs still match the package scope after revision.")
    role_specific = {
        "writer-package": [
            "All assigned headings remain covered after repair.",
            "Output remains Markdown body text.",
        ],
        "adversarial-reviewer": [
            "Output is repaired Markdown, not a critique memo.",
            "Patched claims and tone issues are addressed directly in body text.",
        ],
        "package-check": [
            "Gate result is ready to feed assembly.",
            "Validation targets the latest adversarial reviewer output.",
        ],
        "article-review": [
            "Output is strict JSON.",
            "Findings remain actionable for downstream diffing.",
        ],
        "review-diff": [
            "Output is strict JSON.",
            "Merged findings preserve enough detail from both review streams.",
        ],
    }
    return checks + role_specific.get(role, [])


def build_revision_plan(
    project_root: Path,
    topic_id: str,
    node_id: str,
    reason: str,
    package_id: str | None,
) -> tuple[dict, Path]:
    project_dir, section_manifest, article_packages = load_topic_payloads(project_root, topic_id)
    package_ids = [package["package_id"] for package in article_packages.get("packages", [])]
    resolved_package_id = package_id or infer_package_id(node_id, package_ids)
    role = detect_role(node_id)
    package_scope = None
    if resolved_package_id:
        section_lookup = build_section_lookup(section_manifest)
        package_map = {package["package_id"]: package for package in article_packages.get("packages", [])}
        if resolved_package_id not in package_map:
            raise ValueError(f"unknown package_id: {resolved_package_id}")
        package_scope = build_package_scope(package_map[resolved_package_id], section_lookup)

    expected_output = expected_output_file(topic_id, node_id, role)
    current_output_path = project_root / Path(expected_output)
    revision_id, target = next_revision_target(project_dir, node_id)
    current_output_payload = {}
    if current_output_path.exists() and current_output_path.suffix.lower() == ".json":
        current_output_payload = read_json(current_output_path, {})

    payload = {
        "schema_version": SCHEMA_VERSION,
        "plan_type": "revision-micro-plan",
        "topic_id": topic_id,
        "revision_id": revision_id,
        "created_at": now_iso(),
        "node_id": node_id,
        "role": role,
        "package_id": resolved_package_id or "",
        "reason": reason,
        "source_files": {
            "section_manifest": f"skills/article-director/outputs/{topic_id}/section-manifest.json",
            "article_packages": f"skills/article-director/outputs/{topic_id}/article-packages.json",
            "current_output": expected_output,
        },
        "context": {
            "current_output_exists": current_output_path.exists(),
            "current_output_payload": current_output_payload,
            "upstream_inputs": build_upstream_inputs(topic_id, node_id, role, resolved_package_id),
            "downstream_nodes": build_downstream_nodes(node_id, role, resolved_package_id),
            "package_scope": package_scope or {},
        },
        "revision_framework": {
            "status": "draft",
            "problem_statement": reason,
            "must_preserve": build_must_preserve(role, package_scope),
            "revision_goals": build_revision_goals(role, reason),
            "repair_actions": build_repair_actions(topic_id, node_id, role, package_scope),
            "validation_checks": build_validation_checks(role, package_scope),
            "handoff": {
                "expected_output": expected_output,
                "downstream_nodes": build_downstream_nodes(node_id, role, resolved_package_id),
                "notes": [
                    "If the repair changes package-level meaning, re-evaluate downstream nodes for rerun.",
                    "If the repair changes structure or facts, carry that signal into the next gate or review stage.",
                ],
            },
        },
    }

    return payload, target


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a revision micro plan scaffold for one node")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--package-id", default="")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    payload, target = build_revision_plan(
        project_root=project_root,
        topic_id=args.topic_id,
        node_id=args.node_id,
        reason=args.reason,
        package_id=args.package_id or None,
    )
    write_json(target, payload)
    print(target)


if __name__ == "__main__":
    main()
