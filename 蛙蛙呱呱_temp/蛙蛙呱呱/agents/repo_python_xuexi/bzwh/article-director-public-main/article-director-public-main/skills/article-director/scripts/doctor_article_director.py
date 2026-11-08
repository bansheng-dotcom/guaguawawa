import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_ROOT.parents[1]
OUTPUTS_DIR = SKILL_ROOT / "outputs"

BAD_OUTPUT_DIRS = {
    "echobird-codex-deepseek-tutorial",
    "echobird-codex-deepseek-tutorial-r2",
    "echobird-codex-deepseek-tutorial-r3",
    "echobird-codex-deepseek-tutorial-r4",
    "strategy-playbook-smoke",
    "tutorial-strategy-smoke",
    "tutorial-strategy-v2-smoke",
    "validation-teaching-playbook",
    "_validation",
}

REMOVED_SHORT_SCRIPTS = {
    "compile_short_article_workflow.py",
    "build_short_article_packages.py",
    "seed_short_article_memory.py",
    "build_short_appendix.py",
}


def _issue(message: str, path: Path | None = None) -> dict:
    payload = {"message": message}
    if path is not None:
        payload["path"] = str(path)
    return payload


def _run_python(script: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(PROJECT_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    output = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, output


def check_filesystem() -> list[dict]:
    issues: list[dict] = []
    for dirname in BAD_OUTPUT_DIRS:
        path = OUTPUTS_DIR / dirname
        if path.exists():
            issues.append(_issue("bad or validation output directory still exists", path))
    for path in OUTPUTS_DIR.iterdir() if OUTPUTS_DIR.exists() else []:
        if path.is_dir() and "smoke" in path.name.lower():
            issues.append(_issue("smoke validation output directory should be removed after validation", path))
    for script_name in REMOVED_SHORT_SCRIPTS:
        path = SCRIPT_DIR / script_name
        if path.exists():
            issues.append(_issue("deprecated short workflow script still exists", path))
    for path in OUTPUTS_DIR.rglob("*_short.py"):
        issues.append(_issue("deprecated generated short workflow still exists", path))
    for path in OUTPUTS_DIR.rglob("__pycache__"):
        if "_archive-bad-runs" in path.parts:
            continue
        if "workflow-shape-check-" in str(path.parent):
            continue
        issues.append(_issue("Python cache directory under outputs may hide stale generated workflows", path))
    return issues


def check_entrypoint_docs() -> list[dict]:
    issues: list[dict] = []
    skill_md = SKILL_ROOT / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    required = [
        "init_workflow.py -> workflow_runner.py -> compile_expanded_workflow.py",
        "Deprecated / Disabled Paths",
        "compile_short_article_workflow.py",
    ]
    for marker in required:
        if marker not in text:
            issues.append(_issue(f"SKILL.md missing stability marker: {marker}", skill_md))
    return issues


def check_runner_guards() -> list[dict]:
    issues: list[dict] = []
    runner = SCRIPT_DIR / "workflow_runner.py"
    text = runner.read_text(encoding="utf-8")
    required = [
        "DISABLED_TOPIC_PREFIXES",
        "_guard_workflow_script_path",
        "endswith(\"_short.py\")",
        "echobird-codex-deepseek-tutorial",
        "ARTICLE_DIRECTOR_WORKFLOW_VERSION",
        "--allow-legacy-script",
    ]
    for marker in required:
        if marker not in text:
            issues.append(_issue(f"workflow_runner.py missing guard marker: {marker}", runner))
    return issues


def check_default_workflow_shape() -> list[dict]:
    issues: list[dict] = []
    compiler = SCRIPT_DIR / "compile_expanded_workflow.py"
    text = compiler.read_text(encoding="utf-8")
    required = [
        "MAX_PARALLEL_SECTIONS = 3",
        'writer_id = f"writer-section-{section_id}"',
        'prepare_ai_tone_id = f"prepare-ai-tone-call-{section_id}"',
        '"review-ai-tone"',
        'audit_gate_id = f"validate-ai-tone-audit-{section_id}"',
        'repair_plan_id = f"build-ai-tone-repair-plan-{section_id}"',
        '"review-logic"',
        '"review-structure"',
        '"extract-terms"',
        '"revise-structure"',
        '"revise-de-ai"',
        'regression_id = f"ai-tone-regression-{section_id}"',
        '"revise-personal-style"',
        '"revise-logic"',
        'complete_id = f"section-complete-{section_id}"',
        'node_id="code-check-01"',
        '{"from_node": "code-check-01", "to_node": "human-approval-01"}',
        '"approval_key": "final-article-approval"',
    ]
    forbidden = [
        'node_id="content-ingest-01"',
        '"approval_key": "publish-approval"',
        '{"from_node": "human-approval-01", "to_node": "content-ingest-01"}',
    ]
    for marker in required:
        if marker not in text:
            issues.append(_issue(f"compile_expanded_workflow.py missing default-chain marker: {marker}", compiler))
    for marker in forbidden:
        if marker in text:
            issues.append(_issue(f"compile_expanded_workflow.py still contains drifted default-chain marker: {marker}", compiler))
    return issues


def check_strategy_rules() -> list[dict]:
    validator = SCRIPT_DIR / "validate_strategy_manifest_rules.py"
    ok, output = _run_python(validator)
    if ok:
        return []
    return [_issue("strategy manifest rules validation failed: " + output[:800], validator)]


def check_archive_candidates() -> list[dict]:
    archiver = SCRIPT_DIR / "archive_stale_outputs.py"
    ok, output = _run_python(archiver)
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return [_issue("archive_stale_outputs.py returned non-json output", archiver)]
    issues: list[dict] = []
    for item in payload.get("candidates", []):
        issues.append(_issue(f"stale output candidate should be archived: {item.get('reason', '')}", Path(item.get("path", ""))))
    return issues


def main() -> None:
    issues: list[dict] = []
    issues.extend(check_filesystem())
    issues.extend(check_entrypoint_docs())
    issues.extend(check_runner_guards())
    issues.extend(check_default_workflow_shape())
    issues.extend(check_strategy_rules())
    issues.extend(check_archive_candidates())
    payload = {
        "pass": not issues,
        "issues": issues,
        "checked": {
            "skill_root": str(SKILL_ROOT),
            "outputs_dir": str(OUTPUTS_DIR),
            "official_entrypoint": "init_workflow.py -> workflow_runner.py -> compile_expanded_workflow.py",
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(0 if payload["pass"] else 1)


if __name__ == "__main__":
    main()
