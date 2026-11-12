# -*- coding: utf-8 -*-
"""方法代码深度审计：按方法切片检查统计要素，输出 L0—L4。"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = "\n".join((ROOT / "shared" / "methods" / f).read_text(encoding="utf-8")
                for f in ("core.py", "advanced.py", "deep.py"))


def block(names: list[str]) -> str:
    out = []
    for name in names:
        m = re.search(rf"^def {re.escape(name)}\(", SRC, re.M)
        if not m:
            continue
        nxt = re.search(r"^def ", SRC[m.end():], re.M)
        end = m.end() + nxt.start() if nxt else len(SRC)
        out.append(SRC[m.start():end])
    return "\n".join(out)


SPEC = {
    "matched": {
        "title": "匹配/PSM",
        "funcs": ["matched_diff", "psm_att", "psm_refute", "_smd", "_logit_fit"],
        "features": [
            ("协变量/倾向得分", r"psm_att|propensity|logit_fit"),
            ("平衡检验 SMD", r"smd_before|smd_after|balanced"),
            ("卡尺/共同支撑", r"caliper|common_support"),
            ("不确定性 CI", r"ci95|n_boot|bootstrap"),
            ("反驳/安慰剂", r"placebo|refut"),
            ("聚类/稳健 SE", r"cluster|hc1"),
        ],
    },
    "did": {
        "title": "DID/TWFE",
        "funcs": ["did", "twfe_did", "event_study", "did_placebo", "staggered_att", "_within2"],
        "features": [
            ("固定效应", r"twfe|within2"),
            ("聚类稳健 SE", r"se_cluster|cluster"),
            ("平行趋势", r"pretrend|parallel"),
            ("事件研究/动态效应", r"event_study|leads|lags"),
            ("交错处理/异质性", r"staggered|sun_abraham|callaway"),
            ("安慰剂/置换", r"placebo|permutation"),
        ],
    },
    "elasticity": {
        "title": "价格弹性",
        "funcs": ["elasticity", "elasticity_ols", "elasticity_fe", "elasticity_iv"],
        "features": [
            ("控制变量", r"controls"),
            ("稳健 SE（HC1）", r"hc1|robust"),
            ("置信区间", r"ci95"),
            ("固定效应/面板", r"fixed_effect|demean|panel|within2|双向"),
            ("内生性/工具变量", r"instrument|\biv\b|endogen"),
            ("函数形式/非线性", r"log-log|loglog|spline"),
        ],
    },
    "mmm": {
        "title": "MMM",
        "funcs": ["mmm", "mmm_deep", "mmm_budget", "mmm_contribution_ci", "_adstock", "_hill"],
        "features": [
            ("adstock", r"adstock"),
            ("饱和曲线", r"saturation|hill"),
            ("正则/岭回归", r"ridge|lam"),
            ("留出验证", r"holdout"),
            ("趋势/季节", r"sin|cos|trend"),
            ("贡献分解", r"contribution"),
            ("预算分配/优化", r"budget|allocation|optim"),
            ("不确定性/CI", r"ci95|bootstrap"),
        ],
    },
    "rdd": {
        "title": "RDD",
        "funcs": ["rdd", "rdd_sensitivity", "_local_linear", "_local_quadratic", "rdd_covariate_balance"],
        "features": [
            ("局部线性/核", r"local_linear|triangular|kernel"),
            ("带宽敏感性", r"bandwidth_grid|bws|bandwidth"),
            ("安慰剂断点", r"placebo"),
            ("密度/操纵检验", r"density|mccrary"),
            ("偏差校正", r"bias_correct|robust_bias|quadratic"),
            ("协变量/稳健性", r"covariate|controls"),
        ],
    },
    "fulfillment": {
        "title": "履约/库存",
        "funcs": ["fulfillment_sim", "fulfillment_deep"],
        "features": [
            ("(s,S) 或 (R,Q) 策略", r"\(s,S\)|fulfillment_deep|reorder"),
            ("随机提前期", r"lead_sd|lead_time_sd"),
            ("服务水平", r"service_level|fill_rate"),
            ("预热/稳态", r"warmup|warm_up"),
            ("容量约束", r"capacity"),
            ("置信区间", r"ci95"),
        ],
    },
}


def main() -> None:
    rows = []
    for key, spec in SPEC.items():
        src = block(spec["funcs"])
        checks = [(name, bool(re.search(pat, src, re.I))) for name, pat in spec["features"]]
        got = sum(1 for _, ok in checks if ok)
        total = len(checks)
        rows.append({"method": key, "title": spec["title"], "got": got, "total": total,
                     "level": ("L4 可发表" if got == total else "L3 可审计" if got >= total - 1
                               else "L2 可解释" if got >= total / 2 else "L1 能算"),
                     "gaps": [n for n, ok in checks if not ok]})
    out = ROOT / "workspace" / "method_depth_audit.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'方法':<12}{'得分':<8}{'等级':<12}缺口")
    print("-" * 90)
    for r in rows:
        print(f"{r['title']:<12}{r['got']}/{r['total']:<6}{r['level']:<12}{'、'.join(r['gaps']) or '—'}")
    print(f"\n明细：{out}")
    bad = [r for r in rows if r["got"] < r["total"] / 2]
    if bad:
        print("低于 L2：" + "、".join(r["title"] for r in bad))
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
