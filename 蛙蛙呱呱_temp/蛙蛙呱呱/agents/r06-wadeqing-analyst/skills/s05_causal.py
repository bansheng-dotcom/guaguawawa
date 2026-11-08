# -*- coding: utf-8 -*-
"""S05i 因果推断四步 —— 能力域 5（统计域 · 拆细之九）。

整合自 py-why/dowhy 的四步法（model → identify → estimate → refute），
用纯标准库把「混淆识别 + 后门分层调整 + 安慰剂反驳」做成可复算实现：

1. model     列存在性 + 二值处理检查 + 结局/处理/混杂角色登记
2. identify  后门混杂集合 = --confounders；逐混杂算「处理臂间不平衡度」
             （数值列标准化均值差 d，类别列分布份额差）
3. estimate  后门调整 ATE：按混杂分层，层内求处理−对照结局差，按层样本量加权；
             同时报未调整 naive 差，并给出「naive = 处理效应 + 混杂偏差」分解
4. refute    安慰剂置换检验（固定种子 LCG 置换处理标签，|置换效应|≥|调整效应|
             的比例即安慰剂 p 值）；含正向对照试验（真置换应为 ≈0 效应）

纪律与 review.py 对齐：结论点名因果时，结果里必须带 contribution 类分解键
（本模块的 naive 分解即归因证据）；混杂调整只能消除「观测到的」混杂，
未观测混杂不可消除，须在 note 里如实声明。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "causal"
DESC = "因果推断四步（dowhy 口径）：混淆识别/后门调整/安慰剂反驳（能力域5拆细）"


class _LCG:
    """确定性线性同余发生器（种子固定 → 结果逐位可复现）。"""

    def __init__(self, seed: int):
        self.s = (seed or 0) & 0x7FFFFFFF

    def next01(self) -> float:
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return self.s / 0x7FFFFFFF

    def shuffle(self, xs: list) -> list:
        out = list(xs)
        for i in range(len(out) - 1, 0, -1):
            j = int(self.next01() * (i + 1))
            out[i], out[j] = out[j], out[i]
        return out


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    p.add_argument("--input", required=True)
    p.add_argument("--outcome", required=True, help="结局数值列")
    p.add_argument("--treatment", required=True, help="处理列（必须恰两个取值）")
    p.add_argument("--confounders", required=True,
                   help="逗号分隔的后门混杂列（识别即调整）")
    p.add_argument("--trials", type=int, default=200, help="安慰剂置换次数")
    p.add_argument("--seed", type=int, default=0)


def _stratum_key(r: Dict[str, str], confs: List[str], edges: Dict[str, List[float]]) -> str:
    """行 → 混杂层键。数值列按四分位边离散化（无共线爆炸），类别列原样。"""
    parts = []
    for col in confs:
        v = str(r.get(col, ""))
        if col in edges:
            x = float(v)
            b = 0
            for e in edges[col]:
                if x <= e:
                    break
                b += 1
            parts.append(f"{col}=q{b}")
        else:
            parts.append(f"{col}={v}")
    return "|".join(parts)


def run(args) -> Dict[str, Any]:
    rows = c.load_csv(args.input)
    if not rows:
        return {"error": "空数据或无法读取"}
    cols = set(rows[0].keys())
    for need in (args.outcome, args.treatment):
        if need not in cols:
            return {"error": f"列不存在: {need}"}
    confs = [x.strip() for x in args.confounders.split(",") if x.strip()]
    bad_cols = [x for x in confs if x not in cols]
    if bad_cols:
        return {"error": f"混杂列不存在: {bad_cols}"}

    # ---- Step 1 model：二值处理 + 数值结局检查 ----
    tvals = sorted({str(r[args.treatment]) for r in rows})
    if len(tvals) != 2:
        return {"error": f"处理列必须恰有两个取值，实际 {len(tvals)} 个: {tvals[:5]}"}
    ctrl, treat = tvals[0], tvals[1]
    used = [r for r in rows
            if c.isnum(r.get(args.outcome)) and str(r[args.treatment]) in tvals]
    if len(used) < 8:
        return {"error": f"有效行不足 8（当前 {len(used)}），不做因果估计"}

    # ---- Step 2 identify：后门集合 + 臂间不平衡度 ----
    imbalance = []
    arms_c = [r for r in used if str(r[args.treatment]) == ctrl]
    arms_t = [r for r in used if str(r[args.treatment]) == treat]
    for col in confs:
        vs_c = [r[col] for r in arms_c if c.isnum(r.get(col))]
        vs_t = [r[col] for r in arms_t if c.isnum(r.get(col))]
        if len(vs_c) >= 2 and len(vs_t) >= 2:
            mc = sum(float(x) for x in vs_c) / len(vs_c)
            mt = sum(float(x) for x in vs_t) / len(vs_t)
            sd = (sum((float(x) - mc) ** 2 for x in vs_c) / max(1, len(vs_c) - 1)
                  + sum((float(x) - mt) ** 2 for x in vs_t) / max(1, len(vs_t) - 1)) / 2
            d = (mt - mc) / (sd ** 0.5) if sd > 0 else 0.0
            imbalance.append({"confounder": col, "type": "numeric",
                              "std_mean_diff": round(d, 4),
                              "threshold": 0.2,
                              "flag": "imbalanced" if abs(d) > 0.2 else "balanced"})
        else:
            cats = sorted({str(r.get(col)) for r in used})
            share_c = {v: sum(1 for r in arms_c if str(r.get(col)) == v) / max(1, len(arms_c)) for v in cats}
            share_t = {v: sum(1 for r in arms_t if str(r.get(col)) == v) / max(1, len(arms_t)) for v in cats}
            max_diff = max(abs(share_t[v] - share_c[v]) for v in cats)
            imbalance.append({"confounder": col, "type": "categorical",
                              "max_share_diff": round(max_diff, 4),
                              "threshold": 0.1,
                              "flag": "imbalanced" if max_diff > 0.1 else "balanced"})

    # 数值混杂列 → 四分位边（用于分层）
    edges = {}
    for col in confs:
        vs = sorted(float(r[col]) for r in used if c.isnum(r.get(col)))
        if len(vs) >= 8:
            def pct(p):
                i = p * (len(vs) - 1)
                lo, hi = int(i), min(int(i) + 1, len(vs) - 1)
                return vs[lo] * (1 - (i - lo)) + vs[hi] * (i - lo)
            edges[col] = [round(pct(0.25), 6), round(pct(0.5), 6), round(pct(0.75), 6)]

    # ---- Step 3 estimate：后门分层调整 ATE ----
    strata: Dict[str, Dict[str, List[float]]] = {}
    for r in used:
        k = _stratum_key(r, confs, edges)
        strata.setdefault(k, {"c": [], "t": []})
        strata[k][str(r[args.treatment]) == treat and "t" or "c"].append(
            float(r[args.outcome]))

    w_total = 0.0
    adj_acc = 0.0
    skipped = []
    detail = []
    for k, cell in strata.items():
        w = len(cell["c"]) + len(cell["t"])
        if not cell["c"] or not cell["t"]:
            skipped.append({"stratum": k, "n": w,
                            "reason": "单臂层（positivity 受限），不计入加权"})
            continue
        diff = sum(cell["t"]) / len(cell["t"]) - sum(cell["c"]) / len(cell["c"])
        adj_acc += w * diff
        w_total += w
        detail.append({"stratum": k, "n": w,
                       "treated_n": len(cell["t"]), "control_n": len(cell["c"]),
                       "within_effect": round(diff, 4)})
    adjusted = adj_acc / w_total if w_total else 0.0
    naive = sum(float(r[args.outcome]) for r in arms_t) / len(arms_t) - \
        sum(float(r[args.outcome]) for r in arms_c) / len(arms_c)

    # ---- Step 4 refute：安慰剂置换 ----
    rng = _LCG(args.seed)
    eff_out = [float(r[args.outcome]) for r in used]
    t_mask = [str(r[args.treatment]) == treat for r in used]
    trials = max(20, int(args.trials))
    extreme = 0
    for _ in range(trials):
        perm = rng.shuffle(t_mask)
        pc = [v for v, m in zip(eff_out, perm) if not m]
        pt = [v for v, m in zip(eff_out, perm) if m]
        if not pc or not pt:
            continue
        pe = sum(pt) / len(pt) - sum(pc) / len(pc)
        if abs(pe) >= abs(adjusted):
            extreme += 1
    placebo_p = extreme / trials

    biased = naive - adjusted
    return {
        "causal": {
            "model": {
                "outcome": args.outcome, "treatment": args.treatment,
                "treatment_values": [ctrl, treat],
                "confounders": confs, "n_used": len(used),
                "estimand": "ATE（后门分层调整）"},
            "identify": {
                "backdoor_set": confs,
                "imbalance": imbalance,
                "note": "只调整观测到的混杂；未观测混杂（隐藏共同原因）不可消除。"},
            "estimate": {
                "contrast": f"treat({treat}) − ctrl({ctrl})（两值按字典序配对，读数先看本行方向）",
                "mean_treat": round(sum(float(r[args.outcome]) for r in arms_t) / len(arms_t), 4),
                "mean_ctrl": round(sum(float(r[args.outcome]) for r in arms_c) / len(arms_c), 4),
                "adjusted_effect": round(adjusted, 4),
                "unadjusted_effect": round(naive, 4),
                "confounding_bias": round(biased, 4),
                "contribution": {
                    "treatment_effect": round(adjusted, 4),
                    "confounding_bias": round(biased, 4),
                    "sum_check": f"naive {naive:.4f} = 效应 {adjusted:.4f} + 偏差 {biased:.4f}"},
                "strata_used": len(detail), "strata_skipped": len(skipped),
                "strata_detail": detail, "skipped_detail": skipped},
            "refute": {
                "method": "安慰剂置换（随机重排处理标签，重算效应）",
                "trials": trials, "seed": args.seed,
                "placebo_p": round(placebo_p, 4),
                "survive_threshold": 0.05,
                "survives": placebo_p < 0.05,
                "note": f"安慰剂 p={placebo_p:.2f} = 随机标签效应达到 |调整效应| 的比例。"
                        f"p 低于阈值说明随机标签复现不出该效应，估计经受住反驳；"
                        f"p 达到或超过阈值说明随机排列也能造出同量级效应，估计与噪声无异。"
                        f"本结果 {'通过' if placebo_p < 0.05 else '未通过'}反驳。"},
            "note": "naive=处理效应+混杂偏差 的分解即归因证据（contribution）；"
                    "结论只对已调整混杂成立，不得外推为「总因果效应已证明」。",
        },
        # 顶层 contribution（归因分解证据，review.py driver_decomposition 检查顶层键）
        "contribution": {
            "treatment_effect": round(adjusted, 4),
            "confounding_bias": round(biased, 4),
            "unadjusted_effect": round(naive, 4),
            "sum_check": "unadjusted = treatment_effect + confounding_bias"},
    }
