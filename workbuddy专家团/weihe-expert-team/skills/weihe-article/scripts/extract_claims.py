import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler_lib import build_project_dir, write_json


NUMBER_PATTERN = re.compile(r"\$?\d+(?:\.\d+)?%?")
SOURCE_PATTERN = re.compile(
    r"(来源[:：]|https?://\S+|README|官方文档|公开说明|论文|arXiv|GitHub|summary_table|本地验证|本地实验|验证结果)",
    re.IGNORECASE,
)
EVIDENCE_CONTEXT_PATTERN = re.compile(
    r"(验证|证据|结果|显示|返回|说明|证明|实验|脚本|README|文档|公开说明|官方|论文|仓库|日志|报告|JSON|json)",
    re.IGNORECASE,
)
LOCAL_TRACE_PATTERN = re.compile(
    r"(validate_|verify_|codex-route-validation\.json|verify-codex-deepseek-route\.json|summary_table|results\.json|tmp/|scripts/)",
    re.IGNORECASE,
)
STATUS_CODE_PATTERN = re.compile(r"\b(?:401|403|404|408|409|422|429|500|502|503|504|524)\b")
HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s")
LIST_PREFIX_PATTERN = re.compile(r"(?m)^\s*(?:\d+[.)．、]|[-*+]|[一二三四五六七八九十]+、)\s+")
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
IP_PORT_PATTERN = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?(?:/\S*)?\b")
CODE_SPAN_PATTERN = re.compile(r"`[^`]*`")
PURE_SOURCE_LINE_PATTERN = re.compile(r"^\s*来源[:：]")


def normalize_for_number_scan(paragraph: str) -> str:
    text = paragraph
    text = URL_PATTERN.sub(" ", text)
    text = IP_PORT_PATTERN.sub(" ", text)
    text = CODE_SPAN_PATTERN.sub(" ", text)
    text = LIST_PREFIX_PATTERN.sub("", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*\d+[.)．、]?\s*", "", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_numbers(paragraph: str) -> list[str]:
    working = normalize_for_number_scan(paragraph)
    if not working:
        return []
    numbers = NUMBER_PATTERN.findall(working)
    filtered: list[str] = []
    for number in numbers:
        if STATUS_CODE_PATTERN.fullmatch(number):
            filtered.append(number)
            continue
        if re.fullmatch(r"\d+", number) and len(number) == 1:
            continue
        filtered.append(number)
    return filtered


def is_structural_paragraph(paragraph: str) -> bool:
    stripped = paragraph.strip()
    if not stripped:
        return True
    if HEADING_PATTERN.match(stripped):
        return True
    if PURE_SOURCE_LINE_PATTERN.match(stripped):
        return True
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if not lines:
        return True
    if all(re.match(r"^(?:\d+[.)．、]|[-*+]|[一二三四五六七八九十]+、)\s+", line) for line in lines):
        joined = " ".join(lines)
        if not EVIDENCE_CONTEXT_PATTERN.search(joined):
            return True
    return False


def classify_claim(paragraph: str, numbers: list[str], has_source_marker: bool) -> str:
    has_local_trace = bool(LOCAL_TRACE_PATTERN.search(paragraph))
    has_status_code = bool(STATUS_CODE_PATTERN.search(paragraph))
    has_evidence_context = bool(EVIDENCE_CONTEXT_PATTERN.search(paragraph))
    if has_status_code and (has_local_trace or "返回" in paragraph or "status" in paragraph.lower()):
        return "observed-status"
    if has_source_marker and has_evidence_context:
        return "sourced-assertion"
    if numbers and has_source_marker:
        return "sourced-numeric"
    if numbers and has_local_trace and has_evidence_context:
        return "traceable-numeric"
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract evidence-bearing claims from article draft")
    parser.add_argument("--topic-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    project_dir = build_project_dir(project_root, args.topic_id)
    draft_path = project_root / "tmp" / f"{args.topic_id}-draft.md"
    text = draft_path.read_text(encoding="utf-8")

    claims = []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    for index, paragraph in enumerate(paragraphs, start=1):
        if is_structural_paragraph(paragraph):
            continue
        has_source_marker = bool(SOURCE_PATTERN.search(paragraph))
        numbers = extract_numbers(paragraph)
        claim_kind = classify_claim(paragraph, numbers, has_source_marker)
        if not claim_kind:
            continue
        claims.append(
            {
                "claim_id": f"claim-{index:03d}",
                "paragraph_index": index,
                "excerpt": paragraph[:240],
                "numbers": numbers,
                "has_source_marker": has_source_marker,
                "claim_kind": claim_kind,
                "has_local_trace": bool(LOCAL_TRACE_PATTERN.search(paragraph)),
                "has_status_code": bool(STATUS_CODE_PATTERN.search(paragraph)),
            }
        )

    output_path = project_dir / "claim-extract-01" / "output.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "topic_id": args.topic_id,
        "draft_path": str(draft_path),
        "claim_count": len(claims),
        "claims": claims,
    }
    write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
