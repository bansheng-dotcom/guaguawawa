"""
load_style_experience.py — 风格经验加载器

参考 data-analysis-report-agent/agents/brain_agent.py 的 _load_experience() 模式。
将 style-guide.md、author-soul.md、exemplars/、anti-patterns.json 拼接为一个注入文本。

用法：
    python load_style_experience.py                    # 输出到 stdout
    python load_style_experience.py --output experience_text.txt  # 输出到文件
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
STYLE_DIR = SKILL_ROOT / "style-profiles"


def load_style_experience(max_exemplars: int = 2) -> str:
    """
    加载风格经验库，拼接为注入文本。

    Args:
        max_exemplars: 每类范例最多取几个（避免过长）

    Returns:
        拼接后的经验文本
    """
    parts = []

    # ── 1. 加载风格指南 ──
    guide_path = STYLE_DIR / "style-guide.md"
    if guide_path.exists():
        parts.append("【作者风格指南】\n" + guide_path.read_text(encoding="utf-8"))

    # ── 2. 加载作者站位 ──
    soul_path = STYLE_DIR / "author-soul.md"
    if soul_path.exists():
        parts.append("【作者站位与写作人格】\n" + soul_path.read_text(encoding="utf-8")[:8000])

    # ── 3. 加载范例（每类取 max_exemplars 个）──
    exemplars_dir = STYLE_DIR / "exemplars"
    if exemplars_dir.exists():
        exemplar_parts = []
        for f in sorted(exemplars_dir.glob("*.md")):
            content = f.read_text(encoding="utf-8")
            # 按 "---" 分割范例，取前 max_exemplars 个
            sections = content.split("---")
            selected = sections[:max_exemplars]
            exemplar_parts.append(f"\n### {f.stem}\n\n" + "\n---\n".join(selected))
        if exemplar_parts:
            parts.append("【范例段落】\n" + "\n".join(exemplar_parts))

    # ── 4. 加载禁用模式 ──
    anti_path = STYLE_DIR / "anti-patterns.json"
    if anti_path.exists():
        anti = json.loads(anti_path.read_text(encoding="utf-8"))
        # 只取用户专属的禁用模式，不重复 ai_typical_patterns
        user_anti = anti.get("user_style_anti_patterns", [])
        found_in_corpus = anti.get("found_in_corpus", {})
        # 取在语料中出现过的 AI 味表达（说明用户偶尔也用，需要控制频率）
        corpus_hits = [k for k, v in found_in_corpus.items() if v > 3]
        anti_text = "用户文章中出现过的 AI 味表达（需控制频率）：\n"
        for hit in corpus_hits:
            anti_text += f"- 「{hit}」出现 {found_in_corpus[hit]} 次\n"
        anti_text += "\n禁用模式：\n"
        for rule in user_anti:
            anti_text += f"- {rule}\n"
        parts.append("【禁用模式】\n" + anti_text)

    return "\n\n".join(parts)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="加载风格经验库")
    parser.add_argument("--output", "-o", default=None, help="输出文件路径")
    parser.add_argument("--max-exemplars", type=int, default=2, help="每类范例最多取几个")
    args = parser.parse_args()

    text = load_style_experience(max_exemplars=args.max_exemplars)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"已保存到: {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
