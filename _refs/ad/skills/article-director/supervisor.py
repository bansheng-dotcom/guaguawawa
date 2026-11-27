"""
supervisor — 覆盖度检查

对应 data-analysis-report-agent/workflow.py _supervisor_review()。
在所有 writer 包收敛之后、双审之前运行。

功能：
1. 检查分包数是否 >= MIN_PACKAGES
2. 检查 section-manifest 中的所有 section 是否被某个 package 覆盖
3. 检查策略关键 section 是否存在
4. 检查包间字数平衡性

Returns:
    (is_sufficient, gaps, suggestions)
    is_sufficient: 覆盖是否充分
    gaps: 未覆盖的 section 列表
    suggestions: 补充建议
"""

import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from config import MIN_PACKAGES


def supervisor_review(
    article_packages: list[dict],
    section_manifest: dict,
    strategy: str = "knowledge-explainer",
) -> tuple[bool, list[str], list[str]]:
    """
    覆盖度检查。

    Args:
        article_packages: article-packages.json 中的 packages 列表
        section_manifest: section-manifest.json 内容
        strategy: 当前策略

    Returns:
        (is_sufficient, gaps, suggestions)
    """
    gaps: list[str] = []
    suggestions: list[str] = []

    sections = section_manifest.get("sections", [])
    packages = article_packages if isinstance(article_packages, list) else article_packages.get("packages", [])

    # ── 1. 分包数检查 ──
    if len(packages) < MIN_PACKAGES:
        gaps.append(f"分包数不足：{len(packages)} 包，下限 {MIN_PACKAGES} 包")
        suggestions.append("建议合并相邻 section 后重新分包")

    # ── 2. Section 覆盖检查 ──
    covered_ids = set()
    for pkg in packages:
        for sid in pkg.get("section_ids", []):
            covered_ids.add(sid)

    all_ids = {s["section_id"] for s in sections}
    uncovered = all_ids - covered_ids
    if uncovered:
        uncovered_headings = [
            s["heading"] for s in sections if s["section_id"] in uncovered
        ]
        gaps.append(f"未覆盖 section：{', '.join(uncovered_headings)}")
        suggestions.append(f"建议追加 writer-package-{len(packages)+1:02d}")

    # ── 3. 策略关键 section 检查 ──
    section_text = " ".join(s.get("heading", "") for s in sections)
    if strategy == "knowledge-explainer":
        if not any(kw in section_text for kw in ["机制", "原理", "如何", "实现"]):
            gaps.append("knowledge-explainer 策略缺少「机制/原理」类 section")
    elif strategy == "teaching-playbook":
        if not any(kw in section_text for kw in ["步骤", "操作", "实践", "动手"]):
            gaps.append("teaching-playbook 策略缺少「步骤/操作」类 section")

    # ── 4. 包间字数平衡性检查 ──
    char_counts = []
    for pkg in packages:
        total_target = sum(
            int(s.get("target_word_count", 0) or 0)
            for s in sections
            if s["section_id"] in pkg.get("section_ids", [])
        )
        char_counts.append(total_target)

    if char_counts:
        max_chars = max(char_counts)
        min_chars = min(c for c in char_counts if c > 0) if any(c > 0 for c in char_counts) else 0
        if min_chars > 0 and max_chars / min_chars > 3:
            gaps.append(f"包间字数差异过大：最大 {max_chars} 字 vs 最小 {min_chars} 字（比值 {max_chars/min_chars:.1f}）")
            suggestions.append("建议重新平衡 package 分配")

    is_sufficient = len(gaps) == 0
    return is_sufficient, gaps, suggestions


# ── CLI 入口 ──

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="覆盖度检查（supervisor）")
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--project-root", default=None)
    args = parser.parse_args()

    project_root = Path(args.project_root) if args.project_root else Path(__file__).resolve().parents[3]
    project_dir = project_root / "skills" / "article-director" / "outputs" / args.topic_id

    packages_file = project_dir / "article-packages.json"
    manifest_file = project_dir / "section-manifest.json"
    profile_file = project_dir / "workflow-profile.json"

    if not packages_file.exists():
        print(json.dumps({"pass": False, "issues": [f"article-packages.json 不存在: {packages_file}"]}))
        sys.exit(1)

    packages = json.loads(packages_file.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {"sections": []}
    profile = json.loads(profile_file.read_text(encoding="utf-8")) if profile_file.exists() else {"strategy": "knowledge-explainer"}

    strategy = profile.get("strategy", "knowledge-explainer")
    pkg_list = packages.get("packages", []) if isinstance(packages, dict) else packages

    is_sufficient, gaps, suggestions = supervisor_review(pkg_list, manifest, strategy)

    result = {
        "pass": is_sufficient,
        "gaps": gaps,
        "suggestions": suggestions,
        "package_count": len(pkg_list),
        "section_count": len(manifest.get("sections", [])),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if is_sufficient else 1)


if __name__ == "__main__":
    main()
