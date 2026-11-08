import argparse
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json, write_json


SCHEMA_VERSION = "micro-plan/v1"
PACKAGE_ROLE_ORDER = [
    "writer-package",
    "structure-editor",
    "package-check",
]

PACKAGE_ROLE_SPECS = {
    "writer-package": {
        "stage": "drafting",
        "node_type": "agent",
        "node_id_template": "writer-{package_id}",
        "provider": "codex",
        "temperature": 0.35,
        "output_template": "skills/article-director/outputs/{topic_id}/writer-{package_id}/output.md",
        "input_templates": [
            "tmp/{topic_id}-detailed-outline.md",
            "skills/article-director/outputs/{topic_id}/article-packages.json",
            "skills/article-director/outputs/{topic_id}/section-manifest.json",
        ],
    },
    "structure-editor": {
        "stage": "structure-pass",
        "node_type": "agent",
        "node_id_template": "structure-editor-{package_id}",
        "provider": "codex",
        "temperature": 0.0,
        "output_template": "skills/article-director/outputs/{topic_id}/structure-editor-{package_id}/output.md",
        "input_templates": [
            "skills/article-director/outputs/{topic_id}/writer-{package_id}/output.md",
            "tmp/{topic_id}-detailed-outline.md",
            "skills/article-director/outputs/{topic_id}/section-manifest.json",
        ],
    },
    "package-check": {
        "stage": "package-gate",
        "node_type": "script",
        "node_id_template": "package-check-{package_id}",
        "provider": "",
        "temperature": 0.0,
        "output_template": "skills/article-director/outputs/{topic_id}/package-check-{package_id}/output.json",
        "input_templates": [
            "skills/article-director/outputs/{topic_id}/structure-editor-{package_id}/output.md",
            "skills/article-director/outputs/{topic_id}/article-packages.json",
            "skills/article-director/outputs/{topic_id}/section-manifest.json",
        ],
    },
}

