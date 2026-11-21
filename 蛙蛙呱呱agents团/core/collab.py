# -*- coding: utf-8 -*-
"""core.collab —— 协作层 SOP v1.0 的真实接线。

不是"再算一遍契约"：这里真的调用 R02 的 agent（`guagua.py call r02`）：
    handoff package   → 每个角色一份交接包（package_id）
    portfolio plan    → 波次 / 每波负载
并把账本写进 `plan/ledger.jsonl`，供 R04/报告追溯。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]


def _call_r02(args: List[str], timeout: int = 90) -> Dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "guagua.py", "call", "r02", *args],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"__AGENT_RESULT__\s*(\{.*\})", out, re.S)
    if not m:
        return {"ok": False, "error": out[-400:]}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {"ok": False, "error": out[-400:]}


def ledger(project: Path, event: str, **kw) -> None:
    p = Path(project) / "plan" / "ledger.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now().isoformat(timespec="seconds"), "event": event, **kw}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def sign(project: Path, contracts: List[Dict[str, Any]], intent: str = "") -> Dict[str, Any]:
    """逐份契约调 R02 handoff package，拿 package_id。"""
    project = Path(project)
    receipts = []
    for c in contracts:
        owner = str(c.get("owner") or "")
        inp = {
            "process_doc": str(c.get("task_id") or f"T-{owner}"),
            "artifact": f"cards/{owner}/claims.json",
            "artifact_type": "data",
            "owner": owner,
            "rev": "r1",
            "handoff_to": "r01",
            "repro_commands": [f"python guagua.py call r02 handoff accept --input cards/{owner}/claims.json"],
            "downstream_fields": ["cell_id", "value", "unit", "period",
                                  "source_file", "grade", "quality", "causal_level"],
            "acceptance_criteria": [
                f"格子交付率 ≥70%（{len(c.get('cells') or [])} 格）",
                "每格带 source_file / grade / quality 六维 / causal_level",
            ],
            "must_read": [f"cards/{owner}/TASK.md", "plan/grid.json"],
        }
        tmp = project / "plan" / f"_handoff_{owner}.json"
        _write(tmp, inp)
        res = _call_r02(["handoff", "package", "--input", str(tmp)])
        try:
            tmp.unlink()
        except OSError:
            pass
        receipts.append({
            "owner": owner,
            "task_id": c.get("task_id"),
            "ok": bool(res.get("ok")),
            "package_id": res.get("package_id"),
            "artifact_type": res.get("artifact_type"),
            "criteria_count": res.get("criteria_count"),
            "error": res.get("error") or ("; ".join(
                x.get("msg", "") for x in res.get("checks") or [] if not x.get("ok"))[:200]),
        })
    out = {"schema": "dsh.r02.handoffs/v1",
           "ok": bool(receipts) and all(r["ok"] for r in receipts),
           "count": len(receipts), "receipts": receipts}
    _write(project / "plan" / "handoffs.json", out)
    ledger(project, "handoff", contracts=len(contracts),
           packages=sum(1 for r in receipts if r["ok"]))
    return out


def waves(project: Path, contracts: List[Dict[str, Any]],
          dag: Dict[str, Any], est_hours: int = 2) -> Dict[str, Any]:
    """把契约交给 R02 portfolio plan 排波。

    DAG 的边是**格子级**的；这里先映射到角色级，再交给 R02。
    """
    project = Path(project)
    disp = {}
    try:
        disp = json.loads((project / "plan" / "dispatch.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        disp = {}
    cell_owner = {str(a.get("cell_id")): str(a.get("owner"))
                  for a in disp.get("assignments") or []}
    by_owner = {str(c.get("owner")): str(c.get("task_id")) for c in contracts}
    owner_task = {o: t for o, t in by_owner.items()}
    deps: Dict[str, List[str]] = {tid: [] for tid in by_owner.values()}
    for e in dag.get("edges") or []:
        fo = cell_owner.get(str(e.get("from") or ""))
        to = cell_owner.get(str(e.get("to") or ""))
        if not fo or not to or fo == to:
            continue
        ft, tt = owner_task.get(fo), owner_task.get(to)
        if ft and tt and ft not in deps[tt]:
            deps[tt].append(ft)
    tasks = [{"id": tid, "owner_role": owner,
              "depends_on": deps.get(tid, []), "est_hours": est_hours}
             for owner, tid in by_owner.items()]
    tmp = project / "plan" / "_portfolio_input.json"
    _write(tmp, {"tasks": tasks, "gates": []})
    res = _call_r02(["portfolio", "plan", "--input", str(tmp)])
    try:
        tmp.unlink()
    except OSError:
        pass
    out = {"schema": "dsh.r02.waves/v1", "ok": bool(res.get("ok")),
           "waves": res.get("waves") or [], "wave_load": res.get("wave_load") or {},
           "checks": res.get("checks") or [], "contracts": len(contracts)}
    _write(project / "plan" / "r02_waves.json", out)
    ledger(project, "r02_waves", ok=out["ok"], waves=len(out["waves"]))
    return out
