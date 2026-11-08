import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from compiler_lib import build_project_dir


WRITER_CONTRACT_RE = re.compile(r"(?is)<!--\s*writer-contract\b.*?-->\s*")


def _display_path(project_root: Path, path: Path) -> str:
    try:
        value = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        value = path
    return value.as_posix()


def strip_writer_contract(text: str) -> tuple[str, int]:
    cleaned, count = WRITER_CONTRACT_RE.subn("", text)
    return cleaned.strip() + ("\n" if cleaned.strip() else ""), count


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a section body source for review lanes")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--section-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    section_dir = project_dir / "sections" / args.section_id
    draft_path = section_dir / "draft.md"
    output_path = section_dir / "review-source.md"

    issues: list[str] = []
    if not draft_path.exists():
        issues.append(f"missing {draft_path.name}")
        source = ""
        stripped_count = 0
    else:
        source = draft_path.read_text(encoding="utf-8-sig")
        source, stripped_count = strip_writer_contract(source)
        output_path.write_text(source, encoding="utf-8")

    result = {
        "pass": not issues,
        "issues": issues,
        "passed": ["review source prepared"] if not issues else [],
        "file": _display_path(project_root, output_path),
        "source": _display_path(project_root, draft_path),
        "stripped_writer_contract_count": stripped_count,
        "char_count": len(source),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
