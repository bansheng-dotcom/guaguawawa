import re
from pathlib import Path

from compiler_lib import build_project_dir, read_json

AI_FLUFF_PHRASES = [
    "??????????????",
    "???????????????",
    "??????????????",
    "??????",
    "?????",
    "??????",
    "?????",
    "???",
    "????",
    "???",
    "????",
    "????",
    "??????????????",
]
DIRECT_ENTRY_MARKERS = [
    "???",
    "??",
    "??",
    "??",
    "??",
    "????",
    "????",
    "???",
    "?????",
    "?????",
]
INLINE_APPENDIX_MARKERS = ["????", "????", "????", "?????"]
STRUCTURE_STAGE_ORDER = (
    "final-package-editor",
    "adversarial-reviewer",
    "narrative-smoother",
    "structure-editor",
    "deep-dive-researcher",
    "concept-bridge-rewriter",
    "primer-writer",
    "writer",
)


def render_gate_payload(
    passed: bool,
    file_path: Path,
    passed_items: list[str],
    issues: list[str],
    package_id: str = "",
    stage: str = "",
) -> dict:
    payload = {
        "pass": passed,
        "passed": passed_items,
        "issues": issues,
        "file": str(file_path),
    }
    if package_id:
        payload["package_id"] = package_id
    if stage:
        payload["stage"] = stage
    return payload

def split_section_blocks(text: str) -> list[tuple[str, str]]:
    blocks = []
    current_heading = ""
    current_lines = []
    for line in text.splitlines():
        heading_match = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if heading_match:
            if current_heading:
                blocks.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = heading_match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_heading:
        blocks.append((current_heading, "\n".join(current_lines).strip()))
    return blocks

def strip_heading(block: str) -> str:
    lines = block.splitlines()
    if lines and re.match(r"^#{1,3}\s+", lines[0]):
        lines = lines[1:]
    return "\n".join(lines).strip()

def split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    parts = re.split(r"(?<=[???!?])\s*", compact)
    return [part.strip() for part in parts if part.strip()]

def lead_sentences(block: str, limit: int = 2) -> str:
    sentences = split_sentences(strip_heading(block))
    return " ".join(sentences[:limit]).strip()

def count_list_markers(block: str) -> int:
    return len(re.findall(r"(?mi)^\s*(?:[-*]|\d+[\.?]|[??????????]+?)\s+", strip_heading(block)))

def has_markdown_table(block: str) -> bool:
    lines = [line for line in strip_heading(block).splitlines() if "|" in line]
    return len(lines) >= 2

def has_human_entry(lead_text: str) -> bool:
    if any(marker in lead_text for marker in DIRECT_ENTRY_MARKERS):
        return True
    return "?" in lead_text or "?" in lead_text

def term_is_explained(text: str, term: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).strip()
    term_l = term.lower()
    text_l = normalized.lower()
    simple_markers = [
        f"{term_l} 是",
        f"{term_l} 指",
        f"{term_l} 就是",
        f"所谓 {term_l}",
        f"这里说的 {term_l}",
        f"{term_l} 可以理解成",
        f"{term_l} 可以理解为",
    ]
    return any(marker in text_l for marker in simple_markers)

def starts_with_forbidden_opening(lead_text: str, forbidden_patterns: list[str]) -> str:
    compact = lead_text.lstrip("????:? ")
    for pattern in forbidden_patterns:
        if compact.startswith(pattern):
            return pattern
    return ""

def resolve_package_sections(project_root: Path, topic_id: str, package_id: str):
    project_dir = build_project_dir(project_root, topic_id)
    packages = read_json(project_dir / "article-packages.json", {"packages": []})
    manifest = read_json(project_dir / "section-manifest.json", {"sections": []})
    package = next((item for item in packages.get("packages", []) if item.get("package_id") == package_id), None)
    if package is None:
        return [], {}
    section_map = {section["section_id"]: section for section in manifest.get("sections", [])}
    sections = [section_map[section_id] for section_id in package.get("section_ids", []) if section_id in section_map]
    return sections, package

