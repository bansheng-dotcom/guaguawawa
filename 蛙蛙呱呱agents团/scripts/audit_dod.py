# -*- coding: utf-8 -*-
"""scripts/audit_dod.py —— 对 MASTER-UPGRADE-SOP §10 的 11 条 DoD 做代码级自审。

不跑报告、不读输出，只查「实现 + 接线」是否真的在代码里：
每条给出 PASS / PARTIAL / FAIL 与证据（文件:行为）。

用法：
    python scripts/audit_dod.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def _path(name: str) -> Path:
    """优先返回已归位的 core/<pkg>/<name>；否则回落到平铺文件（含兼容 shim）。"""
    hits = sorted(CORE.glob("*/" + name))
    return hits[0] if hits else CORE / name


def _txt(name: str) -> str:
    p = _path(name)
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def _callers(pattern: str, exclude=("tests", "baselines", "scripts")) -> list:
    """全仓搜一个调用点（排除测试/样例），返回 相对路径:行。"""
    out = []
    for p in ROOT.rglob("*.py"):
        rel = p.relative_to(ROOT).as_posix()
        if any(rel.startswith(e + "/") for e in exclude):
            continue
        try:
            for i, ln in enumerate(p.read_text(encoding="utf-8",
                                               errors="replace").splitlines(), 1):
                if pattern in ln:
                    out.append(f"{rel}:{i}")
        except OSError:
            continue
    return out


checks = []


def ck(no, name, ok, ev):
    checks.append((no, name, "PASS" if ok else "FAIL", ev))


# 1 G1–G25 收格后必跑，结果进 manifest.gate.post
dr = _txt("decision_report.py")
ck(1, "G1–G25 → manifest.gate.post",
   '"_plan_gate("post_gates.json")' in dr or '"post": _plan_gate' in dr,
   "decision_report 写 manifest.gate.post")

# 2 cells_filled 闭环（格子→claims）
disp = _txt("dispatch.py")
ck(2, "cells_filled 闭环（格子→claims）",
   "_bridge_cells_to_claims" in disp and "cells_claims.build" in disp,
   "dispatch.collect 读卡前调 cells_claims.build")

# 3 每份报告有采集契约，含 availability
cc = _txt("collection_contract.py")
cu = _txt("card_upgrade.py")
ck(3, "采集契约含 availability",
   "availability" in cc and "collection_contract" in cu,
   "post_collect 产出 collection_contract.yaml")

# 4 shape_ok_ratio 门禁生效
sg = _txt("shape_gate.py")
ck(4, "shape_ok_ratio 门禁生效",
   "shape_ok_ratio" in sg and "shape_gate" in dr,
   "core/shape_gate.py + decision_report 调用")

# 5 因果阶真赋值 + G15 不依赖 level>=3
ck(5, "因果阶真赋值 + G15 不依赖 level>=3",
   '"I" if str(dim) == "机制"' in cu
   and "level\", 0) >= 3 and" not in cu
   and '"causal_level"' in cu,
   "G15 去 level 依赖，机制格禁 A 阶")

# 6 驱动树
ck(6, "驱动树产出", "def build_driver_tree" in cu and "driver_tree.json" in cu,
   "build_driver_tree + plan/driver_tree.json")

# 7 数据分支产出 data_profile
ck(7, "数据分支产出 data_profile",
   "data_profile" in dr and "profile_dir" in dr,
   "decision_report 写 data_profile.json")

# 8 三前端接产线 + 语义一致性
rf = _txt("report_flow.py")
ck(8, "三前端接产线 + 语义一致性",
   "decision_to_ir" in rf and "semantic_pipeline" in rf,
   "build_sections_contract 调 decision_to_ir + semantic_pipeline")

# 9 chart_query 接主路径 + 1–2 点不出
chu = _txt("chart_units.py")
ck(9, "chart_query 接主路径 + 1–2 点不出",
   "chart_query" in rf and "len(keep) < 3" in chu,
   "chart_query 接入；chart_units 门槛 <3")

# 10 一条门禁链（渲染路径两条为设计选择）
flow_gate = (ROOT / "scripts" / "check_report_flow.py")
fg = flow_gate.read_text(encoding="utf-8", errors="replace") if flow_gate.is_file() else ""
ck(10, "一条门禁链", "F1" in fg and "F12" in fg,
   "check_report_flow F1–F12 一条链")

# 11 core 无业务词 + 样例在 samples/
samples_ok = (ROOT / "samples").is_dir() and not (CORE / "report_theme"
                                                  / "charts_pro" / "samples_data").exists()
ck(11, "core 无业务词 + 样例在 samples/", samples_ok,
   "samples/ 在仓库根，core/ 无 samples_data")

# 追加：MECE 互斥 / 拆卡饱和（本轮新增能力）
ck(12, "MECE 互斥检查", "_mece_mutual" in cu, "TOP+个体 / 重复实体 / 总量+补集")
ck(13, "拆卡饱和两档", "def grid_saturation" in cu, "基础 + 强饱和")

# 追加：数据供给方案（SUPPLY-SOP v7.0）——计划级别要可追溯
try:
    _sp = _txt("supply_plan.py")
    _plan_ok = all(k in _sp for k in ("planned_level", "planned_rows",
                                      "capability_of", "def gate"))
    _disp = _txt("dispatch.py")
    _wired = "capability_of" in _disp and "capability_gate" in _disp
    _cc = _txt("collection_contract.py")
    _rows_ok = "rows_expected_source" in _cc
    ck(14, "供给方案可追溯",
       _plan_ok and _wired and _rows_ok,
       "supply_plan + dispatch.capability + rows_expected 用真实行数")
except Exception as exc:  # noqa: BLE001
    ck(14, "供给方案可追溯", False, str(exc)[:60])

# 追加：入口文档一致（2026-11-23：SKILL 写 v5 / README 写 v13，同一时间却不同版）
try:
    import subprocess as _sp_run
    _r = _sp_run.run([sys.executable, str(ROOT / "scripts" / "check_doc_consistency.py")],
                     capture_output=True, text=True, encoding="utf-8",
                     errors="replace", timeout=60)
    ck(15, "入口文档同版",
       _r.returncode == 0,
       (_r.stdout or "").strip().splitlines()[0][:70] if _r.stdout else "检查失败")
except Exception as exc:  # noqa: BLE001
    ck(15, "入口文档同版", False, str(exc)[:60])

print("=" * 74)
print(f"{'#':<3} {'DoD 条目':<34} {'结果':<6} 证据")
print("-" * 74)
npass = 0
for no, name, res, ev in checks:
    print(f"{no:<3} {name:<34} {res:<6} {ev}")
    npass += res == "PASS"
print("=" * 74)
print(f"PASS {npass}/{len(checks)}")
sys.exit(0 if npass == len(checks) else 1)
