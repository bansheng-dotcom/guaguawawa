import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = PROJECT_ROOT / "skills" / "article-director" / "harness"
AI_TONE_INVOCATION_SCRIPT = Path(r"D:\知识库\skills\内容生产\ai-tone-director\scripts\invocation_log.py")
if str(HARNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(HARNESS_ROOT))

from article_validator import validate_article


def main() -> None:
    parser = argparse.ArgumentParser(description="Compatibility wrapper for article-director article checks")
    parser.add_argument("path")
    parser.add_argument("--profile", default="standard")
    parser.add_argument("--strategy", default="knowledge-explainer")
    parser.add_argument("--topic-id", default="")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        print(json.dumps({"pass": False, "issues": [f"file not found: {path}"], "file": str(path)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    text = path.read_text(encoding="utf-8")
    passed, messages = validate_article(text, strategy=args.strategy, profile=args.profile)
    workflow_issues: list[str] = []
    workflow_warnings: list[str] = []
    if args.topic_id:
        project_dir = PROJECT_ROOT / "skills" / "article-director" / "outputs" / args.topic_id
        result = subprocess.run(
            [
                sys.executable,
                str(AI_TONE_INVOCATION_SCRIPT),
                "validate-run",
                "--project-dir",
                str(project_dir),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            trace_payload = json.loads((result.stdout or "").strip())
        except json.JSONDecodeError:
            trace_payload = {}
        if result.returncode != 0:
            workflow_issues.extend(trace_payload.get("issues") or [result.stdout.strip() or result.stderr.strip() or "ai-tone trace validation failed"])
        else:
            workflow_warnings.extend(trace_payload.get("warnings") or [])
    passed = passed and not workflow_issues
    payload = {
        "pass": passed,
        "passed": ["article check passed"] if passed else [],
        "issues": [message for message in messages if not message.startswith("WARNING:")] + workflow_issues,
        "warnings": [message for message in messages if message.startswith("WARNING:")] + workflow_warnings,
        "file": str(path),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
