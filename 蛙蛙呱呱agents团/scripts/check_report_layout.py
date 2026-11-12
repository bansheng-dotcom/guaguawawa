# -*- coding: utf-8 -*-
"""报告版式出厂检查（不关心报告是谁画的，只看 HTML 结果）。

四条硬规则（对应 REPORT-STANDARD 第七节）：
  R1 首屏不得出现保真分数（保留率/溯源率/弃置率）
  R2 最后一节必须是「口径与分数」
  R3 附录必须折叠（<details> 不带 open）
  R4 不得出现「结论清单」类重复章节

用法：
  python scripts/check_report_layout.py --all
  python scripts/check_report_layout.py <file.html> [...]
  python scripts/check_report_layout.py --all --json workspace/baseline/layout_check.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM.parent

FIDELITY_WORDS = ("保留率", "溯源率", "弃置率")
DUP_TITLES = ("结论清单", "结论速览", "摘要复述", "结论汇总", "结论摘录")
FOOTER_TITLES = ("数据口径与说明", "口径与说明", "附录")  # 不算"最后一节"

_HEAD = re.compile(r"<h([12])[^>]*>(.*?)</h\1>", re.S | re.I)
_DETAILS = re.compile(r"<details([^>]*)>(.*?)</details>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def _text(html: str) -> str:
    s = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
    s = _TAG.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _headings(html: str) -> list[tuple[int, str]]:
    return [(int(m.group(1)), _text(m.group(2))) for m in _HEAD.finditer(html)]


def check_html(path: Path) -> dict:
    html = path.read_text(encoding="utf-8", errors="replace")
    heads = _headings(html)
    text_all = _text(html)

    # R1 首屏：第一个 h2 之前（没有 h2 则取全文前 3000 字）不得出现分数词
    first_h2 = html.find("<h2")
    hero = _text(html[:first_h2]) if first_h2 > 0 else text_all[:3000]
    r1 = [w for w in FIDELITY_WORDS if w in hero]

    # R2 末节：仅当报告含保真分数时强制（业务报告可以以行动表收尾）
    has_fidelity = any(w in text_all for w in FIDELITY_WORDS)
    main_heads = [h for _, h in heads if not any(h.startswith(x) for x in FOOTER_TITLES)]
    last_h2 = main_heads[-1] if main_heads else ""
    r2 = []
    if has_fidelity and not ("口径与分数" in last_h2 or "分数与口径" in last_h2):
        r2.append(f"含保真分数但末节是「{last_h2 or '无'}」")

    # R3 附录折叠
    r3 = []
    for attrs, body in _DETAILS.findall(html):
        rows = body.count("<tr")
        summary = ""
        m = re.search(r"<summary[^>]*>(.*?)</summary>", body, re.S | re.I)
        if m:
            summary = _text(m.group(1))
        looks_appendix = ("附录" in summary and rows >= 10) or rows >= 80
        if looks_appendix and "open" in attrs.lower():
            r3.append(f"「{summary[:20] or '附录'}」默认展开（{rows} 行）")

    # R4 重复章节
    r4 = [h for _, h in heads if any(k in h for k in DUP_TITLES)]

    # 参考指标（不作判定，只报数）
    sentences = [s.strip() for s in re.split(r"(?<=[。；！？])", text_all) if len(s.strip()) >= 12]
    dup = [k for k, v in Counter(sentences).items() if v > 1]

    violations = []
    for w in r1:
        violations.append(f"R1 首屏出现「{w}」")
    violations += [f"R2 {x}" for x in r2]
    violations += [f"R3 {x}" for x in r3]
    violations += [f"R4 重复章节「{x}」" for x in r4]

    return {
        "path": str(path),
        "chars": len(html),
        "sections": len([h for lvl, h in heads if lvl == 2]) or len(heads),
        "tables": html.count("<table"),
        "rows": html.count("<tr"),
        "details": html.count("<details"),
        "duplicate_sentences": len(dup),
        "violations": violations,
        "ok": not violations,
    }


REPORT_DIRS = ("摘要版", "底稿版", "默认主题版", "out")


def discover() -> list[Path]:
    """只收成品报告：projects/*/out，以及调研项目根目录与摘要/底稿/主题子目录。"""
    out: list[Path] = []
    proj = TEAM / "projects"
    if proj.exists():
        out += sorted(proj.glob("*/out/*.html"))
    for d in sorted(ROOT.glob("内蒙古*调研*")):
        out += sorted(d.glob("*.html"))
        for sub in REPORT_DIRS:
            out += sorted((d / sub).glob("*.html"))
    return [p for p in out if p.is_file() and p.stat().st_size > 15_000]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    paths = [Path(x) for x in args.paths] if args.paths else (discover() if args.all else [])
    if not paths:
        print("没有可检查的 HTML：给路径，或加 --all")
        return 1

    results = [check_html(p) for p in paths if p.exists()]
    bad = [r for r in results if not r["ok"]]

    print(f"{'报告':<44}{'节':>3}{'表':>4}{'行':>5}{'重复句':>6}  结果")
    for r in results:
        name = Path(r["path"]).name
        name = name if len(name) <= 42 else name[:20] + "…" + name[-20:]
        print(f"{name:<44}{r['sections']:>3}{r['tables']:>4}{r['rows']:>5}"
              f"{r['duplicate_sentences']:>6}  {'PASS' if r['ok'] else 'FAIL'}")

    if bad:
        print("\n违规明细：")
        for r in bad:
            print(f"\n[{Path(r['path']).name}]")
            for v in r["violations"]:
                print("  -", v)
    print(f"\n合计 {len(results)} 份，违规 {len(bad)} 份")

    if args.json:
        p = Path(args.json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"明细已写：{p}")

    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
