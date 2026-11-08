import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compile_expanded_workflow import compile_nodes


REQUIRED_FINAL_NODES = [
    "style-harmonizer-check-01",
    "finalize-draft-01",
    "final-draft-integrity-01",
    "argument-flow-check-01",
    "article-review-a-01",
    "article-review-b-01",
    "review-diff-01",
    "code-check-01",
    "human-approval-01",
]

LEAN_REQUIRED_FINAL_NODES = [
    "final-integrator-01",
    "style-harmonizer-check-01",
    "finalize-draft-01",
    "final-draft-integrity-01",
    "argument-flow-check-01",
    "code-check-01",
    "human-approval-01",
]


def load_generated_script(path: Path) -> tuple[list[dict], list[dict]]:
    spec = importlib.util.spec_from_file_location("generated_article_workflow", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load workflow script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.NODE_DEFS), list(module.EDGE_DEFS)


def edge_exists(edges: list[dict], source: str, target: str) -> bool:
    return any(edge.get("from_node") == source and edge.get("to_node") == target for edge in edges)


def validate(nodes: list[dict], edges: list[dict]) -> dict[str, Any]:
    node_ids = {str(node.get("node_id")) for node in nodes}
    failures: list[str] = []
    is_lean = "final-integrator-01" in node_ids or any(node_id.startswith("section-editor-") for node_id in node_ids)

    if is_lean:
        return validate_lean(nodes, edges)

    for node_id in REQUIRED_FINAL_NODES:
        if node_id not in node_ids:
            failures.append(f"missing final node: {node_id}")

    required_edges = [
        ("style-harmonizer-01", "style-harmonizer-check-01"),
        ("style-harmonizer-check-01", "source-map-repair-01"),
        ("finalize-draft-01", "final-draft-integrity-01"),
        ("final-draft-integrity-01", "argument-flow-check-01"),
        ("argument-flow-check-01", "article-review-a-01"),
        ("argument-flow-check-01", "article-review-b-01"),
        ("article-review-a-01", "review-diff-01"),
        ("article-review-b-01", "review-diff-01"),
        ("review-diff-01", "code-check-01"),
        ("code-check-01", "human-approval-01"),
    ]
    for source, target in required_edges:
        if not edge_exists(edges, source, target):
            failures.append(f"missing edge: {source} -> {target}")

    section_review_nodes = [
        node_id
        for node_id in node_ids
        if node_id.startswith((
            "tag-paragraphs-",
            "build-argument-spine-",
            "prepare-ai-tone-call-",
            "review-ai-tone-",
            "validate-ai-tone-audit-",
            "build-ai-tone-repair-plan-",
            "review-logic-",
            "review-structure-",
            "ai-tone-regression-",
        ))
    ]
    if not section_review_nodes:
        failures.append("missing section review nodes")

    section_ids = sorted(
        node_id.removeprefix("review-ai-tone-")
        for node_id in node_ids
        if node_id.startswith("review-ai-tone-")
    )
    for section_id in section_ids:
        required_section_nodes = [
            f"build-argument-spine-{section_id}",
            f"writer-section-{section_id}",
            f"prepare-ai-tone-call-{section_id}",
            f"review-ai-tone-{section_id}",
            f"validate-ai-tone-audit-{section_id}",
            f"build-ai-tone-repair-plan-{section_id}",
            f"revise-de-ai-{section_id}",
            f"ai-tone-regression-{section_id}",
            f"revise-personal-style-{section_id}",
        ]
        for required_node in required_section_nodes:
            if required_node not in node_ids:
                failures.append(f"missing section ai-tone node: {required_node}")
        required_section_edges = [
            (f"seed-longform-memory-01", f"build-argument-spine-{section_id}"),
            (f"build-argument-spine-{section_id}", f"writer-section-{section_id}"),
            (f"tag-paragraphs-{section_id}", f"prepare-ai-tone-call-{section_id}"),
            (f"prepare-ai-tone-call-{section_id}", f"review-ai-tone-{section_id}"),
            (f"review-ai-tone-{section_id}", f"validate-ai-tone-audit-{section_id}"),
            (f"validate-ai-tone-audit-{section_id}", f"build-ai-tone-repair-plan-{section_id}"),
            (f"build-ai-tone-repair-plan-{section_id}", f"review-logic-{section_id}"),
            (f"revise-de-ai-{section_id}", f"ai-tone-regression-{section_id}"),
            (f"ai-tone-regression-{section_id}", f"revise-personal-style-{section_id}"),
        ]
        for source, target in required_section_edges:
            if not edge_exists(edges, source, target):
                failures.append(f"missing section ai-tone edge: {source} -> {target}")

    schema_by_node = {str(node.get("node_id")): str(node.get("schema_check_id") or "") for node in nodes}
    if schema_by_node.get("article-review-a-01") != "article-review-result":
        failures.append("article-review-a-01 schema is not article-review-result")
    if schema_by_node.get("article-review-b-01") != "article-review-result":
        failures.append("article-review-b-01 schema is not article-review-result")
    if schema_by_node.get("review-diff-01") != "review-diff-result":
        failures.append("review-diff-01 schema is not review-diff-result")

    return {
        "pass": not failures,
        "failures": failures,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "section_review_node_count": len(section_review_nodes),
        "final_nodes": [node_id for node_id in REQUIRED_FINAL_NODES if node_id in node_ids],
    }


