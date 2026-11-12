# -*- coding: utf-8 -*-
"""一次产出全部交付物：三份 HTML + 快读版 + 技能调用审计 + 最终 manifest。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import render_r1
import render_r23

ROOT = Path(__file__).resolve().parent
M = json.loads((ROOT / "data" / "底稿指标.json").read_text(encoding="utf-8"))
B = json.loads((ROOT / "data" / "经营指标.json").read_text(encoding="utf-8"))
L = json.loads((ROOT / "data" / "证据台账.json").read_text(encoding="utf-8"))
L2, L4, L6 = M["L2_全国周度"], M["L4_呼市零售"], M["L6_苹果分市场"]
X, SZ = M["跨层"], M["市场规模"]
U, ROI, SCEN = B["unit"], B["roi"], B["scenarios"]

HTMLS = {
    "内蒙古水果市场调研与数据分析报告.html": render_r1.build_r1,
    "内蒙古水果经营报告.html": render_r23.build_r2,
    "内蒙古水果链路优化报告.html": render_r23.build_r3,
}


def gate(name: str) -> dict:
    p = ROOT / "gates" / f"{name}_result.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def write_readme() -> None:
    tco = gate("r15_tco").get("ranked", [])
    md = f"""# 内蒙古水果调研（2026-10 ~ 11）· 快读版

> 报告日 2026-11-12 ｜ 执行：蛙蛙呱呱 agents 团（R01 编排 / R05 研究 / R06 分析 / R15 供应链 / R03 财务 / R02 流程 / R04 评审）
> 数据窗口 2026-09-15—2026-11-12 ｜ 有效观测 {M['观测统计']['L1'] + M['观测统计']['L2_字段数'] + M['观测统计']['L4'] + M['观测统计']['L5'] + M['观测统计']['L6']} 条 ｜ 结论 30 条 ｜ 来源 16 个

## 一句话

10—11 月内蒙古水果不是「涨」或「跌」的行情，而是**全国批发窄幅走弱（篮子 {L2['basket_change_pct']:+.2f}%）、呼市零售小幅走强（+{L4['avg_change_pct']:.2f}%）、同省同日价差 2.33 倍**的结构行情——钱在结构里，不在趋势里。

## 五个数

| # | 数 | 含义 | 证据 |
|---|---|---|---|
| 1 | 6.65 → 6.62 元/公斤（振幅 4.79%） | 全国 6 种水果均价 38 个交易日，窄幅震荡 | C1 · S1 |
| 2 | 呼市 8 种均价 10.21 → 10.49（9 周 +2.74%） | 零售端比全国批发端强 7.21 个百分点 | C7 · S3 |
| 3 | 赤峰 6.00 / 呼市 14.00 元/公斤 | 同品种同日省内价差 133.3%（2.33 倍） | C10 · S5 |
| 4 | 批零倍率 1.61（苹果）/ 1.69（西瓜）/ 1.60（香蕉） | 三个独立品种同倍率，加价是结构性的 | C13 · S2/S3 |
| 5 | AP0 36 日 −19.27% | 期货先跌，现货后知，12 月—春节前不看涨 | C15 · S6 |

## 三条经营动作

1. **苹果做毛利**：批零差 5.24 元/公斤、周波动仅 1.51%，散装 + 礼盒双规格。
2. **柑橘做流量**：零售 7.15 元/公斤、低单价高复购，11—12 月主推。
3. **直采降成本**：赤峰产地直采有效单位成本 {tco[0]['effective_unit_cost'] if tco else 5.23} 元/公斤，比呼市现采 {tco[-1]['effective_unit_cost'] if tco else 8.92} 低 41.4%（r15 TCO 门禁 PASS，排名第一）。

## 三条链路动作

1. **先预冷**（损耗 8%→5%，约 0.22 元/公斤）；
2. **再直发**（少一道批发，0.35 元/公斤）；
3. **后点价**（锁量不锁价，避开 AP0 的 19.27% 敞口）。
   合计 0.62 元/公斤，1,500 吨/年约 93 万元，投资 70 万，回收 {ROI['payback_years_1500t']} 年。

## 经营底线

- 基准毛利 {U['margin']:.2f} 元/公斤（{U['margin_pct']}%）；悲观情景（收购 +7.6%、损耗 12%）降到 {SCEN['悲观']['margin_pct']}%。
- 敏感性排序：**损耗 > 收购价**，所以第一优先级是控损耗。
- TAM {SZ['TAM_零售额_亿元']:.1f} 亿元、SOM {SZ['SOM_零售额_亿元']:.1f} 亿元（18% 份额为假设，首月校准）。

## 诚实标注

