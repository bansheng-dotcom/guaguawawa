# -*- coding: utf-8 -*-
"""结论层：把技能结果压成 conclusion / caveats / status（报告层直接消费）。

原则：只从已有字段派生，不新增数字；没有把握的结论宁可不写。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _n(x, nd=2):
    try:
        return round(float(x), nd)
    except (TypeError, ValueError):
        return x


def _status(result: Dict[str, Any]) -> str:
    if result.get("ok") is False or result.get("error"):
        return "blocked"
    if result.get("warnings") or result.get("placebo_status") == "unavailable":
        return "warn"
    if result.get("status") in ("warn", "unavailable", "blocked"):
        return result["status"]
    return "ok"


def enrich(result: Dict[str, Any], skill: str, action: Optional[str] = None) -> Dict[str, Any]:
    """就地补充 conclusion/caveats/status；已存在则不覆盖。"""
    if not isinstance(result, dict):
        return result
    status = _status(result)
    conclusion = None
    caveats: List[str] = []

    key = skill if skill != "explore" else (action or "")
    try:
        if key == "quality":
            conclusion = f"数据质量 {_n(result.get('overall_score'), 1)}/10（{result.get('grade', '—')}），六维中 {sum(1 for v in (result.get('dimension_score') or {}).values() if v < 10)} 维未满分。"
            if result.get("violations"):
                caveats.append(f"{len(result['violations'])} 条规则被触发，见 violations")
            if (result.get("dimension_score") or {}).get("timeliness") == 0:
                caveats.append("及时性 0 分：最新数据超过 SLA，不能当日报用")
        elif key == "abtest":
            a = result.get("abtest", {})
            conclusion = f"{a.get('decision')}：lift {a.get('lift_pct')}%，p={_n(a.get('p_exact') or a.get('p_value_approx'), 4)}，SRM={a.get('srm_flag')}。"
            if a.get("srm_flag"):
                caveats.append("SRM 失配：结果不可采信，需重跑")
            if not a.get("significant"):
                caveats.append("主指标不显著，不能宣布成功")
        elif key == "did":
            d = result.get("did", {})
            conclusion = f"ATT {_n(d.get('att'), 0)}（t={d.get('t')}，p={_n(d.get('p'), 4)}）。"
            pt = (d.get("pretrend") or {})
            if pt.get("passed") is False:
                caveats.append("线性预趋势未通过，平行趋势存疑")
            js = ((result.get("event_study") or {}).get("pretrend_joint") or {})
            if js.get("p") is not None and js["p"] <= 0.1:
                caveats.append(f"事件研究 pre 联合检验 p={js['p']}，存在预趋势")
            if result.get("placebo", {}).get("p_perm") == 0.0:
                caveats.append("安慰剂通过（p=0），但仍只对观测混杂成立")
        elif key == "matched":
            m = result.get("matched", {})
            conclusion = f"PSM ATT {m.get('att')}（95% CI {m.get('ci95')}，质量 {m.get('quality', '—')}）。"
            if not m.get("balanced"):
                caveats.append(f"协变量未完全平衡（SMD {m.get('smd_after_max')}）")
            if m.get("n_matched", 0) < m.get("n_treat", 0) * 0.6:
                caveats.append("匹配覆盖不足，ATT 仅代表可匹配子样本")
        elif key == "rdd":
            r = result.get("rdd", {})
            conclusion = f"断点估计 {r.get('estimate')}（se {r.get('se')}）。"
            if r.get("placebo_status") == "unavailable":
                caveats.append(f"安慰剂不可用：{r.get('placebo_reason')}")
            if not r.get("robust"):
                caveats.append("robust=false，不能外推到其他断点")
        elif key == "elasticity":
            e = result.get("elasticity", {})
            conclusion = f"价格弹性 {e.get('elasticity')}（R² {e.get('r2')}，n={e.get('n')}）。"
            caveats.append("log-log 线性近似，不能外推到大幅调价")
        elif key == "regression":
            r = result.get("multivariate") or result.get("regression") or {}
            if result.get("multivariate"):
                names = [c.get("name") for c in r.get("coef", []) if c.get("name") != "const"]
                conclusion = f"{r.get('model')}：{', '.join(names)}，R²={r.get('r2') or r.get('pseudo_r2')}，n={r.get('n')}。"
            else:
                conclusion = f"一元 OLS：斜率 {r.get('slope')}，R²={r.get('r_squared')}。"
            if result.get("multivariate", {}).get("warnings"):
                caveats += result["multivariate"]["warnings"]
            caveats.append("回归系数是条件相关，不是因果")
        elif key == "ttest":
            t = result.get("welch_t", {})
            conclusion = f"均值差 {t.get('diff')}，p_exact={_n(t.get('p_exact'), 4)}，显著={t.get('significant')}。"
            caveats.append("只比较两组，未控混杂")
        elif key == "chi2":
            c = result.get("chi2", {})
            conclusion = f"χ²={c.get('chi2_statistic')}（df={c.get('df')}），p_exact={_n(c.get('p_exact'), 4)}，V={c.get('cramers_v')}。"
            caveats.append("期望频数<5 时卡方近似不可靠")
        elif key == "anova":
            a = result.get("anova", {})
            conclusion = f"F={a.get('f_statistic')}（p_exact={_n(a.get('p_exact'), 4)}），η²={a.get('eta_squared')}。"
            caveats.append("单因素，未控协变量")
        elif key == "funnel":
            st = result.get("stages", [])
            if st:
                conclusion = f"整体转化 {st[-1].get('conversion_overall')}（{st[0].get('count')} → {st[-1].get('count')}）。"
                caveats.append("累计到达口径，未去重跨设备")
        elif key == "metrics":
            conclusion = f"GMV {_n(result.get('gmv'), 0)}，AOV {result.get('aov')}，客户 {result.get('customer_count')}。"
        elif key == "rootcause":
            items = result.get("items") or result.get("segments") or []
            if items and isinstance(items[0], dict):
                top = items[0]
                conclusion = f"最大贡献：{top.get('segment')}（{top.get('share_pct') or top.get('contribution_pct')}%）。"
        elif key == "describe":
            d = (result.get("describe") or {})
            first = next((v for v in d.values() if isinstance(v, dict)), {})
            if first:
                conclusion = f"均值 {first.get('mean')}，中位数 {first.get('median')}，偏度 {first.get('skew')}。"
        elif key == "selfmedia":
            conclusion = f"看板状态 {result.get('status')}，{result.get('platform_count')} 平台。"
            if result.get("status") == "partial":
                caveats.append("平台未覆盖全，不能当 ready 日报")
        elif key == "rfm":
            conclusion = f"{result.get('user_count', 0)} 个用户完成 RFM 打分。"
        elif key == "metrics":
            conclusion = f"GMV {_n(result.get('gmv'), 0)}，AOV {result.get('aov')}，客户 {result.get('customer_count')}。"
        elif key == "causal":
            e = (result.get("causal") or {}).get("estimate", {})
            conclusion = f"后门调整效应 {e.get('adjusted_effect')}（未调整 {e.get('unadjusted_effect')}）。"
            caveats.append("只调整观测到的混杂，未观测混杂无法消除")
        elif key == "scinlp":
            conclusion = f"{result.get('doc_count', 0)} 条文本、{result.get('token_count', 0)} 个词。"
            caveats.append("中文分词为空格/标点切分，需 jieba/spaCy")
        elif key == "segment":
            conclusion = f"{result.get('k')} 群，silhouette={result.get('silhouette')}。"
        elif key == "viz":
            if (result.get("subject") or result.get("chart_type")):
                conclusion = f"图表规格 {result.get('chart_type')} 校验{'通过' if result.get('ok') else '未通过'}。"
            else:
                conclusion = "图表规格校验完成。" if result.get("ok") else "图表规格校验未通过。"
        elif key == "power":
            pw = result.get("power") or {}
            if pw.get("required_n_per_group"):
                conclusion = f"每组需 {pw['required_n_per_group']} 个样本（power={pw.get('target_power')}）。"
            elif pw.get("mde_solvable"):
                conclusion = f"给定样本下 MDE={pw['mde_solvable']}。"
        elif key == "time_series":
            conclusion = f"{result.get('n', 0)} 个时点，季节性强度 {result.get('seasonality_strength')}。"
        elif key == "cohort":
            conclusion = f"{len(result.get('periods') or [])} 个 cohort 已计算。"
        elif key == "semantics":
            if action == "tree":
                conclusion = f"指标树 {result.get('metric_count', 0)} 个指标。"
            elif action == "reconcile":
                conclusion = f"对账 {result.get('status')}（差 {_n(result.get('pct_diff'), 3)}%）。"
            elif action == "validate":
                conclusion = "语义模型校验通过。" if result.get("ok") else "语义模型校验未通过。"
            else:
                conclusion = "语义技能执行完成。"
    except Exception:  # noqa: BLE001  结论层不许挡住出数
        conclusion = None

    if conclusion and not result.get("conclusion"):
        result["conclusion"] = conclusion
    if caveats:
        result.setdefault("caveats", caveats)
    result.setdefault("status", status)
    return result