def validate_lean(nodes: list[dict], edges: list[dict]) -> dict[str, Any]:
    node_ids = {str(node.get("node_id")) for node in nodes}
    failures: list[str] = []

    for node_id in LEAN_REQUIRED_FINAL_NODES:
        if node_id not in node_ids:
            failures.append(f"missing lean final node: {node_id}")

    required_edges = [
        ("draft-assembler-01", "final-integrator-01"),
        ("final-integrator-01", "style-harmonizer-check-01"),
        ("style-harmonizer-check-01", "source-map-repair-01"),
        ("finalize-draft-01", "final-draft-integrity-01"),
        ("final-draft-integrity-01", "argument-flow-check-01"),
        ("argument-flow-check-01", "code-check-01"),
        ("code-check-01", "human-approval-01"),
    ]
    for source, target in required_edges:
        if not edge_exists(edges, source, target):
            failures.append(f"missing lean edge: {source} -> {target}")

    section_ids = sorted(
        node_id.removeprefix("section-writer-")
        for node_id in node_ids
        if node_id.startswith("section-writer-")
    )
    if not section_ids:
        failures.append("missing lean section-writer nodes")
    for section_id in section_ids:
        required_section_nodes = [
            f"build-argument-spine-{section_id}",
            f"build-writer-context-window-{section_id}",
            f"section-writer-{section_id}",
            f"prepare-section-review-source-{section_id}",
            f"tag-paragraphs-{section_id}",
            f"prepare-ai-tone-call-{section_id}",
            f"review-ai-tone-{section_id}",
            f"review-style-{section_id}",
            f"review-logic-{section_id}",
            f"review-structure-{section_id}",
            f"review-simplify-{section_id}",
            f"merge-edit-brief-{section_id}",
            f"paragraph-rewrite-designer-{section_id}",
            f"section-editor-{section_id}",
            f"section-rewrite-gate-{section_id}",
            f"materialize-section-editor-{section_id}",
            f"validate-ai-tone-audit-{section_id}",
            f"build-ai-tone-repair-plan-{section_id}",
            f"ai-tone-regression-{section_id}",
            f"section-complete-{section_id}",
        ]
        for required_node in required_section_nodes:
            if required_node not in node_ids:
                failures.append(f"missing lean section node: {required_node}")
        required_section_edges = [
            (f"build-argument-spine-{section_id}", f"build-writer-context-window-{section_id}"),
            (f"build-writer-context-window-{section_id}", f"section-writer-{section_id}"),
            (f"section-writer-{section_id}", f"prepare-section-review-source-{section_id}"),
            (f"prepare-section-review-source-{section_id}", f"tag-paragraphs-{section_id}"),
            (f"tag-paragraphs-{section_id}", f"prepare-ai-tone-call-{section_id}"),
            (f"prepare-ai-tone-call-{section_id}", f"review-ai-tone-{section_id}"),
            (f"prepare-ai-tone-call-{section_id}", f"review-style-{section_id}"),
            (f"prepare-ai-tone-call-{section_id}", f"review-logic-{section_id}"),
            (f"prepare-ai-tone-call-{section_id}", f"review-structure-{section_id}"),
            (f"prepare-ai-tone-call-{section_id}", f"review-simplify-{section_id}"),
            (f"review-ai-tone-{section_id}", f"merge-edit-brief-{section_id}"),
            (f"review-style-{section_id}", f"merge-edit-brief-{section_id}"),
            (f"review-logic-{section_id}", f"merge-edit-brief-{section_id}"),
            (f"review-structure-{section_id}", f"merge-edit-brief-{section_id}"),
            (f"review-simplify-{section_id}", f"merge-edit-brief-{section_id}"),
            (f"merge-edit-brief-{section_id}", f"paragraph-rewrite-designer-{section_id}"),
            (f"paragraph-rewrite-designer-{section_id}", f"section-editor-{section_id}"),
            (f"section-editor-{section_id}", f"section-rewrite-gate-{section_id}"),
            (f"section-rewrite-gate-{section_id}", f"materialize-section-editor-{section_id}"),
            (f"materialize-section-editor-{section_id}", f"validate-ai-tone-audit-{section_id}"),
            (f"validate-ai-tone-audit-{section_id}", f"build-ai-tone-repair-plan-{section_id}"),
            (f"build-ai-tone-repair-plan-{section_id}", f"ai-tone-regression-{section_id}"),
            (f"ai-tone-regression-{section_id}", f"section-complete-{section_id}"),
            (f"section-complete-{section_id}", "draft-assembler-01"),
        ]
        for source, target in required_section_edges:
            if not edge_exists(edges, source, target):
                failures.append(f"missing lean section edge: {source} -> {target}")

    schema_by_node = {str(node.get("node_id")): str(node.get("schema_check_id") or "") for node in nodes}
    for section_id in section_ids:
        for review_node in (
            f"review-ai-tone-{section_id}",
            f"review-style-{section_id}",
            f"review-logic-{section_id}",
            f"review-structure-{section_id}",
            f"review-simplify-{section_id}",
        ):
            if schema_by_node.get(review_node) != "section-review-result":
                failures.append(f"{review_node} schema is not section-review-result")
        if schema_by_node.get(f"merge-edit-brief-{section_id}") != "code-check-result":
            failures.append(f"merge-edit-brief-{section_id} schema is not code-check-result")
        if schema_by_node.get(f"paragraph-rewrite-designer-{section_id}") != "paragraph-rewrite-design":
            failures.append(f"paragraph-rewrite-designer-{section_id} schema is not paragraph-rewrite-design")
        if schema_by_node.get(f"section-editor-{section_id}") != "section-editor-result":
            failures.append(f"section-editor-{section_id} schema is not section-editor-result")
        if schema_by_node.get(f"section-rewrite-gate-{section_id}") != "code-check-result":
            failures.append(f"section-rewrite-gate-{section_id} schema is not code-check-result")
        if schema_by_node.get(f"materialize-section-editor-{section_id}") != "code-check-result":
            failures.append(f"materialize-section-editor-{section_id} schema is not code-check-result")

    lean_agent_roles = {
        str(node.get("role"))
        for node in nodes
        if str(node.get("node_type") or "agent") == "agent"
    }
    allowed_agent_roles = {
        "section-writer",
        "section-rewriter",
        "section-review-ai-tone",
        "section-review-style",
        "section-review-logic",
        "section-review-structure",
        "section-review-simplify",
        "paragraph-rewrite-designer",
        "final-integrator",
    }
    unexpected_roles = sorted(role for role in lean_agent_roles if role not in allowed_agent_roles)
    if unexpected_roles:
        failures.append(f"unexpected lean agent roles: {', '.join(unexpected_roles)}")

    return {
        "pass": not failures,
        "failures": failures,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "section_review_node_count": len([node_id for node_id in node_ids if node_id.startswith("review-")]),
        "section_editor_fanout_review_count": len(
            [
                node_id
                for node_id in node_ids
                if node_id.startswith(
                    (
                        "review-ai-tone-",
                        "review-style-",
                        "review-logic-",
                        "review-structure-",
                        "review-simplify-",
                    )
                )
            ]
        ),
        "final_nodes": [node_id for node_id in LEAN_REQUIRED_FINAL_NODES if node_id in node_ids],
        "workflow_mode": "lean-v1",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate compiled article review chain")
    parser.add_argument("--topic-id", default="")
    parser.add_argument("--workflow-script", default="")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    if args.workflow_script:
        nodes, edges = load_generated_script(Path(args.workflow_script))
    elif args.topic_id:
        nodes, edges = compile_nodes(args.topic_id, project_root)
    else:
        raise SystemExit("pass --topic-id or --workflow-script")

    payload = validate(nodes, edges)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if payload["pass"] else 1)


if __name__ == "__main__":
    main()