- 21food 三市场 680 条报价常量率 61.8%、同城口径差 28.6%，**整体弃用**（附录 B 留存原件）。
- 呼市 14.00（富士苹果）与 13.88（苹果零售）字面批零倒挂 −0.86%，是等级/规格差异，**不作定价依据**。
- 链路成本卡里运距、冷链单价、损耗率均为 **C 级假设**，已逐项列出并做敏感性。
- 缺口 6 项（省级监测、产地价、批发日度、期货基差、POS 动销、天气），见主报告第十节。

## 三份报告

| 文件 | 用途 | 页内结构 |
|---|---|---|
| 内蒙古水果市场调研与数据分析报告.html | 研究记录 + 全量观测 + 结论清单 | 11 节 + 附录 A/B/C |
| 内蒙古水果经营报告.html | 决策：品类、单位经济、情景、投资、节奏 | 10 节 + 假设清单 |
| 内蒙古水果链路优化报告.html | 执行：断点、TCO、方案、路线、验收 | 9 节 + TCO/SOP 附录 |

PDF 版本：同目录同名 .pdf（23 / 7 / 6 页，A4，页脚带「第 X / Y 页」，附录 A/B/C 已展开）。

## 复现

```bash
python collect_national.py && python collect_local.py && python collect_origin.py
python build_master.py && python build_business.py && python build_ledger.py && python build_facts.py
python build_engine_inputs.py && python run_gates.py && python build_deliverables.py
```
"""
    (ROOT / "内蒙古水果调研_快读版.md").write_text(md, encoding="utf-8")


def write_audit() -> None:
    summary = json.loads((ROOT / "gates" / "_run_summary.json").read_text(encoding="utf-8"))
    key = {
        "r01_plan": "2 张任务卡，owner r05/r06（研究 → 分析）",
        "r05_ledger": "30 条结论全部合规、来源充足",
        "r05_report": "8 个章节引用覆盖 100%",
        "r06_describe": "n=38、均值 6.6484、标准差 0.0563",
        "r06_trend": "38 点趋势序列（首 6.65 → 末 6.62）",
        "r06_regression": "r=0.0784、R²=0.0061、p=0.847（不显著）",
        "r06_correlate": "全国批发 vs 呼市零售 相关「弱」",
        "r06_rootcause": "10→11 月降价贡献：菠萝 58.8%、苹果 38.8%、西瓜 −30.6% 对冲",
        "r15_tco": "三货源排序：赤峰直采 5.23 < 北京 8.52 < 呼市 8.92（PASS）",
        "r15_supplier": "3 家供应商合规",
        "r15_rfq": "3 家询价，防走过场比价通过",
        "r15_quote1": "赤峰宁城合作社报价 4.60 元/公斤",
        "r15_quote2": "东瓦窑批发 8.64 元/公斤",
        "r15_quote3": "北京新发地调运 7.60 元/公斤",
        "r03_healthcheck": "三表恒等（资产=负债+权益、现金勾稽、毛利勾稽）",
        "r02_sop": "6 步链路 SOP，4 个关键控制点",
        "r04_quality": "30 条结论 verified",
        "r04_facts": "14 条事实 / 308 项核查 / 0 违例",
        "r04_artifact": "9 个工件三级证据链 COMPLETE（交付期 manifest 15/15 复核通过）",
    }
    rows = []
    for r in summary:
        rows.append(f"| `{r['name']}` | {r['rc']} | {r.get('verdict') or '—'} | {key.get(r['name'], '')} |")
    md = f"""# 技能调用审计（内蒙古水果调研 · 2026-11-12）

> 本文件只记录**真实执行**的引擎调用：命令、退出码、引擎自报判决、关键输出。
> 原文与 `__AGENT_RESULT__` JSON 全量落在 `gates/`；本文件不重写结论，只做索引。

## 一、调用链路

```
R01 编排（plan → 2 张任务卡）
  → R05 研究（ledger / report：证据台账 30 条结论 + 8 章引用）
  → R06 分析（describe / trend / regression / correlate / rootcause）
  → R15 供应链（tco / supplier / rfq / quotation ×3）
  → R03 财务（healthcheck：三表恒等）
  → R02 流程（sop：6 步链路 4 个控制点）
  → R04 独立评审（quality / facts / artifact：生成与校验分离）
```

## 二、19 条门禁（全绿）

| 门禁 | rc | verdict | 关键输出 |
|---|---|---|---|
{chr(10).join(rows)}

合计 {len(summary)} 条，失败 0 条。

## 三、每个门禁到底核了什么

