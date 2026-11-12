# -*- coding: utf-8 -*-
"""方法深度层：PSM、TWFE-DID、带控制弹性、RDD 敏感性、MMM adstock/饱和、履约 (s,S)。

对照参考实现：
- DoWhy: identify → estimate → refute（这里补 PSM + 平衡/安慰剂）
- pyfixest: FE + cluster-robust + pretrend（这里补 TWFE + 聚类 + 平行趋势）
- Robyn: adstock + saturation + ridge + holdout（这里补网格 + 留出）
- rdrobust: bandwidth sensitivity + placebo（这里补带宽网格 + 安慰剂 + 密度）
- SimPy/OR-Tools: (s,S) 策略 + 随机提前期（这里补蒙特卡洛）
"""
from __future__ import annotations

import math
import random
from typing import Sequence

from .advanced import _solve


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def _var(xs: Sequence[float]) -> float:
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / max(1, len(xs) - 1)


def _norm_p(t: float) -> float:
    return 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))


def _inv(a: list[list[float]]) -> list[list[float]]:
    n = len(a)
    cols = []
    for c in range(n):
        e = [1.0 if i == c else 0.0 for i in range(n)]
        cols.append(_solve([row[:] for row in a], e))
    return [[cols[c][r] for c in range(n)] for r in range(n)]


def _matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))]
            for i in range(len(a))]


