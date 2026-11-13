#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R06 端到端验收脚本（T10）。

一键跑完：demo → 全部技能 smoke → harness 门禁（干净/脏数据）→
contract 契约 → review 对抗评审 → case 案例库。任一失败返回非 0 退出码。

用法：
    python run_tests.py          # 全量
    python run_tests.py --no-fail # 跳过「必须失败」断言（仅供调试）
"""
from __future__ import annotations

import argparse
import json
import os

import subprocess
import sys
# --- 引导仓库根入 sys.path：本文件可被直接 `python xxx.py` 执行 ---
_boot = os.path.dirname(os.path.abspath(__file__))
while _boot and not os.path.isdir(os.path.join(_boot, "core")):
    _boot = os.path.dirname(_boot)
if _boot and _boot not in sys.path:
    sys.path.insert(0, _boot)
from core.workspace import role_workspace  # noqa: E402
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# 48 型图表库共享于 core/charts；测试需把该目录加入 import 路径。
_CHART_DIR = os.path.join(os.path.dirname(HERE), "core", "charts")
if _CHART_DIR not in sys.path:
    sys.path.insert(0, _CHART_DIR)


def run(argv):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "agent.py", *argv], cwd=HERE,
                       capture_output=True, text=True, encoding="utf-8", env=env)
    return r.returncode, r.stdout, r.stderr


def extract(stdout):
    marker = "__AGENT_RESULT__"
    i = stdout.find(marker)
    if i == -1:
        return None
    s = stdout[i + len(marker):].strip()
    try:
        return json.loads(s)
    except Exception:
        a, b = s.find("{"), s.rfind("}")
        return json.loads(s[a:b + 1]) if a != -1 and b != -1 else None


PASS = []
FAIL = []


def must_pass(name, argv, parse=False):
    rc, out, err = run(argv)
    data = extract(out) if parse else None
    ok = (rc == 0)
    (PASS if ok else FAIL).append(name)
    if not ok:
        print(f"  [FAIL] {name}\n    argv={' '.join(argv)}\n    rc={rc}\n"
              f"    out={out[-400:]}\n    err={err[-400:]}")
    else:
        print(f"  [ok] {name}")
    return data


def must_fail(name, argv):
    rc, out, err = run(argv)
    ok = (rc != 0)
    (PASS if ok else FAIL).append(name)
    if not ok:
        print(f"  [FAIL] {name} 预期非0退出，实际 rc=0\n    out={out[-300:]}")
    else:
        print(f"  [ok] {name}（预期失败，符合门禁）")


def must_check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'ok' if cond else 'FAIL'}] {name}  {detail}")


def _write_causal(path):
    """带真实混杂的模拟集（LCG 确定性）：会员→开闸概率与消费，真实处理效应=−6
    （fixed−dynamic）。causal 四步必须把混杂偏差从 naive 里剥离出来。"""
    s = 7

    def r01():
        nonlocal s
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        return s / 0x7FFFFFFF

    lines = ["user,is_member,hours_peak,treatment,spend"]
    for i in range(160):
        member = 1 if r01() < 0.5 else 0
        peak = round(r01(), 3)
        t = "dynamic" if r01() < (0.75 if member else 0.25) else "fixed"
        spend = 20 + 8 * member + (10 if peak > 0.5 else 0) + (6 if t == "dynamic" else 0)
        u = r01() * 6 - 3  # 简化正态扰动（够用，不必精确）
        lines.append(f"u{i},{member},{peak},{t},{round(spend + u, 2)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_clean(path):
    """写一份干净订单 CSV（无缺失、无哨兵值），供「干净必须 PASS」门禁断言。"""
    chans = ["抖音", "微信", "小红书", "知乎"]
    statuses = ["浏览", "加购", "支付", "下单"]
    lines = ["order_id,date,channel,status,user_id,amount"]
    for i in range(1, 21):
        amt = round(50 + i * 3.7, 2)
        lines.append(f"{i},2024-01-{i:02d},{chans[i % 4]},{statuses[i % 4]},u{i},{amt}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fail", action="store_true")
    args = ap.parse_args()

    print("== 1) demo 生成示例数据 + 语义模型 ==")
    _, out, _ = run(["demo"])
    d = extract(out)
    csv = d["demo_csv"]
    model = d["semantic_model"]
    print(f"  csv={csv}\n  model={model}")

    clean = os.path.join(role_workspace(HERE), "_tmp_clean.csv")
    _write_clean(clean)
    spec = os.path.join(role_workspace(HERE), "_tmp_chart_spec.json")
    with open(spec, "w", encoding="utf-8") as f:
        json.dump({"chart_type": "bar", "title": "各渠道营收",
                   "x_field": "label", "y_field": "value",
                   "data": [{"label": "抖音", "value": 120.0},
                            {"label": "微信", "value": 80.0}]}, f, ensure_ascii=False)
    saas_csv = os.path.join(role_workspace(HERE), "_tmp_saas.csv")
    with open(saas_csv, "w", encoding="utf-8") as f:
        f.write("customer_id,month,mrr,status\n"
                "c1,2024-01,100,active\nc2,2024-01,200,active\nc3,2024-01,300,active\n"
                "c1,2024-02,100,active\nc2,2024-02,250,active\n"
                "c3,2024-02,0,canceled\nc4,2024-02,150,active\n")
    pareto_spec = os.path.join(role_workspace(HERE), "_tmp_pareto_spec.json")
    with open(pareto_spec, "w", encoding="utf-8") as f:
        json.dump({"chart_type": "pareto", "title": "前 N 项贡献",
                   "category_field": "item", "value_field": "v",
                   "data": [{"item": "A", "v": 50.0}, {"item": "B", "v": 30.0}]},
                  f, ensure_ascii=False)
    print(f"  clean={clean}\n  chart_spec={spec}\n  saas_csv={saas_csv}")

    print("== 2) 全部技能 smoke（能力域5已拆细为 7 模块；explore/viz 看全 31 子技能 + 48 图表）==")
    must_pass("semantics.validate", ["semantics", "validate", "--input", model])
    must_pass("semantics.link", ["semantics", "link", "--input", model, "--data", csv])
    must_pass("semantics.compute", ["semantics", "compute", "--input", model, "--data", csv])
    must_pass("quality.audit", ["quality", "audit", "--input", csv, "--pk", "order_id", "--date", "date"])
    must_pass("explore.trend", ["explore", "trend", "--input", csv, "--date", "date", "--value", "amount"])
    must_pass("explore.groupby", ["explore", "groupby", "--input", csv, "--group", "channel", "--value", "amount"])
    must_pass("explore.funnel", ["explore", "funnel", "--input", csv, "--stage", "status"])
    must_pass("explore.cohort", ["explore", "cohort", "--input", csv, "--user", "user_id", "--period", "date"])
    must_pass("explore.rfm", ["explore", "rfm", "--input", csv, "--user", "user_id", "--date", "date", "--value", "amount"])
    must_pass("explore.time_series", ["explore", "time_series", "--input", csv, "--date", "date", "--value", "amount", "--window", "3"])
    must_pass("explore.segment", ["explore", "segment", "--input", csv, "--features", "amount", "--k", "3", "--user", "user_id"])
    must_pass("explore.metrics[saas]", ["explore", "metrics", "--input", saas_csv, "--model", "saas"])
    must_pass("explore.metrics[ecommerce]", ["explore", "metrics", "--input", csv, "--model", "ecommerce", "--value", "amount", "--customer", "user_id"])
    must_pass("rootcause.decompose", ["rootcause", "decompose", "--input", csv, "--dim", "channel", "--value", "amount", "--period", "date", "--before", "2024-01-01", "--after", "2024-12-31"])
    must_pass("rootcause.drilldown", ["rootcause", "drilldown", "--input", csv, "--dim", "channel", "--value", "amount"])
    must_pass("describe", ["describe", "--input", csv, "--col", "amount"])
    must_pass("correlate", ["correlate", "--input", csv, "--col-a", "amount", "--col-b", "amount"])
    must_pass("ttest", ["ttest", "--input", csv, "--value", "amount", "--group", "channel", "--group-a", "抖音", "--group-b", "微信"])
    must_pass("chi2", ["chi2", "--input", csv, "--row", "channel", "--col", "status"])
    must_pass("anova", ["anova", "--input", csv, "--value", "amount", "--group", "channel"])
    must_pass("regression", ["regression", "--input", csv, "--x", "amount", "--y", "amount"])
    must_pass("abtest", ["abtest", "--input", csv, "--group", "channel", "--control", "抖音", "--treatment", "微信", "--metric", "amount"])
    # 能力域5 拆细之八/九：power（功效设计，statsmodels 同口径）+ causal（dowhy 四步）
    causal_csv = os.path.join(role_workspace(HERE), "_tmp_causal.csv")
    _write_causal(causal_csv)
    pw_n = must_pass("power[n]", ["power", "--baseline", "0.15", "--mde", "0.03"], parse=True)
    pwn = pw_n["power"]["required_n_per_group"]
    must_check("power[n≈statsmodels 同口径]", 2200 <= pwn <= 2600, f"n={pwn}")
    pw_m = must_pass("power[mde反解]", ["power", "--baseline", "0.15", "--n-per-group", "1000"], parse=True)
    m = pw_m["power"]["mde_solvable"]
    must_check("power[mde∈(0.03,0.08)]", 0.03 < m < 0.08, f"mde={m}")
    pwrj = os.path.join(role_workspace(HERE), "_tmp_power_result.json")
    with open(pwrj, "w", encoding="utf-8") as f:
        json.dump(pw_n, f, ensure_ascii=False)
    must_pass("power.contract", ["contract", "validate", "--skill", "power", "--action", "power", "--output", pwrj])
    ca = must_pass("causal[4step]", ["causal", "--input", causal_csv, "--outcome", "spend",
                                     "--treatment", "treatment", "--confounders", "is_member,hours_peak",
                                     "--trials", "200", "--seed", "0"], parse=True)
    must_check("causal[contribution 顶层]", isinstance(ca.get("contribution"), dict))
    est = ca["causal"]["estimate"]
    must_check("causal[调整效应≈真值-6]", abs(est["adjusted_effect"] + 6) < 1.5,
               f"adj={est['adjusted_effect']}")
    must_check("causal[混杂偏差被剥离]", abs(est["confounding_bias"]) > 0.3,
               f"bias={est['confounding_bias']} naive={est['unadjusted_effect']}")
    must_check("causal[安慰剂通过]", ca["causal"]["refute"]["survives"] is True,
               f"p={ca['causal']['refute']['placebo_p']}")
    carj = os.path.join(role_workspace(HERE), "_tmp_causal_result.json")
    with open(carj, "w", encoding="utf-8") as f:
        json.dump(ca, f, ensure_ascii=False)
    must_pass("causal.contract", ["contract", "validate", "--skill", "causal", "--action", "causal", "--output", carj])
    must_pass("causal.review", ["review", "--result", carj, "--skill", "causal", "--action", "causal", "--data", causal_csv])
    must_pass("scinlp.describe", ["scinlp", "describe", "--input", csv, "--col", "amount"])
    must_pass("viz.spec", ["viz", "spec", "--input", spec])
    must_pass("viz.spec[pareto]", ["viz", "spec", "--input", pareto_spec])
    must_pass("viz.guide", ["viz", "guide", "--chart", "bar"])
    must_pass("viz.guide[all48]", ["viz", "guide"])
    # 48 提示词注册表接入 chart-spec 环节（viz.prompt / spec.prompt_meta / 注册表完整性）
    vp_all = must_pass("viz.prompt[all48]", ["viz", "prompt"], parse=True)
    must_check("viz.prompt[count==48]", vp_all.get("count") == 48,
               f"count={vp_all.get('count')}")
    must_check("viz.prompt[首尾对齐]",
               vp_all["items"][0]["id"] == "viz-01" and vp_all["items"][-1]["id"] == "viz-48",
               f"first={vp_all['items'][0]['id']} last={vp_all['items'][-1]['id']}")
    vp_c = must_pass("viz.prompt[control]", ["viz", "prompt", "--chart", "control"], parse=True)
    pc = vp_c.get("prompt", {})
    must_check("viz.prompt[control 模板含控制限]", "控制限" in pc.get("prompt_template", ""),
               f"id={pc.get('id')}")
    must_check("viz.prompt[control 检查清单非空]", len(pc.get("checklist", [])) >= 3,
               f"n={len(pc.get('checklist', []))}")
    vs = must_pass("viz.spec[prompt_meta]", ["viz", "spec", "--input", spec], parse=True)
    pm = vs.get("prompt_meta", {})
    must_check("viz.spec[附 prompt_id]", pm.get("prompt_id") == "viz-01",
               f"prompt_id={pm.get('prompt_id')}")
    must_check("viz.spec[附检查清单]", len(pm.get("checklist", [])) >= 3,
               f"n={len(pm.get('checklist', []))}")
    # 48 型图表库已上收为全角色共享（core/charts）。
    import chart_lib as _cl
    svg = _cl.funnel_chart({"title": "t", "stages": [{"label": "曝光", "value": 10000},
                                                    {"label": "到店", "value": 2400},
                                                    {"label": "办卡", "value": 480}]})
    must_check("render.funnel[主要流失点标注]", "主要流失点" in svg and "流失" in svg)
    svg = _cl.pareto_chart({"title": "t", "items": [{"label": "C区", "value": 43000},
                                                    {"label": "B区", "value": 3000},
                                                    {"label": "A区", "value": 2000},
                                                    {"label": "D区", "value": 2000}]})
    must_check("render.pareto[前N项+80%参考线]",
               "前 1 项累计贡献 86.0%" in svg and "累计 80%" in svg)
    svg = _cl.histogram_chart({"title": "t", "values": [15, 14, 16, 15, 14, 16, 13, 15, 17]})
    must_check("render.histogram[均值/中位参考线]",
               "均值" in svg and "中位" in svg)
    svg = _cl.scatter_chart({"title": "t", "points": [{"x": i, "y": 2.5 * i + 3} for i in range(12)]})
    must_check("render.scatter[OLS+非因果声明]", "r=" in svg and "非因果" in svg)
    svg = _cl.grouped_bar_chart({"title": "t", "categories": ["C区", "B区"],
                                 "series": [{"name": "九月", "values": [95, 27]},
                                            {"name": "十月", "values": [52, 30], "accent": True}]})
    must_check("render.grouped_bar[图例+值标注]",
               svg.count("<rect") >= 4 and "十月" in svg)
    must_check("render[覆盖 48 型]",
               len(_cl.RENDERERS) == 48
               and {c["key"] for c in _cl.CHART_INDEX} == set(_cl.RENDERERS),
               f"n={len(_cl.RENDERERS)}")
    # 渲染器统一由 core 提供；角色目录不再保留副本。
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
    import report_renderer as _rr
    bad = {"doc_type": "t", "title_lines": ["t"], "standfirst": "", "metric_strip": [],
           "summary": [], "notes": [], "footer": "",
           "sections": [{"title": "x", "chart": {
               "title": "c", "unit_meta": "元", "source": "s", "type": "grouped_bar",
               "categories": ["a"],
               "series": [{"name": f"系{i}", "values": [1]} for i in range(4)]}}]}
    must_check("render.gate[grouped_bar>3 拒绝]",
               "系列超过 3" in str(_rr.validate_contract(bad)))

    # ---- 第八轮：38 型扩展渲染器（chart_renderers_ext）逐一 smoke + 纪律落码断言 ----
    import chart_renderers_ext as _ce
    XS = {
        "vbar": ({"title": "t", "categories": ["A", "B", "C"], "values": [10, 20, 15],
                  "accent_idx": 1}, ["纵轴自 0", "20"]),
        "hbar": ({"title": "t", "items": [{"label": "A", "value": 30, "accent": True},
                                          {"label": "B", "value": 20}], "top_n": 2},
                 ["按值降序", "Top 2"]),
        "stacked_bar": ({"title": "t", "categories": ["Q1", "Q2"],
                         "segments": [{"name": "新客", "values": [10, 20]},
                                      {"name": "老客", "values": [30, 25]}]},
                        ["Σ 40", "各分段之和"]),
        "pct_stacked": ({"title": "t", "categories": ["Q1", "Q2"],
                         "segments": [{"name": "新客", "values": [10, 20]},
                                      {"name": "老客", "values": [30, 25]}]},
                        ["n=40", "合计 100%"]),
        "area": ({"title": "t", "xlabels": ["1月", "2月", "3月"],
                  "series": [{"name": "营收", "values": [10, 12, 15]}]},
                 ["纵轴自 0 起", "当期值"]),
        "pie": ({"title": "t", "items": [{"label": "A", "value": 40, "accent": True},
                                         {"label": "B", "value": 30},
                                         {"label": "C", "value": 20},
                                         {"label": "D", "value": 5},
                                         {"label": "E", "value": 3},
                                         {"label": "F", "value": 2}]},
                ["其他", "合计 100", "顺时针"]),
        "donut": ({"title": "t", "items": [{"label": "A", "value": 40, "accent": True},
                                           {"label": "B", "value": 30},
                                           {"label": "C", "value": 20}]},
                  ["同口径", "合计"]),
        "dumbbell": ({"title": "t", "items": [{"label": "A", "a": 10, "b": 18},
                                              {"label": "B", "a": 12, "b": 9}],
                      "a_label": "去年", "b_label": "今年"},
                     ["共同尺度", "+8"]),
        "dot": ({"title": "t", "items": [{"label": "A", "value": 30, "accent": True},
                                         {"label": "B", "value": 20}]},
                ["按值降序", "无图例"]),
        "lollipop": ({"title": "t", "items": [{"label": "A", "value": 30, "accent": True},
                                              {"label": "B", "value": 20}], "top_n": 2},
                     ["茎线非柱形", "Top 2"]),
        "waffle": ({"title": "t", "items": [{"label": "A", "value": 40, "accent": True},
                                            {"label": "B", "value": 35},
                                            {"label": "C", "value": 25}]},
                   ["每格 = 1%", "格）"]),
        "bubble": ({"title": "t", "points": [{"x": 1, "y": 2, "size": 30, "label": "P1",
                                              "accent": True},
                                             {"x": 2, "y": 3, "size": 20, "label": "P2"},
                                             {"x": 3, "y": 1, "size": 10, "label": "P3"}]},
                   ["面积映射", "气泡大小"]),
        "heatmap": ({"title": "t", "rows": ["R1", "R2"], "cols": ["C1", "C2", "C3"],
                     "cells": [[1, 2, None], [3, 0, 2]]},
                    ["缺失", "单色阶"]),
        "radar": ({"title": "t", "axes": ["速度", "成本", "质量", "交付", "服务"],
                   "series": [{"name": "我方", "values": [4, 3, 5, 4, 3], "accent": True},
                              {"name": "对手", "values": [3, 4, 3, 3, 4]}]},
                  ["统一尺度", "不是总分"]),
        "violin": ({"title": "t", "groups": [{"label": "A", "values": [1, 2, 2, 3, 3, 3, 4, 4, 5],
                                              "accent": True},
                                             {"label": "B", "values": [2, 3, 3, 4, 4, 5, 5, 6]}]},
                   ["n=9", "中位"]),
        "ridgeline": ({"title": "t", "groups": [{"label": "2023", "values": [1, 2, 2, 3, 3, 4]},
                                                {"label": "2024", "values": [2, 3, 3, 4, 4, 5],
                                                 "accent": True}]},
                      ["共享横轴", "峰"]),
        "parallel": ({"title": "t", "axes": ["成本", "速度", "质量"],
                      "items": [{"name": "甲", "values": [3, 4, 2], "accent": True},
                                {"name": "乙", "values": [4, 2, 4]},
                                {"name": "丙", "values": [2, 3, 3]}]},
                     ["标准化", "甲"]),
        "error_bar": ({"title": "t", "err_type": "SD",
                       "items": [{"label": "A", "value": 10, "err": 2, "accent": True},
                                 {"label": "B", "value": 12, "err": 3}]},
                      ["误差口径：SD", "10.0±2.0"]),
        "forest": ({"title": "t", "items": [{"label": "A", "est": 1.2, "lo": 0.8, "hi": 1.6,
                                             "accent": True},
                                            {"label": "B", "est": 0.9, "lo": 0.5, "hi": 1.3}]},
                    ["无效应基线", "非因果"]),
        "bullet": ({"title": "t", "label": "续费率", "value": 82, "target": 90, "unit": "%",
                    "bands": [{"to": 70, "label": "差"}, {"to": 85, "label": "中"},
                              {"to": 100, "label": "优"}], "target_source": "年度目标"},
                   ["目标 90", "达成"]),
        "gauge": ({"title": "t", "value": 72, "min": 0, "max": 100, "target": 85, "unit": "%"},
                  ["距目标", "文字状态"]),
        "cal_heatmap": ({"title": "t", "days": [{"date": "2026-10-01", "value": 5},
                                                {"date": "2026-10-02", "value": 8},
                                                {"date": "2026-10-04", "value": 0},
                                                {"date": "2026-10-05", "value": 12}],
                         "unit": "次"},
                        ["10月", "缺失（≠0）"]),
        "gantt": ({"title": "t", "tasks": [{"label": "调研", "start": "2026-10-01",
                                            "end": "2026-10-10", "accent": True},
                                           {"label": "上线", "start": "2026-10-26",
                                            "end": "2026-10-26", "milestone": True}],
                   "today": "2026-10-15"},
                  ["今日", "里程碑"]),
        "candlestick": ({"title": "t", "candles": [{"label": "10-01", "open": 10, "high": 12,
                                                    "low": 9, "close": 11},
                                                   {"label": "10-02", "open": 11, "high": 11.5,
                                                    "low": 9.5, "close": 10, "accent": True}]},
                        ["红涨绿跌", "合法性校验"]),
        "sankey": ({"title": "t", "nodes": [{"id": "s", "label": "线索"},
                                            {"id": "m", "label": "商机"},
                                            {"id": "w", "label": "成交"}],
                    "links": [{"from": "s", "to": "m", "value": 100},
                              {"from": "m", "to": "w", "value": 40}]},
                   ["主路径", "100"]),
        "streamgraph": ({"title": "t", "xlabels": ["1月", "2月", "3月"],
                         "series": [{"name": "话题A", "values": [10, 12, 11], "accent": True},
                                    {"name": "话题B", "values": [6, 8, 7]}]},
                        ["最新值", "话题A"]),
        "treemap": ({"title": "t", "items": [{"label": "A", "value": 50, "accent": True},
                                             {"label": "B", "value": 30},
                                             {"label": "C", "value": 15}]},
                    ["squarify", "面积∝数值"]),
        "sunburst": ({"title": "t", "root": {"label": "总", "children": [
            {"label": "A", "value": 50, "accent": True,
             "children": [{"label": "A1", "value": 30}, {"label": "A2", "value": 20}]},
            {"label": "B", "value": 40}]}},
                      ["水平", "层级"]),
        "choropleth": ({"title": "t", "regions": [{"name": "广东", "value": 120},
                                                  {"name": "浙江", "value": 80},
                                                  {"name": "新疆", "value": None},
                                                  {"name": "西藏", "value": 0},
                                                  {"name": "某国", "value": 50}],
                        "unit": "万元"},
                       ["匹配率", "未匹配"]),
        "symbol_map": ({"title": "t", "points": [{"name": "北京", "lon": 116.4, "lat": 39.9,
                                                  "value": 300, "accent": True},
                                                 {"name": "上海", "lon": 121.5, "lat": 31.2,
                                                  "value": 260}], "unit": "万元"},
                       ["等距圆柱", "面积映射"]),
        "geo_flow": ({"title": "t", "points": [{"id": "bj", "name": "北京", "lon": 116.4,
                                                "lat": 39.9},
                                               {"id": "sh", "name": "上海", "lon": 121.5,
                                                "lat": 31.2}],
                      "flows": [{"from": "bj", "to": "sh", "value": 100}]},
                     ["主通道", "100"]),
        "network": ({"title": "t", "nodes": [{"id": "a", "label": "甲", "size": 10,
                                              "accent": True},
                                             {"id": "b", "label": "乙"},
                                             {"id": "c", "label": "丙"}],
                     "edges": [{"a": "a", "b": "b", "weight": 5},
                               {"a": "a", "b": "c", "weight": 3}],
                     "node_size_label": "客户数"},
                    ["各自只表达一个指标", "环形等比"]),
        "rose": ({"title": "t", "sectors": [{"label": "N", "value": 30},
                                            {"label": "NE", "value": 50, "accent": True},
                                            {"label": "E", "value": 20},
                                            {"label": "SE", "value": 35},
                                            {"label": "S", "value": 25},
                                            {"label": "W", "value": 15}]},
                 ["面积∝数值", "√"]),
        "target_band": ({"title": "t", "xlabels": ["1月", "2月", "3月"],
                         "series": [{"name": "达成", "values": [88, 92, 95]}],
                         "band": {"lo": 90, "hi": 95, "label": "合格区间"}},
                        ["目标带", "合格区间"]),
        "bridge": ({"title": "t", "start": {"label": "1月", "value": 100},
                    "deltas": [{"label": "新客户", "value": 30},
                               {"label": "流失", "value": -25}],
                    "end": {"label": "2月", "value": 105}},
                   ["回到终点", "排名"]),
        "dual_axis": ({"title": "t", "xlabels": ["1月", "2月"],
                       "bars": {"name": "营收", "values": [100, 120], "unit": "万元"},
                       "line": {"name": "毛利率", "values": [30, 32], "unit": "%"}},
                      ["自 0 起", "不同单位"]),
        "kpi_break": ({"title": "t", "kpi": {"label": "月度营收", "value": 128, "unit": "万",
                                             "delta_label": "环比 +12%"},
                       "trend": {"xlabels": ["7月", "8月", "9月"], "values": [100, 110, 118]},
                       "breakdown": {"items": [{"label": "新客户", "value": 18, "accent": True},
                                               {"label": "流失", "value": -4}]}},
                      ["驱动拆解", "口径"]),
        "small_mult": ({"title": "t", "panels": [
            {"title": "华东", "xlabels": ["1月", "2月"], "values": [30, 35], "accent": True},
            {"title": "华南", "xlabels": ["1月", "2月"], "values": [20, 21]},
            {"title": "华北", "xlabels": ["1月", "2月"], "values": [25, 27]},
            {"title": "西南", "xlabels": ["1月", "2月"], "values": [10, 14]}]},
                       ["共享同一纵轴尺度", "华东"]),
    }
    for k, (sample, marks) in XS.items():
        svg = _ce.RENDERERS[k](sample)
        must_check(f"render.ext[{k}]",
                   svg.startswith("<svg") and svg.endswith("</svg>")
                   and "NaN" not in svg and all(m in svg for m in marks),
                   f"marks={marks}")

    # 纪律负例门禁（validate_contract 层）
    def _gate_chart(t: str, ch: dict) -> str:
        return str(_rr.validate_contract({
            "doc_type": "t", "title_lines": ["t"], "standfirst": "", "metric_strip": [],
            "summary": [], "notes": [], "footer": "",
            "sections": [{"title": "x", "chart": {"title": "c", "unit_meta": "u",
                                                  "source": "s", "type": t, **ch}}]}))
    must_check("render.gate[radar>2 拒绝]",
               "超过 2" in _gate_chart("radar", {"axes": ["a", "b", "c"],
                   "series": [{"name": str(i), "values": [1, 2, 3]} for i in range(3)]}))
    must_check("render.gate[error_bar 无口径拒绝]",
               "SD/SE/CI" in _gate_chart("error_bar", {"items": [{"label": "A", "value": 1,
                                                                   "err": 1}]}))
    must_check("render.gate[candlestick OHLC 非法拒绝]",
               "非法" in _gate_chart("candlestick", {"candles": [{"label": "x", "open": 10,
                   "high": 11, "low": 9, "close": 12}]}))
    must_check("render.gate[bridge 不回终点拒绝]",
               "回到终点" in _gate_chart("bridge", {"start": {"label": "s", "value": 100},
                   "deltas": [{"label": "d", "value": 10}],
                   "end": {"label": "e", "value": 120}}))
    must_check("render.gate[small_mult>6 拒绝]",
               "超过 6" in _gate_chart("small_mult", {"panels": [
                   {"title": str(i), "xlabels": ["a", "b"], "values": [1, 2]}
                   for i in range(7)]}))
    must_check("render.gate[gauge 超范围拒绝]",
               "不在" in _gate_chart("gauge", {"value": 120, "min": 0, "max": 100}))
    must_check("render.gate[area 多系列拒绝]",
               "单系列" in _gate_chart("area", {"xlabels": ["a", "b"],
                   "series": [{"name": "x", "values": [1, 2]},
                              {"name": "y", "values": [2, 3]}]}))

    print("== 3) harness 确定性门禁（干净数据必须 PASS）==")
    report = os.path.join(role_workspace(HERE), "_tmp_report.md")
    os.makedirs(os.path.dirname(report), exist_ok=True)
    with open(report, "w", encoding="utf-8") as f:
        f.write("# 结论\n抖音渠道贡献 62% 营收，Q3 利润率 15.2%，属健康水平。\n\n"
                "## QA 清单\n- 数据来源 orders.csv（59 行）\n")
    plan = os.path.join(role_workspace(HERE), "_tmp_plan.json")
    with open(plan, "w", encoding="utf-8") as f:
        json.dump({
            "round": 1, "analytical_step": "decomposition",
            "question": "按渠道拆解收入贡献",
            "query_spec": {"metrics": ["amount"], "group_by": ["channel"],
                           "date_range": {"start": "2024-01-01", "end": "2024-12-31"}},
            "expected_output": {"format": "json", "required_fields": ["segments"]},
            "acceptance_criteria": {"min_rows": 1, "all_required_fields": True},
            "stop_condition": {"if_impact_below_pct": 3.0, "reason": "minor 停止"}},
            f, ensure_ascii=False)

    must_pass("harness.dataset", ["harness", "dataset", "--input", clean, "--semantic", model])
    must_pass("harness.report", ["harness", "report", "--input", report])
    must_pass("harness.semantic", ["harness", "semantic", "--input", model])
    must_pass("harness.plan", ["harness", "plan", "--input", plan])
    must_pass("harness.verify", ["harness", "verify", "--data", clean, "--report", report, "--semantic", model])

    print("== 4) 契约 / 评审 / 案例 ==")
    must_pass("contract.list", ["contract", "list"])
    rj = os.path.join(role_workspace(HERE), "_tmp_result.json")
    with open(rj, "w", encoding="utf-8") as f:
        json.dump({"describe": {"amount": {"count": 59, "mean": 1922.7}}}, f)
    must_pass("contract.validate", ["contract", "validate", "--skill", "describe", "--action", "describe", "--output", rj])

    # review.pass：用真实 rootcause.decompose 输出做合法评审（含证据分解）
    _, dout, _ = run(["rootcause", "decompose", "--input", csv, "--dim", "channel",
                      "--value", "amount", "--period", "date",
                      "--before", "2024-01-01", "--after", "2024-12-31"])
    drj = os.path.join(role_workspace(HERE), "_tmp_decompose_result.json")
    with open(drj, "w", encoding="utf-8") as f:
        json.dump(extract(dout), f, ensure_ascii=False)
    must_pass("review.pass", ["review", "--result", drj, "--skill", "rootcause",
                              "--action", "decompose", "--data", csv])
    must_pass("case.list", ["case", "list"])
    for cid in ["retail-profitability", "demo-orders", "ab-experiment", "selfmedia-dashboard"]:
        must_pass(f"case.validate[{cid}]", ["case", "validate", "--case", cid])
    must_pass("harness.runlog", ["harness", "runlog", "--n", "3"])

    print("== 5) 门禁不得是摆设：脏数据/幻觉/伪造结论必须 FAIL ==")
    if not args.no_fail:
        dirty = os.path.join(role_workspace(HERE), "_tmp_dirty.csv")
        with open(dirty, "w", encoding="utf-8") as f:
            f.write("order_id,channel,amount\n1,抖音,100\n2,抖音,\n3,抖音,200\n"
                    "4,抖音,150\n5,抖音,\n6,抖音,99999\n7,抖音,\n")
        must_fail("harness.dataset[脏数据缺列]", ["harness", "dataset", "--input", dirty])

        hallu = os.path.join(role_workspace(HERE), "_tmp_hallu_model.json")
        with open(hallu, "w", encoding="utf-8") as f:
            f.write(json.dumps({"semantic_models": [{"name": "m",
                "entities": [{"name": "orders", "expr": "not_a_real_table"}],
                "dimensions": [{"name": "ghost", "expr": "no_such_column"}],
                "measures": [{"name": "amt", "expr": "amount"}]}], "metrics": []}))
        must_fail("semantics.link[幻觉列]", ["semantics", "link", "--input", hallu, "--data", csv])

        contr = os.path.join(role_workspace(HERE), "_tmp_bad_result.json")
        with open(contr, "w", encoding="utf-8") as f:
            f.write('{"conclusion": "渠道A导致收入下降，建议加大投入"}')
        must_fail("review[点名因果无分解证据]",
                  ["review", "--result", contr, "--skill", "rootcause",
                   "--action", "drilldown", "--data", csv])
        bad = os.path.join(role_workspace(HERE), "_tmp_empty.json")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("{}")
        must_fail("contract.validate[缺必填字段]",
                  ["contract", "validate", "--skill", "describe", "--action", "describe", "--output", bad])

    # 6) 每个技能产出的验证闭环（真实运行 → 契约校验 → 对抗评审）
    print("\n== 6) 每个技能产出的验证闭环（contract + review 双重验证）==")
    import verify_loop as vl
    loop_data = vl.prepare()
    loop_plan = vl.build_plan(loop_data)
    for r in vl.run_closed_loop(loop_plan):
        ok = r.get("contract_ok") and r.get("review_verdict") == "PASS"
        name = f"closed-loop.{r['skill']}.{r['action']}"
        (PASS if ok else FAIL).append(name)
        print(f"  [{'ok' if ok else 'FAIL'}] {name}"
              f"  contract={'OK' if r.get('contract_ok') else 'X'}"
              f"  review={r.get('review_verdict')}")

    # 7) 十维演进集成回归套件 (L01~L10)
    print("\n== 7) 十维演进元模型集成测试套件 (L01~L10 Dual Zero-Regression Gate) ==")
    import unittest
    import tests.test_engines_l01_l10 as t_l10
    import tests.test_evolution_cycle2 as t_c2
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(t_l10.TestR06EvolutionSuite)
    for case_name in ("TestRound1ToolsIntentHeal", "TestRound2SpecSlopScenario",
                      "TestRound3BundlePatchMemoryResilience"):
        case = getattr(t_c2, case_name, None)
        if case is not None:
            suite.addTests(loader.loadTestsFromTestCase(case))
    runner = unittest.TextTestRunner(verbosity=0)
    res = runner.run(suite)
    l10_ok = res.wasSuccessful()
    (PASS if l10_ok else FAIL).append("metamodel.10stages.l01_to_l10")
    print(f"  [{'ok' if l10_ok else 'FAIL'}] metamodel.10stages.l01_to_l10 (ran {res.testsRun} tests)")

    print("\n================ 验收结果 ================")
    print(f"  PASS {len(PASS)} / {len(PASS)+len(FAIL)}")
    if FAIL:
        print("  失败项：")
        for n in FAIL:
            print(f"    - {n}")
        sys.exit(1)
    print("  ALL GREEN")
    sys.exit(0)


if __name__ == "__main__":
    main()
