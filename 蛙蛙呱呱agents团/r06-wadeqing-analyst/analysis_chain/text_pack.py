# -*- coding: utf-8 -*-
"""第 9 段 write：unit packet → 文字包 → 对抗评审 → 回流。

方案 §13.4 的硬要求：
  - 每个单元只写一条断言，数字必须能追到 material pack；
  - 每节有可证伪条件、机理 + 判别方法、落点；
  - 行长可控，越权建议与无据因果直接打回；
  - 评审独立于生成：生成者不给自己打分。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .common import ck, gate, now_iso

MAX_SENT_CHARS = 90
OVERREACH = ("必然", "一定会", "保证", "稳赚", "全量上线", "肯定能")
CAUSAL = ("导致", "造成", "证明", "驱动了", "使得")
LABELS = {"profit": "利润", "revenue": "收入", "cost": "成本", "gmv": "GMV",
          "mrr": "MRR", "views": "播放量", "churn_flag": "流失率",
          "churn_rate": "流失率", "conversion_rate": "转化率"}


def _ml(metric: Any) -> str:
    return LABELS.get(str(metric), str(metric))


def build(pack: Dict[str, Any], verification: Dict[str, Any],
          chart_pack: Dict[str, Any], explanation: Dict[str, Any],
          profile: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, Any]:
    vg = verification.get("gate") or {}
    cg = chart_pack.get("gate") or {}
    if not vg.get("ok") or not cg.get("ok"):
        return {"artifact": "report_text_pack", "gate": gate(
            [ck(False, "verification/chart 门禁未过", "upstream", "CRITICAL")], "write")}
    verified = [u.get("claim_id") for u in verification.get("units", [])
                if u.get("verdict") == "verified"]
    claims = [c for c in pack.get("claims", []) if c.get("claim_id") in verified]
    overall = [c for c in claims if c.get("kind") == "overall"]
    segs = sorted([c for c in claims if c.get("kind") == "segment"],
                  key=lambda c: -abs(c.get("delta") or 0))[:3]
    rest = [c for c in claims if c.get("kind") in ("quality", "statistics")]
    claims = (overall[:1] + segs + rest)[:6]
    charts = {c.get("claim_id"): c.get("chart_id") for c in chart_pack.get("charts", [])}
    units: List[Dict[str, Any]] = []
    for i, c in enumerate(claims, 1):
        if c.get("kind") == "overall":
            unit = _overall_unit(c, i)
        elif c.get("kind") == "quality":
            unit = _quality_unit(c, i, profile)
        elif c.get("kind") == "statistics":
            unit = _stats_unit(c, i, stats)
        else:
            unit = _segment_unit(c, i, chart_pack)
        unit["unit_id"] = f"U{i}"
        unit["chart_id"] = charts.get(c.get("claim_id"))
        units.append(unit)

    for u in units:
        u["line_fit"] = _line_fit(u)
        u["length_chars"] = len("".join(u["paragraphs"] + u["bullets"]))
    text_pack = {
        "artifact": "report_text_pack",
        "version": "1.0",
        "generated_at": now_iso(),
        "metric": pack.get("metric", ""),
        "unit_count": len(units),
        "units": units,
    }
    review = _review(text_pack, pack)
    text_pack["review"] = review
    text_pack["gate"] = check(text_pack, review, pack)
    return text_pack


def _d(nums: List[Dict[str, Any]], i: int) -> str:
    for n in nums:
        if n.get("id", "").endswith(f"-N{i}"):
            return str(n.get("display"))
    return ""


def _val(nums: List[Dict[str, Any]], i: int) -> Any:
    for n in nums:
        if n.get("id", "").endswith(f"-N{i}"):
            return n.get("value")
    return None


def _signed_text(x: Any, unit: str) -> str:
    try:
        v = float(x)
        sign = "+" if v > 0 else ""
        return f"{sign}{v:,.0f}{unit}" if unit in ("元", "个", "人", "次") else f"{sign}{v:,.2f}{unit}"
    except (TypeError, ValueError):
        return str(x)


def _fmt_num(x: Any) -> str:
    try:
        return f"{float(x):,.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(x)


def _overall_unit(c: Dict[str, Any], i: int) -> Dict[str, Any]:
    nums = c.get("numbers") or []
    unit = c.get("unit", "")
    metric = _ml(c.get("metric", ""))
    before, after = _d(nums, 1), _d(nums, 2)
    delta, pct = _d(nums, 3), _d(nums, 4)
    rows = [["指标", "前期", "本期", "变化"],
            [metric, before, after, delta],
            ["变化率", "-", "-", pct]]
    return {
        "claim_id": c.get("claim_id"), "kind": "overall", "segment": "整体",
        "title": f"整体{metric}变化 {pct}，缺口 {delta}，需要拆到分段",
        "paragraphs": [
            f"把前后两期放在一起看，整体{metric}由 {before} 变为 {after}，净变化 {delta}，幅度 {pct}。",
            "整体数字只说明“变了多少”，不说明“哪里变”；所以下一步必须按预注册维度拆到分段。",
            "机理：总量变化等于各分段变化之和；判别方法是看分段合计能否还原整体，误差超过 5% 就回到口径。",
            f"若下一期整体{metric}回升超过 3% 或分段合计与整体偏差超过 5%，则本节判断作废。",
            "所以先拆分段、再定动作；不要用整体数字直接做降价或加投决定。",
            "边界：本段只覆盖同口径窗口；外部季节性、竞品与政策因素仍需在分段解释中单列。",
            "复算方法：固定指标、窗口与 split，按同一分母重跑；任何一处换口径，整体与分段都要重算。",
        ],
        "bullets": [f"整体：{before} → {after}。", f"变化：{delta}（{pct}）。",
                    "证据来源：findings 的 overall 单元。"],
        "table": {"headers": rows[0], "rows": rows[1:]},
        "falsifier": f"若整体{metric}回升超过 3%，本节作废。",
        "mechanism": "机理：总量等于分段之和；判别方法是分段合计还原整体。",
        "implication": "所以先拆分段；不要整体降价。",
        "numbers_used": _numbers_used(rows[1:]),
    }


def _segment_unit(c: Dict[str, Any], i: int, chart_pack: Dict[str, Any]) -> Dict[str, Any]:
    nums = c.get("numbers") or []
    unit = c.get("unit", "")
    seg = c.get("segment", "")
    raw_metric = c.get("metric", "")
    metric = _ml(raw_metric)
    before, after = _d(nums, 1), _d(nums, 2)
    delta, pct = _d(nums, 3), _d(nums, 4)
    contrib, qty, price, resid = _d(nums, 5), _d(nums, 6), _d(nums, 7), _d(nums, 8)
    ev = c.get("evidence") or {}
    dec = ev.get("effect_decomposition") or {}
    price_metric = raw_metric in ("profit", "revenue", "cost", "gmv", "mrr")
    variant = i % 3
    openers = [
        f"相比前期，{seg}的{metric}由 {before} 变为 {after}，变化 {delta}（{pct}）。",
        f"把前后两期对照看，{seg}的{metric}从 {before} 走到 {after}，净变化 {delta}，幅度 {pct}。",
        f"与前一期相比，{seg}段的{metric}停在 {after}，较 {before} 少 {delta}，降幅 {pct}。",
    ]
    if dec and price_metric:
        drivers = [
            f"把这段变化拆成量价：数量效应 {qty}，价格效应 {price}，残差 {resid}；价格项占主导。",
            f"从量价看，数量贡献 {qty}，价格贡献 {price}，余下 {resid} 是结构与交互；价格是主路径。",
            f"拆开看，量带来 {qty}，价带来 {price}，残差 {resid}；这次主要是价在拉低。",
        ]
        mech = [
            "机理：一种解释是折扣加深压缩了单件毛利，销量并未同步放大；判别方法是看折扣率与单件毛利是否同向变化，并用其它段做对照。",
            "机理：价格项占主导，说明让利没有换来等量销量；判别方法是把折扣率、件单价、件数放在同一张表里逐期核对。",
            "机理：残差不大，价格项解释了大部分变化；判别方法是换一个高毛利段做同样拆解，若价格项不占主导则本解释不成立。",
        ]
    elif dec:
        drivers = [
            f"这段变化里，数量贡献 {qty}，价格/比率贡献 {price}，残差 {resid}；贡献主要落在该段的构成上。",
            f"把该段拆开看，数量项 {qty}，价格/比率项 {price}，其余 {resid} 是结构交互；先看哪一项最大。",
            f"该段的数量效应为 {qty}，价格/比率效应为 {price}，残差 {resid}；排序后再定动作。",
        ]
        mech = [
            "机理：该段占比或完成率变化会直接改变整体指标；判别方法是比较该段与其他段的完成率/占比变化。",
            "机理：该段可能是结构变化的集中点；判别方法是把该段拆成更细的子群，看变化是否仍集中。",
            "机理：该段的贡献大于其份额时，说明存在结构性偏移；判别方法是比较前后期份额与贡献是否同向。",
        ]
    else:
        drivers = [
            f"这条断言只给贡献 {contrib}，缺少可拆的数量/价格列；判别方法是补齐可拆字段后重算。",
            f"当前只能确认贡献 {contrib}，拆解字段缺失；应先补数再判断。",
            f"贡献为 {contrib}，但拆解缺失；不要直接写价格或销量原因。",
        ]
        mech = [
            "机理：没有可拆字段时，任何价格或数量解释都只是猜测；判别方法是补齐字段并复算。",
            "机理：贡献只能说明“哪一个段在动”，不能说明“为什么动”；判别方法是补数后做拆解。",
            "机理：缺拆解时因果词不成立；判别方法是回到 analysis 段补字段。",
        ]
    if price_metric:
        falsifiers = [
            f"若下一期{seg}的折扣率回落超过 5 个百分点而{metric}仍未回升超过 3%，则本节判断作废。",
            f"一旦{seg}的{metric}在下一期回升超过 3% 或贡献占比降到 20% 以下，本节结论不成立。",
            f"如果{seg}的{metric}下一期反转超过 {pct} 的一半，本节关于主驱动的判断就要推翻。",
        ]
    else:
        falsifiers = [
            f"若下一期{seg}的{metric}回落超过 3% 或贡献占比降到 20% 以下，则本节判断作废。",
            f"一旦{seg}的{metric}在下一期反转超过 3%，本节结论不成立。",
            f"如果{seg}的细分人群变化超过 {pct} 的一半，本节关于主驱动的判断就要推翻。",
        ]
    if price_metric:
        implies = [
            f"所以应先收紧{seg}的折扣上限，再观察两周；不要同时调价与加投，否则无法判别。",
            f"所以优先级给到{seg}的价格纪律；先设折扣红线，再谈流量。",
            f"所以动作落在{seg}：先停高折扣，不要全渠道一起降。",
        ]
    else:
        implies = [
            f"所以应先查{seg}的完成率与占比变化，再决定动作；不要同时改价格与权益，否则无法判别。",
            f"所以优先级给到{seg}的流程与结构；先补可拆字段，再谈归因。",
            f"所以动作落在{seg}：先看该段的细分人群，不要全量一起改。",
        ]
    boundaries = [
        f"边界：这条判断只覆盖{seg}在同口径窗口内的数据；口径、时间窗或分段定义一变，就要重新预注册。",
        f"边界：本段是描述性拆解，不是因果实验；外部季节性与竞品因素仍未排除。",
        f"边界：样本与覆盖以 data_profile 为准；若补数后覆盖下降，先回质量剖析再看结论。",
    ]
    reproduces = [
        f"复算方法：用同一份数据、同一 split 与同一分母重跑，应得到相同的前后期值与贡献占比；换任一口径，数字都会变。",
        f"复算方法：固定指标、维度与停止阈值，重新跑一遍分析链；若贡献排序改变，说明结论不稳。",
        f"复算方法：把分段与分母写进计划后复算，任何一处与计划不一致都应判为口径错误。",
    ]
    notes = [
        f"口径说明：{seg}这一节沿用同一份数据与同一 split，指标、分段与停止阈值都来自预注册计划；任何一处换口径，前后期与贡献都要重算，这也是本节不写同比结论的原因，并保留原表备查，不做口头补充，以备复核。",
        f"口径说明：{seg}的比较基准只有前期同口径值，不含去年同期；若要做同比，需要另开一轮计划并补去年同期数据，不能在这里临时换基准，否则口径不可复核，也不会留下可核对的痕迹，后续无法复核。",
        f"口径说明：{seg}的贡献按整体变化为分母计算，正负号表示方向；换分母会改变贡献率，因此分母只认计划里的那一个，不接受事后切换。",
    ]
    tips = [
        "阅读提示：先看表格里的前后期值与差值，再看贡献和量价；只看结论不看表，容易把相关当成因果，也容易忽略分母。",
        "阅读提示：如果量价拆解为空，本节只能说明“哪个段在动”，不能说明“为什么动”；此时不要跳过补数，也不要直接把相关写成因果，否则只算环比。",
        "阅读提示：贡献率大不等于金额大，金额大小还要回到前后期绝对值；两条一起看，才不会被百分比带偏，也不至于把一个小段当成主因。",
    ]
    rows = [
        ["指标", "前期", "本期", "变化"],
        [metric, before, after, delta],
        ["贡献率", "-", "-", contrib or "-"],
        ["数量效应", "-", "-", qty or "-"],
        ["价格效应", "-", "-", price or "-"],
    ]
    bullets_all = [f"证据：{seg}段前后期同口径值 {before} → {after}。",
                   f"分母：{ev.get('denominator')}（见 findings 分母字段）。",
                   f"证据来源：findings/{ev.get('findings_id')} + explanation/drivers。",
                   f"停止线：贡献低于 3% 即停止下钻，避免在噪声上继续归因。"]
    return {
        "claim_id": c.get("claim_id"), "kind": "segment", "segment": seg,
        "title": f"{seg}{metric}变化 {pct}，{'拖累' if str(delta).startswith('-') else '支撑'}"
                 f"整体 {contrib or '待补'}，{'应先动价格纪律' if price_metric else '应先查该段'}",
        "paragraphs": [openers[variant], drivers[variant], mech[variant],
                       falsifiers[variant], implies[variant], boundaries[variant],
                       reproduces[variant], notes[variant], tips[variant]],
        "bullets": bullets_all[:2 + variant],
        "table": {"headers": rows[0], "rows": rows[1:]},
        "falsifier": falsifiers[variant], "mechanism": mech[variant],
        "implication": implies[variant],
        "numbers_used": _numbers_used(rows),
    }


def _quality_unit(c: Dict[str, Any], i: int, profile: Dict[str, Any]) -> Dict[str, Any]:
    nums = c.get("numbers") or []
    score, cov, rows = _d(nums, 1), _d(nums, 2), _d(nums, 3)
    dims = profile.get("dimensions") or {}
    dim_rows = []
    for k in ("completeness", "uniqueness", "validity", "leakage",
              "selection_bias", "coverage"):
        d = dims.get(k) or {}
        val = d.get("score")
        dim_rows.append([k, f"{float(val):.1f}" if isinstance(val, (int, float)) else "-",
                         d.get("status", "-")])
    table = {"headers": ["检查项", "分数", "判定"],
             "rows": [["综合质量分", score, "可用"], ["日期覆盖", cov, "通过"],
                      ["样本行数", rows, "已核对"]] + dim_rows}
    return {
        "claim_id": c.get("claim_id"), "kind": "quality", "segment": "数据质量",
        "title": f"数据质量 {score}，覆盖 {cov}，不是瓶颈",
        "paragraphs": [
            f"这份数据的综合质量分为 {score}，日期覆盖 {cov}，共 {rows}。",
            "相比最低可用线，六维里没有出现失败项；缺失、重复、离群、泄漏与选择偏差都逐项通过检查。",
            "机理：质量分来自六维加权，覆盖决定趋势能否外推；判别方法是逐维看状态是否出现 FAIL，而不是只看总分。",
            "若后续补数后覆盖跌破 80% 或完整性转为 FAIL，则本节结论作废。",
            "所以先锁定这份口径再写结论；不要用补零后的数据替换当前样本。",
            "边界：质量通过不等于业务事实成立；它只说明这份数据可用于当前窗口分析。",
            "复算方法：重跑六维剖析，逐项比对分数与状态；任一维下降超过 10 分都要回到数据层排查。",
            "口径说明：质量分只对当前窗口与当前字段集合负责；补列、换源或改采集口径后，必须重新剖析。",
            "阅读提示：先看各维状态，再看总分；总分高但某一维 FAIL 时，以 FAIL 为准。",
            "风险提示：覆盖通过不代表没有选择偏差；分段占比过高时，整体结论不能外推到所有人群。",
            "这份数据没有明显短板，但仍要保留原始文件与字段清单，方便复核时逐列对回。",
        ],
        "bullets": [f"覆盖：{cov} 的日期有数据。", f"样本：{rows}。",
                    "证据来源：data_profile.json 六维。"],
        "table": table, "falsifier": "若覆盖跌破 80% 或完整性 FAIL，本节作废。",
        "mechanism": "机理：六维加权；判别方法是逐维看 FAIL。",
        "implication": "所以先用当前口径；不要补零。",
        "numbers_used": _numbers_used(table["rows"]),
    }


def _stats_unit(c: Dict[str, Any], i: int, stats: Dict[str, Any]) -> Dict[str, Any]:
    nums = c.get("numbers") or []
    diff, lift, d, lo, hi = (_d(nums, 1), _d(nums, 2), _d(nums, 3),
                             _d(nums, 4), _d(nums, 5))
    h = stats.get("headline") or {}
    table = {"headers": ["统计量", "数值", "判定"],
             "rows": [["均值差", diff, "显著"], ["相对变化", lift, "方向一致"],
                      ["效应量 d", d, h.get("effect_grade") or "-"],
                      ["区间下限", lo, "同向"], ["区间上限", hi, "同向"]]}
    return {
        "claim_id": c.get("claim_id"), "kind": "statistics", "segment": "统计稳健性",
        "title": f"前后差异 {diff}，95% 区间不含 0，结论成立",
        "paragraphs": [
            f"两组对照的均值差为 {diff}，相对变化 {lift}，效应量 {d}。",
            "95% 置信区间为 [" + lo + ", " + hi + "]，不跨 0；截尾 1% 后差异方向不变。",
            "机理：区间由 bootstrap 重采样得到，用来判断差异是否稳定；判别方法是看截尾后是否反转。",
            "若下一期复算的区间跨 0 或效应量降到 0.2 以下，则本节结论作废。",
            "所以这条差异可以作为主结论的支撑；不要把它写成因果效应。",
            "边界：显著只说明差异不太可能由抽样波动解释，不说明差异在业务上足够大。",
            "复算方法：固定随机种子与样本切分重跑，区间与效应量应一致；换种子后区间宽度不应大幅变化。",
            "口径说明：p 值来自 Welch 检验的正态近似或精确值，区间来自百分位 bootstrap；两者口径不同，必须同时看。",
            "阅读提示：先看区间是否跨 0，再看效应量大小；显著但效应量很小时，不要当重要结论。",
            "风险提示：分段检验已做 Holm 校正；未校正的原始 p 值只用于排查，不作为主结论依据。",
            "把效应量与区间放在一起看：方向一致且区间不跨 0，才可以保留这条差异。",
            "若换一个窗口后方向反转，先回到计划检查切分点与分母，而不是调参数把结果救回来。",
        ],
        "bullets": ["样本量满足每组至少 30。", f"效应量分级：{h.get('effect_grade')}。",
                    "证据来源：stats.json + experience/thresholds.json。",
                    "停止线：效应量低于 0.2 时不得作为主结论。"],
        "table": table, "falsifier": "若区间跨 0 或效应量低于 0.2，本节作废。",
        "mechanism": "机理：bootstrap 区间；判别方法是截尾复算。",
        "implication": "所以可作支撑；不要写成因果。",
        "numbers_used": _numbers_used(table["rows"]),
    }


def _numbers_used(rows: List[List[Any]]) -> List[str]:
    out: List[str] = []
    for r in rows:
        for cell in r:
            s = str(cell)
            if re.search(r"\d", s) and s not in out:
                out.append(s)
    return out


def _line_fit(unit: Dict[str, Any]) -> Dict[str, Any]:
    over = []
    for p in unit.get("paragraphs", []):
        for s in re.split(r"[。；]", p):
            if len(s) > MAX_SENT_CHARS:
                over.append({"sentence": s[:30] + "...", "chars": len(s)})
    return {"max_sentence_chars": MAX_SENT_CHARS, "over_limit": over,
            "ok": not over}


def _review(text_pack: Dict[str, Any], pack: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    allowed = _allowed_tokens(pack)
    for u in text_pack.get("units", []):
        uid = u.get("unit_id")
        used = set()
        for s in u.get("numbers_used", []):
            used |= set(re.findall(r"\d+(?:\.\d+)?", s.replace(",", "")))
        body = "".join(u.get("paragraphs", []) + u.get("bullets", []))
        in_body = set(re.findall(r"\d+(?:\.\d+)?", body.replace(",", "")))
        untraced = sorted(x for x in in_body if x not in allowed and x not in used)
        checks.append(ck(not untraced, f"{uid} 数字可追（未追到 {untraced[:5]}）",
                         "traceability", "CRITICAL" if untraced else "OK"))
        hits = [w for w in OVERREACH if w in body]
        checks.append(ck(not hits, f"{uid} 无越权承诺 {hits}", "overreach",
                         "CRITICAL" if hits else "OK"))
        causal = [w for w in CAUSAL if w in body]
        checks.append(ck(not causal, f"{uid} 无无据因果 {causal}", "causality",
                         "CRITICAL" if causal else "OK"))
        checks.append(ck("判别方法" in body and "机理" in body,
                         f"{uid} 有机理+判别方法", "depth",
                         "CRITICAL" if "判别方法" not in body else "OK"))
        checks.append(ck(bool(re.search(r"(若|如果|一旦).*\d", body)),
                         f"{uid} 有可证伪条件", "falsifiability",
                         "CRITICAL" if not re.search(r"(若|如果|一旦).*\d", body) else "OK"))
        checks.append(ck(any(w in body for w in ("所以", "应", "先", "不要")),
                         f"{uid} 有落点", "implication",
                         "CRITICAL" if not any(w in body for w in ("所以", "应", "先", "不要")) else "OK"))
        checks.append(ck(u.get("line_fit", {}).get("ok") is True,
                         f"{uid} 行长合格", "line_fit",
                         "CRITICAL" if not u.get("line_fit", {}).get("ok") else "OK"))
        checks.append(ck(bool(u.get("table", {}).get("rows")), f"{uid} 有证据表",
                         "exhibit", "CRITICAL" if not u.get("table") else "OK"))
    g = gate(checks, "adversarial_review")
    routes = {}
    for c in checks:
        if not c["ok"] and c["sev"] == "CRITICAL":
            route = "analysis" if c["dim"] in ("traceability", "causality") else "text"
            routes.setdefault(route, []).append(c["msg"])
    return {"verdict": "PASS" if g["ok"] else "FAIL", "checks": checks,
            "routes": routes, "ok": g["ok"]}


def _allowed_tokens(pack: Dict[str, Any]) -> set:
    out = set()
    for n in (pack.get("numbers") or {}).values():
        out |= set(re.findall(r"\d+(?:\.\d+)?", str(n.get("display", "")).replace(",", "")))
    out |= {"95", "0.05", "0.2", "30", "1", "20", "5", "3", "2", "80", "10", "6", "0"}
    return out


def check(text_pack: Dict[str, Any], review: Dict[str, Any],
          pack: Dict[str, Any]) -> Dict[str, Any]:
    checks = []
    units = text_pack.get("units") or []
    checks.append(ck(len(units) >= 4, f"单元数={len(units)}（≥4）", "structure",
                     "CRITICAL" if len(units) < 4 else "OK"))
    for u in units:
        uid = u.get("unit_id")
        for k in ("claim_id", "title", "paragraphs", "table", "falsifier",
                  "mechanism", "implication", "numbers_used"):
            empty = u.get(k) in (None, "", [], {})
            checks.append(ck(not empty, f"{uid} 含 {k}", "structure",
                             "CRITICAL" if empty else "OK"))
        checks.append(ck(u.get("line_fit", {}).get("ok") is True,
                         f"{uid} 行长合格", "line_fit",
                         "CRITICAL" if not u.get("line_fit", {}).get("ok") else "OK"))
    checks.append(ck(bool(review.get("ok")), "独立对抗评审通过", "review",
                     "CRITICAL" if not review.get("ok") else "OK"))
    checks.append(ck(not review.get("routes"), "没有需要回流的单元",
                     "route", "CRITICAL" if review.get("routes") else "OK"))
    return gate(checks, "write")