def _twfe_multi(y: Sequence[float], X: list[list[float]],
                unit: Sequence[object], time: Sequence[object]) -> tuple[list[float], list[float]]:
    """多变量 TWFE：返回 (系数, 聚类到 unit 的稳健 SE)。"""
    umap = {v: i for i, v in enumerate(sorted(set(unit), key=str))}
    tmap = {v: i for i, v in enumerate(sorted(set(time), key=str))}
    u = [umap[v] for v in unit]
    t = [tmap[v] for v in time]
    yw = _within2(y, u, t)
    cols = [_within2([row[j] for row in X], u, t) for j in range(len(X[0]))]
    k = len(cols)
    n = len(y)
    XtX = [[sum(cols[a][i] * cols[b][i] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(cols[a][i] * yw[i] for i in range(n)) for a in range(k)]
    beta = _solve(XtX, Xty)
    resid = [yw[i] - sum(cols[j][i] * beta[j] for j in range(k)) for i in range(n)]
    meat = [[0.0] * k for _ in range(k)]
    for g in set(u):
        idx = [i for i in range(n) if u[i] == g]
        score = [sum(cols[j][i] * resid[i] for i in idx) for j in range(k)]
        for a in range(k):
            for b in range(k):
                meat[a][b] += score[a] * score[b]
    inv = _inv(XtX)
    V = _matmul(_matmul(inv, meat), inv)
    return beta, [math.sqrt(max(0.0, V[j][j])) for j in range(k)]


# ------------------------------------------------------------------ PSM
def _logit_fit(x: list[list[float]], t: list[int]) -> list[float]:
    k = len(x[0])
    beta = [0.0] * k
    for _ in range(60):
        p = [1 / (1 + math.exp(-_dot(row, beta))) for row in x]
        w = [max(1e-6, pi * (1 - pi)) for pi in p]
        grad = [sum(x[i][j] * (t[i] - p[i]) for i in range(len(t))) for j in range(k)]
        h = [[sum(x[i][a] * x[i][b] * w[i] for i in range(len(t))) for b in range(k)] for a in range(k)]
        for j in range(k):
            h[j][j] += 1e-6
        step = _solve(h, grad)
        beta = [beta[j] + step[j] for j in range(k)]
        if max(abs(s) for s in step) < 1e-9:
            break
    return beta


def _smd(a: Sequence[float], b: Sequence[float]) -> float:
    denom = math.sqrt((_var(a) + _var(b)) / 2) or 1e-9
    return (_mean(a) - _mean(b)) / denom


def psm_att(treat_y: Sequence[float], control_y: Sequence[float],
            treat_x: Sequence[Sequence[float]], control_x: Sequence[Sequence[float]],
            caliper: float = 0.2, n_boot: int = 1000, seed: int = 42,
            cluster: Sequence[object] | None = None) -> dict:
    """倾向得分匹配 ATT：logit PS + 最近邻（卡尺）+ 匹配前后 SMD + 自助 CI。"""
    nt, nc = len(treat_y), len(control_y)
    if nt < 5 or nc < 5:
        raise ValueError("处理组/对照组各至少 5 个观测")
    k = len(treat_x[0])
    x = [[1.0] + list(row) for row in treat_x] + [[1.0] + list(row) for row in control_x]
    t = [1] * nt + [0] * nc
    beta = _logit_fit(x, t)
    ps = [1 / (1 + math.exp(-_dot(row, beta))) for row in x]
    ps_t, ps_c = ps[:nt], ps[nt:]
    logit = [math.log(max(1e-9, p) / max(1e-9, 1 - p)) for p in ps]
    lt, lc = logit[:nt], logit[nt:]
    cal = caliper * (sum((v - _mean(lt)) ** 2 for v in lt) / max(1, nt - 1)) ** 0.5
    matches, used = [], []
    for i, v in enumerate(lt):
        best, bd = None, 1e9
        for j, w in enumerate(lc):
            if j in used:
                continue
            d = abs(v - w)
            if d < bd and d <= cal:
                best, bd = j, d
        if best is not None:
            matches.append((i, best))
            used.append(best)
    if not matches:
        raise ValueError("卡尺内无匹配：放宽 caliper 或检查协变量")
    att = _mean([treat_y[i] - control_y[j] for i, j in matches])
    rng = random.Random(seed)
    boots = []
    if cluster is not None:
        groups: dict[object, list[tuple[int, int]]] = {}
        for pair in matches:
            groups.setdefault(cluster[pair[0]], []).append(pair)
        keys = list(groups)
        for _ in range(n_boot):
            pick = []
            for _ in keys:
                pick.extend(groups[keys[rng.randrange(len(keys))]])
            boots.append(_mean([treat_y[i] - control_y[j] for i, j in pick]))
    else:
        for _ in range(n_boot):
            pick = [matches[rng.randrange(len(matches))] for _ in matches]
            boots.append(_mean([treat_y[i] - control_y[j] for i, j in pick]))
    boots.sort()
    smd_before = [_smd([r[c] for r in treat_x], [r[c] for r in control_x]) for c in range(k)]
    fi = [i for i, _ in matches]
    fj = [j for _, j in matches]
    smd_after = [_smd([treat_x[i][c] for i in fi], [control_x[j][c] for j in fj]) for c in range(k)]
    return {"att": round(att, 4),
            "ci95": [round(boots[int(n_boot * 0.025)], 4), round(boots[int(n_boot * 0.975)], 4)],
            "n_matched": len(matches), "n_treat": nt, "n_control": nc,
            "caliper_logit": round(cal, 4),
            "smd_before_max": round(max(abs(v) for v in smd_before), 3),
            "smd_after_max": round(max(abs(v) for v in smd_after), 3),
            "balanced": max(abs(v) for v in smd_after) < 0.1,
            "cluster_bootstrap": cluster is not None,
            "note": "PS 由协变量 logit 估计；ATT 仅对匹配上的处理组"}


def psm_refute(treat_y: Sequence[float], control_y: Sequence[float],
               treat_x: Sequence[Sequence[float]], control_x: Sequence[Sequence[float]],
               caliper: float = 0.2, seed: int = 42) -> dict:
    """PSM 反驳：安慰剂处理（随机重排）+ 子集重估。"""
    rng = random.Random(seed)
    base = psm_att(treat_y, control_y, treat_x, control_x, caliper, 500, seed)
    pooled_y = list(treat_y) + list(control_y)
    pooled_x = [list(r) for r in treat_x] + [list(r) for r in control_x]
    idx = list(range(len(pooled_y)))
    rng.shuffle(idx)
    nt = len(treat_y)
    try:
        placebo = psm_att([pooled_y[i] for i in idx[:nt]],
                          [pooled_y[i] for i in idx[nt:]],
                          [pooled_x[i] for i in idx[:nt]],
                          [pooled_x[i] for i in idx[nt:]], caliper, 300, seed)
        placebo_att = placebo["att"]
    except ValueError:
        placebo_att = None
    k = max(2, int(len(treat_y) * 0.1))
    try:
        sub = psm_att(treat_y[:-k], control_y[:-k], treat_x[:-k], control_x[:-k],
                      caliper, 300, seed)
        subset_att = sub["att"]
    except ValueError:
        subset_att = None
    passed = (placebo_att is not None and abs(placebo_att) < 0.5 * abs(base["att"]))
    if subset_att is not None:
        passed = passed and abs(subset_att - base["att"]) < 0.3 * abs(base["att"]) + 1e-9
    return {"original_att": base["att"], "placebo_att": placebo_att,
            "subset_att": subset_att, "passed": passed,
            "note": "安慰剂 |ATT| 应远小于主效应；子集应同向"}


# ------------------------------------------------------------------ TWFE DID
def _within2(v: Sequence[float], u: Sequence[int], t: Sequence[int]) -> list[float]:
    nu, nt_ = max(u) + 1, max(t) + 1
    grand = _mean(v)
    um = [0.0] * nu
    tm = [0.0] * nt_
    cu = [0] * nu
    ct = [0] * nt_
    for vi, ui, ti in zip(v, u, t):
        um[ui] += vi
        tm[ti] += vi
        cu[ui] += 1
        ct[ti] += 1
    um = [um[i] / cu[i] for i in range(nu)]
    tm = [tm[i] / ct[i] for i in range(nt_)]
    return [vi - um[ui] - tm[ti] + grand for vi, ui, ti in zip(v, u, t)]


def twfe_did(y: Sequence[float], treat: Sequence[int], post: Sequence[int],
             unit: Sequence[object], time: Sequence[object]) -> dict:
    """双向固定效应 DID：unit + time FE，聚类到 unit 的稳健标准误，附平行趋势检验。"""
    n = len(y)
    if not (n == len(treat) == len(post) == len(unit) == len(time)):
        raise ValueError("y/treat/post/unit/time 长度必须一致")
    umap = {v: i for i, v in enumerate(sorted(set(unit), key=str))}
    tmap = {v: i for i, v in enumerate(sorted(set(time), key=str))}
    u = [umap[v] for v in unit]
    ti = [tmap[v] for v in time]
    d = [treat[i] * post[i] for i in range(n)]
    yw = _within2(y, u, ti)
    dw = _within2(d, u, ti)
    denom = sum(v * v for v in dw)
    if denom < 1e-12:
        raise ValueError("处理变量无变异（全 0 或全 1）")
    beta = sum(a * b for a, b in zip(yw, dw)) / denom
    e = [yw[i] - beta * dw[i] for i in range(n)]
    meat = 0.0
    for g in set(u):
        s = sum(dw[i] * e[i] for i in range(n) if u[i] == g)
        meat += s * s
    se = math.sqrt(meat) / denom
    tstat = beta / se if se else float("nan")
    # 平行趋势：pre 期 treated × 线性时间
    pre_idx = [i for i in range(n) if post[i] == 0]
    pre_t = [ti[i] for i in pre_idx]
    if len(set(pre_t)) >= 2 and len(set(treat[i] for i in pre_idx)) == 2 and len(pre_idx) >= 6:
        mt = _mean(pre_t)
        xp = [treat[i] * (ti[i] - mt) for i in pre_idx]
        yp = [y[i] for i in pre_idx]
        up = [u[i] for i in pre_idx]
        ypw = _within2(yp, up, pre_t)
        xpw = _within2(xp, up, pre_t)
        den = sum(v * v for v in xpw)
        if den > 1e-12:
            b_pre = sum(a * b for a, b in zip(ypw, xpw)) / den
            ep = [ypw[i] - b_pre * xpw[i] for i in range(len(ypw))]
            meat_p = sum(sum(xpw[i] * ep[i] for i in range(len(ypw)) if up[i] == g) ** 2 for g in set(up))
            se_p = math.sqrt(meat_p) / den
            pretrend = {"coef": round(b_pre, 4), "se": round(se_p, 4),
                        "p": round(_norm_p(b_pre / se_p), 4) if se_p else None,
                        "passed": (abs(b_pre / se_p) < 1.96) if se_p else None}
        else:
            pretrend = {"coef": None, "p": None, "passed": None}
    else:
        pretrend = {"coef": None, "p": None, "passed": None}
    return {"att": round(beta, 4), "se_cluster": round(se, 4), "t": round(tstat, 2),
            "p": round(_norm_p(tstat), 4), "n": n, "n_units": len(set(u)),
            "pretrend": pretrend,
            "note": "unit+time 双向固定效应；SE 聚类到 unit；pretrend p>0.05 才支持平行趋势"}


def event_study(y: Sequence[float], treat: Sequence[int], post: Sequence[int],
                unit: Sequence[object], time: Sequence[object], window: int = 3) -> dict:
    """事件研究：相对处理时点的 leads/lags 系数（omit -1），双向 FE + 聚类 SE。"""
    adoption: dict[object, object] = {}
    for i in range(len(y)):
        if treat[i] == 1 and post[i] == 1:
            u = unit[i]
            if u not in adoption or time[i] < adoption[u]:
                adoption[u] = time[i]
    rel = []
    for i in range(len(y)):
        if unit[i] in adoption:
            rel.append(int(time[i]) - int(adoption[unit[i]]))
        else:
            rel.append(None)
    rels = sorted({r for r in rel if r is not None and -window <= r <= window and r != -1})
    if not rels:
        raise ValueError("没有可估计的相对时点")
    X = [[1.0 if rel[i] == r else 0.0 for r in rels] for i in range(len(y))]
    beta, se = _twfe_multi(y, X, unit, time)
    out = {str(r): {"coef": round(beta[j], 4), "se": round(se[j], 4),
                    "p": round(_norm_p(beta[j] / se[j]), 4) if se[j] else None}
           for j, r in enumerate(rels)}
    pre = [v["coef"] for k, v in out.items() if int(k) < -1]
    return {"coefficients": out, "pretrend_joint_max": round(max((abs(v) for v in pre), default=0), 4),
            "note": "以 -1 期为基准；pre 期系数应接近 0"}


def did_placebo(y: Sequence[float], treat: Sequence[int], post: Sequence[int],
                unit: Sequence[object], time: Sequence[object], n_perm: int = 100,
                seed: int = 42) -> dict:
    """DID 置换安慰剂：打乱 unit 的处理标签，比较安慰剂 ATT 分布。"""
    rng = random.Random(seed)
    main = twfe_did(y, treat, post, unit, time)["att"]
    units = sorted(set(unit), key=str)
    tmap = {u: treat[next(i for i in range(len(y)) if unit[i] == u)] for u in units}
    vals = [tmap[u] for u in units]
    cnt = 0
    draws = []
    for _ in range(n_perm):
        rng.shuffle(vals)
        mp = dict(zip(units, vals))
        new_t = [mp[u] for u in unit]
        try:
            att = twfe_did(y, new_t, post, unit, time)["att"]
        except ValueError:
            continue
        draws.append(att)
        if abs(att) >= abs(main):
            cnt += 1
    return {"main_att": main, "placebo_n": len(draws),
            "p_perm": round(cnt / len(draws), 4) if draws else None,
            "note": "p>0.1 表示主效应不是随机标签造成的"}


def staggered_att(y: Sequence[float], treat: Sequence[int], post: Sequence[int],
                  unit: Sequence[object], time: Sequence[object]) -> dict:
    """交错处理：按 adopted cohort 做 not-yet-treated 的 group-time ATT 加权。"""
    adoption: dict[object, object] = {}
    for i in range(len(y)):
        if treat[i] == 1 and post[i] == 1:
            u = unit[i]
            if u not in adoption or time[i] < adoption[u]:
                adoption[u] = time[i]
    times = sorted(set(time))
    rows = {(unit[i], time[i]): y[i] for i in range(len(y))}
    cells = []
    for u, g in adoption.items():
        idx = times.index(g)
        if idx == 0:
            continue
        pre = times[idx - 1]
        cohort = [v for v in adoption if adoption[v] == g]
        for t in times[idx:]:
            if (u, t) not in rows or (u, pre) not in rows:
                continue
            tr = [rows[(v, t)] - rows[(v, pre)] for v in cohort
                  if (v, t) in rows and (v, pre) in rows]
            ctrl_units = [v for v in set(unit) if v not in adoption or adoption[v] > t]
            ctrl = [rows[(v, t)] - rows[(v, pre)] for v in ctrl_units
                    if (v, t) in rows and (v, pre) in rows]
            if tr and ctrl:
                cells.append({"cohort": str(g), "time": str(t),
                              "att": _mean(tr) - _mean(ctrl), "n_treat": len(tr)})
    if not cells:
        raise ValueError("没有可用的 not-yet-treated 对照")
    wsum = sum(c["n_treat"] for c in cells)
    att = sum(c["att"] * c["n_treat"] for c in cells) / wsum
    sd = math.sqrt(sum(c["n_treat"] * (c["att"] - att) ** 2 for c in cells) / max(1, wsum))
    return {"att": round(att, 4), "se": round(sd / math.sqrt(len(cells)), 4),
            "n_cells": len(cells), "cohorts": sorted({c["cohort"] for c in cells}),
            "note": "简化 CS 估计：not-yet-treated 对照；未做协变量调整"}


# ------------------------------------------------------------------ 弹性（带控制 + HC1）
def elasticity_ols(price: Sequence[float], qty: Sequence[float],
                   controls: Sequence[Sequence[float]] | None = None) -> dict:
    """log-log 多元 OLS：ln q = a + b ln p + controls；HC1 稳健标准误 + 95% CI。"""
    n = len(price)
    if n != len(qty) or n < 5:
        raise ValueError("价格与销量等长且至少 5 个点")
    k = 1 + 1 + (len(controls[0]) if controls else 0)
    X = []
    for i in range(n):
        row = [1.0, math.log(price[i])]
        if controls:
            row += [float(v) for v in controls[i]]
        X.append(row)
    Y = [math.log(q) for q in qty]
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a] * Y[i] for i in range(n)) for a in range(k)]
    beta = _solve(XtX, Xty)
    fit = [_dot(X[i], beta) for i in range(n)]
    e = [Y[i] - fit[i] for i in range(n)]
    # HC1: bread * meat * bread
    bread = [[0.0] * k for _ in range(k)]
    for a in range(k):
        for b in range(k):
            bread[a][b] = XtX[a][b]
    inv = [[0.0] * k for _ in range(k)]
    for c in range(k):
        ecol = [1.0 if i == c else 0.0 for i in range(k)]
        sol = _solve([row[:] for row in bread], ecol)
        for r in range(k):
            inv[r][c] = sol[r]
    meat = [[sum(X[i][a] * X[i][b] * e[i] * e[i] for i in range(n)) * n / max(1, n - k)
             for b in range(k)] for a in range(k)]
    V = [[sum(inv[a][x] * meat[x][y] * inv[y][b] for x in range(k) for y in range(k))
          for b in range(k)] for a in range(k)]
    se = math.sqrt(max(0.0, V[1][1]))
    my = _mean(Y)
    ss_res = sum(v * v for v in e)
    ss_tot = sum((v - my) ** 2 for v in Y) or 1e-12
    return {"elasticity": round(beta[1], 4), "se_hc1": round(se, 4),
            "ci95": [round(beta[1] - 1.96 * se, 4), round(beta[1] + 1.96 * se, 4)],
            "r2": round(1 - ss_res / ss_tot, 4), "n": n, "controls": k - 2,
            "note": "log-log；HC1；控制变量可缓解但不等同于识别"}


