import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from appendix_builder_lib import build_project_dir, load_term_registry, parse_source_map, render_appendix


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic appendix for longform article")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    memory_dir = project_dir / "memory"
    term_registry = load_term_registry(memory_dir)
    sources, reading_order = parse_source_map(memory_dir / "source-map.md")

    appendix_text = render_appendix("## 附录", term_registry, sources, reading_order)
    output_path = project_dir / "appendix-agent-01" / "output.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(appendix_text, encoding="utf-8")
    print(appendix_text)


if __name__ == "__main__":
    main()
