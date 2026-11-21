# -*- coding: utf-8 -*-
"""唯一报告门禁（2026-11-15 产线收敛后 / 2026-11-20 收紧）：只看 HTML 成品，不看是谁画的。

替代旧七件套（layout / depth / style / substance / diversity / project / analysis）。
它们的前提是「20 个角色各出一份报告」，产线收敛后那个前提不存在了；
现在只回答一个问题：**这一份 R01 报告能不能发给创始人。**

九条判据（任一不过即 FAIL）：
  F1 版式四规则（复用 scripts/check_report_layout.py）
  F2 标题即结论且带数字（首屏可见文本必须有数字；`<title>` 不算）
  F3 结论段至少一条带数字（summary 块）
  F4 每个业务章节至少一句带数字
  F5 每节有**非空**边界（只写 data-label 属性、边界正文为空 → 仍然 FAIL）
  F6 末节是「口径与分数」，且正文写够（≥80 字、含数字）
  F7 **每一张**图都有自己的来源，且来源文字非空（不是「有 N 个 class」）
  F8 不出现 JSON/字段回显（` ```json `、`"ok":`）
  F9 内部重复句 ≤ 10%，数字密度 ≥ 25/千字，禁用词 0
  F10 深度（与 core.report_quality 同一判据）
  F11 报告不得自证门禁（「全部门禁通过」这类话只能由 manifest 出，不能由正文说）

判据标记（fig-src / data-label / summary / 口径与分数）一律从
`core.report_marks` 取，禁止在本文件里写字面量——2026-11-20 的
「默认 flow 过不了自己的门禁」就是两边各写一份导致的。

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

from core.report_marks import (  # noqa: E402
    BOUNDARY_LABEL,
    CALIBER_TITLE,
    FIGURE_SRC_CLASS,
    MIN_BOUNDARY_CHARS,
    MIN_CALIBER_CHARS,
    MIN_FIGURE_SOURCE_CHARS,
    SUMMARY_SECTION_ID,
)

BANNED = ("需要关注", "有待进一步分析", "值得注意", "综合来看",
          "可能存在问题", "有待观察", "进一步优化")
# 自证门禁：通过与否由 manifest.gate.flow 说，正文不许自己宣布
SELF_CERT = ("全部门禁通过", "门禁全部通过", "两道门禁独立校验", "已通过全部门禁")

_TAG = re.compile(r"<[^>]+>")
_H2 = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S | re.I)
_SECTION = re.compile(r"<section[^>]*>([\s\S]*?)</section>", re.I)
_FIGURE = re.compile(r"<figure[^>]*>[\s\S]*?</figure>", re.I)
_NUM = re.compile(r"\d+(?:\.\d+)?")
_CLASS_ATTR = re.compile(r'class="([^"]*)"', re.I)
_HEAD = re.compile(r"<head[\s\S]*?</head>", re.I)


def _text(html: str) -> str:
    s = _HEAD.sub(" ", html)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
    s = _TAG.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _classes(fragment: str) -> set:
    out = set()
    for m in _CLASS_ATTR.finditer(fragment):
        out |= set(m.group(1).split())
    return out


def _figure_has_source(fig: str) -> bool:
    """图内必须有一个**有文字**的 fig-src 元素。"""
    cls = re.escape(FIGURE_SRC_CLASS)
    m = re.search(
        r'<([a-zA-Z][\w-]*)([^>]*class="[^"]*(?<![\w-])' + cls + r'(?![\w-])[^"]*"[^>]*)>'
        r'([\s\S]*?)</\1>', fig, re.I)
    if not m:
        return False
    t = re.sub(r"^来源[:：]?\s*", "", _text(m.group(3))).strip()
    return len(t) >= MIN_FIGURE_SOURCE_CHARS


def _boundary_texts(html: str):
    """取所有「本节边界」的正文；「什么会推翻它」不算边界。"""
    out = []
    for m in re.finditer(r"<div([^>]*)>([\s\S]*?)</div>", html, re.I):
        cls = _classes("<div" + m.group(1) + ">")
        if "boundary" not in cls or "sec-falsifier" in cls:
            continue
        t = _text(m.group(2))
        if t.startswith("边界"):
            t = t[len("边界"):]
        elif BOUNDARY_LABEL in m.group(1):
            t = t.replace(BOUNDARY_LABEL, "")
        out.append(t.strip())
    return out


def _section_with_title(sections, title: str) -> str:
    """找 h2 里含 title 的那个 section；找不到返回空串。"""
    for sec in sections:
        h = re.search(r"<h2[^>]*>([\s\S]*?)</h2>", sec, re.I)
        if h and title in _text(h.group(1)):
            return sec
    return ""


def _stats(html: str) -> dict:
    text = _text(html)
    figures = _FIGURE.findall(html)
    # 重复句只查正文：决策纸/动作页/附录会合法复述正文标题与数字，
    # 把它们算进来会把“有决策纸”误判成“车轱辘话”。
    body = re.sub(
        r'<section class="[^"]*(?:summary|acts|appendix|cover|toc|back)[^"]*"[\s\S]*?</section>',
        "", html, flags=re.I)
    sentences = [x.strip() for x in re.split(r"[。；;\n]", _text(body)) if len(x.strip()) >= 12]
    dup = {k: v for k, v in Counter(sentences).items() if v > 1}
    dup_count = sum(v - 1 for v in dup.values())
    nums = len(_NUM.findall(text))
    return {
        "chars": len(text),
        "numbers": nums,
        "density": round(nums / max(1, len(text)) * 1000, 1),
        "figures": len(figures),
        "figure_sources": sum(1 for f in figures if _figure_has_source(f)),
        "boundaries": len([t for t in _boundary_texts(html) if len(t) >= MIN_BOUNDARY_CHARS]),
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

    sections = _SECTION.findall(html)
    # 封面/决策纸/目录/封底是「页面」，不是业务章节：不计入章节数、不参与每节深度
    raw_sections = re.findall(r"<section[^>]*>[\s\S]*?</section>", html, re.I)
    content_sections = [
        s for s in raw_sections
        if "<h2" in s.lower()
        and not re.search(r'id="appendix"', s, re.I)
        and not re.search(r'class="page (summary|cover|toc|back)"', s, re.I)
    ]
    # 标题序列只取业务章节：来源附录（page appendix）不是「末节」
    heads = [re.sub(r"<[^>]+>", "", h).strip()
             for h in _H2.findall("".join(content_sections))]

    # F2 标题即结论且带数字（只看可见正文，<title> 不算）
    first_h2 = html.find("<h2")
    hero = _text(html[:first_h2]) if first_h2 > 0 else text[:800]
    if not _NUM.search(hero):
        v.append({"id": "F2_headline_number", "msg": "首屏标题/导语里没有数字：标题不是结论"})

    # F3 结论段至少一条带数字（结论先行块）；flow 渲染器把 class 放在 id 前，按属性匹配
    summary = re.search(
        r'<section[^>]*\bid="' + re.escape(SUMMARY_SECTION_ID) + r'"[^>]*>([\s\S]*?)</section>',
        html, re.I)
    lede = summary.group(1) if summary else \
        " ".join(re.findall(r'<p class="sec-lede"[^>]*>([\s\S]*?)</p>', html, re.I))
    if not _NUM.search(_text(lede)):
        v.append({"id": "F3_summary_number", "msg": "结论段没有带数字的结论"})

    # F4 每节带数字（附录除外）
    for sec in sections:
        h = re.search(r"<h2[^>]*>([\s\S]*?)</h2>", sec, re.I)
        if not h:
            continue
        title = _text(h.group(1))
        body = _text(sec)
        if not _NUM.search(body):
            v.append({"id": "F4_section_number", "msg": f"章节「{title}」没有数字判断"})

    # F5 边界：三种载体都算，但都要求**有正文**——
    #   ① 独立的「边界」节；② 每节一条「本节边界」；③ 口径节里的「结论成立的条件」。
    # 只挂 data-label 属性、边界正文为空，仍然 FAIL。
    boundary_ok = False
    for sec in sections:
        h = re.search(r"<h2[^>]*>([\s\S]*?)</h2>", sec, re.I)
        if h and "边界" in _text(h.group(1)) and len(_text(sec)) >= 40:
            boundary_ok = True
            break
    cal_txt = _text(_section_with_title(sections, CALIBER_TITLE))
    if not boundary_ok and "条件" in cal_txt:
        chunks = [c for c in re.split(r"[；;。\n]", cal_txt) if len(c.strip()) >= 12]
        boundary_ok = len(chunks) >= 5
    n_sec = len(content_sections) or 1
    need = max(1, int(round(n_sec * 0.6)))
    if n_sec >= 5:
        need = max(3, need)
    if not boundary_ok and stats["boundaries"] < need:
        v.append({"id": "F5_boundary",
                  "msg": f"有正文的边界只有 {stats['boundaries']} 条，"
                         f"需 {need} 条（{len(content_sections)} 节），"
                         f"或口径节里写清「结论成立的条件」；"
                         f"只挂 {BOUNDARY_LABEL} 属性不算"})

    # F6 末节口径与分数：位置对还不够，正文要写够
    if not heads or CALIBER_TITLE not in heads[-1]:
        v.append({"id": "F6_last_section",
                  "msg": f"末节不是「{CALIBER_TITLE}」，而是「{heads[-1] if heads else '无'}」"})
    else:
        last_txt = _text(_section_with_title(sections, CALIBER_TITLE))
        if len(last_txt) < MIN_CALIBER_CHARS or not _NUM.search(last_txt):
            v.append({"id": "F6_caliber_body",
                      "msg": f"「{CALIBER_TITLE}」正文只有 {len(last_txt)} 字"
                             f"（需 ≥{MIN_CALIBER_CHARS} 且含数字）"})

    # F7 图必须有来源：逐图校验，一张图缺来源就是缺
    figures = _FIGURE.findall(html)
    bad_figs = [i + 1 for i, f in enumerate(figures) if not _figure_has_source(f)]
    if bad_figs:
        v.append({"id": "F7_figure_source",
                  "msg": f"{len(figures)} 张图里 {len(bad_figs)} 张没有来源文字"
                         f"（第 {'、'.join(map(str, bad_figs[:8]))} 张）；"
                         f"只挂 class 不算"})

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

    # F10 深度：与 core.report_quality 共用同一判据（按体量自动分档 research/baseline），
    # 不再出现「flow 说 PASS、深度门禁说 FAIL」的两套结论。
    depth = None
    try:
        from core import report_quality  # noqa: PLC0415
        depth = report_quality.audit(path, "auto")
        if not depth["ok"]:
            for c in depth["checks"]:
                if c.get("hard") and not c["ok"]:
                    v.append({"id": "F10_depth",
                              "msg": f"[{depth['profile']}] {c['id']}: "
                                     f"{c['value']} 需 {c['need']}（{c['msg']}）"})
    except Exception as exc:  # noqa: BLE001
        v.append({"id": "F10_depth", "msg": f"深度门禁不可用: {exc}"})

    # F11 不得自证门禁：结论只能由 manifest.gate.flow 出
    self_cert = [w for w in SELF_CERT if w in text]
    if self_cert:
        v.append({"id": "F11_self_certified",
                  "msg": "正文自证门禁（" + "、".join(self_cert)
                         + "）：门禁结论只能写进 manifest.gate.flow"})

    return {"file": str(path), "ok": not v, "violations": v, "stats": stats,
            "depth": ({"profile": depth["profile"], "ok": depth["ok"],
                       "score": depth["score"]} if depth else None)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    targets = [Path(x) for x in a.files]
    if a.dir:
        # 跳过 `_*.html`：那是排障/试渲染留下的中间件，不是交付物
        targets += sorted(p for p in Path(a.dir).glob("*.html")
                          if not p.name.startswith("_"))
    if not targets:
        print("用法: python scripts/check_report_flow.py <report.html> | --dir <out>")
        return 2
    results = [check_html(p) for p in targets]
    for r in results:
        mark = "PASS" if r["ok"] else "FAIL"
        prof = (r.get("depth") or {}).get("profile", "?")
        print(f"{mark}  {r['file']}  密度 {r['stats']['density']}  "
              f"图 {r['stats']['figures']}/{r['stats']['figure_sources']}  "
              f"边界 {r['stats']['boundaries']}  重复句 {r['stats']['duplicate_rate']:.0%}"
              f"  深度档 {prof}")
        for x in r["violations"]:
            print(f"      - [{x['id']}] {x['msg']}")
    if a.json:
        Path(a.json).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
