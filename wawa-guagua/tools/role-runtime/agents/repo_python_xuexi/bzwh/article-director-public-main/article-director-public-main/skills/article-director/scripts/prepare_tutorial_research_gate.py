import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, write_json


def _collect_sources(topic_id: str, project_root: Path) -> list[str]:
    candidates = [
        project_root / "tmp" / "source-repos" / "EchoBird" / "README.md",
        project_root / "tmp" / "source-repos" / "EchoBird" / "tools" / "codex" / "README.md",
        project_root / "tmp" / f"{topic_id}-research.md",
        project_root / "tmp" / f"{topic_id}-paper-close-reading.md",
    ]
    return [str(path) for path in candidates if path.exists()]


def _infer_findings(topic_id: str, project_root: Path) -> list[str]:
    findings: list[str] = []
    echo_root = project_root / "tmp" / "source-repos" / "EchoBird"
    main_readme = echo_root / "README.md"
    codex_readme = echo_root / "tools" / "codex" / "README.md"
    if main_readme.exists():
        findings.append("EchoBird 官方 README 存在，可作为安装入口与发布命名规则依据。")
    if codex_readme.exists():
        findings.append("EchoBird Codex 集成 README 存在，可作为 Codex proxy、Apply to Codex 与 Responses 路径依据。")
    if "echobird" in topic_id.lower():
        findings.append("该教程涉及版本敏感实现，正文写作前必须先确认适用边界和主线步骤。")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare deterministic fact gate for teaching-playbook workflows")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    output_path = project_dir / "tutorial-research-gate-01" / "output.json"

    sources = _collect_sources(args.topic_id, project_root)
    findings = _infer_findings(args.topic_id, project_root)
    passed = bool(sources)
    issues = [] if passed else ["missing tutorial source anchors: no local official or research sources found"]

    payload = {
        "pass": passed,
        "passed": findings,
        "issues": issues,
        "file": str(output_path),
        "topic_id": args.topic_id,
        "source_files": sources,
        "gate_type": "tutorial-fact-gate",
    }
    write_json(output_path, payload)
    print(output_path)


if __name__ == "__main__":
    main()
