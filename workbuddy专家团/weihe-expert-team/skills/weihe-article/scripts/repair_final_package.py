import argparse
import json
import re
from pathlib import Path

PLACEHOLDER_TEXT = "??????????????????????"
DIRECT_ENTRY_MARKERS = ["???", "??", "????", "????", "???", "??", "??", "??"]
FORBIDDEN_OPENING_PATTERNS = ["????", "??????", "?????", "??????", "?????", "???", "????", "???"]
TERM_DEFINITIONS = {
    "Agent": "???? Agent???????????? AI ?????",
    "agent": "???? agent???????????? AI ?????",
    "runtime": "???? runtime???????????????????????????????",
    "graph": "???? graph?????????????????????????",
    "typed relation graph": "typed relation graph ??????????????????????????????",
    "prerequisite": "prerequisite ????????????? A ???? B?",
    "pipeline": "???? pipeline??????????????",
}

def split_sections(text: str):
    parts = re.split(r"(?m)^##\s+", text)
    sections = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        heading = f"## {lines[0].strip()}"
        body = "\n".join(lines[1:]).strip()
        sections.append((heading, body))
    return sections

def heading_key(heading: str) -> str:
    return f"## {heading}"

def align_section_bodies(blocks, headings):
    aligned = []
    cursor = 0
    for heading in headings:
        key = heading_key(heading)
        body = ""
        for index in range(cursor, len(blocks)):
            block_heading, block_body = blocks[index]
            if block_heading == key:
                body = block_body
                cursor = index + 1
                break
        aligned.append(body)
    return aligned

def split_sentences(text: str):
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    parts = re.split(r"(?<=[????])\s*", compact)
    return [part.strip() for part in parts if part.strip()]

def first_two_sentences(body: str) -> str:
    return " ".join(split_sentences(body)[:2]).strip()

def has_direct_entry(lead: str) -> bool:
    if any(marker in lead for marker in DIRECT_ENTRY_MARKERS):
        return True
    return "?" in lead or "?" in lead

def term_is_explained(lead: str, term: str) -> bool:
    normalized = re.sub(r"\s+", " ", lead).strip()
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

def inject_after_first_sentence(body: str, inserted: str) -> str:
    sentences = split_sentences(body)
    if not sentences:
        return inserted.strip()
    head = sentences[0]
    rest = " ".join(sentences[1:]).strip()
    if rest:
        return f"{head}\n\n{inserted}\n\n{rest}".strip()
    return f"{head}\n\n{inserted}".strip()

def strip_forbidden_opening(body: str) -> str:
    stripped = body.lstrip()
    for pattern in FORBIDDEN_OPENING_PATTERNS:
        if stripped.startswith(pattern):
            stripped = re.sub(rf"^{re.escape(pattern)}[????\s]*", "", stripped, count=1)
    return stripped.strip()

def repair_body(heading: str, body: str, section_meta: dict) -> str:
    body = strip_forbidden_opening(body.strip()) or PLACEHOLDER_TEXT
    lead = first_two_sentences(body)
    if section_meta.get('human_entry_required') and not has_direct_entry(lead):
        body = "\n\n".join([f"?????????????{heading}?", body]).strip()
    lead = first_two_sentences(body)
    for term in section_meta.get('reader_unknown_terms', []):
        if term in lead and not term_is_explained(lead, term):
            definition = TERM_DEFINITIONS.get(term)
            if definition:
                body = inject_after_first_sentence(body, definition)
                lead = first_two_sentences(body)
    return body.strip()

def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic-id', required=True)
    parser.add_argument('--package-id', required=True)
    parser.add_argument('--stage', default='final-package-editor')
    parser.add_argument('--fallback-stage', default='narrative-smoother')
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[3]
    base_dir = project_root / 'skills' / 'article-director' / 'outputs' / args.topic_id
    output_path = base_dir / f'{args.stage}-{args.package_id}' / 'output.md'
    fallback_path = base_dir / f'{args.fallback_stage}-{args.package_id}' / 'output.md'
    packages = load_json(project_root / 'skills' / 'article-director' / 'outputs' / args.topic_id / 'article-packages.json')
    package = next(item for item in packages['packages'] if item['package_id'] == args.package_id)
    manifest = load_json(project_root / 'skills' / 'article-director' / 'outputs' / args.topic_id / 'section-manifest.json')
    section_meta = {item['section_id']: item for item in manifest['sections']}
    current_sections = split_sections(output_path.read_text(encoding='utf-8')) if output_path.exists() else []
    fallback_sections = split_sections(fallback_path.read_text(encoding='utf-8')) if fallback_path.exists() else []
    current_bodies = align_section_bodies(current_sections, package['section_headings'])
    fallback_bodies = align_section_bodies(fallback_sections, package['section_headings'])
    repaired_blocks = []
    for index, heading in enumerate(package['section_headings']):
        key = heading_key(heading)
        sid = package['section_ids'][index]
        body = current_bodies[index] or fallback_bodies[index]
        repaired_blocks.append(f"{key}\n\n{repair_body(heading, body, section_meta.get(sid, {}))}".strip())
    output_path.write_text("\n\n".join(repaired_blocks).strip() + "\n", encoding='utf-8')
    print(output_path)

if __name__ == '__main__':
    main()
