import argparse
from pathlib import Path


def derive_outline(topic_id: str, project_root: Path) -> Path:
    detailed_path = project_root / "tmp" / f"{topic_id}-detailed-outline.md"
    outline_path = project_root / "tmp" / f"{topic_id}-outline.md"
    text = detailed_path.read_text(encoding="utf-8")

    lines = text.splitlines()
    collected: list[str] = []
    last_level2 = ""
    inserted_title = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            heading = stripped[2:].strip()
            if not inserted_title:
                collected.append(f"# {heading}")
                inserted_title = True
            continue
        if stripped.startswith("## "):
            last_level2 = stripped
            collected.append("")
            collected.append(stripped)
            continue
        if stripped.startswith("### "):
            if last_level2:
                collected.append(stripped)
            continue

    normalized: list[str] = []
    for line in collected:
        if line == "" and (not normalized or normalized[-1] == ""):
            continue
        normalized.append(line)
    output = "\n".join(normalized).strip() + "\n"
    outline_path.write_text(output, encoding="utf-8")
    return outline_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive a concise outline from the detailed outline")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    path = derive_outline(args.topic_id, project_root)
    print(path)


if __name__ == "__main__":
    main()
