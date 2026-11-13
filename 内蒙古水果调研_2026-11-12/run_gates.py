# -*- coding: utf-8 -*-
"""跑真引擎：R01 / R05 / R06 / R15 / R03 / R02 / R04 的门禁结果落盘到 gates/。

每条命令保留 stdout 原文 + 解析后的 __AGENT_RESULT__ JSON；
技能调用审计只引用这里的真实输出，不手写结论。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEAM = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
PY = sys.executable
GATES = ROOT / "gates"
GATES.mkdir(exist_ok=True)
D, E = ROOT / "data", ROOT / "engine"

CMD = [
    ("r01_plan", ["call", "r01", "plan", "--intent",
                  "内蒙古水果品类 2026 年 10—11 月市场调研，产出调研与数据分析报告、经营报告、链路优化报告"]),
    ("r05_ledger", ["call", "r05", "research", "ledger", "--input", str(D / "证据台账.json")]),
    ("r05_report", ["call", "r05", "research", "report", "--input", str(D / "证据台账.json")]),
    ("r06_describe", ["call", "r06", "describe", "--input", str(E / "r06_日度.csv"), "--col", "水果6种均价"]),
    ("r06_trend", ["call", "r06", "explore", "trend", "--input", str(E / "r06_日度.csv"),
                   "--date", "date", "--value", "水果6种均价"]),
    ("r06_regression", ["call", "r06", "regression", "--input", str(E / "r06_周度_篮子.csv"),
                        "--x", "全国6种均价", "--y", "呼市8种零售均价"]),
    ("r06_correlate", ["call", "r06", "correlate", "--input", str(E / "r06_周度_篮子.csv"),
                       "--col-a", "全国6种均价", "--col-b", "呼市8种零售均价"]),
    ("r06_rootcause", ["call", "r06", "rootcause", "decompose", "--input", str(E / "r06_品类前后期.csv"),
                       "--dim", "品类", "--value", "价格", "--period", "期间", "--before", "10月", "--after", "11月"]),
    ("r15_tco", ["call", "r15", "tco", "compare", "--input", str(E / "r15_tco_apple.json")]),
    ("r15_supplier", ["call", "r15", "procurement", "supplier", "--input", str(E / "r15_supplier.json")]),
    ("r15_rfq", ["call", "r15", "procurement", "rfq", "--input", str(E / "r15_rfq.json")]),
    ("r15_quote1", ["call", "r15", "procurement", "quotation", "--input", str(E / "r15_quote_1.json")]),
    ("r15_quote2", ["call", "r15", "procurement", "quotation", "--input", str(E / "r15_quote_2.json")]),
    ("r15_quote3", ["call", "r15", "procurement", "quotation", "--input", str(E / "r15_quote_3.json")]),
    ("r03_healthcheck", ["call", "r03", "cfo", "healthcheck", "--input", str(E / "r03_healthcheck.json")]),
    ("r02_sop", ["call", "r02", "process", "sop", "--input", str(E / "r02_sop.json")]),
    ("r04_quality", ["call", "r04", "quality", "critique", "--input", str(D / "证据台账.json")]),
    ("r04_facts", ["call", "r04", "facts", "check", "--input", str(D / "facts_check.json")]),
    ("r04_artifact", ["call", "r04", "artifact", "verify", "--input", str(D / "artifact_manifest.json")]),
]


def run_one(name: str, args: list[str]) -> dict:
    proc = subprocess.run(
        [PY, str(TEAM / "guagua.py"), *args], cwd=str(TEAM), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=240,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    out = (proc.stdout or "").strip()
    (GATES / f"{name}.txt").write_text(
        out + ("\n--- stderr ---\n" + (proc.stderr or "") if proc.stderr else ""), encoding="utf-8")
    payload = None
    for line in out.splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            try:
                payload = json.loads(line[len("__AGENT_RESULT__ "):])
            except json.JSONDecodeError:
                payload = None
    if payload is not None:
        (GATES / f"{name}_result.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"name": name, "rc": proc.returncode, "ok": (payload or {}).get("ok"),
            "verdict": (payload or {}).get("verdict"), "has_json": payload is not None,
            "stdout_tail": out.splitlines()[-1][:160] if out else ""}


def main() -> None:
    only = sys.argv[1:] or None
    results = []
    for name, args in CMD:
        if only and name not in only:
            continue
        r = run_one(name, args)
        results.append(r)
        print(f"{r['name']:<16} rc={r['rc']} ok={r['ok']} verdict={r['verdict']} json={r['has_json']}")
    if only:
        return
    (GATES / "_run_summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    fails = [r for r in results if r["rc"] != 0 or r["ok"] is False]
    print(f"\n合计 {len(results)} 条，失败 {len(fails)} 条")
    for f in fails:
        print("  FAIL:", f["name"], f["stdout_tail"])


if __name__ == "__main__":
    main()
