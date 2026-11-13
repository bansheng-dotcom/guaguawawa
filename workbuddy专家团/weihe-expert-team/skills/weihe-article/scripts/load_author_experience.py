"""
load_author_experience.py — 作者经验加载器

将作者文风、认知风格、作者站位、范例段落拼接为一个可注入文本。
AI 味标准已迁移到 ai-tone-director，不在本注入包内复制规则。

用法：
    python load_author_experience.py
    python load_author_experience.py --output author-experience.md
"""

import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
STYLE_DIR = SKILL_ROOT / "style-profiles"
AI_TONE_DIRECTOR = Path(r"D:\知识库\skills\内容生产\ai-tone-director")


def _read(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if limit and len(text) > limit:
        return text[:limit].rstrip() + "\n\n[...truncated...]"
    return text


def _load_anti_patterns() -> str:
    path = STYLE_DIR / "anti-patterns.json"
    if not path.exists():
        return ""
    payload = json.loads(path.read_text(encoding="utf-8"))
    lines = ["# 禁用与限频表达"]
    user_rules = payload.get("user_style_anti_patterns", [])
    if user_rules:
        lines.append("\n## 用户风格禁用规则")
        lines.extend(f"- {item}" for item in user_rules)
    found = payload.get("found_in_corpus", {})
    frequent = [(k, v) for k, v in found.items() if isinstance(v, int) and v > 3]
    if frequent:
        lines.append("\n## 语料中也出现但需限频的表达")
        lines.extend(f"- 「{k}」：{v} 次" for k, v in frequent[:12])
    return "\n".join(lines)


def _load_exemplars(max_sections_per_file: int) -> str:
    exemplars_dir = STYLE_DIR / "exemplars"
    if not exemplars_dir.exists():
        return ""
    parts: list[str] = []
    for path in sorted(exemplars_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        chunks = [chunk.strip() for chunk in content.split("---") if chunk.strip()]
        if chunks:
            parts.append(f"# 范例：{path.stem}\n\n" + "\n\n---\n\n".join(chunks[:max_sections_per_file]))
    return "\n\n".join(parts)


def load_author_experience(max_exemplars: int = 2) -> str:
    parts = [
        "# 作者经验注入包",
        "本注入包用于写作、审查和个人文风修订。重点学习作者的理解路径和判断方式，不只学习词语。",
        f"AI 味审查与修订标准由 ai-tone-director 管理：{AI_TONE_DIRECTOR / 'SKILL.md'}",
    ]

    sections = [
        ("作者句式与语气风格", STYLE_DIR / "style-guide.md", 6000),
        ("作者认知与逻辑风格", STYLE_DIR / "cognitive-style-guide.md", 6000),
        ("作者站位与写作人格", STYLE_DIR / "author-soul.md", 8000),
    ]
    for title, path, limit in sections:
        text = _read(path, limit=limit)
        if text:
            parts.append(f"\n\n## {title}\n\n{text}")

    anti = _load_anti_patterns()
    if anti:
        parts.append("\n\n## 禁用与限频表达\n\n" + anti)

    exemplars = _load_exemplars(max_sections_per_file=max_exemplars)
    if exemplars:
        parts.append("\n\n## 作者范例片段\n\n" + exemplars)

    return "\n".join(parts).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="加载作者经验注入包")
    parser.add_argument("--output", "-o", default="", help="输出文件路径")
    parser.add_argument("--max-exemplars", type=int, default=2, help="每类范例最多注入几段")
    args = parser.parse_args()

    text = load_author_experience(max_exemplars=args.max_exemplars)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(args.output)
    else:
        print(text)


if __name__ == "__main__":
    main()
