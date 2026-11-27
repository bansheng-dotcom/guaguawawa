import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMAS: dict[str, dict[str, Any]] = {
    "execution-plan": {
        "kind": "markdown",
        "required_patterns": [
            r"(?mi)^##?\s*(执行计划|Execution Plan)",
            r"(?mi)^##?\s*(任务拆解|Task Breakdown)",
        ],
        "min_list_items": 3,
    },
    "topic-outline": {
        "kind": "markdown",
        "required_patterns": [
            r"(?mi)^#\s+.+",
            r"(?mi)^##\s+.+",
        ],
    },
    "detailed-outline": {
        "kind": "markdown",
        "required_patterns": [
            r"(?mi)^#\s+.+",
            r"(?mi)^##\s+.+",
        ],
        "required_section_labels": [
            "论点",
            "读者卡点",
            "上下游承接",
            "逻辑难点",
            "需要解释",
            "需要引用",
            "需要案例",
            "提示词样例",
            "规范化前后",
            "展示方式",
            "writer可执行信息",
            "待研究",
        ],
    },
    "article-review-result": {
        "kind": "json",
        "required_fields": ["pass", "score", "summary"],
        "required_any": [
            ["scope", "round1_逻辑", "round1_logic"],
            ["dimension", "round2_AI味", "round2_ai_tone"],
            ["issues", "round3_人感", "round3_reader_feel"],
        ],
    },
    "section-review-result": {
        "kind": "json",
        "required_fields": ["pass", "score", "summary"],
    },
    "ai-tone-context-pack": {
        "kind": "json",
        "required_fields": [
            "schema_version",
            "topic_id",
            "section_id",
            "phase",
            "idempotency_key",
            "source",
            "scan_path",
            "log_dir",
            "audit_must_include",
        ],
    },
    "term-extraction-result": {
        "kind": "json",
        "required_fields": ["terms", "summary"],
    },
    "section-review-context": {
        "kind": "json",
        "required_fields": ["pass", "topic_id", "section_id", "reviews", "terms"],
    },
    "paragraph-rewrite-design": {
        "kind": "json",
        "required_fields": [
            "pass",
            "summary",
            "section_id",
            "rewrite_mode",
            "section_rewrite_intent",
            "handoff_to_rewriter",
        ],
    },
    "section-editor-result": {
        "kind": "json",
        "required_fields": [
            "pass",
            "score",
            "summary",
            "scope",
            "section_id",
            "ai_tone_audit",
            "logic_review",
            "structure_review",
            "terms",
            "paragraph_rewrite_design_consumed",
            "final_markdown",
        ],
    },
    "image-manifest": {
        "kind": "json",
        "required_fields": ["topic_id", "generated_at", "images"],
    },
    "section-manifest": {
        "kind": "json",
        "required_fields": ["topic_id", "sections"],
    },
    "article-packages": {
        "kind": "json",
        "required_fields": ["topic_id", "package_count", "packages"],
    },
    "image-manifest-source": {
        "kind": "json",
        "required_fields": ["topic_id", "images"],
    },
    "image-packages": {
        "kind": "json",
        "required_fields": ["topic_id", "package_count", "packages"],
    },
    "image-component-manifest": {
        "kind": "json",
        "required_fields": ["topic_id", "components"],
    },
    "expanded-workflow": {
        "kind": "python",
        "required_patterns": [
            r"PROJECT_ID\s*=",
            r"NODE_DEFS\s*=",
            r"EDGE_DEFS\s*=",
        ],
    },
    "experiment-manifest": {
        "kind": "json",
        "required_fields": ["topic_id", "baseline", "scenarios", "source_files"],
    },
    "normalized-runs": {
        "kind": "json",
        "required_fields": ["topic_id", "baseline", "scenarios", "source_files"],
    },
    "experiment-summary": {
        "kind": "json",
        "required_fields": ["baseline", "scenarios", "best_savings", "source_files"],
    },
    "code-check-result": {
        "kind": "json",
        "required_fields": ["pass", "issues", "file"],
        "optional_fields": ["passed"],
    },
    "review-diff-result": {
        "kind": "json",
        "required_fields": ["pass", "consensus", "conflicts", "review_a_path", "review_b_path"],
    },
    "content-ingest-result": {
        "kind": "json",
        "required_fields": ["pass", "formal_id", "publish_path", "outline_path", "asset_dir", "source_dir"],
    },
}


