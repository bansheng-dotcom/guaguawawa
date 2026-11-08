import json
import re
from pathlib import Path
from urllib.parse import urlparse


def build_project_dir(project_root: Path, topic_id: str) -> Path:
    return project_root / "skills" / "article-director" / "outputs" / topic_id


def load_term_registry(memory_dir: Path) -> dict:
    term_path = memory_dir / "term-registry.json"
    if not term_path.exists():
        return {"terms": []}
    return json.loads(term_path.read_text(encoding="utf-8"))


def parse_source_map(path: Path) -> tuple[list[dict], list[str]]:
    if not path.exists():
        return [], []

    official_sources: list[dict] = []
    local_sources: list[dict] = []
    reading_order: list[str] = []

    current_section = ""
    current_item: dict | None = None

    def flush_current() -> None:
        nonlocal current_item
        if not current_item:
            return
        target = official_sources if current_item.get("source_type") == "official" else local_sources
        target.append(current_item)
        current_item = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if line.startswith("## "):
            flush_current()
            current_section = stripped[3:].strip()
            continue

        if current_section in {"官方资料", "本地资料"}:
            source_type = "official" if current_section == "官方资料" else "local"
            if stripped.startswith("- `"):
                flush_current()
                title = stripped[3:].split("`", 1)[0]
                current_item = {"title": title, "locator": "", "note": "", "source_type": source_type}
                continue
            if current_item and stripped and not stripped.startswith("- "):
                current_item["locator"] = stripped
                continue
            if current_item and stripped.startswith("- "):
                current_item["note"] = stripped[2:].strip()
                continue

        if current_section == "延伸阅读顺序" and stripped.startswith("- "):
            reading_order.append(stripped[2:].strip())

    flush_current()
    return official_sources + local_sources, reading_order


def render_appendix(main_heading: str, term_registry: dict, sources: list[dict], reading_order: list[str]) -> str:
    lines = [main_heading, "", "### 术语速查", ""]
    terms = term_registry.get("terms", [])
    if not terms:
        lines.append("- 暂无需要单独附录化的术语，正文已承担必要解释。")
    for term in terms:
        explanation = term.get("plain_explanation", "").strip()
        if explanation:
            lines.append(f"- {term['term']}：{explanation}")
        else:
            lines.append(f"- {term['term']}")

    lines.extend(["", "### 参考资料与一句话说明", ""])
    if not sources:
        lines.append("- 暂无已确认参考资料")
    else:
        for source in sources:
            label = "官方" if source.get("source_type") == "official" else "本地"
            lines.append(f"- [{label}] {source['title']}")
            locator = source.get("locator", "").strip()
            if locator:
                lines.append(f"  - {locator}")
            note = source.get("note", "").strip()
            if note:
                lines.append(f"  - {note}")

    lines.extend(["", "### 延伸阅读", ""])
    if not reading_order:
        lines.append("- 先看最直接支撑正文结论的来源，再看配套实现和补充阅读。")
    else:
        for item in reading_order:
            lines.append(f"- {item}")

    return "\n".join(lines).strip() + "\n"


def extract_source_candidates(text: str) -> tuple[list[str], list[str]]:
    def _clean_locator(value: str) -> str:
        return value.rstrip("`。，、；：:;,.>)」』”")

    url_matches = re.findall(r"https?://[^\s)>\"]+", text)
    local_matches = re.findall(
        r"(?:(?:tmp|skills|state|platforms|assets|scripts)/[A-Za-z0-9_\-./]+|[A-Za-z0-9_\-./]+(?:README\.md|\.py|\.json|\.md))",
        text,
    )
    urls = sorted({_clean_locator(item) for item in url_matches})
    locals_ = sorted({_clean_locator(item) for item in local_matches if "/" in item or item.endswith((".py", ".json", ".md"))})
    return urls, locals_


def title_from_locator(locator: str) -> str:
    cleaned = locator.strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        parsed = urlparse(cleaned)
        path = parsed.path.rstrip("/")
        return f"{parsed.netloc}{path}" if path else parsed.netloc
    return Path(cleaned).name or cleaned
