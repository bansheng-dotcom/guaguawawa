import argparse
import json
import re
from pathlib import Path

DIRECT_ENTRY_MARKERS = ["???", "??", "??", "??", "??", "????", "????", "???", "?????"]
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
    escaped = re.escape(term)
    patterns = [rf"{escaped}[?( ]{{0,3}}(?:?|???|?????|????)", rf"(?:????|??){escaped}"]
    return any(re.search(pattern, lead) for pattern in patterns)

def lead_terms_needing_explanation(lead: str, section_meta: dict):
    fragments = []
    for term in section_meta.get("reader_unknown_terms", []):
        if term in lead and not term_is_explained(lead, term):
            definition = TERM_DEFINITIONS.get(term)
            if definition and definition not in fragments:
                fragments.append(definition)
    return fragments

def inject_after_first_sentence(body: str, inserted: str) -> str:
    sentences = split_sentences(body)
    if not sentences:
        return inserted.strip()
    head = sentences[0]
    rest = " ".join(sentences[1:]).strip()
    if rest:
        return f"{head}\n\n{inserted}\n\n{rest}".strip()
    return f"{head}\n\n{inserted}".strip()

def build_direct_entry(section_meta: dict) -> str:
    heading = str(section_meta.get("heading") or "").strip()
    return f"?????????????{heading}?" if heading else "??????????????????????????"

def repair_body(body: str, section_meta: dict) -> str:
    body = body.strip() or '????????????????????????'
    lead = first_two_sentences(body)
    if section_meta.get('human_entry_required') and not has_direct_entry(lead):
        body = "\n\n".join([build_direct_entry(section_meta), body]).strip()
    lead = first_two_sentences(body)
    for fragment in lead_terms_needing_explanation(lead, section_meta):
        body = inject_after_first_sentence(body, fragment)
        lead = first_two_sentences(body)
    return body.strip()

def load_section_manifest(project_root: Path, topic_id: str):
    data = json.loads((project_root / 'skills' / 'article-director' / 'outputs' / topic_id / 'section-manifest.json').read_text(encoding='utf-8'))
    return {item['section_id']: item for item in data['sections']}

def load_package(project_root: Path, topic_id: str, package_id: str):
    data = json.loads((project_root / 'skills' / 'article-director' / 'outputs' / topic_id / 'article-packages.json').read_text(encoding='utf-8'))
    for pkg in data['packages']:
        if pkg['package_id'] == package_id:
            return pkg
    raise ValueError(f'package not found: {package_id}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic-id', required=True)
    parser.add_argument('--package-id', required=True)
    parser.add_argument('--stage', default='concept-bridge-rewriter')
    parser.add_argument('--fallback-stage', default='primer-writer')
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[3]
    base_dir = project_root / 'skills' / 'article-director' / 'outputs' / args.topic_id
    output_path = base_dir / f'{args.stage}-{args.package_id}' / 'output.md'
    fallback_path = base_dir / f'{args.fallback_stage}-{args.package_id}' / 'output.md'
    package = load_package(project_root, args.topic_id, args.package_id)
    section_meta = load_section_manifest(project_root, args.topic_id)
    current_sections = split_sections(output_path.read_text(encoding='utf-8')) if output_path.exists() else []
    fallback_sections = split_sections(fallback_path.read_text(encoding='utf-8')) if fallback_path.exists() else []
    current_bodies = align_section_bodies(current_sections, package['section_headings'])
    fallback_bodies = align_section_bodies(fallback_sections, package['section_headings'])
    repaired_blocks = []
    for index, heading in enumerate(package['section_headings']):
        key = heading_key(heading)
        section_id = package['section_ids'][index]
        meta = dict(section_meta.get(section_id, {}))
        meta['heading'] = heading
        body = current_bodies[index] or fallback_bodies[index]
        repaired_blocks.append(f"{key}\n\n{repair_body(body, meta)}".strip())
    output_path.write_text("\n\n".join(repaired_blocks).strip() + "\n", encoding='utf-8')
    print(output_path)

if __name__ == '__main__':
    main()