def validate_markdown(text: str, schema: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for pattern in schema.get("required_patterns", []):
        if not re.search(pattern, text, re.MULTILINE):
            failures.append(f"missing pattern: {pattern}")
    min_items = schema.get("min_list_items")
    if min_items:
        items = re.findall(r"(?mi)^\s*(?:\d+\.|-|\*)\s+\S", text)
        if len(items) < min_items:
            failures.append(f"list items below minimum: {len(items)} < {min_items}")

    section_labels = schema.get("required_section_labels", [])
    if section_labels:
        failures.extend(validate_markdown_section_labels(text, section_labels))
    return failures


SECTION_LABEL_ALIASES: dict[str, list[str]] = {
    "读者卡点": ["读者卡点", "读者难点", "读者理解卡点"],
    "上下游承接": ["上下游承接", "上下游知识", "上下游连接", "前后承接"],
    "提示词样例": ["提示词样例", "prompt 示例", "prompt样例", "Prompt 示例"],
    "规范化前后": ["规范化前后", "before/after", "Before/After", "前后对比"],
    "展示方式": ["展示方式", "展示形式", "呈现方式"],
    "writer可执行信息": ["writer可执行信息", "写作执行信息", "writer 执行信息"],
}


def markdown_h2_sections(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[start:end]))
    return sections


def section_has_label(section_text: str, label: str) -> bool:
    aliases = SECTION_LABEL_ALIASES.get(label, [label])
    return any(
        re.search(rf"(?mi)^\s*{re.escape(alias)}\s*:", section_text)
        for alias in aliases
    )


def validate_markdown_section_labels(text: str, labels: list[str]) -> list[str]:
    sections = markdown_h2_sections(text)
    if not sections:
        return ["detailed outline must contain at least one H2 section"]

    failures: list[str] = []
    for heading, body in sections:
        missing = [label for label in labels if not section_has_label(body, label)]
        if missing:
            failures.append(f"section '{heading}' missing labels: {', '.join(missing)}")
    return failures


def validate_json(text: str, schema: dict[str, Any]) -> list[str]:
    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        return [f"json parse failed: {exc}"]

    failures: list[str] = []
    for field in schema.get("required_fields", []):
        if field not in data:
            failures.append(f"missing field: {field}")

    for options in schema.get("required_any", []):
        if not any(option in data for option in options):
            failures.append(f"missing any-of fields: {options}")

    return failures