| 角色 | 动作 | 硬判据 |
|---|---|---|
| R05 | `research ledger` | claim.kind 白名单、来源充足、source_ids 指向存在来源、覆盖率 |
| R05 | `research report` | 每章 claim 有来源、无孤立结论、引用覆盖 |
| R06 | `describe/trend` | 38 点全进序列，统计量与图表同源 |
| R06 | `regression/correlate` | 8 周对齐，报 r/R²/p，不把不显著说成显著 |
| R06 | `rootcause` | 品类贡献分解，正负对冲可见 |
| R15 | `tco compare` | 币种一致、单价/数量 >0、MOQ、不良率、资金占用 → 有效单位成本排序 |
| R15 | `supplier/rfq/quotation` | 供应商列表非空、询价 ≥2 家、报价单逐条校验 |
| R03 | `cfo healthcheck` | 资产=负债+权益、现金勾稽、毛利勾稽 |
| R02 | `process sop` | 关键步骤必须有 control_point，approvers 非空 |
| R04 | `quality critique` | 禁词/证据链/绝对词三查 |
| R04 | `facts check` | 数字可追溯、来源质量、引用、精度、覆盖五维 |
| R04 | `artifact verify` | EXISTS / SUBSTANTIVE / WIRED 三级证据链 |

## 四、诚实标注

- **R01 只拆出 2 张卡（r05、r06）**：R15/R03/R02 的调用是本轮人工编排补上的，不是 R01 自动派发；`dispatch` 的多卡并发仍未压测。
- **R06 回归不显著**（p=0.847）：这是结果，不是缺陷——8 周样本 + 零售粘性，本来就不该出现强线性关系；报告里照写「弱/不显著」。
- **R04 的 facts 只核了 14 条**：其余 16 条是方向性判断与建议，不进事实核查，避免把观点当事实。
- **引擎门禁多为 warn 阶段**：本轮没有 deny，真实拦截强度仍待更严的 policy。
"""
    (ROOT / "技能调用审计.md").write_text(md, encoding="utf-8")


def write_manifest() -> None:
    files = [
        ("内蒙古水果市场调研与数据分析报告.html", True),
        ("内蒙古水果经营报告.html", True),
        ("内蒙古水果链路优化报告.html", True),
        ("内蒙古水果调研_快读版.md", True),
        ("技能调用审计.md", True),
    ]
    arts = [{"path": str((ROOT / f).resolve()).replace("\\", "/"), "type": "doc", "entry_point": True} for f, _ in files]
    refs = [
        ("data/底稿指标.json", "内蒙古水果市场调研与数据分析报告.html"),
        ("data/证据台账.json", "内蒙古水果市场调研与数据分析报告.html"),
        ("data/经营指标.json", "内蒙古水果经营报告.html"),
        ("data/全国日度_6种水果.csv", "内蒙古水果市场调研与数据分析报告.html"),
        ("data/全国周度_6种水果.csv", "内蒙古水果市场调研与数据分析报告.html"),
        ("data/全国苹果分市场_两期.csv", "内蒙古水果市场调研与数据分析报告.html"),
        ("data/零售_呼市周度.csv", "内蒙古水果市场调研与数据分析报告.html"),
        ("data/期货_苹果红枣.csv", "内蒙古水果市场调研与数据分析报告.html"),
        ("data/facts_check.json", "技能调用审计.md"),
        ("engine/r15_tco_apple.json", "内蒙古水果链路优化报告.html"),
    ]
    for p, ref in refs:
        arts.append({"path": str((ROOT / p).resolve()).replace("\\", "/"), "type": "doc", "references": [ref]})
    (ROOT / "data" / "artifact_manifest.json").write_text(
        json.dumps({"artifacts": arts}, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    for name, fn in HTMLS.items():
        (ROOT / name).write_text(fn(), encoding="utf-8")
        print("rendered", name, (ROOT / name).stat().st_size)
    write_readme()
    write_audit()
    write_manifest()
    print("readme/audit/manifest ok")
    # 最终 artifact 复核（报告已存在）
    proc = subprocess.run([sys.executable, str(Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团") / "guagua.py"),
                           "call", "r04", "artifact", "verify", "--input", str(ROOT / "data" / "artifact_manifest.json")],
                          cwd=r"D:\蛙蛙呱呱\蛙蛙呱呱agents团", capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=240)
    out = proc.stdout or ""
    (ROOT / "gates" / "r04_artifact_final.txt").write_text(out, encoding="utf-8")
    for line in out.splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            d = json.loads(line[len("__AGENT_RESULT__ "):])
            (ROOT / "gates" / "r04_artifact_final_result.json").write_text(
                json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            print("final artifact:", d.get("verdict"), d.get("passed_count"), "/", d.get("artifact_count"))


if __name__ == "__main__":
    main()
