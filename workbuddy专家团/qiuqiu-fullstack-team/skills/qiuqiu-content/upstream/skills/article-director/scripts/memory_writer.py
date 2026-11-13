import argparse
from datetime import datetime
from pathlib import Path


def append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(content)
        if not content.endswith("\n"):
            handle.write("\n")


def overwrite_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def journal(memory_dir: Path, node_id: str, status: str, summary: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_text(
        memory_dir / "interaction-journal.md",
        f"## [{stamp}] {node_id} — {status}\n{summary}\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Article Director memory writer")
    parser.add_argument("--action", required=True, choices=["append", "overwrite", "journal"])
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--file", default="")
    parser.add_argument("--content", default="")
    parser.add_argument("--node-id", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--summary", default="")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    memory_dir = project_dir / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    if args.action == "append":
        append_text(memory_dir / Path(args.file).name, args.content.replace("\\n", "\n"))
    elif args.action == "overwrite":
        overwrite_text(memory_dir / Path(args.file).name, args.content.replace("\\n", "\n"))
    else:
        journal(memory_dir, args.node_id, args.status, args.summary)


if __name__ == "__main__":
    main()
