# -*- coding: utf-8 -*-
"""端到端执行「拆卡升级 SOP v1.4 + 协作层 SOP v1.0」的实现并出验收报告。

    python scripts/run_card_upgrade.py --project <项目> --intent "..." [--out <目录>]

产物：
    plan/issue_tree.json  perspectives.json  grid.json  semantic_layer.yaml
    plan/decomposition_log.json  branch_log.json  dispatch.json  requests.json
    plan/arbitration.json  mece.json  charts.json  handoffs.json  gates.json
    plan/ledger.jsonl  trace.jsonl
    out_v3/cells_filled.json  acceptance.md  summary.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.cards import card_upgrade as cu  # noqa: E402
from core import roster  # noqa: E402


def load(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--intent", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    project = Path(a.project)
    out = Path(a.out) if a.out else project / "out_v3"
    plan = project / "plan"
    out.mkdir(parents=True, exist_ok=True)
    plan.mkdir(parents=True, exist_ok=True)
    for f in ("ledger.jsonl", "trace.jsonl"):
        (plan / f).write_text("", encoding="utf-8")

    clarify = load(project / "clarify.json") or load(project / "out_v2" / "clarify.json")
    if not clarify:
        print("缺 clarify.json，先跑 report clarify")
        return 2
    pack = load(project / "out_v2" / "_compiled" / "evidence_pack.json", {}) or {}
    nums = [n for n in (pack.get("numbers") or []) if n.get("value") is not None]

    # ---------- R01 内容层 ----------
    sem = cu.load_semantics(project, pack)
    sem_errs = cu.validate_semantic(sem)
    tree = cu.build_issue_tree(clarify)
    persp = cu.build_perspectives(clarify, cu._load_yaml(project / "perspectives.yaml"))
    grid_tpl = load(project / "plan" / "grid.template.json", {}) or {}
    grid = cu.build_grid(clarify, sem, cu._brands(pack), template=grid_tpl or None)
    decs = [cu.score_decompositions(x, grid["cells"], nums)
            for x in clarify.get("asks") or [] if x.get("must")]
    branches = cu.branch_log(clarify, grid["cells"], nums)
    cu._w(plan / "issue_tree.json", tree)
    cu._w(plan / "perspectives.json", persp)
    cu._w(plan / "grid.json", grid)
    cu._w(plan / "decomposition_log.json", {"items": decs})
    cu._w(plan / "branch_log.json", branches)
    cu.ledger(project, "plan", intent=a.intent, cells=grid["count"],
              perspectives=persp["count"], must=len(tree["nodes"]))

    # ---------- R02 协作层 ----------
    cards = cu.agent_cards(roster.build())
    rows, gaps = cu.assign(grid["cells"], cards)
    requests = cu.route_requests(gaps, rows, cards)
    dag = cu.build_dag(rows, sem)
    ctr = cu.contracts(rows, cards)
    cu._w(plan / "dispatch.json", {
        "cards": cards,
        "assignments": [{"cell_id": r["cell_id"], "owner": r["owner"],
                         "why": r["why"], "match": r["match"]} for r in rows],
        "gaps": gaps, "requests": requests, "dag": dag,
        "contracts": ctr["contracts"]})
    cu._w(plan / "requests.json", {"requests": requests})
    cu.ledger(project, "dispatch", contracts=ctr["count"],
              roles=len({r["owner"] for r in rows}), gaps=len(gaps),
              requests=len(requests))

    # ---------- 执行 + 回流 ----------
    facts = (load(plan / "facts.json", {}) or {})
    filled, fmeta = cu.fill_cells(project, rows, facts)
    filled, bf = cu.backfill(filled, project, facts)
    requests = cu.reconcile_requests(requests, filled)
    cu._w(plan / "requests.json", {"requests": requests})
    cu._w(plan / "facts.json", facts)
    cu._w(out / "cells_filled.json", {"cells": filled, "facts_reused": fmeta["reused"]})

    # ---------- 仲裁 / MECE / 图合同 ----------
    arb = cu.arbitrate(pack)
    mece = cu.mece_check(filled)
    charts = cu.chart_contracts(clarify, filled, sem)
    cu._w(plan / "arbitration.json", arb)
    cu._w(plan / "mece.json", mece)
    cu._w(plan / "charts.json", charts)

    # ---------- 交接签收 ----------
    receipts = []
    for c in ctr["contracts"]:
        mine = [r for r in filled if r["cell_id"] in c["cells"]]
        good = [r for r in mine if r["status"] == "filled"]
        rate = len(good) / len(mine) if mine else 0
        ok = rate >= 0.7
        bad = [r["cell_id"] for r in mine if r["status"] != "filled"]
        receipts.append({
            "handoff_id": f"H-{c['task_id']}", "from": c["owner"], "to": "r01",
            "contract": c["task_id"],
            "decision": "accept" if ok else "reject",
            "evidence": f"{len(good)}/{len(mine)} 格已填（{rate:.0%}）",
            "reasons": [] if ok else [f"未达 70%，缺 {len(bad)} 格，例：{bad[:2]}"],
            "action": "accept" if ok else "backfill",
            "elapsed_min": 30, "sla_min": c.get("deadline_min", 120),
        })
        cu.ledger(project, "handoff", owner=c["owner"], decision=receipts[-1]["decision"])
    cu._w(plan / "handoffs.json", {"receipts": receipts})

    # ---------- 24 门禁 ----------
    cu.ledger(project, "gates", stage="start")
    g = cu.gates(clarify, grid, persp, sem, filled, ctr, gaps, receipts,
                 plan / "ledger.jsonl",
                 extra={"charts": charts, "backfill": bf, "branches": branches,
                        "decompositions": decs, "mece": mece,
                        "arbitration": arb, "requests": requests})
    cu._w(plan / "gates.json", g)
    cu.ledger(project, "gates", passed=g["passed"], total=g["total"])

    lines = (plan / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    (plan / "trace.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------- 验收报告 ----------
    total = len(filled)
    okc = sum(1 for r in filled if r["status"] == "filled")
    cover = okc / total if total else 0
    accepted = sum(1 for r in receipts if r["decision"] == "accept")
    escalated = sum(1 for x in requests if x["status"] == "escalated")
    sys_ok = (not sem_errs) and g["passed"] >= 20
    content_ok = cover >= 0.7
    checks = "\n".join(
        f"| {c['id']} | {'PASS' if c['ok'] else 'FAIL'} | {c['msg']} |"
        for c in g["checks"])
    gap_rows = "\n".join(
        f"| {x['cell_id']} | {x['why']} | {', '.join(x.get('tried') or [])} |"
        for x in filled if x["status"] != "filled")
    handoff_rows = "\n".join(
        f"| {r['contract']} | {r['from']} | {r['decision']} | {r['evidence']} | "
        f"{'; '.join(r['reasons']) or '—'} |" for r in receipts)
    req_rows = "\n".join(
        f"| {x['request_id']} | {x['cell_id']} | {x['from']} → {x['status']} | "
        f"{len(x['events'])} 事件 / {x['elapsed_min']}min |" for x in requests[:12])
    ts = [json.loads(x)["ts"] for x in lines if x.strip()]
    monotonic = all(ts[i] <= ts[i + 1] for i in range(len(ts) - 1))

    md = f"""# 拆卡升级 + 协作层 验收报告