def parse_json_payload(text: str) -> Any:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {}


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_issue_list(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if isinstance(item, str):
            continue
        if isinstance(item, dict) and (
            "issue" in item
            or "message" in item
            or "id" in item
            or "quote" in item
            or "why_ai_like" in item
            or "repair_strategy" in item
        ):
            continue
        return False
    return True


def validate_article_review_result(text: str) -> list[str]:
    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        return [f"json parse failed: {exc}"]

    failures: list[str] = []
    common_required = ["pass", "score", "summary"]
    current_required = [
        "scope",
        "dimension",
        "issues",
        "blocking_issues",
        "advisory_issues",
        "must_fix",
    ]
    legacy_rounds = (
        "round1_逻辑",
        "round2_AI味",
        "round3_人感",
        "round1_logic",
        "round2_ai_tone",
        "round3_reader_feel",
    )
    has_current_contract = any(field in data for field in ("scope", "dimension", "issues"))
    has_legacy_contract = any(field in data for field in legacy_rounds)
    required_fields = common_required + (current_required if has_current_contract or not has_legacy_contract else [])
    for field in required_fields:
        if field not in data:
            failures.append(f"missing field: {field}")

    if "pass" in data and not isinstance(data["pass"], bool):
        failures.append("field pass must be bool")
    if "score" in data:
        try:
            score = float(data["score"])
            if score < 0 or score > 100:
                failures.append("field score must be between 0 and 100")
        except (TypeError, ValueError):
            failures.append("field score must be numeric")
    if "summary" in data and not isinstance(data["summary"], str):
        failures.append("field summary must be string")

    if "scope" in data and not isinstance(data["scope"], str):
        failures.append("field scope must be string")
    if "dimension" in data and not isinstance(data["dimension"], str):
        failures.append("field dimension must be string")

    for field in ("issues", "blocking_issues", "advisory_issues", "must_fix"):
        if field in data and not _is_issue_list(data[field]):
            failures.append(f"{field} must be list[str|issue-object]")

    for round_key in legacy_rounds:
        round_payload = data.get(round_key)
        if round_payload is None:
            continue
        if not isinstance(round_payload, dict):
            failures.append(f"{round_key} must be object")
            continue
        if "pass" not in round_payload or not isinstance(round_payload.get("pass"), bool):
            failures.append(f"{round_key}.pass must be bool")
        if "notes" not in round_payload or not _is_issue_list(round_payload.get("notes")):
            failures.append(f"{round_key}.notes must be string list or issue-object list")

    return failures


def validate_ai_tone_section_review(data: dict[str, Any], output_path: Path) -> list[str]:
    failures: list[str] = []
    required = [
        "scope",
        "dimension",
        "issues",
        "blocking_issues",
        "advisory_issues",
        "must_fix",
        "ai_tone_invocation",
    ]
    for field in required:
        if field not in data:
            failures.append(f"AI tone review missing field: {field}")
    if data.get("scope") != "section":
        failures.append("AI tone review scope must be section")
    if data.get("dimension") != "ai_tone":
        failures.append("AI tone review dimension must be ai_tone")
    invocation = data.get("ai_tone_invocation")
    if not isinstance(invocation, dict):
        failures.append("AI tone review ai_tone_invocation must be object")
        invocation = {}
    for field in ("topic_id", "section_id", "phase", "idempotency_key", "source_hash"):
        if not str(invocation.get(field, "")).strip():
            failures.append(f"AI tone review invocation missing {field}")
    context_path = output_path.parent / "ai-tone-context-pack.json"
    if not context_path.exists():
        failures.append("AI tone review missing sibling ai-tone-context-pack.json")
        return failures
    try:
        context = json.loads(context_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        failures.append(f"AI tone context pack parse failed: {exc}")
        return failures
    expected = context.get("audit_must_include", {}).get("ai_tone_invocation", {})
    for field in ("topic_id", "section_id", "phase", "idempotency_key", "source_hash"):
        if str(invocation.get(field, "")) != str(expected.get(field, "")):
            failures.append(f"AI tone invocation {field} does not match context pack")
    scan_path_raw = context.get("scan_path")
    if scan_path_raw:
        scan_path = Path(str(scan_path_raw))
        try:
            scan_payload = json.loads(scan_path.read_text(encoding="utf-8-sig")) if scan_path.exists() else {}
        except json.JSONDecodeError:
            scan_payload = {}
        scan_hit_count = int(scan_payload.get("scan", {}).get("hit_count", 0) or 0)
        issue_total = 0
        for field in ("issues", "blocking_issues", "advisory_issues", "must_fix"):
            value = data.get(field)
            if isinstance(value, list):
                issue_total += len(value)
        if scan_hit_count > 0 and issue_total == 0:
            if not data.get("deterministic_evidence_acknowledged") and not data.get("false_positive_notes"):
                failures.append("AI tone deterministic scan has hits but audit has no issue or false-positive explanation")
    return failures


def validate_review_diff_result(text: str) -> list[str]:
    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        return [f"json parse failed: {exc}"]

    failures: list[str] = []
    required_fields = [
        "pass",
        "consensus",
        "conflicts",
        "review_a_path",
        "review_b_path",
        "blocking_issues",
        "advisory_issues",
        "rollback_target",
        "rollback_targets",
        "revision_required",
        "human_review_required",
        "summary",
    ]
    for field in required_fields:
        if field not in data:
            failures.append(f"missing field: {field}")

    if "pass" in data and not isinstance(data["pass"], bool):
        failures.append("field pass must be bool")
    if "consensus" in data and data["consensus"] not in {"approved", "revise", "human-review"}:
        failures.append("field consensus must be approved|revise|human-review")
    if "conflicts" in data and not _is_issue_list(data["conflicts"]):
        failures.append("field conflicts must be list[str|issue-object]")
    for field in ("blocking_issues", "advisory_issues", "rollback_targets", "failing_dimensions"):
        if field in data and not isinstance(data[field], list):
            failures.append(f"field {field} must be list")
    for field in ("revision_required", "human_review_required"):
        if field in data and not isinstance(data[field], bool):
            failures.append(f"field {field} must be bool")
    if "rollback_target" in data and not isinstance(data["rollback_target"], str):
        failures.append("field rollback_target must be string")
    if "summary" in data and not isinstance(data["summary"], str):
        failures.append("field summary must be string")

    return failures


def validate_python(text: str, schema: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for pattern in schema.get("required_patterns", []):
        if not re.search(pattern, text, re.MULTILINE):
            failures.append(f"missing pattern: {pattern}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate article-director outputs")
    parser.add_argument("--output", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    path = Path(args.output)
    if not path.exists():
        print(json.dumps({"passed": False, "failures": [f"file not found: {path}"]}, ensure_ascii=False, indent=2))
        sys.exit(1)

    schema = SCHEMAS.get(args.schema)
    if not schema:
        print(json.dumps({"passed": True, "warnings": [f"unknown schema: {args.schema}"]}, ensure_ascii=False, indent=2))
        return

    text = path.read_text(encoding="utf-8-sig")
    kind = schema["kind"]
    if kind == "markdown":
        failures = validate_markdown(text, schema)
    elif kind == "json":
        if args.schema == "article-review-result":
            failures = validate_article_review_result(text)
        elif args.schema == "review-diff-result":
            failures = validate_review_diff_result(text)
        elif args.schema == "section-review-result":
            failures = validate_json(text, SCHEMAS["section-review-result"])
            data = parse_json_payload(text)
            if "issues" in data and not _is_issue_list(data.get("issues")):
                failures.append("issues must be list[str|issue-object]")
            if "blocking_issues" in data and not _is_issue_list(data.get("blocking_issues")):
                failures.append("blocking_issues must be list[str|issue-object]")
            if path.name in {"review-ai-tone.json", "review-ai-tone-findings.json"} or data.get("dimension") == "ai_tone":
                if isinstance(data, dict):
                    failures.extend(validate_ai_tone_section_review(data, path))
                else:
                    failures.append("AI tone review output must be object")
        elif args.schema == "term-extraction-result":
            failures = validate_json(text, SCHEMAS["term-extraction-result"])
            data = parse_json_payload(text)
            if "terms" in data and not isinstance(data.get("terms"), list):
                failures.append("terms must be list")
        elif args.schema == "section-review-context":
            failures = validate_json(text, SCHEMAS["section-review-context"])
        elif args.schema == "paragraph-rewrite-design":
            failures = validate_json(text, SCHEMAS["paragraph-rewrite-design"])
            data = parse_json_payload(text)
            if isinstance(data, dict):
                rewrite_mode = str(data.get("rewrite_mode") or "")
                if rewrite_mode == "paragraph_rewrite_design_v2":
                    expected_rubric = {
                        "meaning_and_fact_preservation": 20,
                        "review_absorption": 20,
                        "de_ai_tone": 15,
                        "reader_readability": 15,
                        "workflow_scene": 10,
                        "author_judgment_and_light_soul": 10,
                        "section_connection": 10,
                    }
                    rubric = data.get("judge_rubric")
                    if not isinstance(rubric, dict):
                        failures.append("judge_rubric must be object")
                        rubric = {}
                    for key, expected_value in expected_rubric.items():
                        if rubric.get(key) != expected_value:
                            failures.append(f"judge_rubric.{key} must be {expected_value}")

                    coverage = data.get("coverage")
                    if not isinstance(coverage, dict):
                        failures.append("coverage must be object")
                        coverage = {}
                    body_ids = coverage.get("body_paragraph_ids")
                    covered_ids = coverage.get("covered_paragraph_ids")
                    if not isinstance(body_ids, list) or not body_ids:
                        failures.append("coverage.body_paragraph_ids must be a non-empty list")
                        body_ids = []
                    if not isinstance(covered_ids, list) or not covered_ids:
                        failures.append("coverage.covered_paragraph_ids must be a non-empty list")
                        covered_ids = []
                    missing_coverage = sorted(set(map(str, body_ids)) - set(map(str, covered_ids)))
                    if missing_coverage:
                        failures.append(f"coverage.covered_paragraph_ids missing body paragraphs: {', '.join(missing_coverage)}")
                    preserved_non_body_ids = coverage.get("preserved_non_body_ids")
                    if preserved_non_body_ids is not None and not isinstance(preserved_non_body_ids, list):
                        failures.append("coverage.preserved_non_body_ids must be list")

                    rewrite_units = data.get("rewrite_units")
                    if not isinstance(rewrite_units, list):
                        failures.append("rewrite_units must be list")
                        rewrite_units = []
                    valid_intensities = {"local_rewrite", "unit_redesign", "section_bridge"}
                    unit_source_ids: set[str] = set()
                    for index, unit in enumerate(rewrite_units):
                        if not isinstance(unit, dict):
                            failures.append(f"rewrite_units[{index}] must be object")
                            continue
                        for field in ("unit_id", "source_paragraph_ids", "rewrite_intensity", "current_function", "target_function", "meaning_to_preserve"):
                            if field not in unit:
                                failures.append(f"rewrite_units[{index}].{field} is required")
                        source_ids = unit.get("source_paragraph_ids")
                        if not isinstance(source_ids, list) or not source_ids:
                            failures.append(f"rewrite_units[{index}].source_paragraph_ids must be a non-empty list")
                            source_ids = []
                        unit_source_ids.update(map(str, source_ids))
                        intensity = str(unit.get("rewrite_intensity") or "")
                        if intensity not in valid_intensities:
                            failures.append(f"rewrite_units[{index}].rewrite_intensity must be one of {', '.join(sorted(valid_intensities))}")
                        for field in ("problems_to_absorb", "meaning_to_preserve", "non_negotiables", "allowed_micro_edits", "do_not_change"):
                            if field in unit and not isinstance(unit.get(field), list):
                                failures.append(f"rewrite_units[{index}].{field} must be list")
                        candidates = unit.get("candidates", [])
                        if candidates is not None and not isinstance(candidates, list):
                            failures.append(f"rewrite_units[{index}].candidates must be list")
                            candidates = []
                        if intensity == "unit_redesign":
                            if not isinstance(candidates, list) or len(candidates) < 2 or len(candidates) > 4:
                                failures.append(f"rewrite_units[{index}].unit_redesign candidates must contain 2-4 items")
                                candidates = [] if not isinstance(candidates, list) else candidates
                            selected = str(unit.get("selected_candidate") or "")
                            if not selected:
                                failures.append(f"rewrite_units[{index}].selected_candidate is required for unit_redesign")
                            if not str(unit.get("selected_draft") or "").strip():
                                failures.append(f"rewrite_units[{index}].selected_draft is required for unit_redesign")
                            candidate_ids = {str(candidate.get("candidate_id") or "") for candidate in candidates if isinstance(candidate, dict)}
                            if selected and candidate_ids and selected not in candidate_ids:
                                failures.append(f"rewrite_units[{index}].selected_candidate must match a candidate_id")
                            for candidate_index, candidate in enumerate(candidates):
                                if not isinstance(candidate, dict):
                                    failures.append(f"rewrite_units[{index}].candidates[{candidate_index}] must be object")
                                    continue
                                if not str(candidate.get("draft") or "").strip():
                                    failures.append(f"rewrite_units[{index}].candidates[{candidate_index}].draft is required")
                                scores = candidate.get("scores")
                                if not isinstance(scores, dict):
                                    failures.append(f"rewrite_units[{index}].candidates[{candidate_index}].scores must be object")
                                    continue
                                for key in expected_rubric:
                                    value = scores.get(key)
                                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                                        failures.append(f"rewrite_units[{index}].candidates[{candidate_index}].scores.{key} must be number")
                                total = scores.get("total")
                                if not isinstance(total, (int, float)) or isinstance(total, bool):
                                    failures.append(f"rewrite_units[{index}].candidates[{candidate_index}].scores.total must be number")
                        elif intensity in {"local_rewrite", "section_bridge"}:
                            if not str(unit.get("selected_draft") or unit.get("judge_reason") or "").strip():
                                failures.append(f"rewrite_units[{index}] must include selected_draft or judge_reason")

                    micro_edits = data.get("paragraph_micro_edits")
                    if not isinstance(micro_edits, list):
                        failures.append("paragraph_micro_edits must be list")
                        micro_edits = []
                    micro_ids: set[str] = set()
                    for index, edit in enumerate(micro_edits):
                        if not isinstance(edit, dict):
                            failures.append(f"paragraph_micro_edits[{index}] must be object")
                            continue
                        paragraph_id = str(edit.get("paragraph_id") or "")
                        if not paragraph_id:
                            failures.append(f"paragraph_micro_edits[{index}].paragraph_id is required")
                        else:
                            micro_ids.add(paragraph_id)
                        if not str(edit.get("instruction") or "").strip():
                            failures.append(f"paragraph_micro_edits[{index}].instruction is required")
                        if not str(edit.get("reason") or "").strip():
                            failures.append(f"paragraph_micro_edits[{index}].reason is required")
                        if "avoid" in edit and not isinstance(edit.get("avoid"), list):
                            failures.append(f"paragraph_micro_edits[{index}].avoid must be list")
                    actual_covered = unit_source_ids | micro_ids
                    missing_actual_coverage = sorted(set(map(str, body_ids)) - actual_covered)
                    if missing_actual_coverage:
                        failures.append(f"body paragraphs lack rewrite unit or micro edit coverage: {', '.join(missing_actual_coverage)}")
                elif rewrite_mode == "paragraph_rewrite_design":
                    designs = data.get("designs")
                    if not isinstance(designs, list) or not designs:
                        failures.append("designs must be a non-empty list")
                    else:
                        required_design_fields = [
                            "paragraph_ids",
                            "current_function",
                            "target_function",
                            "rewrite_scope",
                            "problems_to_absorb",
                            "meaning_to_preserve",
                            "target_shape",
                            "avoid",
                        ]
                        valid_scopes = {
                            "keep",
                            "rewrite_sentence",
                            "rewrite_whole_paragraph",
                            "merge_paragraphs",
                            "split_paragraph",
                            "delete",
                        }
                        for index, design in enumerate(designs):
                            if not isinstance(design, dict):
                                failures.append(f"designs[{index}] must be object")
                                continue
                            for field in required_design_fields:
                                if field not in design:
                                    failures.append(f"designs[{index}].{field} is required")
                            paragraph_ids = design.get("paragraph_ids")
                            if not isinstance(paragraph_ids, list) or not paragraph_ids:
                                failures.append(f"designs[{index}].paragraph_ids must be a non-empty list")
                            scope = str(design.get("rewrite_scope") or "")
                            if scope not in valid_scopes:
                                failures.append(f"designs[{index}].rewrite_scope must be one of {', '.join(sorted(valid_scopes))}")
                            for field in ("problems_to_absorb", "meaning_to_preserve", "target_shape", "avoid"):
                                if field in design and not isinstance(design.get(field), list):
                                    failures.append(f"designs[{index}].{field} must be list")
                else:
                    failures.append("rewrite_mode must be paragraph_rewrite_design_v2 or paragraph_rewrite_design")
            else:
                failures.append("paragraph rewrite design output must be object")
        elif args.schema == "section-editor-result":
            failures = validate_json(text, SCHEMAS["section-editor-result"])
            data = parse_json_payload(text)
            if isinstance(data, dict):
                if data.get("scope") != "section":
                    failures.append("scope must be section")
                if not isinstance(data.get("ai_tone_audit"), dict):
                    failures.append("ai_tone_audit must be object")
                if not isinstance(data.get("logic_review"), dict):
                    failures.append("logic_review must be object")
                if not isinstance(data.get("structure_review"), dict):
                    failures.append("structure_review must be object")
                if not isinstance(data.get("terms"), list):
                    failures.append("terms must be list")
                design_consumed = data.get("paragraph_rewrite_design_consumed")
                if not isinstance(design_consumed, dict):
                    failures.append("paragraph_rewrite_design_consumed must be object")
                else:
                    if not str(design_consumed.get("design_summary") or "").strip():
                        failures.append("paragraph_rewrite_design_consumed.design_summary is required")
                    v2_fields = ("covered_paragraph_ids", "used_units", "adapted_units", "micro_edits_applied", "bridge_edits", "deferred_items")
                    legacy_fields = ("used_designs", "adapted_designs", "ignored_designs")
                    has_v2 = any(field in design_consumed for field in v2_fields)
                    has_legacy = any(field in design_consumed for field in legacy_fields)
                    if has_v2:
                        for field in v2_fields:
                            if not isinstance(design_consumed.get(field), list):
                                failures.append(f"paragraph_rewrite_design_consumed.{field} must be list")
                    elif has_legacy:
                        for field in legacy_fields:
                            if not isinstance(design_consumed.get(field), list):
                                failures.append(f"paragraph_rewrite_design_consumed.{field} must be list")
                    else:
                        failures.append("paragraph_rewrite_design_consumed must include v2 unit fields or legacy design fields")
                supervisor = data.get("supervisor_judgment")
                if not isinstance(supervisor, dict):
                    failures.append("supervisor_judgment must be object")
                    supervisor = {}
                title_complexity = str(supervisor.get("title_complexity") or "").strip().lower()
                if title_complexity not in {"simple", "complex"}:
                    failures.append("supervisor_judgment.title_complexity must be simple|complex")
                logic_policy = supervisor.get("logic_load_policy")
                if not isinstance(logic_policy, dict):
                    failures.append("supervisor_judgment.logic_load_policy must be object")
                    logic_policy = {}
                expected_policy = "strict" if title_complexity == "simple" else "contextual" if title_complexity == "complex" else ""
                for field in ("judgment_count", "causal_chain_length", "concept_density"):
                    value = str(logic_policy.get(field) or "").strip().lower()
                    if value not in {"strict", "contextual"}:
                        failures.append(f"supervisor_judgment.logic_load_policy.{field} must be strict|contextual")
                    elif expected_policy and value != expected_policy:
                        failures.append(f"supervisor_judgment.logic_load_policy.{field} must be {expected_policy} for {title_complexity}")
                final_markdown = data.get("final_markdown")
                if not isinstance(final_markdown, str) or not final_markdown.strip():
                    failures.append("final_markdown must be non-empty string")
                elif not re.search(r"(?m)^##\s+", final_markdown):
                    failures.append("final_markdown must contain one ## section heading")
        else:
            failures = validate_json(text, schema)
    else:
        failures = validate_python(text, schema)

    print(json.dumps({"passed": not failures, "schema": args.schema, "failures": failures}, ensure_ascii=False, indent=2))
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
