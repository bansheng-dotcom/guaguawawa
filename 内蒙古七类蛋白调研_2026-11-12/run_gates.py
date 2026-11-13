# -*- coding: utf-8 -*-
"""跑真引擎：把 R05 / R06 / R15 的门禁结果落盘到 gates/。

每条命令都留 stdout 原文 + 解析后的 __AGENT_RESULT__ JSON，
审计文件（技能调用审计.md）只引用这里的真实输出。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\蛙蛙呱呱\内蒙古七类蛋白调研_2026-11-12")
TEAM = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
PY = sys.executable
GATES = ROOT / "gates"
GATES.mkdir(exist_ok=True)

D = ROOT / "data"
E = ROOT / "engine"

CMD = [
    ("r05_ledger", ["call", "r05", "research", "ledger", "--input", str(D / "证据台账_ledger.json")]),
    ("r05_report", ["call", "r05", "research", "report", "--input", str(D / "证据台账_ledger.json")]),
    ("r06_describe", ["call", "r06", "describe", "--input", str(D / "全区采价_月度.csv"), "--col", "11月5日"]),
    ("r06_trend_egg", ["call", "r06", "explore", "trend", "--input", str(E / "r06_周度_鸡蛋批发.csv"),
                       "--date", "日期", "--value", "鸡蛋"]),
    ("r06_rootcause", ["call", "r06", "rootcause", "decompose", "--input", str(E / "r06_篮子_前后期.csv"),
                       "--dim", "品类", "--value", "价格", "--period", "期间", "--before", "10月", "--after", "11月"]),
    ("r06_correlate", ["call", "r06", "correlate", "--input", str(E / "r06_区域价格_呼市vs乌兰察布.csv"),
                       "--col-a", "呼和浩特", "--col-b", "乌兰察布"]),
    ("r06_regression", ["call", "r06", "regression", "--input", str(E / "r06_区域价格_呼市vs乌兰察布.csv"),
                        "--x", "乌兰察布", "--y", "呼和浩特"]),
    ("r15_tco_beef", ["call", "r15", "tco", "compare", "--input", str(E / "r15_tco_beef.json")]),
    ("r15_tco_goose", ["call", "r15", "tco", "compare", "--input", str(E / "r15_tco_goose.json")]),
    ("r15_tco_shrimp", ["call", "r15", "tco", "compare", "--input", str(E / "r15_tco_shrimp.json")]),
    ("r15_supplier", ["call", "r15", "procurement", "supplier", "--input", str(E / "r15_supplier.json")]),
    ("r15_rfq", ["call", "r15", "procurement", "rfq", "--input", str(E / "r15_rfq_beef.json")]),
    ("r15_quote1", ["call", "r15", "procurement", "quotation", "--input", str(E / "r15_quote_1.json")]),
    ("r15_quote2", ["call", "r15", "procurement", "quotation", "--input", str(E / "r15_quote_2.json")]),
    ("r15_quote3", ["call", "r15", "procurement", "quotation", "--input", str(E / "r15_quote_3.json")]),
    ("r04_artifact", ["call", "r04", "artifact", "verify", "--input", str(D / "artifact_manifest.json")]),
    ("r04_quality", ["call", "r04", "quality", "critique", "--input", str(D / "证据台账_ledger.json")]),
]


def run_one(name: str, args: list[str]) -> dict:
    proc = subprocess.run(
        [PY, str(TEAM / "guagua.py"), *args],
        cwd=str(TEAM), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        env={**__import__("os").environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    out = (proc.stdout or "").strip()
    (GATES / f"{name}.txt").write_text(out + ("\n--- stderr ---\n" + (proc.stderr or "") if proc.stderr else ""),
                                       encoding="utf-8")
    payload = None
    for line in out.splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            try:
                payload = json.loads(line[len("__AGENT_RESULT__ "):])
            except json.JSONDecodeError:
                payload = None
    if payload is not None:
        (GATES / f"{name}_result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"name": name, "rc": proc.returncode, "ok": (payload or {}).get("ok"),
            "verdict": (payload or {}).get("verdict"), "has_json": payload is not None,
            "stdout_tail": out.splitlines()[-1][:160] if out else ""}


def main() -> None:
    results = []
    for name, args in CMD:
        r = run_one(name, args)
        results.append(r)
        print(f"{r['name']:<16} rc={r['rc']} ok={r['ok']} verdict={r['verdict']}")
    (GATES / "_run_summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    fails = [r for r in results if r["rc"] != 0 or r["ok"] is False]
    print(f"\n合计 {len(results)} 条，失败 {len(fails)} 条")
    for f in fails:
        print("  FAIL:", f["name"], f["stdout_tail"])


if __name__ == "__main__":
    main()
