import argparse
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize an article-director workflow")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--brief", default="")
    parser.add_argument("--strategy", default="knowledge-explainer")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    script = project_root / "skills" / "article-director" / "scripts" / "init_workflow.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--topic-id",
            args.topic_id,
            "--title",
            args.title,
            "--brief",
            args.brief,
            "--strategy",
            args.strategy,
            "--non-interactive",
            "--yes",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    if result.stdout:
        print(result.stdout.strip())


if __name__ == "__main__":
    main()
