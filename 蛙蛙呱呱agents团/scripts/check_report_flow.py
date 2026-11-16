# -*- coding: utf-8 -*-
"""唯一报告门禁（2026-11-15 产线收敛后）：只看 HTML 成品，不看是谁画的。

替代旧七件套（layout / depth / style / substance / diversity / project / analysis）。
它们的前提是「20 个角色各出一份报告」，产线收敛后那个前提不存在了；
现在只回答一个问题：**这一份 R01 报告能不能发给创始人。**

九条判据（任一不过即 FAIL）：
  F1 版式四规则（复用 scripts/check_report_layout.py）
  F2 标题即结论且带数字（standfirst 必须有数字）
  F3 结论段至少一条带数字（summary 块）
  F4 每个业务章节至少一句带数字
  F5 有「边界」章节，写清只对什么成立
  F6 末节是「口径与分数」（自检信息不被藏起来，也不挡在结论前）
  F7 每张图都有来源
  F8 不出现 JSON/字段回显（` ```json `、`"ok":`）
  F9 内部重复句 ≤ 10%，数字密度 ≥ 25/千字，禁用词 0

用法：
  python scripts/check_report_flow.py <report.html> [...]
  python scripts/check_report_flow.py --dir workspace/_flow_demo/out
  python guagua.py report check --html <report.html>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

BANNED = ("需要关注", "有待进一步分析", "值得注意", "综合来看",
          "可能存在问题", "有待观察", "进一步优化")

_TAG = re.compile(r"<[^>]+>")
_H2 = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S | re.I)
_SECTION = re.compile(r"<section[^>]*>([\s\S]*?)</section>", re.I)
_FIGURE = re.compile(r"<figure[^>]*>[\s\S]*?</figure>", re.I)
_FIG_SRC = re.compile(r'class="fig-src"', re.I)
_NUM = re.compile(r"\d+(?:\.\d+)?")


def _text(html: str) -> str:
    s = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
    s = _TAG.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _stats(html: str) -> dict:
    text = _text(html)
    figures = _FIGURE.findall(html)
    sentences = [x.strip() for x in re.split(r"[。；;\n]", text) if len(x.strip()) >= 12]
    dup = {k: v for k, v in Counter(sentences).items() if v > 1}
    dup_count = sum(v - 1 for v in dup.values())
    nums = len(_NUM.findall(text))
    return {
        "chars": len(text),
        "numbers": nums,
        "density": round(nums / max(1, len(text)) * 1000, 1),
        "figures": len(figures),
        "figure_sources": len(_FIG_SRC.findall(html)),
        "duplicate_sentences": dup_count,
        "duplicate_rate": round(dup_count / max(1, len(sentences)), 3),
        "density_floor": 25,
    }


def check_html(path) -> dict:
    path = Path(path)
    html = path.read_text(encoding="utf-8", errors="replace")
    text = _text(html)
    stats = _stats(html)
    v = []

    # F1 版式四规则
    try:
        from check_report_layout import check_html as check_layout
        lay = check_layout(path)
        for x in lay.get("violations") or []:
            v.append({"id": "F1_layout", "msg": x})
    except Exception as exc:  # noqa: BLE001
        v.append({"id": "F1_layout", "msg": f"版式检查不可用: {exc}"})

    heads = [re.sub(r"<[^>]+>", "", h).strip() for h in _H2.findall(html)]

    # F2 标题即结论且带数字
    first_h2 = html.find("<h2")
    hero = _text(html[:first_h2]) if first_h2 > 0 else text[:800]
    if not _NUM.search(hero):
        v.append({"id": "F2_headline_number", "msg": "首屏标题/导语里没有数字：标题不是结论"})

    # F3 结论段至少一条带数字（结论先行块）
    summary = re.search(r'<section id="summary">([\s\S]*?)</section>', html, re.I)
    lede = summary.group(1) if summary else \
        " ".join(re.findall(r'<p class="sec-lede"[^>]*>([\s\S]*?)</p>', html, re.I))
    if not _NUM.search(_text(lede)):
        v.append({"id": "F3_summary_number", "msg": "结论段没有带数字的结论"})

    # F4 每节带数字（附录除外）
    for sec in _SECTION.findall(html):
        h = re.search(r"<h2[^>]*>([\s\S]*?)</h2>", sec, re.I)
        if not h:
            continue
        title = _text(h.group(1))
        body = _text(sec)
        if not _NUM.search(body):
            v.append({"id": "F4_section_number", "msg": f"章节「{title}」没有数字判断"})

    # F5 边界：独立边界节，或每节带「本节边界」，或口径说明里写了边界
    notes_m = re.search(r'<section class="notes"[\s\S]*?</section>', html, re.I)
    notes_txt = _text(notes_m.group(0)) if notes_m else ""
    if not (any("边界" in h for h in heads) or "本节边界" in text or "边界" in notes_txt):
        v.append({"id": "F5_boundary", "msg": "没有「边界」章节：没说清结论只对什么成立"})

    # F6 末节口径与分数
    if not heads or "口径与分数" not in heads[-1]:
        v.append({"id": "F6_last_section",
                  "msg": f"末节不是「口径与分数」，而是「{heads[-1] if heads else '无'}」"})

    # F7 图必须有来源
    if stats["figures"] and stats["figure_sources"] < stats["figures"]:
        v.append({"id": "F7_figure_source",
                  "msg": f"{stats['figures']} 张图只有 {stats['figure_sources']} 个来源"})

    # F8 不出现 JSON / 字段回显
    if "```json" in html or re.search(r'"ok"\s*:', text):
        v.append({"id": "F8_raw_json", "msg": "正文出现 JSON 或字段回显：这是日志不是报告"})

    # F9 重复句 / 数字密度 / 禁用词
    if stats["duplicate_rate"] > 0.10:
        v.append({"id": "F9_duplicate",
                  "msg": f"内部重复句 {stats['duplicate_rate']:.0%} > 10%"})
    if stats["density"] < stats["density_floor"]:
        v.append({"id": "F9_density",
                  "msg": f"数字密度 {stats['density']}/千字 < {stats['density_floor']}"})
    hits = [w for w in BANNED if w in text]
    if hits:
        v.append({"id": "F9_banned", "msg": "禁用词：" + "、".join(hits)})

    return {"file": str(path), "ok": not v, "violations": v, "stats": stats}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    targets = [Path(x) for x in a.files]
    if a.dir:
        targets += sorted(Path(a.dir).glob("*.html"))
    if not targets:
        print("用法: python scripts/check_report_flow.py <report.html> | --dir <out>")
        return 2
    results = [check_html(p) for p in targets]
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        print(f"{mark}  {r['file']}  密度 {r['stats']['density']}  "
              f"图 {r['stats']['figures']}  重复句 {r['stats']['duplicate_rate']:.0%}")
        for x in r["violations"]:
            print(f"      - [{x['id']}] {x['msg']}")
    if a.json:
        Path(a.json).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
