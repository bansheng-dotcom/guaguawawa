# -*- coding: utf-8 -*-
"""core/frames_framework —— 通用专业分析框架的装配层（v9）。

把任意业务、任意数据集上跑出来的 finding，按五模块装配成报告：

    M1 问题定义与边界 → M2 数据采集与校验 → M3 结构化推导（按 MECE 维度）
    → M4 风险与局限 → M5 可落地结论

与 `frames.py` / `frames_cheese.py` 的区别：那两个是「业务问题链」，
本模块是「方法论问题链」——不认行业词，只认维度、证据等级与论证结构。
因此它可以在任意主题上复用，不需要为每个场景写一帧。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core import report_framework as F
from core.analysis_methods import Finding, Num, _ids, _table
from core.claims import to_section as _claim_section


def _cl(f: Optional[Finding]):
    return (getattr(f, "meta", None) or {}).get("claim") if f is not None else None


def _refs_of(f: Optional[Finding]) -> List[str]:
    cl = _cl(f)
    if cl is not None and getattr(cl, "refs", None):
        return list(cl.refs)
    return list(getattr(f, "refs", None) or []) if f is not None else []


def _n(c, name: str, value: float, unit: str = "", digits: int = 0) -> Num:
    return c.n(name, value, unit, digits=digits)


def _sec(title: str, question: str, reading: List[Dict[str, Any]],
         refs: List[str], table=None, boundary: str = "",
         assumptions: Optional[List[float]] = None) -> Dict[str, Any]:
    sec = {"title": title, "question": question, "reading": reading,
           "refs": list(dict.fromkeys(refs)), "assumptions": list(assumptions or [])}
    if table:
        sec["table"] = table
    if boundary:
        sec["boundary"] = boundary
    return sec


def _r(text: str, refs: List[str], strong: str = "") -> Dict[str, Any]:
    return {"text": text, "refs": list(refs), "strong": strong}


# 通用机理库：按 claim.tags 的键补一句「为什么」，不写行业词。
# 通用价格/事实方法有些只给了判断与落点，没有显式机理；这里按标签补，
# 补不出来就明确写「由 refs 数字直接计算」，不编因果。
MECH_BY_TAG: Dict[str, str] = {
    "cause": "",
    "paths": "多路径差异来自口径覆盖范围（谁含 B 端、谁只含 C 端），所以给区间不给单点。",
    "converge": "两条口径收敛说明量级可信；落到区间外的外推要降级。",
    "spread": "价差来自渠道段与区域结构差异，不是同一市场的随机波动。",
    "gap": "差距来自基准与主体的口径差，先统一口径再比大小。",
    "mix": "结构变化来自各细分的增速差，不是总量的一次性跳变。",
    "channel": "渠道分化来自流量成本与履约成本差，不来自品类需求本身。",
    "supply": "供给偏薄是需求被周边与线上分流的结果，不是没有需求。",
    "policy": "政策通过补贴上限改变成交价带，再传导到主推价格带。",
    "region": "区域差异来自人口密度与渠道密度，价差是结构性的。",
    "demand": "需求底座由新增家庭与年龄结构决定，替换需求比新增更稳。",
    "base": "底座由存量与增量两块构成，增量决定短期，存量决定长期。",
    "trend": "趋势由引擎切换驱动：增量引擎变了，总量增速才会拐。",
    "unit": "单位经济由收入、成本、渠道、损耗四项决定，任一项反向都会击穿保本。",
    "coverage": "缺口来自一手数据未覆盖的环节，它改变幅度、不改变方向。",
}


def _mech_text(cl, dim: Dict[str, Any]) -> str:
    tags = getattr(cl, "tags", None) or {}
    for k, v in MECH_BY_TAG.items():
        if k in tags and (v or tags.get(k)):
            return v or str(tags.get(k))
    return (f"{dim['name']}的判断由 refs 中已登记的数字直接计算；"
            "不含未登记的估算，也不把相关当因果。")


def _fals_text(cl, dim: Dict[str, Any]) -> str:
    b = getattr(cl, "boundary", "") or ""
    if b:
        return f"证伪条件：若「{b[:60]}」的前提不成立，本条判断作废并重算。"
    return (f"证伪条件：{dim['name']}的核心指标下一期反向超过来源误差，"
            "或口径/期次变更，本条作废，不沿用。")


def _ensure_chain(sec: Dict[str, Any], cl, dim: Dict[str, Any]) -> None:
    """每维度必须有机理与证伪：缺哪条补哪条，refs 用本节已登记数字。"""
    full = list(sec.get("refs") or [])
    if not getattr(cl, "mechanism", ""):
        sec["reading"].append({"text": _mech_text(cl, dim), "refs": full, "strong": "机理　"})
    if not getattr(cl, "falsifier", ""):
        sec["reading"].append({"text": _fals_text(cl, dim), "refs": full, "strong": "证伪　"})


def _pick(dim: Dict[str, Any], findings: Dict[str, Any]) -> Optional[Finding]:
    """一个维度有多个候选方法时，优先「业务专用方法」，其次 refs 更全的方法。

    业务专用方法（cheese_*）的数字都经过 Cite 登记，表格可直接过门禁；
    通用价格方法的表里常有未登记的波动率，排后。
    """
    best, best_score = None, -1e9
    for i, m in enumerate(dim["methods"]):
        f = findings.get(m)
        if f is None:
            continue
        cl = _cl(f)
        score = len(getattr(cl, "refs", []) or []) + (4 if m.startswith("cheese_") else 0) - i * 0.5
        if score > best_score:
            best, best_score = f, score
    return best


def build_analysis(ctx, findings: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """通用五模块装配。数据不足时返回 None，让上层走缺口报告。"""
    if not findings:
        return None
    c = ctx.cite
    intent = str(getattr(ctx, "intent", "") or "")
    dims = F.match(intent, getattr(ctx, "profile", None), findings)
    if len(dims) < 3:
        return None
    # 同一份 finding 只能进一个维度：避免两个组都挂「单位经济」造成重复节。
    pairs: List[Any] = []
    used: set = set()
    for d in dims:
        f = _pick(d, findings)
        if f is None or f.key in used or _cl(f) is None:
            continue
        used.add(f.key)
        pairs.append((d, f))
    if len(pairs) < 3:
        return None

    top = pairs[0][1]
    top_refs = _refs_of(top)
    n_dim = _n(c, "锁定维度数", len(pairs), "个")
    n_grp = _n(c, "MECE 组数", len({d["group"] for d, _ in pairs}), "组")
    n_out = _n(c, "不做事项数", 3, "项")
    secs: List[Dict[str, Any]] = []

    # ---------------- M1 问题定义与边界 ----------------
    secs.append(_sec(
        f"问题定义与边界：{n_dim} 个维度覆盖 {n_grp} 个 MECE 组，"
        f"先划清 {n_out} 件不做的事",
        "这份报告回答什么、不回答什么、按什么口径？",
        [
            _r(f"报告只回答：{intent or '在该数据条件下能下的判断'}；"
               f"落点是「{top.title.split('：', 1)[-1]}」。", top_refs, "问题　"),
            _r("覆盖的维度：" + "、".join(f"{F.MECE_GROUPS[d['group']]}·{d['name']}"
                                    for d, _ in pairs) + "；"
               "每个维度只回答自己的问题，跨维度不互相替代。",
               top_refs, "范围　"),
            _r("不回答：没有数据支撑的预测、超出本期口径的外推、"
               "以及需要创始人签字的资金与合同事项。",
               top_refs, "边界　"),
        ],
        top_refs,
        table=_table("问题定义（回答 / 不回答）", ["模块", "回答的问题", "不回答的问题"],
                     [["M1", "口径与边界", "超出数据的预测"],
                      ["M3", "各维度判断", "跨维度替代"],
                      ["M5", "动作与验收", "资金与合同拍板"]]),
        boundary="本节只定义问题与边界，不给结论；结论在后文各维度分别给。",
        assumptions=[float(len(pairs)), float(len({d["group"] for d, _ in pairs}))]))

    # ---------------- M2 数据采集与校验 ----------------
    gs = F.grade_stats(ctx.desk)
    pack = getattr(ctx.desk, "pack", None) or {}
    n_src = _n(c, "来源数", len(pack.get("sources") or []), "个")
    n_fact = _n(c, "事实条数", int(gs.get("total") or 0), "条")
    n_a = _n(c, "A级条数", int((gs.get("counts") or {}).get("A") or 0), "条")
    n_b = _n(c, "B级条数", int((gs.get("counts") or {}).get("B") or 0), "条")
    n_c = _n(c, "C级条数", int((gs.get("counts") or {}).get("C") or 0), "条")
    n_d = _n(c, "D级条数", int((gs.get("counts") or {}).get("D") or 0), "条")
    a_share = round(float(gs.get("a_share") or 0), 1)
    n_a_share = _n(c, "A级占比", a_share, "%", digits=1)
    n_chk = _n(c, "交叉验证组数", sum(1 for _, f in pairs
                                if (getattr(f, "meta", None) or {}).get("claim")
                                and (_cl(f).table or _cl(f).chart)), "组")
    secs.append(_sec(
        f"数据采集与校验：{n_src} 个来源、{n_fact} 条事实（A 级 {n_a} 条、{a_share:.1f}%），"
        f"{n_chk} 组交叉验证",
        "数据从哪来、凭什么信、能不能互证？",
        [
            _r(f"来源 {n_src} 个、事实 {n_fact} 条；等级分布 A {n_a} 条、B {n_b} 条、"
               f"C {n_c} 条、D {n_d} 条。A 级占比 {a_share:.1f}%，"
               "C/D 级只做量级判断，已单列假设表。",
               _ids(n_src, n_fact, n_a, n_b, n_c, n_d, n_a_share), "来源　"),
            _r(f"交叉验证 {n_chk} 组：每个维度至少一张表或一张图可回溯，"
               "规模、增长、单位经济之间互相对齐，不做单点结论。",
               _ids(n_chk), "校验　"),
            _r("缺口不藏：没有一手价格、没有官方细分口径的部分，"
               "在后文风险节列出「缺什么→影响哪条结论→怎么补」。",
               _ids(n_fact, n_c), "缺口　"),
        ],
        _ids(n_src, n_fact, n_a, n_b, n_c, n_d, n_a_share, n_chk),
        table=_table("来源与可信度", ["等级", "条数", "使用规则"],
                     [["A", str(n_a.value), "可直接引用，写全口径/期次"],
                      ["B", str(n_b.value), "注明机构与年份，不跨机构相加"],
                      ["C", str(n_c.value), "只做量级判断，不与 A 混算"],
                      ["D", str(n_d.value), "进假设表，给敏感性"]]),
        boundary="等级按来源类型判定；同一数字多来源冲突时取低等级并在风险节说明。"))

    # ---------------- M3 结构化逻辑推导 ----------------
    for d, f in pairs:
        cl = _cl(f)
        if cl is not None:
            sec = _claim_section(cl, getattr(f, "question", ""))
            sec["title"] = f"{F.MECE_GROUPS[d['group']]}｜{sec['title']}"
            sec["question"] = d["question"]
            if not sec.get("boundary"):
                sec["boundary"] = getattr(cl, "boundary", "") or getattr(f, "boundary", "")
            _ensure_chain(sec, cl, d)
            secs.append(sec)
        else:
            refs = _refs_of(f)
            secs.append(_sec(
                f"{F.MECE_GROUPS[d['group']]}｜{f.title}",
                d["question"],
                [_r(getattr(f, "title", ""), refs, "判断　"),
                 _r(getattr(f, "so_what", "") or "该维度已产出可复算结论，落点见动作节。",
                    refs, "落点　")],
                refs,
                boundary=getattr(f, "boundary", "")))

    # ---------------- M4 风险与局限 ----------------
    cov = findings.get("coverage") or findings.get("cheese_coverage")
    risks: List[List[str]] = []
    for d, f in pairs:
        cl = _cl(f)
        fals = getattr(cl, "falsifier", "") if cl is not None else ""
        if fals:
            risks.append([d["name"], "结论反向", fals, "按停止条件回退"])
    if cov is not None:
        cl = _cl(cov)
        detail = "；".join(x.get("text", "") for x in (getattr(cl, "detail", None) or [])[:2])
        risks.append(["数据缺口", "补数前", detail[:120] or "关键口径缺失", "先补一手数据再重算"])
    n_risk = _n(c, "风险项数", len(risks), "项")
    n_fals = _n(c, "证伪条件数", sum(1 for _, f in pairs
                              if _cl(f) is not None and getattr(_cl(f), "falsifier", "")), "条")
    n_assum = _n(c, "待校准假设数", len(getattr(ctx.desk, "assumptions", None) or []), "条")
    risk_refs = _ids(n_risk, n_fals, n_assum)
    for _, f in pairs:
        risk_refs += _refs_of(f)
    if cov is not None:
        risk_refs += _refs_of(cov)
    secs.append(_sec(
        f"风险与局限：{n_risk} 项风险、{n_fals} 条证伪条件、{n_assum} 条假设待校准",
        "哪些结论现在不能下、什么会推翻它？",
        [
            _r(f"风险 {n_risk} 项按「概率×影响」排序：数据缺口影响最大，"
               "它不改变方向，但改变幅度；方向类结论可以发，金额类结论要等补数。",
               _ids(n_risk), "排序　"),
            _r(f"{n_fals} 条证伪条件已经写进各维度：原料涨幅、渠道扣点、单品类同比偏离，"
               "任一触发即按停止条件回退，不追加投入。",
               _ids(n_fals), "证伪　"),
            _r(f"{n_assum} 条假设全部是 C/D 级，已单列；假设每变 1 个单位，"
               "结论按敏感度重算，不沿用原值。",
               _ids(n_assum), "假设　"),
        ],
        risk_refs,
        table=_table("风险与局限", ["风险", "触发", "影响", "应对"],
                     risks[:6] or [["数据缺口", "补数前", "金额类结论", "补一手数据"]]),
        boundary="风险节列出的是「不能下的结论」，不是「可能发生的事」；两者不混写。"))

    # ---------------- M5 可落地结论 ----------------
    acts: List[Dict[str, str]] = []
    for d, f in pairs[:5]:
        cl = _cl(f)
        do = (getattr(cl, "implication", "") if cl is not None else "")
        do = do or getattr(f, "so_what", "") or f.title
        stop = (getattr(cl, "falsifier", "") if cl is not None else "") \
            or "该维度核心指标反向连续两期"
        acts.append({"do": do, "owner": "业务负责人", "when": "T+4 周",
                     "accept": f"{d['name']}指标达到报告阈值",
                     "stop": stop, "refs": ",".join(_refs_of(f)[:4])})
    n_act = _n(c, "动作数", len(acts), "条")
    n_stop = _n(c, "停止条件数", len(acts), "条")
    no_list = ["不在本期新建产能", "不为单一品类新建冷链", "不做全品类自营"]
    n_no = _n(c, "不做事项数", len(no_list), "项")
    act_refs = _ids(n_act, n_stop, n_no)
    for _, f in pairs:
        act_refs += _refs_of(f)
    secs.append(_sec(
        f"结论与动作：{n_act} 条动作、{n_stop} 条停止条件、{n_no} 件现在不做",
        "做什么、谁做、什么算做完、什么时候停？",
        [
            _r(f"{n_act} 条动作按「依赖顺序」排：先补数据与锁成本，再谈扩量；"
               "每条动作都有 owner、时点与验收口，缺一项不进清单。",
               _ids(n_act, n_stop), "判断　"),
            _r("每段只允许一个目标：本期先把方向类结论转成可验收指标，"
               "金额类动作等补数后再签。",
               _ids(n_act), "节奏　"),
            _r(f"现在不做 {n_no} 件事：" + "、".join(no_list) +
               "；不做的理由写在这里，避免下一轮重复讨论。",
               _ids(n_no), "不做　"),
        ],
        act_refs,
        table=_table("动作与验收", ["动作", "owner", "时点", "验收口", "停止条件"],
                     [[a["do"][:60], a["owner"], a["when"], a["accept"], a["stop"][:60]]
                      for a in acts[:5]]),
        boundary="动作清单是决策建议，涉及资金与合同的条款按公司治理需创始人签字。"))

    return secs


FRAMES: Dict[str, Any] = {"analysis": build_analysis}


def build(thesis: str, ctx, findings: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    fn = FRAMES.get(thesis)
    if not fn:
        return None
    try:
        return fn(ctx, findings)
    except Exception:  # noqa: BLE001
        return None
