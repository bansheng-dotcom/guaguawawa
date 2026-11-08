"""
article_validator — 终稿校验

对应 data-analysis-report-agent/harness/output_validator.py。
整合 check_article.py 的确定性检查逻辑。

校验规则：
1. 字数 >= MIN_CHARS（或 MIN_CHARS_SHORT）
2. 不得命中 ai-tone-director 的确定性证据词（中英文）
3. 必须包含「延伸阅读」section
4. 必须以 # 标题开头
5. 不得包含内部框架标签泄露

设计原则：
- 硬约束由代码断言，非 prompt 软提示
- 错误累积返回，不 raise
- 区分 hard error 和 WARNING
"""

import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from config import MIN_CHARS, MIN_CHARS_SHORT, FORBIDDEN_ZH, FORBIDDEN_EN


SOFT_CONNECTIVE_WORDS = {"首先", "其次", "再次", "最后", "因此", "所以", "于是"}


def validate_article(
    article_text: str,
    strategy: str = "knowledge-explainer",
    profile: str = "standard",
) -> tuple[bool, list[str]]:
    """
    校验最终文章。

    Args:
        article_text: 最终文章文本（Markdown）
        strategy: 当前策略
        profile: 检查 profile（standard / short-experience）

    Returns:
        (is_valid, errors)
        errors 中 "WARNING:" 前缀的为软警告，不阻断
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not article_text or not article_text.strip():
        return False, ["文章为空"]

    min_chars = MIN_CHARS_SHORT if profile == "short-experience" else MIN_CHARS

    # ── 1. 标题检查 ──
    if not article_text.lstrip("﻿").strip().startswith("#"):
        errors.append("缺少一级标题（# 开头）")

    # ── 2. 字数检查 ──
    clean_text = re.sub(r"[#\*\-\|\>\`\[\]\(\)\~\s]", "", article_text)
    if len(clean_text) < min_chars:
        errors.append(f"字数不足：{len(clean_text)} 字，下限 {min_chars} 字")

    # ── 3. ai-tone-director 确定性证据词检查 ──
    forbidden_hits = _check_forbidden_words(article_text, profile)
    if forbidden_hits:
        errors.append(f"命中 AI 味确定性证据词：{', '.join(forbidden_hits[:5])}")

    # ── 4. 必要结构检查 ──
    if not re.search(r"延伸阅读|后续阅读|后续选题|延伸话题", article_text):
        errors.append("缺少必要结构：文末延伸阅读/后续选题")

    # ── 5. 内部标签泄露检查（WARNING）──
    internal_labels = ["数据事实", "运营逻辑", "组织归因", "业务结论"]
    leaked = [label for label in internal_labels if label in article_text]
    if leaked:
        warnings.append(f"WARNING: 内部框架标签泄露：{', '.join(leaked)}")

    # ── 6. 摘要数字检查（WARNING）──
    summary_match = re.search(r"(?:摘要|总结|结论)[：:]\s*(.+?)(?:\n\n|\Z)", article_text, re.DOTALL)
    if summary_match:
        summary = summary_match.group(1)
        if not re.search(r"\d", summary):
            warnings.append("WARNING: 摘要中无具体数字")

    # ── 合并结果 ──
    all_errors = errors + warnings
    is_valid = len(errors) == 0  # warnings 不阻断

    return is_valid, all_errors


def _check_forbidden_words(text: str, profile: str) -> list[str]:
    """检查 ai-tone-director 确定性证据词，返回命中列表"""
    hits = []

    # 中文禁词
    forbidden_zh = tuple(w for w in FORBIDDEN_ZH if w not in SOFT_CONNECTIVE_WORDS)

    for word in forbidden_zh:
        if word in text:
            hits.append(f"[中]'{word}'")

    # 英文禁词
    for word in FORBIDDEN_EN:
        if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            hits.append(f"[英]'{word}'")

    return hits


# ── CLI 入口（兼容 check_article.py 的调用方式）──

def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="文章终稿校验（harness 版）")
    parser.add_argument("path", help="文章文件路径")
    parser.add_argument("--profile", default="standard", choices=["standard", "short-experience"])
    parser.add_argument("--strategy", default="knowledge-explainer")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    file_path = Path(args.path)
    if not file_path.exists():
        print(f"文件不存在: {args.path}")
        sys.exit(2)

    text = file_path.read_text(encoding="utf-8")
    is_valid, messages = validate_article(text, strategy=args.strategy, profile=args.profile)

    result = {
        "pass": is_valid,
        "passed": [m for m in messages if not m.startswith("WARNING:")],
        "issues": [m for m in messages if not m.startswith("WARNING:") and not m.startswith("字数") and not m.startswith("命中")],
        "warnings": [m for m in messages if m.startswith("WARNING:")],
        "file": str(file_path),
    }

    if args.verbose:
        for msg in messages:
            prefix = "  [WARN] " if msg.startswith("WARNING:") else "  [FAIL] " if not is_valid else "  [PASS] "
            print(f"{prefix}{msg}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
