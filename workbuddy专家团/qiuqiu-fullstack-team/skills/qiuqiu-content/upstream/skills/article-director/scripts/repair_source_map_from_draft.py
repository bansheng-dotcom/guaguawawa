import argparse
from datetime import date
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from appendix_builder_lib import build_project_dir, extract_source_candidates, parse_source_map, title_from_locator


def _relative_locator(project_root: Path, locator: str) -> str:
    if not locator:
        return locator
    locator = locator.strip().rstrip("`。，、；：:;,.>)」』”")
    path = Path(locator)
    if path.is_absolute():
        try:
            return path.relative_to(project_root).as_posix()
        except ValueError:
            return path.as_posix()
    return locator.replace("\\", "/")


def _read_body_source(project_dir: Path, project_root: Path, topic_id: str) -> str:
    candidates = [
        project_dir / "style-harmonizer-01" / "output.md",
        project_root / "tmp" / f"{topic_id}-draft.md",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def _merge_sources(existing: list[dict], urls: list[str], local_refs: list[str], project_root: Path) -> list[dict]:
    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for item in existing:
        locator = _relative_locator(project_root, item.get("locator", "").strip())
        title = item.get("title", "").strip()
        if locator and (not title or len(title) <= 2):
            title = title_from_locator(locator)
        normalized = {
            "title": title,
            "locator": locator,
            "note": item.get("note", "").strip(),
            "source_type": item.get("source_type", "official"),
        }
        key = (normalized["source_type"], normalized["locator"] or normalized["title"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)

    for url in urls:
        key = ("official", url)
        if key in seen:
            continue
        seen.add(key)
        merged.append(
            {
                "title": title_from_locator(url),
                "locator": url,
                "note": "正文直接引用的外部资料，附录需保留以便读者回查。",
                "source_type": "official",
            }
        )

    for ref in local_refs:
        locator = ref.replace("\\", "/")
        key = ("local", locator)
        if key in seen:
            continue
        seen.add(key)
        merged.append(
            {
                "title": title_from_locator(locator),
                "locator": locator,
                "note": "正文直接引用的本地脚本、文档或结果文件，用于复核步骤或实验输出。",
                "source_type": "local",
            }
        )

    merged.sort(key=lambda item: (item["source_type"], item["title"].lower()))
    return merged


def _write_source_map(path: Path, sources: list[dict], reading_order: list[str]) -> None:
    official = [item for item in sources if item.get("source_type") == "official"]
    local = [item for item in sources if item.get("source_type") != "official"]

    lines = [
        "# Source Map",
        "",
        f"更新时间：`{date.today().isoformat()}`",
        "",
        "## 官方资料",
        "",
    ]
    for source in official:
        lines.append(f"- `{source['title']}`")
        if source.get("locator"):
            lines.append(f"  {source['locator']}")
        if source.get("note"):
            lines.append(f"  - {source['note']}")

    lines.extend(["", "## 本地资料", ""])
    for source in local:
        lines.append(f"- `{source['title']}`")
        if source.get("locator"):
            lines.append(f"  {source['locator']}")
        if source.get("note"):
            lines.append(f"  - {source['note']}")

    lines.extend(["", "## 延伸阅读顺序", ""])
    if not reading_order:
        reading_order = [
            "先看最直接支撑正文结论的来源，再看配套实现和补充阅读。",
            "涉及本地脚本或结果文件时，先确认它是配套资料还是需要读者自己运行得到的输出。",
        ]
    for item in reading_order:
        lines.append(f"- {item}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair source map from finalized draft references")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    memory_dir = project_dir / "memory"
    source_map_path = memory_dir / "source-map.md"

    existing_sources, reading_order = parse_source_map(source_map_path)
    body_text = _read_body_source(project_dir, project_root, args.topic_id)
    urls, local_refs = extract_source_candidates(body_text)
    merged_sources = _merge_sources(existing_sources, urls, local_refs, project_root)
    _write_source_map(source_map_path, merged_sources, reading_order)
    print(source_map_path)


if __name__ == "__main__":
    main()
