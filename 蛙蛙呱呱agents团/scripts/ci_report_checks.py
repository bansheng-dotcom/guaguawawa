# -*- coding: utf-8 -*-
"""CI 闸门：唯一报告产线（2026-11-15 收敛后）。

只验五件事，全部围绕「一条产线、一份报告」：
  [1] 20 个角色入口可用（执行角色还在，只是不再出报告）
  [2] 分支 A（单角色）从真实 result 出一份报告，且过门禁
  [3] 分支 B（跨角色）从两份 result 出一份报告，且过门禁
  [4] 角色侧已无报告引擎（静态扫描：没人再 import 被删除的产线模块）
  [5] 图表能力 48/48 不退化
  [10] 48 型图表经报告管线嵌入：v2 不回退、无双标题、卡框口径齐备

旧的 [1] spec/[2][3] contract/[4] legacy/[7] substance 五项已随产线一起删除。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures" / "report_flow"
OUT = ROOT.parent / "workspace" / "_ci_report_flow"

DEAD_MODULES = (
    "report_pipeline", "report_engine", "report_generator",
    "kernel_report_adapter", "report_modules", "report_blueprint",
    "corpus_analysis", "enhanced_report_renderer", "report_kernel.layers",
    "report_kernel.spec", "report_kernel.aggregate",
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    fails: list[str] = []

    # [1] 20 角色入口
    rc, out = run([sys.executable, "guagua.py", "check"])
    tail = [l for l in out.strip().splitlines() if "通过" in l]
    print(f"[1] roles check rc={rc} :: {tail[-1] if tail else out.strip()[-60:]}")
    if rc:
        fails.append("roles")

    # [2] 分支 A
    out_a = OUT / "a"
    rc, out = run([sys.executable, "guagua.py", "report", "run",
                   "--intent", "客户续约风险体检",
                   "--results", str(FIX / "r13_result.json"),
                   "--out", str(out_a)])
    print(f"[2] flow(A) rc={rc}")
    if rc:
        fails.append("flow-A")
        print("   ", out.strip()[:200])
    rc, out = run([sys.executable, "scripts/check_report_flow.py",
                   "--dir", str(out_a)])
    print(f"[2] gate(A) rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
    if rc:
        fails.append("gate-A")

    # [3] 分支 B
    out_b = OUT / "b"
    rc, out = run([sys.executable, "guagua.py", "report", "run",
                   "--intent", "2月经营诊断",
                   "--results", str(FIX / "r06_result.json"), str(FIX / "r13_result.json"),
                   "--out", str(out_b)])
    print(f"[3] flow(B) rc={rc}")
    if rc:
        fails.append("flow-B")
        print("   ", out.strip()[:200])
    rc, out = run([sys.executable, "scripts/check_report_flow.py",
                   "--dir", str(out_b)])
    print(f"[3] gate(B) rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
    if rc:
        fails.append("gate-B")

    # [3b] 报告只有一份，且出具人是 R01
    man = out_b / "manifest.json"
    if man.exists():
        m = json.loads(man.read_text(encoding="utf-8"))
        one = m.get("producer") == "r01" and m.get("branch") == "B" and m.get("ok")
        print(f"[3b] manifest producer={m.get('producer')} branch={m.get('branch')} ok={m.get('ok')}")
        if not one:
            fails.append("manifest")
    else:
        print("[3b] manifest 缺失")
        fails.append("manifest")

    # [4] 角色侧无报告引擎
    pat = re.compile(r"^\s*(?:from|import)\s+\S*(?:" +
                     "|".join(re.escape(x) for x in DEAD_MODULES) + r")", re.M)
    bad = []
    for p in list(ROOT.glob("r*/agent.py")) + list(ROOT.glob("core/*.py")) + \
            list(ROOT.glob("shared/*.py")):
        if pat.search(p.read_text(encoding="utf-8", errors="replace")):
            bad.append(str(p.relative_to(ROOT)))
    print(f"[4] role-side report engine imports: {len(bad)} {bad[:3]}")
    if bad:
        fails.append("dual-engine")

    # [5] 图表能力
    rc, out = run([sys.executable, "-m", "core.chart_capabilities", "--check"])
    print(f"[5] charts rc={rc} :: {out.strip().splitlines()[-1] if out.strip() else ''}")
    if rc:
        fails.append("charts")

    # [6] v7 深度线：区域市场调研（带来源事实表）+ 九条门禁 + 反模板门禁
    out_v7 = OUT / "v7_market"
    rc, out = run([sys.executable, "guagua.py", "report", "produce",
                   "--intent", "内蒙古家居百货市场调研",
                   "--dir", str(ROOT.parent / "家居百货内蒙调研_2026-11-15"),
                   "--out", str(out_v7)])
    print(f"[6] flow(v7-market) rc={rc}")
    if rc:
        fails.append("flow-v7")
        print("   ", out.strip()[:200])
    rc, out = run([sys.executable, "scripts/check_report_flow.py",
                   "--dir", str(out_v7)])
    print(f"[6] gate(v7) rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
    if rc:
        fails.append("gate-v7")
    rc, out = run([sys.executable, "-m", "core.report_quality",
                   str(out_v7 / "report.html")])
    print(f"[6] depth(v7) rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
    if rc:
        fails.append("depth-v7")

    # [7] 学习层：Move 卡片必须可校验（来源/反例/代码落点/回归）
    rc, out = run([sys.executable, "scripts/check_move_cards.py"])
    tail7 = [l for l in out.strip().splitlines() if "PASS" in l]
    print(f"[7] move cards rc={rc} :: {tail7[-1] if tail7 else out.strip()[-60:]}")
    if rc:
        fails.append("move-cards")

    # [8] 领域层：20 角色领域包完整（书/方法/指标/决策/误判/章节）
    rc, out = run([sys.executable, "scripts/check_role_packs.py"])
    tail8 = [l for l in out.strip().splitlines() if "PASS；" in l]
    print(f"[8] role packs rc={rc} :: {tail8[-1] if tail8 else out.strip()[-60:]}")
    if rc:
        fails.append("role-packs")

    # [9] 接入层：120 条领域方法必须落到现有技能，或显式标成新增
    rc, out = run([sys.executable, "scripts/check_skill_integration.py"])
    tail9 = [l for l in out.strip().splitlines() if "方法 " in l]
    print(f"[9] skill integration rc={rc} :: {tail9[0] if tail9 else out.strip()[-60:]}")
    if rc:
        fails.append("skill-integration")

    # [10] 图表嵌入：48 型走报告渲染管线，v2 不回退、无双标题、卡框口径齐备
    rc, out = run([sys.executable, "scripts/check_chart_report_embed.py"])
    print(f"[10] chart embed rc={rc} :: {out.strip().splitlines()[0] if out.strip() else ''}")
    if rc:
        fails.append("chart-embed")

    print(f"\n=== {'FAIL: ' + ','.join(fails) if fails else 'ALL PASS'} ===")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