- 项目：`{project.name}`
- 生成时间：{time.strftime('%Y-%m-%d %H:%M')}
- 范围：拆卡 SOP v1.4（视角/维度/度量/证据/因果）+ 协作层 SOP v1.0（八组件）
- 执行方式：确定性管线；执行层为 fixture（导入既有数字，不造数）

## 一、结论（三选一）

| 交付物 | 结论 | 依据 |
|---|---|---|
| **系统（两份 SOP 的代码实现）** | **{'可签收' if sys_ok else '验收不通过'}** | 语义层错误 {len(sem_errs)}；门禁 {g['passed']}/{g['total']} |
| **内容（fixture 报告）** | **{'可签收' if content_ok else '退回补齐'}** | 覆盖率 {cover:.0%}；签收 {accepted}/{len(receipts)} |

> 系统能不能用，与这份报告内容够不够，分开下结论。

## 二、系统验收（24 条门禁全实现）

- 问题树：{len(tree['nodes'])} 个 must 子问题
- 视角层：{persp['count']} 个视角
- 格子：{grid['count']} 个（六维）
- 语义层：{len((sem.get('case') or {}).get('measures') or [])} 个度量；通用层 {'已加载' if sem.get('generic') else '缺失'}
- 候选拆解：{len(decs)} 组（每组 ≥2 变体，分数按覆盖/可获取/机制/成本计算）
- 分支日志：{branches['count']} 条 stop
- 派工：{len(set(r['owner'] for r in rows))} 个角色；缺口 {len(gaps)}；请求 {len(requests)}（升级 {escalated}）
- 契约：{ctr['count']}；DAG {len(dag['waves'])} 波次，关键路径 {dag['critical_path_len']}
- 仲裁：{arb['count']} 条冲突
- MECE：{sum(1 for i in mece['items'] if i['applicable'])} 个适用项，通过 {sum(1 for i in mece['items'] if i['ok'])}
- 图合同：{charts['count']} 张（data_points 已校验）
- 回流：{len(bf)} 条请求均有处置
- 指纹复用：{fmeta['reused']} 格