def elasticity_fe(price: Sequence[float], qty: Sequence[float],
                  unit: Sequence[object], time: Sequence[object],
                  controls: Sequence[Sequence[float]] | None = None) -> dict:
    """面板固定效应弹性：unit+time 双向去均值，聚类到 unit。"""
    n = len(price)
    umap = {v: i for i, v in enumerate(sorted(set(unit), key=str))}
    tmap = {v: i for i, v in enumerate(sorted(set(time), key=str))}
    u = [umap[v] for v in unit]
    t = [tmap[v] for v in time]
    y = [math.log(v) for v in qty]
    x = [math.log(v) for v in price]
    cols = [x] + ([[row[j] for row in controls] for j in range(len(controls[0]))] if controls else [])
    yw = _within2(y, u, t)
    cols = [_within2(c, u, t) for c in cols]
    k = len(cols)
    XtX = [[sum(cols[a][i] * cols[b][i] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(cols[a][i] * yw[i] for i in range(n)) for a in range(k)]
    beta = _solve(XtX, Xty)
    resid = [yw[i] - sum(cols[j][i] * beta[j] for j in range(k)) for i in range(n)]
    meat = 0.0
    for g in set(u):
        s = sum(cols[0][i] * resid[i] for i in range(n) if u[i] == g)
        meat += s * s
    se = math.sqrt(meat) / sum(v * v for v in cols[0])
    return {"elasticity": round(beta[0], 4), "se_cluster": round(se, 4),
            "ci95": [round(beta[0] - 1.96 * se, 4), round(beta[0] + 1.96 * se, 4)],
            "n": n, "n_units": len(set(u)), "controls": k - 1,
            "note": "log-log + 双向 FE；聚类到 unit；FE 只吸收不随时间变的混杂"}


def elasticity_iv(price: Sequence[float], qty: Sequence[float],
                  instrument: Sequence[float],
                  controls: Sequence[Sequence[float]] | None = None) -> dict:
    """2SLS 弹性：工具变量 + 控制变量；返回一阶段 F 与二阶段弹性。"""
    n = len(price)
    y = [math.log(v) for v in qty]
    x = [math.log(v) for v in price]
    z = [float(v) for v in instrument]
    ctrl = controls or []
    X = [[1.0, x[i]] + [float(ctrl[i][j]) for j in range(len(ctrl[0]))] if ctrl else [1.0, x[i]]
         for i in range(n)]
    Z = [[1.0, z[i]] + [float(ctrl[i][j]) for j in range(len(ctrl[0]))] if ctrl else [1.0, z[i]]
         for i in range(n)]
    ZtZ = [[sum(Z[i][a] * Z[i][b] for i in range(n)) for b in range(len(Z[0]))] for a in range(len(Z[0]))]
    ZtZi = _inv(ZtZ)
    ZtX = [[sum(Z[i][a] * X[i][b] for i in range(n)) for b in range(len(X[0]))] for a in range(len(Z[0]))]
    Zty = [sum(Z[i][a] * y[i] for i in range(n)) for a in range(len(Z[0]))]
    # 一阶段 F：x 对 Z 回归
    Ztx = [sum(Z[i][a] * x[i] for i in range(n)) for a in range(len(Z[0]))]
    b1 = [sum(ZtZi[a][b] * Ztx[b] for b in range(len(Z[0]))) for a in range(len(Z[0]))]
    res1 = [x[i] - sum(Z[i][j] * b1[j] for j in range(len(Z[0]))) for i in range(n)]
    s2 = sum(v * v for v in res1) / max(1, n - len(Z[0]))
    # 工具变量系数（第二个）的方差
    V1 = _matmul(_matmul(ZtZi, [[sum(Z[i][a] * Z[i][b] for i in range(n)) for b in range(len(Z[0]))]
                                for a in range(len(Z[0]))]), ZtZi)
    f_stat = (b1[1] ** 2) / (s2 * V1[1][1]) if V1[1][1] else 0.0
    # 二阶段：X'PzX, X'Pzy
    PzX = _matmul(_matmul(Z, ZtZi), ZtX)
    XtPzX = [[sum(X[i][a] * PzX[i][b] for i in range(n)) for b in range(len(X[0]))]
             for a in range(len(X[0]))]
    Pzy = [sum(PzX[i][a] * y[i] for i in range(n)) for a in range(len(X[0]))]
    beta = _solve(XtPzX, Pzy)
    resid = [y[i] - sum(X[i][j] * beta[j] for j in range(len(X[0]))) for i in range(n)]
    sigma2 = sum(v * v for v in resid) / max(1, n - len(X[0]))
    V = [[sigma2 * _inv(XtPzX)[a][b] for b in range(len(X[0]))] for a in range(len(X[0]))]
    se = math.sqrt(max(0.0, V[1][1]))
    return {"elasticity": round(beta[1], 4), "se_2sls": round(se, 4),
            "ci95": [round(beta[1] - 1.96 * se, 4), round(beta[1] + 1.96 * se, 4)],
            "first_stage_F": round(f_stat, 2), "weak_iv": f_stat < 10,
            "n": n, "note": "2SLS；F<10 提示弱工具变量，弹性不可信"}


# ------------------------------------------------------------------ RDD 敏感性
def _local_linear(y: Sequence[float], x: Sequence[float], cutoff: float, bw: float) -> tuple[float, float]:
    """三角核加权局部线性：返回 (断点跳跃, 截距标准误)。"""
    left_x, left_y, left_w, right_x, right_y, right_w = [], [], [], [], [], []
    for xi, yi in zip(x, y):
        d = abs(xi - cutoff)
        if d > bw:
            continue
        w = max(0.0, 1 - d / bw)
        if xi < cutoff:
            left_x.append(xi - cutoff)
            left_y.append(yi)
            left_w.append(w)
        else:
            right_x.append(xi - cutoff)
            right_y.append(yi)
            right_w.append(w)
    if len(left_x) < 4 or len(right_x) < 4:
        raise ValueError("带宽内两侧各至少 4 个点")

    def fit(xs, ys, ws):
        sw = sum(ws)
        mx = sum(w * v for w, v in zip(ws, xs)) / sw
        my = sum(w * v for w, v in zip(ws, ys)) / sw
        sxx = sum(w * (v - mx) ** 2 for w, v in zip(ws, xs))
        if sxx < 1e-12:
            raise ValueError("带宽内 running 无变异")
        slope = sum(ws[i] * (xs[i] - mx) * (ys[i] - my) for i in range(len(xs))) / sxx
        a = my - slope * mx
        resid = [ys[i] - (a + slope * xs[i]) for i in range(len(xs))]
        sigma2 = sum(w * r * r for w, r in zip(ws, resid)) / max(1, len(xs) - 2)
        se = math.sqrt(sigma2 * (1 / sw + mx * mx / sxx))
        return a, se

    a_l, se_l = fit(left_x, left_y, left_w)
    a_r, se_r = fit(right_x, right_y, right_w)
    return a_r - a_l, math.sqrt(se_l ** 2 + se_r ** 2)


def rdd_sensitivity(y: Sequence[float], x: Sequence[float], cutoff: float,
                    bandwidths: Sequence[float] | None = None,
                    covariates: Sequence[Sequence[float]] | None = None) -> dict:
    """RDD 敏感性：带宽网格 + 安慰剂断点 + 密度检验 + 二次偏差校正 + 协变量平衡。"""
    if len(y) != len(x) or len(y) < 12:
        raise ValueError("y/x 等长且至少 12 个点")
    span = max(x) - min(x)
    base = (bandwidths[0] if bandwidths else span / 2)
    grid = [round(base * m, 3) for m in (0.6, 0.8, 1.0, 1.2, 1.5)]
    rows = []
    for bw in grid:
        try:
            est, se = _local_linear(y, x, cutoff, bw)
            rows.append({"bandwidth": bw, "estimate": round(est, 4), "se": round(se, 4),
                         "t": round(est / se, 2) if se else None})
        except ValueError:
            continue
    if not rows:
        raise ValueError("所有带宽都失败：放宽 bandwidth")
    main = _local_linear(y, x, cutoff, base)
    # 安慰剂断点（25%/75% 分位，离主断点足够远）
    xs = sorted(x)
    q25, q75 = xs[len(xs) // 4], xs[3 * len(xs) // 4]
    placebos = []
    for c in (q25, q75):
        if abs(c - cutoff) < 0.15 * span:
            continue
        bw_c = min(base, max(4.0, abs(c - cutoff) * 0.6))
        try:
            e, _ = _local_linear(y, x, c, bw_c)
            placebos.append(round(e, 4))
        except ValueError:
            continue
    p_placebo = (sum(1 for e in placebos if abs(e) >= abs(main[0])) / len(placebos)) if placebos else None
    # 密度：断点 ±0.1bw 的样本数是否对称（简单二项近似）
    near = [v for v in x if abs(v - cutoff) <= 0.1 * base]
    nl = sum(1 for v in near if v < cutoff)
    nr = len(near) - nl
    if nl + nr >= 6:
        z = (nl - nr) / math.sqrt(nl + nr)
        p_density = round(_norm_p(z), 4)
    else:
        p_density = None
    try:
        quad = _local_quadratic(y, x, cutoff, base)
    except ValueError:
        quad = None
    cov = rdd_covariate_balance(covariates, x, cutoff, base) if covariates else None
    return {"estimate": round(main[0], 4), "se": round(main[1], 4),
            "bandwidth_grid": rows,
            "placebo_estimates": placebos, "p_placebo": p_placebo,
            "density_p": p_density,
            "quadratic_estimate": round(quad, 4) if quad is not None else None,
            "covariate_balance": cov,
            "robust": (p_placebo is not None and p_placebo < 0.1),
            "note": "带宽越小越局部；安慰剂 p<0.1 才算通过；密度 p<0.05 提示操纵"}


def _local_quadratic(y: Sequence[float], x: Sequence[float], cutoff: float, bw: float) -> float:
    """局部二次（偏差校正的粗糙替代）：左右各拟合 1+x+x²，取截距差。"""
    sides = {"l": [], "r": []}
    for xi, yi in zip(x, y):
        d = abs(xi - cutoff)
        if d > bw:
            continue
        w = max(0.0, 1 - d / bw)
        sides["l" if xi < cutoff else "r"].append((xi - cutoff, yi, w))
    if len(sides["l"]) < 6 or len(sides["r"]) < 6:
        raise ValueError("二次拟合两侧各至少 6 个点")
    ans = {}
    for key, rows in sides.items():
        X = [[1.0, v, v * v] for v, _, _ in rows]
        W = [w for _, _, w in rows]
        yy = [z for _, z, _ in rows]
        XtWX = [[sum(W[i] * X[i][a] * X[i][b] for i in range(len(rows))) for b in range(3)]
                for a in range(3)]
        XtWy = [sum(W[i] * X[i][a] * yy[i] for i in range(len(rows))) for a in range(3)]
        ans[key] = _solve(XtWX, XtWy)[0]
    return ans["r"] - ans["l"]


def rdd_covariate_balance(covariates: Sequence[Sequence[float]], x: Sequence[float],
                          cutoff: float, bw: float) -> dict:
    """断点附近协变量平衡：左右 SMD，max|SMD|<0.1 视为平衡。"""
    k = len(covariates[0])
    left = [i for i in range(len(x)) if cutoff - bw <= x[i] < cutoff]
    right = [i for i in range(len(x)) if cutoff <= x[i] <= cutoff + bw]
    if len(left) < 4 or len(right) < 4:
        raise ValueError("协变量平衡两侧样本不足")
    smds = []
    for j in range(k):
        a = [covariates[i][j] for i in left]
        b = [covariates[i][j] for i in right]
        smds.append(_smd(a, b))
    return {"smd": [round(v, 3) for v in smds],
            "max_abs_smd": round(max(abs(v) for v in smds), 3),
            "balanced": max(abs(v) for v in smds) < 0.1}


# ------------------------------------------------------------------ MMM 深度
def _adstock(x: Sequence[float], theta: float) -> list[float]:
    out = []
    carry = 0.0
    for v in x:
        carry = v + theta * carry
        out.append(carry)
    return out


def _hill(x: Sequence[float], alpha: float, gamma: float) -> list[float]:
    return [v ** alpha / (v ** alpha + gamma ** alpha + 1e-9) for v in x]


def mmm_deep(channels: Sequence[Sequence[float]], y: Sequence[float],
             names: Sequence[str] | None = None, holdout: float = 0.2,
             lam: float = 0.01) -> dict:
    """MMM：几何 adstock + Hill 饱和 + 趋势/季节 + ridge + 留出验证 + 贡献占比。"""
    n = len(y)
    k = len(channels)
    if k == 0 or len(channels[0]) != n:
        raise ValueError("channels 应为「每行一个渠道、长度=n」")
    names = list(names or [f"ch{i+1}" for i in range(k)])
    if n < 12:
        raise ValueError("至少 12 个观测")
    h = max(3, int(n * holdout))
    train = n - h
    best = None
    for theta in (0.0, 0.3, 0.6):
        for alpha in (0.5, 1.0, 1.5):
            cols = []
            gammas = []
            for j in range(k):
                raw = [float(channels[j][i]) for i in range(n)]
                ad = _adstock(raw, theta)
                pos = sorted(v for v in ad if v > 0)
                gamma = pos[len(pos) // 2] if pos else 1.0
                gammas.append(gamma)
                cols.append(_hill(ad, alpha, gamma))
            X = [[1.0, float(i)] for i in range(n)]
            for j in range(k):
                X = [row + [cols[j][i]] for i, row in enumerate(X)]
            # 季节项：52 周周期
            X = [row + [math.sin(2 * math.pi * i / 52), math.cos(2 * math.pi * i / 52)]
                 for i, row in enumerate(X)]
            p = len(X[0])
            Xtr, ytr = X[:train], y[:train]
            Xte, yte = X[train:], y[train:]
            XtX = [[sum(Xtr[i][a] * Xtr[i][b] for i in range(train)) for b in range(p)] for a in range(p)]
            for a in range(1, p):  # 不惩罚截距
                XtX[a][a] += lam
            Xty = [sum(Xtr[i][a] * ytr[i] for i in range(train)) for a in range(p)]
            beta = _solve(XtX, Xty)
            pred = [_dot(Xte[i], beta) for i in range(h)]
            mse = sum((pred[i] - yte[i]) ** 2 for i in range(h)) / h
            if best is None or mse < best["mse"]:
                best = {"mse": mse, "theta": theta, "alpha": alpha, "beta": beta,
                        "X": X, "p": p, "gammas": gammas}
    beta = best["beta"]
    X = best["X"]
    fit = [_dot(row, beta) for row in X]
    my = _mean(y)
    r2_train = 1 - sum((y[i] - fit[i]) ** 2 for i in range(train)) / (sum((y[i] - my) ** 2 for i in range(n)) or 1e-12)
    r2_hold = 1 - best["mse"] * h / (sum((y[i] - my) ** 2 for i in range(train, n)) or 1e-12)
    means = [sum(X[i][j] for i in range(n)) / n for j in range(best["p"])]
    contrib = [beta[j] * means[j] for j in range(2, 2 + k)]
    pos = sum(max(0.0, c) for c in contrib) or 1e-12
    return {"adstock_theta": best["theta"], "saturation_alpha": best["alpha"],
            "r2_train": round(r2_train, 4), "r2_holdout": round(r2_hold, 4),
            "coef": {names[j]: round(beta[2 + j], 4) for j in range(k)},
            "contribution_pct": {names[j]: round(max(0.0, contrib[j]) / pos * 100, 1) for j in range(k)},
            "gammas": [round(v, 4) for v in best["gammas"]],
            "n": n, "holdout_n": h, "note": "adstock/饱和/ridge/留出验证；仍为关联模型"}


def mmm_budget(channels: Sequence[Sequence[float]], y: Sequence[float],
               names: Sequence[str] | None = None, total_budget: float = 100.0,
               steps: int = 100) -> dict:
    """按边际响应做预算分配：在 Hill 饱和曲线上贪心加水。"""
    fit = mmm_deep(channels, y, names)
    names = list(fit["coef"].keys())
    k = len(names)
    theta, alpha = fit["adstock_theta"], fit["saturation_alpha"]
    gammas = fit["gammas"]
    betas = [fit["coef"][nm] for nm in names]

    def resp(j: int, spend: float) -> float:
        steady = spend / max(1e-6, 1 - theta)
        h = steady ** alpha / (steady ** alpha + gammas[j] ** alpha + 1e-9)
        return betas[j] * h

    alloc = [0.0] * k
    step = total_budget / steps
    for _ in range(steps):
        gains = [resp(j, alloc[j] + step) - resp(j, alloc[j]) for j in range(k)]
        j = max(range(k), key=lambda x: gains[x])
        alloc[j] += step
    equal = total_budget / k
    expected = sum(resp(j, alloc[j]) for j in range(k))
    baseline = sum(resp(j, equal) for j in range(k))
    return {"allocation": {names[j]: round(alloc[j], 2) for j in range(k)},
            "share_pct": {names[j]: round(alloc[j] / total_budget * 100, 1) for j in range(k)},
            "expected_response": round(expected, 4),
            "baseline_equal_split": round(baseline, 4),
            "lift_pct": round((expected - baseline) / abs(baseline) * 100, 2) if baseline else None,
            "note": "基于拟合的 Hill 曲线贪心分配；未考虑渠道间交互"}


def mmm_contribution_ci(channels: Sequence[Sequence[float]], y: Sequence[float],
                        names: Sequence[str] | None = None, n_boot: int = 100,
                        seed: int = 42) -> dict:
    """贡献占比的块自助 CI：重采样行、重拟合、取分位。"""
    rng = random.Random(seed)
    base = mmm_deep(channels, y, names)
    names = list(base["contribution_pct"].keys())
    n = len(y)
    block = max(2, n // 6)
    draws = {nm: [] for nm in names}
    for _ in range(n_boot):
        starts = [rng.randrange(max(1, n - block + 1)) for _ in range(max(1, n // block + 1))]
        idx = []
        for s in starts:
            idx.extend(range(s, min(n, s + block)))
        idx = idx[:n] or list(range(n))
        ch = [[channels[j][i] for i in idx] for j in range(len(channels))]
        yy = [y[i] for i in idx]
        try:
            r = mmm_deep(ch, yy, names)
        except Exception:
            continue
        for nm in names:
            draws[nm].append(r["contribution_pct"][nm])
    out = {}
    for nm in names:
        vals = sorted(draws[nm])
        out[nm] = {"point": base["contribution_pct"][nm],
                   "ci95": [round(vals[int(len(vals) * 0.025)], 1),
                            round(vals[int(len(vals) * 0.975)], 1)] if vals else None}
    return {"contribution": out, "n_boot": n_boot,
            "note": "块自助；分位 CI 只反映抽样不确定性"}


# ------------------------------------------------------------------ 履约 (s,S)
def fulfillment_deep(demand_mean: float, demand_sd: float, lead_mean: float,
                     lead_sd: float, s: float, S: float, days: int = 60,
                     sims: int = 1000, seed: int = 42, warmup: float = 0.1) -> dict:
    """(s,S) 补货 + 随机提前期：履约率、周期服务水平、平均库存、95% CI。"""
    if not (0 <= s < S):
        raise ValueError("需满足 0 <= s < S")
    rng = random.Random(seed)
    start = int(days * max(0.0, min(0.5, warmup)))
    fills, csls, avgs = [], [], []
    for _ in range(sims):
        inv = S
        pipeline: list[tuple[int, float]] = []
        served = total = 0.0
        inv_sum = 0.0
        order_cycles = 0
        stockout_cycles = 0
        in_cycle = False
        cycle_stockout = False
        for d in range(days):
            for arr, qty in list(pipeline):
                if arr <= d:
                    inv += qty
                    pipeline.remove((arr, qty))
            demand = max(0.0, rng.gauss(demand_mean, demand_sd))
            take = min(inv, demand)
            inv -= take
            if d >= start:
                total += demand
                served += take
                if take < demand and in_cycle:
                    cycle_stockout = True
                inv_sum += inv
            position = inv + sum(q for _, q in pipeline)
            if position < s:
                qty = S - position
                lt = max(1, int(round(rng.gauss(lead_mean, lead_sd))))
                pipeline.append((d + lt, qty))
                if not in_cycle:
                    in_cycle = True
                    order_cycles += 1
                    if cycle_stockout:
                        stockout_cycles += 1
                    cycle_stockout = False
        if in_cycle:
            stockout_cycles += 1 if cycle_stockout else 0
        fills.append(served / total if total else 1.0)
        csls.append(1 - stockout_cycles / max(1, order_cycles))
        avgs.append(inv_sum / max(1, days - start))
    fills.sort()
    return {"fill_rate": round(sum(fills) / sims * 100, 2),
            "cycle_service_level": round(sum(csls) / sims * 100, 2),
            "avg_inventory": round(sum(avgs) / sims, 2),
            "fill_rate_ci95": [round(fills[int(sims * 0.025)] * 100, 2),
                               round(fills[int(sims * 0.975)] * 100, 2)],
            "s": s, "S": S, "lead_mean": lead_mean, "lead_sd": lead_sd,
            "warmup_days": start,
            "note": "(s,S) 策略；提前期随机；周期服务水平按订货周期计"}