def package_output_path(project_root: Path, topic_id: str, package_id: str, stage_name: str = "") -> Path:
    project_dir = build_project_dir(project_root, topic_id)
    if stage_name:
        candidate = project_dir / f"{stage_name}-{package_id}" / "output.md"
        if candidate.exists():
            return candidate
        if stage_name.endswith(f"-{package_id}"):
            direct = project_dir / stage_name / "output.md"
            if direct.exists():
                return direct
    for stage_prefix in STRUCTURE_STAGE_ORDER:
        candidate = project_dir / f"{stage_prefix}-{package_id}" / "output.md"
        if candidate.exists():
            return candidate
    return project_dir / f"writer-{package_id}" / "output.md"

def evaluate_reader_accessibility(text: str, sections: list[dict]):
    blocks = split_section_blocks(text)
    issues, passed = [], []
    for index, section in enumerate(sections):
        if index >= len(blocks):
            issues.append(f"{section['heading']}: ??????")
            continue
        _, block = blocks[index]
        lead = lead_sentences(block)
        if section.get("human_entry_required") and not has_human_entry(lead):
            issues.append(f"{section['heading']}: ?????????????????")
        forbidden = starts_with_forbidden_opening(lead, section.get("forbidden_opening_patterns", []))
        if forbidden:
            issues.append(f"{section['heading']}: ???????? `{forbidden}`")
        for term in section.get("reader_unknown_terms", []):
            if term in lead and not term_is_explained(lead, term):
                issues.append(f"{section['heading']}: ?? `{term}` ?????????????????")
        if not any(section["heading"] in item for item in issues):
            passed.append(f"{section['heading']}: accessible-opening")
    return passed, issues

def evaluate_structure_mismatch(text: str, sections: list[dict]):
    blocks = split_section_blocks(text)
    issues, passed = [], []
    for index, section in enumerate(sections):
        if index >= len(blocks):
            issues.append(f"{section['heading']}: ??????")
            continue
        _, block = blocks[index]
        body = strip_heading(block)
        mode = section.get("recommended_presentation", "prose")
        list_count = count_list_markers(block)
        if mode == "comparison-table" and not (has_markdown_table(block) or ("????" in body and "????" in body)):
            issues.append(f"{section['heading']}: ????????????????????")
        elif mode == "procedural-steps" and not (list_count >= 2 or ("??" in body and "??" in body and "????" in body)):
            issues.append(f"{section['heading']}: ??????????????????????")
        elif mode == "numbered-reasons" and list_count < min(2, max(2, int(section.get('parallel_point_count', 2) or 2))):
            issues.append(f"{section['heading']}: ?????????????????")
        elif mode == "checklist" and list_count < 3:
            issues.append(f"{section['heading']}: ??????????????")
        elif mode == "problem-solution-blocks" and not (("????" in body and "????" in body) or ("??" in body and "??" in body)):
            issues.append(f"{section['heading']}: ?????-????????????")
        elif section.get("parallel_point_count", 1) >= 3 and list_count == 0 and not has_markdown_table(block) and mode != "prose":
            issues.append(f"{section['heading']}: ???????????? prose")
        else:
            passed.append(f"{section['heading']}: structure-ok")
    return passed, issues

def evaluate_discourse_flaws(text: str, sections: list[dict]):
    blocks = split_section_blocks(text)
    issues, passed = [], []
    for index, section in enumerate(sections):
        if index >= len(blocks):
            issues.append(f"{section['heading']}: ??????")
            continue
        _, block = blocks[index]
        body = strip_heading(block)
        local_issues = []
        for phrase in AI_FLUFF_PHRASES:
            if phrase in body:
                local_issues.append(f"????? `{phrase}`")
        for marker in INLINE_APPENDIX_MARKERS:
            if marker in body:
                local_issues.append(f"????????? `{marker}`")
        if '??????????????' in body or '??????????' in body:
            local_issues.append('?????????? writer ?????????')
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", body) if item.strip()]
        if section.get("recommended_presentation") != "prose":
            if any(len(paragraph) >= 220 for paragraph in paragraphs) and count_list_markers(block) == 0 and not has_markdown_table(block):
                local_issues.append('?????????????????')
        if local_issues:
            issues.extend([f"{section['heading']}: {item}" for item in local_issues])
        else:
            passed.append(f"{section['heading']}: discourse-ok")
    return passed, issues