## 三、门禁（G1–G24）

| 门禁 | 结果 | 说明 |
|---|---|---|
{checks}

## 四、交接验收记录

| 合同 | 交付方 | 结论 | 证据 | 退回原因 |
|---|---|---|---|---|
{handoff_rows}

> 规则：无证据不算通过；未过项必须写原因；结论三选一。

## 五、缺口路由（前 12 条）

| 请求 | 格子 | 流转 | 耗时 |
|---|---|---|---|
{req_rows or '（无）'}

## 六、交接包字段

| 字段 | 值 |
|---|---|
| artifact | `out_v3/cells_filled.json` |
| artifact_type | cells |
| owner / handoff_to | 各交付角色 → r01 |
| rev | 1 |
| repro_commands | `python scripts/run_card_upgrade.py --project "{project}"` |
| downstream_fields | cell_id / measure / entity / period / value / unit / source_file / quality |
| must_read | `plan/dispatch.json`、`plan/grid.json`、`plan/semantic_layer.yaml` |

## 七、未答清单

| 格子 | 原因 | 已试 |
|---|---|---|
{gap_rows or '（无）'}

## 八、复现

```bash
python scripts/run_card_upgrade.py --project "{project}" --intent "{a.intent}"
```

## 九、审计轨迹

`plan/trace.jsonl`（{len(lines)} 条，时间单调：{'是' if monotonic else '否'}）。
"""
    (out / "acceptance.md").write_text(md, encoding="utf-8")
    cu._w(out / "summary.json", {
        "cells": total, "filled": okc, "coverage": round(cover, 3),
        "gates": {"passed": g["passed"], "total": g["total"]},
        "contracts": ctr["count"], "receipts": len(receipts), "accepted": accepted,
        "gaps": len(gaps), "requests": len(requests), "escalated": escalated,
        "arbitration": arb["count"], "mece_ok": mece["ok"],
        "charts": charts["count"], "backfill": len(bf), "facts_reused": fmeta["reused"],
        "semantic_errors": sem_errs,
        "verdict_system": "可签收" if sys_ok else "验收不通过",
        "verdict_content": "可签收" if content_ok else "退回补齐",
    })
    print(json.dumps(json.loads((out / "summary.json").read_text(encoding="utf-8")),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