REVIEW_TEMPLATES = [
    {
        "node_id": "article-review-a-01",
        "role": "article-review",
        "review_variant": "A",
        "stage": "global-review",
        "node_type": "agent",
        "provider": "codex",
        "temperature": 0.0,
        "depends_on": ["finalize-draft-01"],
        "next_nodes": ["review-diff-01"],
        "input_files": [
            "tmp/{topic_id}-draft.md",
            "skills/article-director/outputs/{topic_id}/section-manifest.json",
        ],
        "output_file": "skills/article-director/outputs/{topic_id}/article-review-a-01/output.json",
        "objective": "Review the whole draft for logic, structure, and boundary discipline in strict JSON.",
        "focus_points": [
            "Check whether the final draft follows the section thesis and overall article scope.",
            "Check whether package boundaries and appendix boundaries stayed intact after assembly.",
            "Flag logic gaps, unsupported jumps, and structural drift with enough detail for repair.",
        ],
        "constraints": [
            "Do not rewrite the article inside the review output.",
            "Return structured review findings only.",
        ],
        "acceptance_checks": [
            "Output is strict JSON, not prose.",
            "Review covers article-wide logic, structure, and scope boundary.",
            "Review points are actionable for a later repair pass.",
        ],
        "handoff_notes": [
            "Feeds review-diff-01 together with article-review-b-01.",
            "Should reference section IDs or headings when possible.",
        ],
    },
    {
        "node_id": "article-review-b-01",
        "role": "article-review",
        "review_variant": "B",
        "stage": "global-review",
        "node_type": "agent",
        "provider": "codex",
        "temperature": 0.15,
        "depends_on": ["finalize-draft-01"],
        "next_nodes": ["review-diff-01"],
        "input_files": [
            "tmp/{topic_id}-draft.md",
            "skills/article-director/outputs/{topic_id}/section-manifest.json",
        ],
        "output_file": "skills/article-director/outputs/{topic_id}/article-review-b-01/output.json",
        "objective": "Review the whole draft for readability, concrete examples, and AI-flavored phrasing in strict JSON.",
        "focus_points": [
            "Check whether a public reader can follow the article without unexplained jumps.",
            "Check whether examples stay concrete enough for the article type.",
            "Scan for filler, AI-flavored phrasing, and over-smoothed generic prose.",
        ],
        "constraints": [
            "Do not rewrite the article inside the review output.",
            "Return structured review findings only.",
        ],
        "acceptance_checks": [
            "Output is strict JSON, not prose.",
            "Review covers readability, examples, and AI-style phrasing.",
            "Review points are specific enough to support a targeted revision plan.",
        ],
        "handoff_notes": [
            "Feeds review-diff-01 together with article-review-a-01.",
            "Should reference concrete passages, sections, or recurring phrasing issues.",
        ],
    },
    {
        "node_id": "review-diff-01",
        "role": "review-diff",
        "review_variant": "merge",
        "stage": "review-merge",
        "node_type": "script",
        "provider": "",
        "temperature": 0.0,
        "depends_on": ["article-review-a-01", "article-review-b-01"],
        "next_nodes": ["code-check-01"],
        "input_files": [
            "skills/article-director/outputs/{topic_id}/article-review-a-01/output.json",
            "skills/article-director/outputs/{topic_id}/article-review-b-01/output.json",
        ],
        "output_file": "state/reviews/{topic_id}.json",
        "objective": "Merge the dual review outputs into one actionable review-diff result.",
        "focus_points": [
            "Preserve both reviewers' distinct findings before deduplication or severity merge.",
            "Keep the merged review JSON stable enough for downstream code-check or revision gates.",
        ],
        "constraints": [
            "Do not rewrite the article here.",
            "Do not discard one review stream without explaining the merge result in JSON fields.",
        ],
        "acceptance_checks": [
            "Output is strict JSON.",
            "Merged output preserves actionable review findings.",
            "Downstream gates can consume the merged review result directly.",
        ],
        "handoff_notes": [
            "Feeds the downstream code-check or revision gate.",
        ],
    },
]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def require_json(path: Path, required_key: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = read_json(path, {})
    if required_key not in payload:
        raise ValueError(f"invalid json at {path}: missing key '{required_key}'")
    return payload


def load_topic_payloads(project_root: Path, topic_id: str) -> tuple[Path, dict, dict]:
    project_dir = build_project_dir(project_root, topic_id)
    section_manifest = require_json(project_dir / "section-manifest.json", "sections")
    article_packages = require_json(project_dir / "article-packages.json", "packages")
    return project_dir, section_manifest, article_packages


def build_section_lookup(section_manifest: dict) -> dict[str, dict]:
    return {section["section_id"]: section for section in section_manifest.get("sections", [])}


def infer_package_id(node_id: str, package_ids: list[str]) -> str | None:
    for package_id in package_ids:
        if package_id in node_id:
            return package_id
    return None


def detect_role(node_id: str) -> str:
    prefixes = [
        ("primer-writer-", "primer-writer"),
        ("deep-dive-researcher-", "deep-dive-researcher"),
        ("structure-editor-", "structure-editor"),
        ("narrative-smoother-", "narrative-smoother"),
        ("adversarial-reviewer-", "adversarial-reviewer"),
        ("package-check-", "package-check"),
        ("writer-", "writer-package"),
        ("article-review-a-", "article-review"),
        ("article-review-b-", "article-review"),
        ("review-diff-", "review-diff"),
    ]
    for prefix, role in prefixes:
        if node_id.startswith(prefix):
            return role
    return "unknown"


def build_package_scope(package: dict, section_lookup: dict[str, dict]) -> dict:
    sections = [section_lookup[section_id] for section_id in package.get("section_ids", []) if section_id in section_lookup]
    fact_sections = [section["section_id"] for section in sections if section.get("requires_fact_verification")]
    image_sections = [section["section_id"] for section in sections if section.get("requires_image")]
    return {
        "section_ids": package.get("section_ids", []),
        "section_headings": package.get("section_headings", []),
        "target_word_count": package.get("target_word_count", 0),
        "target_paragraph_count": package.get("target_paragraph_count", 0),
        "package_score": package.get("package_score", 0.0),
        "risk_tier": package.get("risk_tier", "medium"),
        "requires_fact_verification": package.get("requires_fact_verification", False),
        "fact_sections": fact_sections,
        "image_sections": image_sections,
        "sections": [
            {
                "section_id": section["section_id"],
                "heading": section["heading"],
                "target_word_count": section.get("target_word_count", 0),
                "target_paragraph_count": section.get("target_paragraph_count", 0),
                "risk_tier": section.get("risk_tier", "medium"),
                "argument_complexity": section.get("argument_complexity", 0),
                "cross_section_dependency_count": section.get("cross_section_dependency_count", 0),
                "requires_fact_verification": section.get("requires_fact_verification", False),
                "requires_image": section.get("requires_image", False),
                "recommended_presentation": section.get("recommended_presentation", "prose"),
                "parallel_point_count": section.get("parallel_point_count", 1),
            }
            for section in sections
        ],
    }


def summarize_sections(section_manifest: dict) -> dict:
    sections = section_manifest.get("sections", [])
    risk_distribution = {"low": 0, "medium": 0, "high": 0}
    presentation_distribution: dict[str, int] = {}
    for section in sections:
        risk = section.get("risk_tier", "medium")
        risk_distribution[risk] = risk_distribution.get(risk, 0) + 1
        presentation = section.get("recommended_presentation", "prose")
        presentation_distribution[presentation] = presentation_distribution.get(presentation, 0) + 1
    return {
        "section_count": section_manifest.get("section_count", len(sections)),
        "total_target_word_count": sum(section.get("target_word_count", 0) for section in sections),
        "total_target_paragraph_count": sum(section.get("target_paragraph_count", 0) for section in sections),
        "fact_verification_section_ids": [section["section_id"] for section in sections if section.get("requires_fact_verification")],
        "image_section_ids": [section["section_id"] for section in sections if section.get("requires_image")],
        "risk_distribution": risk_distribution,
        "presentation_distribution": presentation_distribution,
    }


def _format_path(template: str, topic_id: str, package_id: str) -> str:
    return template.format(topic_id=topic_id, package_id=package_id)


def _sections_with_dependencies(package_scope: dict) -> list[str]:
    return [
        section["section_id"]
        for section in package_scope.get("sections", [])
        if section.get("cross_section_dependency_count", 0) > 0
    ]


def _presentation_expectations(package_scope: dict) -> list[str]:
    expectations = []
    for section in package_scope.get("sections", []):
        mode = section.get("recommended_presentation", "prose")
        if mode != "prose":
            expectations.append(f"{section['section_id']} -> {mode}")
    return expectations


def build_focus_points(role: str, package_scope: dict) -> list[str]:
    section_ids = ", ".join(package_scope.get("section_ids", [])) or "no sections"
    headings = package_scope.get("section_headings", [])
    fact_sections = package_scope.get("fact_sections", [])
    dependency_sections = _sections_with_dependencies(package_scope)
    word_count = package_scope.get("target_word_count", 0)
    paragraph_count = package_scope.get("target_paragraph_count", 0)

    shared = [
        f"Stay inside package boundary: {section_ids}.",
        f"Work against target size of about {word_count} words and {paragraph_count} paragraphs before final assembly.",
    ]
    if fact_sections:
        shared.append(f"Keep evidence-sensitive sections stable: {', '.join(fact_sections)}.")
    if dependency_sections:
        shared.append(f"Pay extra attention to sections with cross-section dependencies: {', '.join(dependency_sections)}.")
    if headings:
        shared.append(f"Package headings: {' | '.join(headings)}.")

    role_specific = {
        "writer-package": [
            "Draft all owned sections with full coverage before refinement passes.",
            "Preserve section thesis, evidence anchors, and package ordering from the manifest.",
        ],
        "primer-writer": [
            "Make each section opening understandable to a beginner before deeper detail appears.",
            "Reduce jargon shock without flattening the core claim.",
        ],
        "deep-dive-researcher": [
            "Add theory, mechanism, papers, implementation detail, or boundary conditions only where useful.",
            "Deepen the package without turning the body into an appendix or literature dump.",
        ],
        "structure-editor": [
            "Reorganize the written package into easier public-facing structure after the content is already on the page.",
            "Use bullets, numbered points, short labels, or tables only where they make the existing meaning easier to scan.",
        ],
        "narrative-smoother": [
            "Bridge beginner explanation and deep explanation so the package reads as one coherent arc.",
            "Remove abrupt jumps, filler transitions, and tone drift between sections.",
            "Keep structural presentation intact instead of flattening it back into wall-of-text prose.",
        ],
        "adversarial-reviewer": [
            "Pressure-test jargon gaps, logic breaks, unsupported claims, and AI-flavored phrasing.",
            "Patch the body directly instead of emitting a separate critique memo.",
        ],
        "package-check": [
            "Validate the final package output after adversarial revision, not an earlier stage output.",
            "Confirm section coverage and output readiness before draft assembly.",
        ],
    }
    return role_specific.get(role, []) + shared


def build_constraints(role: str, package_scope: dict) -> list[str]:
    constraints = [
        "Do not cross package boundaries or rewrite sections owned by another package.",
        "Do not introduce appendix material into the main body unless the role explicitly requires it.",
    ]
    if package_scope.get("requires_fact_verification"):
        constraints.append("Do not weaken or paraphrase away evidence-sensitive claims without preserving their support.")

    role_specific = {
        "writer-package": [
            "Do not skip any section assigned to the package.",
            "Do not invent new top-level claims outside the outline scope.",
        ],
        "primer-writer": [
            "Do not replace the section thesis while simplifying the opening.",
            "Do not delete evidence hooks that later stages need.",
        ],
        "deep-dive-researcher": [
            "Do not change the thesis direction while adding depth.",
            "Do not dump raw source lists into paragraph flow.",
        ],
        "structure-editor": [
            "Do not invent new claims, new evidence, or new cases while restructuring.",
            "Do not trade away meaning just to make the page look more structured.",
        ],
        "narrative-smoother": [
            "Do not introduce new arguments just to improve transitions.",
            "Do not smooth away concrete meaning into generic prose.",
            "Do not flatten lists, tables, or block structure back into prose paragraphs.",
        ],
        "adversarial-reviewer": [
            "Do not output an audit report; output repaired Markdown only.",
            "Do not leave unresolved logic breaks in the body when a direct patch is possible.",
        ],
        "package-check": [
            "Do not validate against earlier node outputs.",
            "Do not mark ready if package scope is visibly incomplete.",
        ],
    }
    return constraints + role_specific.get(role, [])


def build_acceptance_checks(role: str, package_scope: dict) -> list[str]:
    checks = {
        "writer-package": [
            "All package headings are covered in the draft output.",
            "Output is Markdown body text, not notes or planning prose.",
            "Draft stays inside assigned package scope.",
        ],
        "primer-writer": [
            "Each section begins with a beginner-friendly entry point.",
            "Core claims and evidence anchors remain intact.",
            "Output remains package-scoped Markdown.",
        ],
        "deep-dive-researcher": [
            "Adds useful mechanism, implementation, or theory detail without thesis drift.",
            "Does not turn the body into a source dump or appendix.",
            "Output remains package-scoped Markdown.",
        ],
        "structure-editor": [
            "Large or overloaded paragraphs are reorganized where needed without changing claims.",
            "Useful tables, bullets, or local structure are added only when they improve readability.",
            "Output remains package-scoped Markdown.",
        ],
        "narrative-smoother": [
            "Transitions are smoother across dependent sections.",
            "Tone is consistent and filler is reduced.",
            "Output remains package-scoped Markdown.",
        ],
        "adversarial-reviewer": [
            "Unsupported claims, jargon gaps, and AI-flavored phrasing are patched in the body.",
            "Output is repaired Markdown, not a review memo.",
            "Package scope is still preserved.",
        ],
        "package-check": [
            "Validation targets the adversarial reviewer output for this package.",
            "Package coverage matches the declared section IDs.",
            "Gate result is ready for draft assembly.",
        ],
    }
    role_checks = checks.get(role, [])
    if package_scope.get("fact_sections"):
        role_checks.append("Fact-sensitive sections still carry stable support through this pass.")
    return role_checks


def build_handoff_notes(role: str, package_id: str) -> list[str]:
    next_map = {
        "writer-package": [f"primer-writer-{package_id}"],
        "primer-writer": [f"deep-dive-researcher-{package_id}"],
        "deep-dive-researcher": [f"structure-editor-{package_id}"],
        "structure-editor": [f"narrative-smoother-{package_id}"],
        "narrative-smoother": [f"adversarial-reviewer-{package_id}"],
        "adversarial-reviewer": [f"package-check-{package_id}"],
        "package-check": ["draft-assembler-01"],
    }
    notes = []
    for node_id in next_map.get(role, []):
        notes.append(f"Primary downstream consumer: {node_id}.")
    if role == "package-check":
        notes.append("Only packages that pass this gate should move into article assembly.")
    return notes


def build_allowed_inputs(topic_id: str, package_id: str, role: str, package_scope: dict) -> list[dict]:
    section_headings = package_scope.get("section_headings", [])
    outline_input = {
        "path": f"tmp/{topic_id}-detailed-outline.md",
        "kind": "markdown_sections",
        "section_headings": section_headings,
    }
    package_input = {
        "path": f"skills/article-director/outputs/{topic_id}/article-packages.json",
        "kind": "article_package",
        "package_id": package_id,
    }
    section_manifest_input = {
        "path": f"skills/article-director/outputs/{topic_id}/section-manifest.json",
        "kind": "full_text",
    }
    upstream_map = {
        "writer-package": [],
        "primer-writer": [
            {
                "path": f"skills/article-director/outputs/{topic_id}/writer-{package_id}/output.md",
                "kind": "full_text",
            }
        ],
        "deep-dive-researcher": [
            {
                "path": f"skills/article-director/outputs/{topic_id}/primer-writer-{package_id}/output.md",
                "kind": "full_text",
            }
        ],
        "structure-editor": [
            {
                "path": f"skills/article-director/outputs/{topic_id}/deep-dive-researcher-{package_id}/output.md",
                "kind": "full_text",
            }
        ],
        "narrative-smoother": [
            {
                "path": f"skills/article-director/outputs/{topic_id}/structure-editor-{package_id}/output.md",
                "kind": "full_text",
            }
        ],
        "adversarial-reviewer": [
            {
                "path": f"skills/article-director/outputs/{topic_id}/narrative-smoother-{package_id}/output.md",
                "kind": "full_text",
            }
        ],
        "package-check": [
            {
                "path": f"skills/article-director/outputs/{topic_id}/adversarial-reviewer-{package_id}/output.md",
                "kind": "full_text",
            }
        ],
    }
    allowed = list(upstream_map.get(role, []))
    allowed.append(outline_input)
    allowed.append(package_input)
    if role in {"writer-package", "structure-editor", "package-check"}:
        allowed.append(section_manifest_input)
    return allowed


def build_handoff_contract(node_id: str, output_file: str, next_nodes: list[str], notes: list[str]) -> dict:
    return {
        "current_node": node_id,
        "output_file": output_file,
        "next_nodes": next_nodes,
        "notes": notes,
    }


def build_package_node_plan(topic_id: str, package: dict, package_scope: dict, role: str) -> dict:
    spec = PACKAGE_ROLE_SPECS[role]
    package_id = package["package_id"]
    role_index = PACKAGE_ROLE_ORDER.index(role)
    depends_on = []
    if role_index > 0:
        prev_role = PACKAGE_ROLE_ORDER[role_index - 1]
        depends_on = [_format_path(PACKAGE_ROLE_SPECS[prev_role]["node_id_template"], topic_id, package_id)]
        depends_on = [depends_on[0]]
    next_nodes = []
    if role_index < len(PACKAGE_ROLE_ORDER) - 1:
        next_role = PACKAGE_ROLE_ORDER[role_index + 1]
        next_nodes = [_format_path(PACKAGE_ROLE_SPECS[next_role]["node_id_template"], topic_id, package_id)]
    elif role == "package-check":
        next_nodes = ["draft-assembler-01"]

    node_id = _format_path(spec["node_id_template"], topic_id, package_id)
    output_file = _format_path(spec["output_template"], topic_id, package_id)
    constraints = build_constraints(role, package_scope)
    acceptance_checks = build_acceptance_checks(role, package_scope)
    handoff_notes = build_handoff_notes(role, package_id)
    objective = build_objective(role, package_scope)

    return {
        "micro_plan_id": node_id,
        "node_id": node_id,
        "role": role,
        "node_type": spec["node_type"],
        "stage": spec["stage"],
        "package_id": package_id,
        "package_order": package.get("package_order", 0),
        "depends_on": depends_on,
        "next_nodes": next_nodes,
        "input_files": [_format_path(path, topic_id, package_id) for path in spec["input_templates"]],
        "output_file": output_file,
        "objective": objective,
        "goal": objective,
        "scope": {
            "package_id": package_id,
            "section_ids": package_scope.get("section_ids", []),
            "section_headings": package_scope.get("section_headings", []),
        },
        "section_scope": {
            "section_ids": package_scope.get("section_ids", []),
            "section_headings": package_scope.get("section_headings", []),
        },
        "focus_points": build_focus_points(role, package_scope),
        "constraints": constraints,
        "forbidden_actions": constraints,
        "acceptance_checks": acceptance_checks,
        "verification_checklist": acceptance_checks,
        "required_outputs": [
            f"Write the expected node output to {output_file}.",
            f"Stay inside package scope {', '.join(package_scope.get('section_ids', []))}.",
        ],
        "stop_condition": [
            "Stop after this node output is ready for the next deterministic workflow node.",
            "Do not continue into downstream nodes inside the same execution.",
        ],
        "handoff_notes": handoff_notes,
        "handoff_contract": build_handoff_contract(node_id, output_file, next_nodes, handoff_notes),
        "allowed_inputs": build_allowed_inputs(topic_id, package_id, role, package_scope),
        "runtime_hints": {
            "provider": spec["provider"],
            "temperature": spec["temperature"],
            "parallel_unit": "section" if len(package_scope.get("section_ids", [])) == 1 else "package",
            "risk_tier": package_scope.get("risk_tier", "medium"),
        },
    }


def build_objective(role: str, package_scope: dict) -> str:
    section_count = len(package_scope.get("section_ids", []))
    if role == "writer-package":
        return f"Produce the first complete package draft covering {section_count} assigned sections."
    if role == "primer-writer":
        return "Rewrite each owned section so a beginner can enter the topic before deeper detail appears."
    if role == "deep-dive-researcher":
        return "Add depth, mechanism, implementation detail, and boundaries without changing the package thesis."
    if role == "structure-editor":
        return "Reshape the written package into clearer paragraphs, lists, or tables without changing the thesis."
    if role == "narrative-smoother":
        return "Fuse shallow explanation and deep explanation into one readable narrative arc."
    if role == "adversarial-reviewer":
        return "Pressure-test the package and return repaired Markdown that removes logic drift, jargon gaps, and fluff."
    if role == "package-check":
        return "Validate the repaired package output before assembly."
    return "Complete the assigned package task."


def build_global_plan(topic_id: str, section_manifest: dict, article_packages: dict) -> dict:
    package_summary = {
        "package_count": article_packages.get("package_count", len(article_packages.get("packages", []))),
        "packages": [
            {
                "package_id": package["package_id"],
                "package_order": package.get("package_order", 0),
                "section_ids": package.get("section_ids", []),
                "section_headings": package.get("section_headings", []),
                "target_word_count": package.get("target_word_count", 0),
                "target_paragraph_count": package.get("target_paragraph_count", 0),
                "package_score": package.get("package_score", 0.0),
                "risk_tier": package.get("risk_tier", "medium"),
                "requires_fact_verification": package.get("requires_fact_verification", False),
            }
            for package in article_packages.get("packages", [])
        ],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "plan_type": "global-plan",
        "topic_id": topic_id,
        "generated_at": now_iso(),
        "source_files": {
            "section_manifest": f"skills/article-director/outputs/{topic_id}/section-manifest.json",
            "article_packages": f"skills/article-director/outputs/{topic_id}/article-packages.json",
        },
        "section_summary": summarize_sections(section_manifest),
        "package_summary": package_summary,
        "execution_chain": {
            "package_roles": PACKAGE_ROLE_ORDER,
            "review_templates": [item["node_id"] for item in REVIEW_TEMPLATES],
        },
        "coordination_rules": [
            "Inside one package, nodes run in deterministic chain order.",
            "Across packages, same-stage package nodes may run in parallel.",
            "No package should enter assembly before package-check passes.",
            "Review templates are reserved for post-finalize whole-draft review, not package-local editing.",
        ],
        "outputs": {
            "node_micro_plans": f"skills/article-director/outputs/{topic_id}/micro-plan/node-micro-plans.json",
            "revision_plan_dir": f"skills/article-director/outputs/{topic_id}/micro-plan/revision-plans/",
        },
    }


def build_node_micro_plan_payload(topic_id: str, section_manifest: dict, article_packages: dict) -> dict:
    section_lookup = build_section_lookup(section_manifest)
    package_plans = []
    flat_micro_plans = []
    for package in article_packages.get("packages", []):
        package_scope = build_package_scope(package, section_lookup)
        package_nodes = [
            build_package_node_plan(topic_id, package, package_scope, role)
            for role in PACKAGE_ROLE_ORDER
        ]
        package_plans.append(
            {
                "package_id": package["package_id"],
                "package_order": package.get("package_order", 0),
                "package_scope": package_scope,
                "nodes": package_nodes,
            }
        )
        flat_micro_plans.extend(package_nodes)

    review_templates = []
    for template in REVIEW_TEMPLATES:
        node_id = template["node_id"]
        output_file = template["output_file"].format(topic_id=topic_id)
        constraints = template["constraints"]
        acceptance_checks = template["acceptance_checks"]
        handoff_notes = template["handoff_notes"]
        review_plan = {
            "micro_plan_id": node_id,
            "node_id": node_id,
            "role": template["role"],
            "review_variant": template["review_variant"],
            "node_type": template["node_type"],
            "stage": template["stage"],
            "depends_on": template["depends_on"],
            "next_nodes": template["next_nodes"],
            "input_files": [path.format(topic_id=topic_id) for path in template["input_files"]],
            "output_file": output_file,
            "objective": template["objective"],
            "goal": template["objective"],
            "scope": {"article_scope": "whole-draft-review", "review_variant": template["review_variant"]},
            "focus_points": template["focus_points"],
            "constraints": constraints,
            "forbidden_actions": constraints,
            "acceptance_checks": acceptance_checks,
            "verification_checklist": acceptance_checks,
            "required_outputs": [
                f"Write strict JSON review output to {output_file}.",
                "Keep review findings scoped to whole-draft review rather than rewriting the article.",
            ],
            "stop_condition": [
                "Stop after the review payload is complete and valid JSON.",
                "Do not start merging or rewriting downstream nodes.",
            ],
            "handoff_notes": handoff_notes,
            "handoff_contract": build_handoff_contract(node_id, output_file, template["next_nodes"], handoff_notes),
            "allowed_inputs": [
                {
                    "path": f"tmp/{topic_id}-draft.md",
                    "kind": "full_text",
                },
                {
                    "path": f"skills/article-director/outputs/{topic_id}/section-manifest.json",
                    "kind": "full_text",
                },
            ],
            "runtime_hints": {
                "provider": template["provider"],
                "temperature": template["temperature"],
                "parallel_with": [item["node_id"] for item in REVIEW_TEMPLATES if item["node_id"] != template["node_id"]],
            },
        }
        review_templates.append(review_plan)
        flat_micro_plans.append(review_plan)

    return {
        "schema_version": SCHEMA_VERSION,
        "plan_type": "node-micro-plans",
        "topic_id": topic_id,
        "generated_at": now_iso(),
        "package_plans": package_plans,
        "review_templates": review_templates,
        "micro_plans": flat_micro_plans,
    }


def write_micro_plans(topic_id: str, project_root: Path) -> tuple[Path, Path]:
    project_dir, section_manifest, article_packages = load_topic_payloads(project_root, topic_id)
    micro_plan_dir = project_dir / "micro-plan"
    global_plan = build_global_plan(topic_id, section_manifest, article_packages)
    node_plans = build_node_micro_plan_payload(topic_id, section_manifest, article_packages)

    global_plan_path = micro_plan_dir / "global-plan.json"
    node_plan_path = micro_plan_dir / "node-micro-plans.json"
    write_json(global_plan_path, global_plan)
    write_json(node_plan_path, node_plans)
    return global_plan_path, node_plan_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build article-director global and node micro plans")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    global_plan_path, node_plan_path = write_micro_plans(args.topic_id, project_root)
    print(global_plan_path)
    print(node_plan_path)


if __name__ == "__main__":
    main()
