#!/usr/bin/env python3
"""Extract deterministic style signals from text, files, or markdown folders."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MARKERS = {
    "judgment": [
        "真正的问题",
        "关键",
        "本质",
        "不是",
        "而是",
        "不能简单",
        "这意味着",
    ],
    "transition": [
        "但是",
        "问题在于",
        "如果只",
        "所以",
        "这也是为什么",
        "回过头",
    ],
    "explanation": [
        "换句话说",
        "你可以理解",
        "背后",
        "对应的",
        "落到",
        "真实",
    ],
    "progression": [
        "接下来",
        "再往下",
        "到这里",
        "继续",
        "下一步",
        "重新拆",
    ],
    "boundary": [
        "不意味着",
        "解决不了",
        "不能把",
        "只适用",
        "还不能",
        "阶段性",
    ],
    "action": [
        "看板",
        "专项",
        "复盘",
        "预警",
        "策略",
        "资源配置",
        "跟踪",
    ],
}


SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?])")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def collect_inputs(path: Path) -> list[tuple[str, str]]:
    if path.is_file():
        return [(str(path), read_text(path))]
    files = sorted(
        item
        for item in path.glob("*")
        if item.is_file()
        and item.suffix.lower() in {".md", ".txt"}
        and not item.name.startswith(".")
        and item.name.lower() != "readme.md"
    )
    return [(str(item), read_text(item)) for item in files]


def split_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]


def marker_hits(text: str) -> dict[str, int]:
    return {
        category: sum(text.count(marker) for marker in markers)
        for category, markers in MARKERS.items()
    }


def paragraph_candidates(paragraphs: list[str]) -> list[dict]:
    candidates = []
    for index, paragraph in enumerate(paragraphs, start=1):
        hits = {
            category: [marker for marker in markers if marker in paragraph]
            for category, markers in MARKERS.items()
        }
        hits = {category: values for category, values in hits.items() if values}
        if hits:
            candidates.append(
                {
                    "paragraph_index": index,
                    "char_count": len(paragraph),
                    "sentence_count": len(split_sentences(paragraph)),
                    "markers": hits,
                    "text_preview": paragraph[:360],
                }
            )
    return candidates


def length_buckets(lengths: list[int]) -> dict[str, int]:
    return {
        "short_0_80": sum(1 for value in lengths if value <= 80),
        "medium_81_220": sum(1 for value in lengths if 80 < value <= 220),
        "long_221_plus": sum(1 for value in lengths if value > 220),
    }


def analyze_text(source: str, text: str) -> dict:
    paragraphs = split_paragraphs(text)
    sentences = split_sentences(text)
    paragraph_lengths = [len(paragraph) for paragraph in paragraphs]
    sentence_lengths = [len(sentence) for sentence in sentences]
    avg_paragraph = round(sum(paragraph_lengths) / len(paragraph_lengths), 1) if paragraph_lengths else 0
    avg_sentence = round(sum(sentence_lengths) / len(sentence_lengths), 1) if sentence_lengths else 0

    return {
        "source": source,
        "char_count": len(text),
        "paragraph_count": len(paragraphs),
        "sentence_count": len(sentences),
        "avg_paragraph_chars": avg_paragraph,
        "avg_sentence_chars": avg_sentence,
        "paragraph_length_buckets": length_buckets(paragraph_lengths),
        "marker_counts": marker_hits(text),
        "style_candidates": paragraph_candidates(paragraphs)[:30],
    }


def summarize(files: list[dict]) -> dict:
    total_files = len(files)
    total_paragraphs = sum(item["paragraph_count"] for item in files)
    total_sentences = sum(item["sentence_count"] for item in files)
    total_chars = sum(item["char_count"] for item in files)
    marker_totals = {category: 0 for category in MARKERS}
    buckets = {"short_0_80": 0, "medium_81_220": 0, "long_221_plus": 0}

    for item in files:
        for category, count in item["marker_counts"].items():
            marker_totals[category] += count
        for bucket, count in item["paragraph_length_buckets"].items():
            buckets[bucket] += count

    return {
        "file_count": total_files,
        "char_count": total_chars,
        "paragraph_count": total_paragraphs,
        "sentence_count": total_sentences,
        "paragraph_length_buckets": buckets,
        "marker_totals": marker_totals,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input",
        nargs="?",
        help="Markdown/txt file, folder, or '-' to read stdin",
    )
    parser.add_argument("--text", help="Inline text to analyze")
    parser.add_argument("--out", help="Optional output JSON path")
    args = parser.parse_args()

    if args.text:
        inputs = [("inline_text", args.text)]
        input_label = "inline_text"
    elif args.input == "-":
        text = sys.stdin.read()
        inputs = [("stdin", text)]
        input_label = "stdin"
    elif args.input:
        input_path = Path(args.input)
        inputs = collect_inputs(input_path)
        input_label = str(input_path)
    else:
        parser.error("Provide a file/folder path, --text, or '-' for stdin")

    files = [analyze_text(source, text) for source, text in inputs]
    result = {
        "input": input_label,
        "summary": summarize(files),
        "files": files,
    }

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

