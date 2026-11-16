# -*- coding: utf-8 -*-
"""专业标准门禁（M1—M5）。

用法：
    python scripts/check_professional_standard.py <report.html> [更多 html ...]
    python scripts/check_professional_standard.py <report.html> --dir <项目> --topic "<主题>"

检的是五模块与标准是否真的落到报告里，不看文风：

    M1 问题定义与边界   标题/边界/口径
    M2 数据采集与校验   来源、A/B/C/D 等级、交叉验证、缺口
    M3 结构化逻辑推导   维度前缀、MECE 组 ≥3、每节带数字
    M4 风险与局限       证伪条件、回退
    M5 可落地结论       动作、owner、验收口、停止条件

给了 --dir/--topic 时，额外用框架蓝图做 MECE 预检（组覆盖与维度重叠）。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")
H2 = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S)
DIGIT = re.compile(r"\d")


def _text(html: str) -> str:
    return WS.sub(" ", TAG.sub(" ", html))


def _sections(html: str) -> List[Dict[str, Any]]:
    parts = re.split(r"<h2[^>]*>", html)
    out = []
    for p in parts[1:]:
        head, _, body = p.partition("</h2>")
        labels = [WS.sub(" ", TAG.sub(" ", x)).strip()
                  for x in re.findall(r"<strong>(.*?)</strong>", body, re.S)]
        labels += [WS.sub(" ", TAG.sub(" ", x)).strip()
                   for x in re.findall(r'data-label="([^"]+)"', body)]
        out.append({"title": WS.sub(" ", TAG.sub(" ", head)).strip(),
                    "text": _text(body), "labels": labels})
    return out


def _ok(name: str, cond: bool, note: str = "") -> Dict[str, Any]:
    return {"name": name, "ok": bool(cond), "note": note}


def check_report(path: str) -> Dict[str, Any]:
    html = Path(path).read_text(encoding="utf-8", errors="ignore")
    secs = _sections(html)
    titles = [s["title"] for s in secs]
    full = _text(html)

    m1 = [s for s in secs if "问题定义与边界" in s["title"]]
    m2 = [s for s in secs if "数据采集与校验" in s["title"]]
    m3 = [s for s in secs if "｜" in s["title"] and any(
        g in s["title"] for g in ("需求侧", "供给侧", "竞争与渠道", "财务与经营", "风险与执行"))]
    m4 = [s for s in secs if "风险与局限" in s["title"]]
    m5 = [s for s in secs if "结论与动作" in s["title"]]

    groups = {g for g in ("需求侧", "供给侧", "竞争与渠道", "财务与经营", "风险与执行")
              for s in m3 if g in s["title"]}

    res = []
    res.append(_ok("M1 问题定义与边界", bool(m1) and any(DIGIT.search(s["title"]) for s in m1)
                   and any(("口径" in s["text"] or "边界" in s["text"]) for s in m1),
                   f"M1 节 {len(m1)}"))
    res.append(_ok("M2 数据采集与校验", bool(m2) and "交叉" in (m2[0]["text"] if m2 else "")
                   and "缺口" in (m2[0]["text"] if m2 else "")
                   and all(g in (m2[0]["text"] if m2 else "") for g in ("A", "B", "C", "D")),
                   "来源/等级/校验/缺口"))
    res.append(_ok("M3 结构化逻辑推导", len(m3) >= 3 and len(groups) >= 3
                   and all(DIGIT.search(s["title"]) for s in m3),
                   f"维度节 {len(m3)}，MECE 组 {len(groups)}"))
    mech_l = ("机理", "含义", "机制", "驱动", "传导", "原因", "对照",
              "成本栈", "构成", "拆解", "结构", "极差")
    fals_l = ("证伪", "信号", "变化", "边界", "风险", "停止",
              "敏感性", "闸门", "阈值", "极差", "套利", "触发")

    def _chain(s: Dict[str, Any]) -> bool:
        lab = " ".join(s.get("labels") or [])
        if len(s.get("labels") or []) >= 4:
            return (any(w in lab for w in mech_l) and any(w in lab for w in fals_l))
        return (any(w in s["text"] for w in mech_l) and any(w in s["text"] for w in fals_l))

    res.append(_ok("M3 每维度有机理/证伪", all(_chain(s) for s in m3),
                   "判断→对照→机理→落点→证伪"))
    res.append(_ok("M4 风险与局限", bool(m4) and "证伪" in (m4[0]["text"] if m4 else "")
                   and ("回退" in (m4[0]["text"] if m4 else "")
                        or "应对" in (m4[0]["text"] if m4 else "")), "证伪/回退"))
    res.append(_ok("M5 可落地结论", bool(m5) and "停止条件" in (m5[0]["text"] if m5 else "")
                   and ("验收" in (m5[0]["text"] if m5 else "")
                        or "负责人" in (m5[0]["text"] if m5 else "")
                        or "owner" in (m5[0]["text"] if m5 else "")),
                   "动作/owner/验收/停止"))
    res.append(_ok("S1 每题一节", len(secs) >= 6, f"节数 {len(secs)}"))
    res.append(_ok("S2 来源等级落表", "来源与可信度" in full or ("等级" in full and "A 级" in full),
                   "A/B/C/D"))
    res.append(_ok("S3 禁用空话", not any(w in full for w in (
        "有待进一步分析", "值得注意", "综合来看", "有待观察", "可能存在问题")),
        "禁用词清零"))
    return {"file": path, "checks": res, "ok": all(x["ok"] for x in res)}


def check_v10(path: str) -> Dict[str, Any]:
    """v10 假设驱动稿的门禁（V1—V10）。

    v9 的 M1—M5 管的是「五模块是否齐」；v10 换了结构，管的是「有没有真的
    做假设驱动」：核心矛盾、可证伪假设、逐条验证、定量模型、敏感性、情景、
    决策选项、红队回应、验收与停止、来源等级。缺任何一项即判 FAIL。
    """
    html = Path(path).read_text(encoding="utf-8", errors="ignore")
    secs = _sections(html)
    full = _text(html)
    T = {s["title"]: s for s in secs}

    def _get(*words: str) -> List[Dict[str, Any]]:
        return [s for s in secs if any(w in s["title"] for w in words)]

    v1 = _get("核心矛盾")
    v2 = _get("假设树")
    v3 = [s for s in secs if re.search(r"H[123]", s["title"])]
    v4 = _get("定量模型")
    v5 = _get("敏感性")
    v6 = _get("情景")
    v7 = _get("决策选项")
    v8 = _get("红队")
    v9_ = _get("风险与验收")

    def _rows(s: Dict[str, Any]) -> int:
        return s["text"].count("，") + s["text"].count("；")

    res = []
    res.append(_ok("V1 核心矛盾", bool(v1) and any(DIGIT.search(s["title"]) for s in v1)
                   and any(("矛盾" in s["text"] or "张力" in s["text"]) for s in v1),
                   f"节 {len(v1)}"))
    res.append(_ok("V2 假设树", bool(v2) and "推翻" in (v2[0]["text"] if v2 else "")
                   and (v2[0]["text"] if v2 else "").count("推翻") >= 3,
                   "≥3 条假设各带推翻条件"))
    res.append(_ok("V3 逐条验证", len(v3) >= 3
                   and all(any("反证" in l for l in s["labels"])
                           and any("结论" in l for l in s["labels"]) for s in v3),
                   f"验证节 {len(v3)}"))
    res.append(_ok("V4 定量模型", bool(v4) and "=" in (v4[0]["text"] if v4 else "")
                   and "保本" in (v4[0]["text"] if v4 else ""), "可复算等式 + 保本线"))
    res.append(_ok("V5 敏感性", bool(v5) and (v5[0]["text"] if v5 else "").count("%") >= 3
                   and any(w in (v5[0]["text"] if v5 else "") for w in ("冲击", "敏感")),
                   f"行 {_rows(v5[0]) if v5 else 0}"))
    res.append(_ok("V6 情景", bool(v6) and all(w in (v6[0]["text"] if v6 else "")
                                              for w in ("悲观", "基准", "乐观")), "三情景"))
    res.append(_ok("V7 决策选项", bool(v7) and sum(
        w in (v7[0]["text"] if v7 else "") for w in ("代价", "风险", "排序")) >= 2,
        "选项带代价/风险/排序"))
    res.append(_ok("V8 红队回应", bool(v8)
                   and sum(1 for l in (v8[0]["labels"] if v8 else []) if "反驳" in l) >= 3
                   and "回应" in (v8[0]["text"] if v8 else ""), "≥3 条反驳带回应"))
    res.append(_ok("V9 风险与验收", bool(v9_)
                   and any("停止" in l for l in (v9_[0]["labels"] if v9_ else []))
                   and any("验收" in l for l in (v9_[0]["labels"] if v9_ else [])),
                   "验收口 + 停止条件"))
    res.append(_ok("V10 来源等级", all(g in (v9_[0]["text"] if v9_ else "") for g in ("A 级", "B 级", "C 级"))
                   or "A/B" in full, "A/B/C 级"))
    res.append(_ok("V11 每题一节", len(secs) >= 10, f"节数 {len(secs)}"))
    return {"file": path, "profile": "v10", "checks": res,
            "ok": all(x["ok"] for x in res)}


def _is_v10(html_path: str) -> bool:
    try:
        html = Path(html_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return "核心矛盾" in html and "假设树" in html and "红队" in html


def check_blueprint(report: Dict[str, Any], project: str, topic: str) -> Dict[str, Any]:
    from core import analysis_desk, report_framework
    desk = analysis_desk.scan(project)
    prof = analysis_desk.profile(desk)
    bp = report_framework.blueprint(topic, prof)
    res = [_ok("B1 维度覆盖 ≥3 组", bp["mece"]["groups"] >= 3,
               f"组 {bp['mece']['groups']}"),
           _ok("B2 维度不重叠", not bp["mece"]["duplicates"], str(bp["mece"]["duplicates"])),
           _ok("B3 维度数 ≥3", bp["mece"]["dimensions"] >= 3,
               f"维 {bp['mece']['dimensions']}")]
    report["blueprint"] = {"topic": topic, "mece": bp["mece"], "checks": res}
    report["ok"] = report["ok"] and all(x["ok"] for x in res)
    return report


def main(argv: List[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    files = [a for a in argv if a.lower().endswith(".html")]
    project = topic = None
    for i, a in enumerate(argv):
        if a == "--dir" and i + 1 < len(argv):
            project = argv[i + 1]
        if a == "--topic" and i + 1 < len(argv):
            topic = argv[i + 1]
    bad = 0
    results = []
    for f in files:
        r = check_v10(f) if _is_v10(f) else check_report(f)
        if project and topic:
            r = check_blueprint(r, project, topic)
        results.append(r)
        print(f"\n===== {Path(f).name}")
        for x in r["checks"]:
            print(f"  [{'PASS' if x['ok'] else 'FAIL'}] {x['name']}  {x['note']}")
        print(f"  结论：{'PASS' if r['ok'] else 'FAIL'}")
        if not r["ok"]:
            bad += 1
    if len(results) > 1:
        print(f"\n汇总：{len(results) - bad}/{len(results)} 份通过专业标准门禁")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
