# -*- coding: utf-8 -*-
"""core.report_editorial —— 把「方法库契约」补成「可读的报告」。

差距不在主题，在契约：旧 draft 只有 reading 要点，没有 verdict / kicker /
rail / actions / sources。本模块只做**不造数**的编辑装配：

- verdict：本节第一条判断（reading 首句）
- kicker：标题冒号前的短词（准入/标准/产能/格局/大盘/价格带/履约…）
- rail：图表里最大的 3–4 个数字（bars / items / steps / series）
- actions：reading 里「落点 / 所以」条目 + 本节 falsifier 作停止线
- sources：证据包文件清单
- 封面指标：标题里的「数字 + 单位」抽 4 个（抽不到就留空，不编）

调用：`report_flow.build_sections_contract` 末尾 enrich(contract, pack)。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

GENERIC_TITLES = {"自动汇编报告", "研究报告", "报告", "R01 报告"}
KICKERS = ("准入", "标准", "产能", "格局", "大盘", "价格带", "履约", "规模",
           "结构", "渠道", "增速", "缺口", "产业", "增长", "动作", "风险",
           "成本", "利润", "流量", "转化", "复购", "供应链", "组织", "招聘",
           "评测", "事故", "边界", "口径")
UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(平方米|万吨|亿元|元/公斤|元/斤|%|倍|个|家|天|公里|吨)")


def _clip(text: str, n: int) -> str:
    t = str(text or "")
    if len(t) <= n:
        return t
    cut = t[:n]
    for mark in ("；", "。", "，", "、"):
        k = cut.rfind(mark)
        if k >= n * 0.6:
            return cut[:k + 1] + "…"
    return cut + "…"


def _first_sentence(text: str) -> str:
    head, sep, _ = str(text or "").partition("。")
    return (head + "。") if sep else str(text or "")


def _fmt(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(f - round(f)) < 1e-9:
        return f"{int(round(f))}"
    return f"{f:.2f}".rstrip("0").rstrip(".")


def _unit(ch: Dict[str, Any]) -> str:
    u = str(ch.get("unit_meta") or "").split("；")[0].strip()
    return u


def _rail_items(ch: Dict[str, Any]) -> List[List[str]]:
    """从常见图表 payload 抽 3–4 个最大数字；不产生新数字。"""
    unit = _unit(ch)
    raw: List[tuple] = []
    if ch.get("bars"):
        raw = [(b.get("label", ""), b.get("value")) for b in ch["bars"]]
    elif ch.get("vbars"):
        raw = [(b.get("label", ""), b.get("value")) for b in ch["vbars"]]
    elif ch.get("items"):
        raw = [(b.get("label", ""), b.get("value")) for b in ch["items"]]
    elif ch.get("steps"):
        for s in ch["steps"]:
            v = s.get("value")
            if s.get("kind") in ("start", "end", "total") and v is not None:
                raw.append((s.get("label", ""), v))
        if len(raw) < 3:
            raw = [(s.get("label", ""), s.get("delta", s.get("value")))
                   for s in ch["steps"] if s.get("delta") is not None]
    elif ch.get("series"):
        for s in ch["series"]:
            vals = s.get("values") or []
            if vals:
                raw.append((s.get("name", ""), vals[-1]))
    out = []
    seen = set()
    for label, v in sorted(raw, key=lambda x: abs(float(x[1] or 0)), reverse=True):
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        key = (str(label), round(f, 6))
        if not str(label).strip() or key in seen:
            continue
        seen.add(key)
        out.append([_fmt(f), str(label)[:14], unit])
        if len(out) >= 4:
            break
    return out


def _body(s: Dict[str, Any]) -> str:
    return "".join(str(r.get("text") or "") for r in (s.get("reading") or [])
                   if "边界" not in str(r.get("strong") or ""))


def _kicker(s: Dict[str, Any]) -> str:
    if s.get("kicker"):
        return str(s["kicker"])
    title = str(s.get("title") or "")
    head = title.split("：", 1)[0].split(":", 1)[0].strip()
    if head in KICKERS:
        return head
    for k in KICKERS:
        if title.startswith(k):
            return k
    return "判断"


def _actions(contract: Dict[str, Any]) -> List[Dict[str, str]]:
    if contract.get("actions"):
        return list(contract["actions"])
    out: List[Dict[str, str]] = []
    for s in contract.get("sections") or []:
        if s.get("appendix"):
            continue
        stop = _clip(_first_sentence(s.get("falsifier") or ""), 46)
        picked = None
        for r in (s.get("reading") or []):
            strong = str(r.get("strong") or "")
            text = str(r.get("text") or "")
            if "落点" in strong or text.startswith("所以："):
                picked = text.replace("所以：", "").strip()
        if picked:
            out.append({
                "id": f"A{len(out)+1}",
                "title": picked[:42],
                "who": "—",
                "when": "—",
                "budget": "—",
                "stop": stop or "本节证伪条件成立即停",
                "accept": "可按 refs 复算",
            })
        if len(out) >= 6:
            break
    return out


def _metrics(contract: Dict[str, Any]) -> List[Dict[str, str]]:
    if contract.get("metric_strip"):
        return contract["metric_strip"]
    out: List[Dict[str, str]] = []
    seen = set()
    for s in contract.get("sections") or []:
        if s.get("appendix"):
            continue
        title = str(s.get("title") or "")
        head = title.split("：", 1)[0].strip()
        for num, unit in UNIT_RE.findall(title):
            key = (num, unit)
            if key in seen:
                continue
            seen.add(key)
            value = f"{num}{unit}".replace("平方米", "㎡")
            out.append({"label": head or "关键数字", "value": value,
                        "note": "本节", "status": "none"})
            break
        if len(out) >= 4:
            break
    return out


def enrich(contract: Dict[str, Any], pack: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """就地补编辑字段；已有字段不覆盖（内容侧显式给的不动）。"""
    theme = str(contract.get("theme") or "paper")
    for s in contract.get("sections") or []:
        if s.get("appendix"):
            continue
        body = _body(s)
        s.setdefault("kicker", _kicker(s))
        s.setdefault("verdict", _first_sentence(body) or str(s.get("title") or ""))
        if not s.get("rail"):
            ch = s.get("chart") or {}
            items = _rail_items(ch) if ch else []
            if len(items) >= 3:
                s["rail"] = {"items": items, "line": (s["verdict"][:34] or "本节结论")}
        if not s.get("layout"):
            s["layout"] = "rail" if s.get("rail") and len(body) <= 520 else "blocks"

    if not contract.get("metric_strip"):
        contract["metric_strip"] = _metrics(contract)
    actions = _actions(contract)
    if actions:
        contract.setdefault("actions", actions)
        contract.setdefault("one_thing", actions[0]["title"])
        contract.setdefault("stop_rule", "各节证伪条件成立即停；动作验收不过不加仓。")
    if contract.get("summary"):
        contract.setdefault("summary_title", f"{len(contract['summary'])}条判断，一条动作")
    contract.setdefault("one_x", "先做最小可行单元")
    if contract.get("boundaries"):
        contract.setdefault("boundary", str(contract["boundaries"][0])[:120])
    if pack:
        contract.setdefault("sources", [
            {"id": str(s.get("file", "")), "title": str(s.get("file", "")), "date": ""}
            for s in (pack.get("sources") or [])[:40]
        ])
    n_body = len([x for x in (contract.get("sections") or []) if not x.get("appendix")])
    lines = list(contract.get("title_lines") or [])
    was_generic = bool(lines and str(lines[0]).strip() in GENERIC_TITLES)
    if was_generic:
        if contract.get("standfirst"):
            sf = str(contract["standfirst"])
            lines[0] = sf.split("：", 1)[-1] if "：" in sf else sf
        if len(lines) > 1 and "智能体调研稿" in str(lines[1]):
            lines[1] = f"{contract.get('doc_type', '报告')} · {n_body} 节"
        contract["title_lines"] = lines
    if lines and len(lines) > 1 and str(lines[1]).strip() in ("consulting 重排", ""):
        lines[1] = f"{contract.get('doc_type', '报告')} · {n_body} 节"
        contract["title_lines"] = lines
    kickers = [str(s.get("kicker") or "") for s in (contract.get("sections") or [])
               if not s.get("appendix") and s.get("kicker")
               and s.get("kicker") not in ("口径", "记录层")]
    if kickers:
        if str(contract.get("short_title") or "") in ("", "报告") or \
                str(contract.get("short_title") or "") in GENERIC_TITLES:
            contract["short_title"] = f"{contract.get('doc_type', '报告')} · {kickers[0]}"
        if was_generic:
            contract["standfirst"] = f"从{kickers[0]}到{kickers[-1]}：{len(kickers)} 个判断，一条动作。"
    if theme == "consulting":
        contract["layout"] = "hybrid"
    return contract


def check_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    """三条呈现门禁（硬/软分开）：标题带数字、图下来源与口径、正文不过长。

    硬失败才 block；「本节无图/表」记软提示，不把纯文字节一票否决。
    """
    hard: List[str] = []
    warn: List[str] = []
    for s in contract.get("sections") or []:
        if s.get("appendix"):
            continue
        if str(s.get("kicker") or "") in ("口径", "记录层") or "口径与分数" in str(s.get("title") or ""):
            continue
        n = s.get("index", "?")
        title = str(s.get("title") or "")
        if not re.search(r"\d", title):
            hard.append(f"第 {n} 节标题无数字")
        body = _body(s)
        if len(body) < 120:
            hard.append(f"第 {n} 节正文过短（{len(body)} 字）")
        elif len(body) > 650:
            warn.append(f"第 {n} 节正文偏长（{len(body)} 字）")
        ch = s.get("chart") or {}
        if ch:
            if not ch.get("source"):
                hard.append(f"第 {n} 节图缺 source")
            if not ch.get("unit_meta"):
                hard.append(f"第 {n} 节图缺 unit_meta")
        elif not s.get("table"):
            warn.append(f"第 {n} 节既无图也无表")
        rail = s.get("rail") or {}
        if s.get("layout") == "rail" and len(rail.get("items") or []) < 3:
            hard.append(f"第 {n} 节走 B 页但 rail 少于 3 个数字")
    return {"ok": not hard, "hard": hard, "warn": warn,
            "sections": len([x for x in (contract.get("sections") or []) if not x.get("appendix")])}
