import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, read_json


def _display_path(project_root: Path, path: Path) -> str:
    try:
        value = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        value = path
    return value.as_posix()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create editable article requirements template")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    output_path = project_dir / "article-requirements.json"

    existing = read_json(output_path, {})
    payload = {
        "topic_id": args.topic_id,
        "title": args.title or args.topic_id,
        "target_word_count": existing.get("target_word_count", ""),
        "target_length": existing.get("target_length", ""),
        "priority_sections": existing.get("priority_sections", []),
        "new_requirements": existing.get("new_requirements", []),
        "audience_level": existing.get("audience_level", "beginner-public"),
        "must_include": existing.get("must_include", []),
        "must_avoid": existing.get("must_avoid", []),
        "personal_style_notes": existing.get("personal_style_notes", []),
        "cognitive_style_notes": existing.get("cognitive_style_notes", []),
        "logic_preferences": existing.get("logic_preferences", []),
        "status": existing.get("status", "draft-needs-human-review"),
        "instructions": [
            "请在人工确认前补充目标字数、篇幅、重点章节和新增需求。",
            "如需强化个人认知风格，请补充 cognitive_style_notes：你会如何从0到1理解这个问题、先看什么、排除什么、如何做取舍。",
            "如需强化文章逻辑，请补充 logic_preferences：这篇文章应该先讲什么、不讲什么、哪里必须给判断。",
            "确认后运行 workflow_runner.py --approve --approval-key article-requirements-confirmation。",
            "后续每个 section 写作、审查、修改节点都会读取本文件。",
        ],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "pass": True,
                "issues": [],
                "passed": ["article requirements template ready"],
                "file": _display_path(project_root, output_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
