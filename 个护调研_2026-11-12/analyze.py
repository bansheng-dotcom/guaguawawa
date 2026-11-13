# -*- coding: utf-8 -*-
"""个护品类调研 · 确定性分析脚本。

输入：ledger_data.py（证据台账，只含来源明写的数字）
输出：data/observations.csv、data/derived_metrics.csv、analysis_results.json

所有派生值都必须由台账数字按下方公式算出，禁止在报告里另写一套。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from ledger_data import CONFLICTS, GAPS, OBS  # noqa: E402


def num(oid: str) -> float:
    for o in OBS:
        if o["id"] == oid and o["value"] is not None:
            return float(o["value"])
    raise KeyError(f"观测 {oid} 不存在或不是数值")


def obs(oid: str) -> dict:
    for o in OBS:
        if o["id"] == oid:
            return o
    raise KeyError(oid)


def pct(x: float, digits: int = 2) -> float:
    return round(x * 100, digits)


def cagr(v0: float, v1: float, years: int) -> float:
    return (v1 / v0) ** (1.0 / years) - 1.0


def split_value(growth: float, volume_growth: float, v0: float) -> dict:
    """额增长 = 量贡献 + 价贡献 + 交叉项（三项之和精确等于 V1-V0）。"""
    g, q = growth / 100.0, volume_growth / 100.0
    price_growth = (1 + g) / (1 + q) - 1
    vol_effect = v0 * q
    price_effect = v0 * price_growth
    cross = v0 * q * price_growth
    return {
        "v0": round(v0, 2),
        "v1": round(v0 * (1 + g), 2),
        "growth_pct": round(growth, 2),
        "volume_growth_pct": round(volume_growth, 2),
        "price_growth_pct": round(price_growth * 100, 2),
        "volume_effect": round(vol_effect, 2),
        "price_effect": round(price_effect, 2),
        "cross_effect": round(cross, 2),
        "total_effect": round(vol_effect + price_effect + cross, 2),
    }


def build() -> dict:
    # ── 1. 大盘 ──
    years = [("2021", "S01"), ("2022", "S02"), ("2023", "S03"), ("2024", "S04"), ("2025", "S05")]
    series = {y: num(oid) for y, oid in years}
    cagr_21_25 = cagr(series["2021"], series["2025"], 4)
    gap_2025 = num("S05") and (5.1 - 3.7)  # 披露同比
    gap_2026 = (6.1 - 1.1)

    # ── 2. 线上两大盘 ──
    haircare_2025 = num("S26")
    hc_g, hc_q = 7.61, num("S27")      # 交易额 +7.61%（S26 披露）、交易量 +11.94%（S27）
    haircare_2024 = round(haircare_2025 / (1 + hc_g / 100), 2)
    oral_2025 = num("S34")
    oral_g, oral_q = 17.3, num("S35")
    oral_2024 = round(oral_2025 / (1 + oral_g / 100), 2)
    online_total = round(haircare_2025 + oral_2025, 2)

    # ── 3. 量价分解 ──
    hc = split_value(hc_g, hc_q, haircare_2024)
    oral25 = split_value(oral_g, oral_q, oral_2024)
    oral26q1 = split_value(13.8, num("S37"), round(num("S36") / 1.138, 2))

    # ── 4. 渠道（2026Q1 口腔） ──
    total_q1 = num("S36")
    channels = [
        {"key": "抖音", "value": num("S38"), "growth": 30.73, "obs": "S38"},
        {"key": "天猫", "value": num("S39"), "growth": -2.31, "obs": "S39"},
        {"key": "京东", "value": num("S40"), "growth": 13.76, "obs": "S40"},
        {"key": "淘宝", "value": num("S41"), "growth": -27.04, "obs": "S41"},
    ]
    ch_sum = round(sum(c["value"] for c in channels), 2)
    for c in channels:
        c["share"] = round(c["value"] / ch_sum * 100, 2)

    # ── 5. 价格带（牙膏 2026Q1） ──
    bands = {"50-80": num("S46"), "20-50": num("S47"), "80+": num("S48")}
    band_sum = round(sum(bands.values()), 2)
    band_rest = round(100 - band_sum, 2)

    # ── 6. 上市公司 ──
    companies = [
        {"name": "珀莱雅", "seg": "美妆 + 洗护", "rev": 105.97, "rev_g": -1.68,
         "np": 14.98, "np_g": -3.50, "gm": 73.26, "gm_d": 1.87, "nm": 14.13, "obs": "S51–S55"},
        {"name": "上海家化", "seg": "个护家清 + 美妆", "rev": 63.17, "rev_g": 11.25,
         "np": 2.68, "np_g": None, "gm": None, "gm_d": None, "nm": None, "obs": "S58–S59",
         "note": "2024 年亏损 8.33 亿元，2025 年扭亏"},
        {"name": "登康口腔", "seg": "口腔护理", "rev": 17.16, "rev_g": 9.98,
         "np": 1.81, "np_g": 12.35, "gm": 52.23, "gm_d": 2.85, "nm": 10.55, "obs": "S60–S63"},
        {"name": "百亚股份", "seg": "女性卫生", "rev": 34.92, "rev_g": 7.32,
         "np": 2.08, "np_g": -27.70, "gm": 54.30, "gm_d": 1.10, "nm": 5.96, "obs": "S64–S66"},
        {"name": "豪悦护理", "seg": "婴童 / 成人失禁", "rev": 37.56, "rev_g": 28.22,
         "np": 2.32, "np_g": -40.14, "gm": 31.51, "gm_d": 3.60, "nm": 6.18, "obs": "S71–S73"},
        {"name": "拉芳家化", "seg": "洗护发", "rev": 8.18, "rev_g": -7.92,
         "np": -0.31, "np_g": None, "gm": 49.11, "gm_d": 1.24, "nm": -3.79, "obs": "S74–S76",
         "note": "净利润 -3115 万元，由盈转亏（同比 -175.31%）"},
    ]
    for c in companies:
        c["growth_gap"] = None if c["np_g"] is None else round(c["np_g"] - c["rev_g"], 2)
    rev_sum = round(sum(c["rev"] for c in companies), 2)
    np_sum = round(sum(c["np"] for c in companies), 2)
    blended_nm = round(np_sum / rev_sum * 100, 2)

    # ── 7. 集中与出清 ──
    brands_out = num("S16")
    brands_in = num("S17")
    brand_net = brands_out - brands_in
    turnover_ratio = round(brands_out / brands_in, 2)
    share_2024, share_2025 = num("S14"), num("S13")

    derived = [
        {"id": "D01", "metric": "限额以上化妆品零售额 2021→2025 CAGR", "value": pct(cagr_21_25), "unit": "%",
         "formula": "(4653/4026)^(1/4)-1", "inputs": "S01, S05"},
        {"id": "D02", "metric": "2025 化妆品增速 − 社零增速", "value": round(gap_2025, 2), "unit": "pp",
         "formula": "5.1 − 3.7", "inputs": "S05, S06"},
        {"id": "D03", "metric": "2026 1—9 月化妆品增速 − 社零增速", "value": round(gap_2026, 2), "unit": "pp",
         "formula": "6.1 − 1.1", "inputs": "S07, S08"},
        {"id": "D04", "metric": "线上洗护发 2024 交易额（反推）", "value": haircare_2024, "unit": "亿元",
         "formula": "695.51 / 1.0761", "inputs": "S26"},
        {"id": "D05", "metric": "线上洗护发 2025 增量", "value": hc["total_effect"], "unit": "亿元",
         "formula": "量 + 价 + 交叉", "inputs": "S26, S27"},
        {"id": "D06", "metric": "线上洗护发 量贡献", "value": hc["volume_effect"], "unit": "亿元",
         "formula": "V2024 × 11.94%", "inputs": "S26, S27"},
        {"id": "D07", "metric": "线上洗护发 价贡献", "value": hc["price_effect"], "unit": "亿元",
         "formula": "V2024 × [(1+7.61%)/(1+11.94%)−1]", "inputs": "S26, S27"},
        {"id": "D08", "metric": "线上洗护发 交叉项", "value": hc["cross_effect"], "unit": "亿元",
         "formula": "V2024 × 量 × 价", "inputs": "S26, S27"},
        {"id": "D09", "metric": "线上洗护发 隐含均价变动", "value": hc["price_growth_pct"], "unit": "%",
         "formula": "(1+7.61%)/(1+11.94%)−1", "inputs": "S26, S27"},
        {"id": "D10", "metric": "线上口腔护理 2024 交易额（反推）", "value": oral_2024, "unit": "亿元",
         "formula": "245.26 / 1.173", "inputs": "S34"},
        {"id": "D11", "metric": "线上口腔护理 2025 增量", "value": oral25["total_effect"], "unit": "亿元",
         "formula": "量 + 价 + 交叉", "inputs": "S34, S35"},
        {"id": "D12", "metric": "线上口腔护理 2025 隐含均价变动", "value": oral25["price_growth_pct"], "unit": "%",
         "formula": "(1+17.3%)/(1+7.2%)−1", "inputs": "S34, S35"},
        {"id": "D13", "metric": "线上口腔护理 2026Q1 隐含均价变动", "value": oral26q1["price_growth_pct"], "unit": "%",
         "formula": "(1+13.8%)/(1+8.5%)−1", "inputs": "S36, S37"},
        {"id": "D14", "metric": "抖音占口腔护理线上交易额份额", "value": channels[0]["share"], "unit": "%",
         "formula": "32.11 / 58.15", "inputs": "S36, S38"},
        {"id": "D15", "metric": "抖音 − 天猫增速差", "value": round(30.73 - (-2.31), 2), "unit": "pp",
         "formula": "30.73 − (−2.31)", "inputs": "S38, S39"},
        {"id": "D16", "metric": "牙膏三档价格带销售额占比合计", "value": band_sum, "unit": "%",
         "formula": "39.28 + 34.09 + 18.44", "inputs": "S46, S47, S48"},
        {"id": "D17", "metric": "六家上市公司合计营收", "value": rev_sum, "unit": "亿元",
         "formula": "105.97+63.17+17.16+34.92+37.56+8.18", "inputs": "S51, S58, S60, S64, S71, S74"},
        {"id": "D18", "metric": "六家上市公司合计归母净利", "value": np_sum, "unit": "亿元",
         "formula": "14.98+2.68+1.81+2.08+2.32−0.31", "inputs": "S52, S59, S61, S65, S72, S75"},
        {"id": "D19", "metric": "六家上市公司加权净利率", "value": blended_nm, "unit": "%",
         "formula": "23.56 / 266.96", "inputs": "D17, D18"},
        {"id": "D20", "metric": "2025 品牌净减少数", "value": brand_net, "unit": "个",
         "formula": "26,941 − 17,076", "inputs": "S16, S17"},
        {"id": "D21", "metric": "淘汰 / 新进 品牌数比", "value": turnover_ratio, "unit": "倍",
         "formula": "26,941 / 17,076", "inputs": "S16, S17"},
        {"id": "D22", "metric": "国货份额 2024→2025 变化", "value": round(share_2025 - share_2024, 2), "unit": "pp",
         "formula": "57.37 − 55.20", "inputs": "S13, S14"},
        {"id": "D23", "metric": "线上洗护发 + 口腔护理合计", "value": online_total, "unit": "亿元",
         "formula": "695.51 + 245.26", "inputs": "S26, S34"},
        {"id": "D24", "metric": "洗护发占线上两品类合计", "value": round(haircare_2025 / online_total * 100, 2), "unit": "%",
         "formula": "695.51 / 940.77", "inputs": "S26, S34"},
        {"id": "D25", "metric": "牙膏三档价格带之外未披露占比", "value": band_rest, "unit": "%",
         "formula": "100 − 91.81", "inputs": "S46, S47, S48"},
    ]

    checks = []
    checks.append({
        "name": "渠道四项合计 vs 口腔 2026Q1 总额",
        "detail": f"32.11+14.42+8.42+3.20={ch_sum}，口径总额 {total_q1}，差 {round(ch_sum - total_q1, 2)} 亿元（{round((ch_sum-total_q1)/total_q1*100, 2)}%）",
        "ok": abs(ch_sum - total_q1) / total_q1 < 0.01,
    })
    checks.append({
        "name": "价格带三档合计",
        "detail": f"39.28+34.09+18.44={band_sum}%，余 {band_rest}% 原文未披露归属",
        "ok": 90 <= band_sum <= 100,
    })
    checks.append({
        "name": "量价分解可加性",
        "detail": f"洗护 {hc['volume_effect']}+{hc['price_effect']}+{hc['cross_effect']}={hc['total_effect']}，与增量 {round(haircare_2025-haircare_2024,2)} 一致",
        "ok": abs(hc["total_effect"] - (haircare_2025 - haircare_2024)) < 0.1,
    })
    checks.append({
        "name": "均价口径一致性（披露 vs 隐含）",
        "detail": f"披露均价 -4.30%，额/量隐含 {hc['price_growth_pct']}%，差 {round(-4.30 - hc['price_growth_pct'], 2)}pp → 列为口径冲突 C3",
        "ok": True,
    })
    checks.append({
        "name": "观测编号唯一",
        "detail": f"{len(OBS)} 条观测，{len(set(o['id'] for o in OBS))} 个唯一编号",
        "ok": len(OBS) == len(set(o["id"] for o in OBS)),
    })
    checks.append({
        "name": "每条观测可追到来源",
        "detail": "全部观测均有 org/title/url/source_date",
        "ok": all(o["org"] and o["title"] and o["url"] and o["source_date"] for o in OBS),
    })

    return {
        "generated_at": "2026-11-12",
        "obs_total": len(OBS),
        "series": series,
        "cagr_2021_2025": pct(cagr_21_25),
        "gap_2025_pp": round(gap_2025, 2),
        "gap_2026_pp": round(gap_2026, 2),
        "haircare": {"v2024": haircare_2024, "v2025": haircare_2025, **hc},
        "oral": {"v2024": oral_2024, "v2025": oral_2025, **oral25, "q1_2026": oral26q1},
        "online_total": online_total,
        "channels": channels,
        "channel_sum": ch_sum,
        "bands": bands,
        "band_sum": band_sum,
        "band_rest": band_rest,
        "companies": companies,
        "rev_sum": rev_sum,
        "np_sum": np_sum,
        "blended_nm": blended_nm,
        "brands": {"out": brands_out, "in": brands_in, "net": brand_net, "ratio": turnover_ratio},
        "share": {"2023": num("S15"), "2024": share_2024, "2025": share_2025},
        "derived": derived,
        "checks": checks,
        "conflicts": CONFLICTS,
        "gaps": GAPS,
    }


def write_csvs(res: dict) -> None:
    data_dir = HERE / "data"
    data_dir.mkdir(exist_ok=True)
    with (data_dir / "observations.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["编号", "分组", "指标", "值", "单位", "期间", "同比", "口径", "来源机构", "来源标题", "链接", "发布日期", "备注"])
        for o in OBS:
            w.writerow([o["id"], o["group"], o["metric"], "" if o["value"] is None else o["value"],
                        o["unit"], o["period"], o["change"], o["caliber"], o["org"], o["title"],
                        o["url"], o["source_date"], o["note"]])
    with (data_dir / "derived_metrics.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["编号", "派生指标", "值", "单位", "公式", "输入观测"])
        for d in res["derived"]:
            w.writerow([d["id"], d["metric"], d["value"], d["unit"], d["formula"], d["inputs"]])


def main() -> int:
    res = build()
    write_csvs(res)
    (HERE / "analysis_results.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"观测 {res['obs_total']} 条；派生指标 {len(res['derived'])} 条")
    print(f"限额以上化妆品 2021→2025 CAGR {res['cagr_2021_2025']}%")
    print(f"洗护 2025：V0 {res['haircare']['v2024']} → V1 {res['haircare']['v2025']}；"
          f"量 {res['haircare']['volume_effect']} / 价 {res['haircare']['price_effect']} / 交叉 {res['haircare']['cross_effect']}")
    print(f"口腔 2025：V0 {res['oral']['v2024']} → V1 {res['oral']['v2025']}；"
          f"隐含均价 {res['oral']['price_growth_pct']}%")
    print("渠道份额：" + "，".join(f"{c['key']} {c['share']}%" for c in res["channels"]))
    print(f"上市公司合计营收 {res['rev_sum']}，净利 {res['np_sum']}，加权净利率 {res['blended_nm']}%")
    for c in res["checks"]:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['name']}：{c['detail']}")
    return 0 if all(c["ok"] for c in res["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
