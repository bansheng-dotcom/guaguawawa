# -*- coding: utf-8 -*-
"""scripts/grade_report_level.py —— 报告分级（L0—L4），只用 HTML 判据，不靠自觉。

分级口径（与 REPORT-STANDARD 对齐）：
  L0 日志：字段回显，无结论、无证据
  L1 摘要：有结论句，但缺表格/图表/边界
  L2 研究稿：结论带数字 + 多节结构 + 表格 + 边界（= 内蒙古七类蛋白那份的档位）
  L3 分析稿：L2 + 图表带来源/单位 + 口径冲突与统计复核 + 数字密度达标
  L4 决策级：L3 + 图标题即结论（含数字）+ 表格带单位列 + 结论带动作/停止条件 + 可复现证据包

用法：
    python scripts/grade_report_level.py <file.html> [more.html ...]
    python scripts/grade_report_level.py --dir <目录>        # 递归扫 *.html
    python scripts/grade_report_level.py --json <file.html>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

TOOLS = Path(__file__).resolve().parent.parent

BANNED = ("需要关注", "有待进一步分析", "值得注意", "综合来看", "可能存在问题")


def _text(html: str) -> str:
    t = re.sub(r"(?s)<style.*?</style>", "", html)
    t = re.sub(r"(?s)<script.*?</script>", "", t)
    t = re.sub(r"<[^>]+>", "\n", t)
    return re.sub(r"\s+", "", t)


def grade(path: Path) -> Dict[str, Any]:
    html = path.read_text(encoding="utf-8", errors="replace")
    body = re.sub(r"(?s)<style.*?</style>", "", html)
    text = _text(html)
    n_char = len(text)

    h2 = re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)
    tables = re.findall(r"<table.*?</table>", body, re.S)
    rows = sum(len(re.findall(r"<tr", t)) for t in tables)
    cells = sum(len(re.findall(r"<td", t)) for t in tables)
    figs = re.findall(r'<figure class="fig-card">(.*?)</figure>', body, re.S)
    svgs = body.count("<svg")
    prose = [re.sub(r"<[^>]+>", "", p) for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S)]
    prose = [p for p in prose if len(p) >= 24]

    # 结论：结论区里的条目（ol.concl li 或 .insight）
    concl_items = re.findall(r'<li>(.*?)</li>', body, re.S)
    concl_items = [re.sub(r"<[^>]+>", "", c) for c in concl_items]
    concl_items = [c for c in concl_items if len(c) >= 16]
    concl_with_num = [c for c in concl_items if re.search(r"\d", c)]

    # 图表质量：标题里有没有数字（结论式标题）、有没有来源、有没有单位
    fig_title_num = 0
    fig_with_source = 0
    for f in figs:
        head = re.search(r'<figcaption[^>]*>(.*?)</figcaption>', f, re.S)
        ht = re.sub(r"<[^>]+>", "", head.group(1)) if head else ""
        if re.search(r"\d", ht):
            fig_title_num += 1
        if 'class="fig-src"' in f:
            fig_with_source += 1

    # 表格质量：表头是否带单位（括号里带单位词）
    tables_with_unit = 0
    for t in tables:
        th = re.findall(r"<th[^>]*>(.*?)</th>", t, re.S)
        if any(re.search(r"[（(][^)）]*(亿元|万元|%|pp|百分点|万|点|个|条|天|人|单|分|月|倍|元)[)）]", re.sub(r"<[^>]+>", "", h)) for h in th):
            tables_with_unit += 1

    boundary = body.count('class="boundary"')
    has_boundary = boundary >= 1 or ("边界" in text) or ("局限" in text)
    has_assumption = any(w in text for w in ("口径", "假设", "边界", "局限"))
    has_caliber = bool(re.search(r"口径|边界|假设", body))
    has_conflict = bool(re.search(r"冲突", body))
    has_check = bool(re.search(r"复核", body))
    has_action = bool(re.search(r"停止|阈值|触发|100 个复购|停止条件", body))
    banned_hits = [w for w in BANNED if w in text]
    digits = len(re.findall(r"\d", text))
    density = digits / max(n_char, 1) * 100
    # 字段回显（REPORT-STANDARD R8）：整段在念字段名的比例
    echo = [p for p in prose if re.match(r"^\s*(证据|机制|经营含义|边界|数据来源)[：:]", p)]
    echo_ratio = len(echo) / max(len(prose), 1)
    para_avg = sum(len(p) for p in prose) / max(len(prose), 1)

    # 内部重复句（SOP v3 P0-1）：正文里同一句话出现两次以上
    body2 = re.sub(r"(?s)<nav.*?</nav>", "", body)
    body2 = re.sub(r"(?s)<svg.*?</svg>", "", body2)
    body2 = re.sub(r"(?s)<figcaption.*?</figcaption>", "", body2)
    body2 = re.sub(r"(?s)<h[1-6].*?</h[1-6]>", "", body2)
    body2 = re.sub(r"(?s)<th.*?</th>", "", body2)
    body2 = re.sub(r"(?s)<td.*?</td>", "", body2)
    body2 = re.sub(r"<[^>]+>", "\n", body2)
    _sents = [s.strip() for s in re.split(r"[。；\n]", body2)
              if 16 <= len(s.strip()) <= 140 and re.search(r"[\u4e00-\u9fff]", s)]
    dup_sentences = sum(1 for _s, c in Counter(_sents).items() if c > 1)

    facts = {
        "chars": n_char, "sections": len(h2), "tables": len(tables), "rows": rows,
        "cells": cells, "figures": len(figs), "svgs": svgs,
        "prose_paragraphs": len(prose),
        "conclusions": len(concl_items), "conclusions_with_number": len(concl_with_num),
        "fig_title_with_number": fig_title_num, "fig_with_source": fig_with_source,
        "tables_with_unit": tables_with_unit, "boundary_blocks": boundary,
        "has_caliber": has_caliber, "has_assumption": has_assumption, "has_conflict": has_conflict,
        "has_check": has_check, "has_action": has_action,
        "banned": banned_hits, "digit_density": round(density, 2),
        "echo_ratio": round(echo_ratio, 2), "para_avg": round(para_avg),
        "dup_sentences": dup_sentences,
    }

    # ---- 逐级判定 ----
    reasons: List[str] = []
    level = 0
    if facts["conclusions_with_number"] >= 3 and facts["sections"] >= 5:
        level = 1
    else:
        if facts["conclusions_with_number"] < 3:
            reasons.append(f"带数字的结论只有 {facts['conclusions_with_number']} 条")
        if facts["sections"] < 5:
            reasons.append(f"章节只有 {facts['sections']} 节")
    if (level >= 1 and facts["tables"] >= 5 and facts["cells"] >= 40
            and facts["chars"] >= 4000 and facts["prose_paragraphs"] >= 8
            and facts["sections"] >= 8 and has_assumption and not facts["banned"]):
        level = 2
    elif level >= 1:
        if facts["tables"] < 5:
            reasons.append(f"表少（{facts['tables']}）")
        if facts["cells"] < 40:
            reasons.append(f"表内容少（{facts['cells']} 格）")
        if facts["chars"] < 4000:
            reasons.append(f"正文短（{facts['chars']} 字）")
        if facts["prose_paragraphs"] < 8:
            reasons.append(f"段落少（{facts['prose_paragraphs']} 段）")
        if facts["sections"] < 8:
            reasons.append(f"章节少（{facts['sections']} 节）")
        if not has_assumption:
            reasons.append("无口径/假设/边界说明")
        if facts["banned"]:
            reasons.append("命中禁用词：" + "、".join(facts["banned"]))
    if level >= 2:
        ok3 = (facts["figures"] >= 3 and facts["fig_with_source"] >= facts["figures"]
               and facts["has_conflict"] and facts["has_check"] and facts["digit_density"] >= 1.2
               and facts["echo_ratio"] <= 0.30 and facts["para_avg"] >= 80
               and facts["dup_sentences"] == 0)
        if ok3:
            level = 3
        else:
            if facts["figures"] < 3:
                reasons.append(f"图少（{facts['figures']}）")
            if facts["fig_with_source"] < facts["figures"]:
                reasons.append("有图缺来源")
            if not facts["has_conflict"]:
                reasons.append("无口径冲突节")
            if not facts["has_check"]:
                reasons.append("无统计复核节")
            if facts["digit_density"] < 1.2:
                reasons.append(f"数字密度低（{facts['digit_density']}/100 字）")
            if facts["echo_ratio"] > 0.30:
                reasons.append(f"字段回显过半（{facts['echo_ratio']:.0%}）")
            if facts["para_avg"] < 80:
                reasons.append(f"段落太短（均 {facts['para_avg']} 字）")
            if facts["dup_sentences"]:
                reasons.append(f"内部重复句 {facts['dup_sentences']} 条")
    if level >= 3:
        ok4 = (facts["fig_title_with_number"] >= max(1, facts["figures"] - 1)
               and facts["tables_with_unit"] >= max(2, facts["tables"] // 3)
               and facts["has_action"] and facts["chars"] >= 6000)
        if ok4:
            level = 4
        else:
            if facts["fig_title_with_number"] < max(1, facts["figures"] - 1):
                reasons.append("图标题不是结论句（缺数字）")
            if facts["tables_with_unit"] < max(2, facts["tables"] // 3):
                reasons.append("表头缺单位")
            if not facts["has_action"]:
                reasons.append("结论缺动作/停止条件")
            if facts["chars"] < 6000:
                reasons.append(f"正文偏短（{facts['chars']} 字）")

    facts["level"] = f"L{level}"
    facts["reasons"] = reasons
    return facts


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    paths: List[Path] = [Path(f) for f in a.files]
    if a.dir:
        paths += sorted(Path(a.dir).rglob("*.html"))
    paths = [p for p in paths if p.is_file()]
    if not paths:
        print("没有可评分的 HTML")
        return 2

    out = []
    for p in paths:
        try:
            g = grade(p)
        except Exception as e:  # noqa: BLE001
            g = {"level": "ERR", "reasons": [str(e)]}
        g["file"] = str(p)
        out.append(g)

    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("（诊断口径：只给档位参考，不参与放行；放行看 scripts/check_report_flow.py）")
    print(f"{'档位':<5}{'字':>7}{'节':>4}{'表':>4}{'图':>4}{'结论':>5}{'数字密度':>8}  文件")
        for g in out:
            print(f"{g['level']:<5}{g.get('chars',0):>7}{g.get('sections',0):>4}"
                  f"{g.get('tables',0):>4}{g.get('figures',0):>4}"
                  f"{g.get('conclusions_with_number',0):>5}{g.get('digit_density',0):>8}  "
                  f"{Path(g['file']).name}")
            if g.get("reasons"):
                print("       - " + "；".join(g["reasons"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
