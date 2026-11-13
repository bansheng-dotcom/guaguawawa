# -*- coding: utf-8 -*-
"""L02 意图解构层 —— 复合故障诉求 → 5 阶段 Kahn 恢复 DAG。

SOP v13.0 L02 体检病灶（R20 真实断点）：
    现有 `_INTENT_ROUTES` 只是 14 条关键词硬匹配，只能回答「调哪个技能」；
    面对「支付服务 P1 故障，30 分钟内恢复，RTO<=2h，影响 3 万用户，先回滚再复盘」
    这类复合诉求，答不出动几个阶段、几步、多少人时、谁先谁后、瓶颈在哪，
    既无拓扑排序也无环检测，排期全靠人脑。

对标开源标杆（Stars > 1k）：
    * stanfordnlp/dspy (>17k) —— 自然语言 → 结构化签名/流水线编译
    * ray-project/ray (>33k) —— 任务 DAG 与并行波次执行模型
    * apache/airflow (>36k) —— 有向无环图调度与依赖语义

落地的最低 3 项架构升级：
    1. 复合故障实体抽取（服务/严重度/恢复窗口/RTO-RPO/影响用户/风险词）；
    2. 5 阶段恢复 DAG（审计→探测→诊断→恢复→复盘）的 Kahn 拓扑序与并行波次；
    3. 关键路径 + 人时预算 + 环路检测，并输出可排期 Markdown。

用法：
    python agent.py evolve decompile --text "..." --out ... --md ...
"""
from __future__ import annotations

import datetime
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_SEV_MAP = [
    (("p0", "p1", "一级", "sev1", "致命", "全网", "大面积"), "critical"),
    (("p2", "二级", "sev2", "严重", "核心服务"), "major"),
    (("p3", "三级", "sev3", "一般", "轻微"), "minor"),
]

_STAGE_DEFS = [
    ("audit", "现状审计", 0.5, [], "拓扑/资产清单/变更窗口核对"),
    ("probe", "探测与告警校验", 1.0, [], "SLI 采集/告警规则/值班链路验证"),
    ("diagnose", "根因诊断", 1.5, ["audit", "probe"], "依赖链定位/错误预算归因/影响面评估"),
    ("recover", "恢复与回滚", 2.0, ["diagnose"], "回滚计划/流量切换/数据一致性校验"),
    ("review", "复盘与改进", 1.0, ["recover"], "时间线/根因/RCA 改进项闭环"),
]


def _hours(token: str, unit: str) -> Optional[float]:
    try:
        v = float(token)
    except (TypeError, ValueError):
        return None
    return round(v / 60.0, 4) if unit.lower() in ("min", "分钟", "m") else round(v, 4)


class R20IntentCompiler:
    """把复合故障诉求编译为可排期的 5 阶段恢复 DAG。"""

    ENGINE = "R20IntentCompiler"
    LAYER = "L02"
    CAPABILITIES = [
        "复合故障实体抽取 (服务/严重度/恢复窗口/RTO-RPO/影响用户/风险词)",
        "5 阶段 Kahn 拓扑 DAG (stages/deps/人时/责任人/交付物)",
        "拓扑序 + 并行波次 + 关键路径 + 环路检测与人时预算",
    ]

    # ------------------------------------------------------------------ #
    # 实体抽取
    # ------------------------------------------------------------------ #
    def extract_entities(self, text: str) -> Dict[str, Any]:
        raw = text or ""
        low = raw.lower()
        service = None
        m = re.search(r"([\u4e00-\u9fa5A-Za-z0-9_-]{2,16}?)(?:服务|系统|应用|集群|数据库|网关)", raw)
        if m:
            service = m.group(0)
        elif "核心" in raw:
            service = "核心服务"

        severity = "major"
        for kws, sev in _SEV_MAP:
            if any(k in low for k in kws):
                severity = sev
                break

        window_hours = None
        m = re.search(r"(\d+(?:\.\d+)?)\s*(分钟|min|m|小时|h|hours?)\s*(?:内|之内|以内|完成|恢复)?",
                      raw, re.I)
        if m:
            window_hours = _hours(m.group(1), m.group(2))

        rto = rpo = None
        m = re.search(r"RTO\s*(?:<=|<|≤|=)?\s*(\d+(?:\.\d+)?)\s*(分钟|min|小时|h)", raw, re.I)
        if m:
            rto = _hours(m.group(1), m.group(2))
        m = re.search(r"RPO\s*(?:<=|<|≤|=)?\s*(\d+(?:\.\d+)?)\s*(分钟|min|小时|h)", raw, re.I)
        if m:
            rpo = _hours(m.group(1), m.group(2))

        affected = None
        m = re.search(r"(\d+(?:\.\d+)?)\s*(万)?\s*用户", raw)
        if m:
            affected = int(float(m.group(1)) * (10000 if m.group(2) else 1))

        risk_terms = [w for w in ("回滚", "权限", "证书", "网络", "数据库", "队列", "磁盘",
                                  "容量", "依赖", "超时", "限流", "数据丢失", "资损")
                      if w in raw]
        return {
            "service": service,
            "severity": severity,
            "window_hours": window_hours,
            "rto_hours": rto,
            "rpo_hours": rpo,
            "affected_users": affected,
            "risk_terms": risk_terms,
            "requires_rollback": ("回滚" in raw) or ("退路" in raw),
        }

    # ------------------------------------------------------------------ #
    # DAG 编译
    # ------------------------------------------------------------------ #
    def _build_stages(self, ents: Dict[str, Any]) -> List[Dict[str, Any]]:
        factor = {"critical": 1.5, "major": 1.0, "minor": 0.75}.get(ents["severity"], 1.0)
        stages: List[Dict[str, Any]] = []
        for sid, name, hours, deps, deliverable in _STAGE_DEFS:
            stages.append({
                "id": sid, "name": name, "deps": list(deps),
                "effort_hours": round(hours * factor, 2),
                "assignee": "蛙值守",
                "deliverable": deliverable,
            })
        if ents["requires_rollback"]:
            for st in stages:
                if st["id"] == "recover":
                    st["deliverable"] += "（含回滚计划与演练证据）"
        return stages

    def topo_sort(self, stages: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        ids = [s["id"] for s in stages]
        indeg = {sid: 0 for sid in ids}
        adj: Dict[str, List[str]] = {sid: [] for sid in ids}
        for st in stages:
            for dep in st.get("deps") or []:
                if dep not in indeg:
                    raise ValueError(f"依赖不存在: {st['id']} -> {dep}")
                adj[dep].append(st["id"])
                indeg[st["id"]] += 1
        ready = sorted([sid for sid, d in indeg.items() if d == 0])
        order: List[str] = []
        waves: List[List[str]] = []
        current = list(ready)
        while current:
            waves.append(sorted(current))
            nxt: List[str] = []
            for sid in current:
                order.append(sid)
                for child in adj[sid]:
                    indeg[child] -= 1
                    if indeg[child] == 0:
                        nxt.append(child)
            current = sorted(nxt)
        return {"ok": len(order) == len(ids), "order": order, "waves": waves,
                "cycle_detected": len(order) != len(ids)}

    def critical_path(self, stages: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        by_id = {s["id"]: s for s in stages}
        memo: Dict[str, Tuple[float, List[str]]] = {}

        def walk(sid: str) -> Tuple[float, List[str]]:
            if sid in memo:
                return memo[sid]
            best = (0.0, [])
            for dep in by_id[sid].get("deps") or []:
                h, p = walk(dep)
                if h > best[0]:
                    best = (h, p)
            res = (round(best[0] + float(by_id[sid]["effort_hours"]), 2), best[1] + [sid])
            memo[sid] = res
            return res

        best = max((walk(sid) for sid in by_id), key=lambda x: x[0])
        return {"hours": best[0], "path": best[1]}

    def compile_request(self, text: str, deadline_hours: Optional[float] = None) -> Dict[str, Any]:
        ents = self.extract_entities(text)
        stages = self._build_stages(ents)
        topo = self.topo_sort(stages)
        cp = self.critical_path(stages)
        total = round(sum(s["effort_hours"] for s in stages), 2)
        window = deadline_hours if deadline_hours is not None else ents.get("window_hours")
        feasible = None if window is None else bool(total <= float(window))
        return {
            "ok": bool(topo["ok"]),
            "engine": self.ENGINE, "layer": self.LAYER,
            "request": text,
            "entities": ents,
            "stages": stages,
            "dag": {"vertices": len(stages),
                    "edges": sum(len(s["deps"]) for s in stages),
                    "is_dag": not topo["cycle_detected"]},
            "topo_order": topo["order"],
            "waves": topo["waves"],
            "parallel_waves": len(topo["waves"]),
            "critical_path": cp,
            "total_effort_hours": total,
            "deadline_hours": window,
            "deadline_feasible": feasible,
            "bottleneck": max(stages, key=lambda s: s["effort_hours"])["id"],
            "capabilities": list(self.CAPABILITIES),
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    # ------------------------------------------------------------------ #
    # Markdown 看板
    # ------------------------------------------------------------------ #
    def render_markdown(self, compiled: Dict[str, Any]) -> str:
        ents = compiled.get("entities") or {}
        lines = [
            "# 复合故障诉求 · 恢复 DAG 编译单",
            "",
            f"- 服务：{ents.get('service') or '未识别'}",
            f"- 严重度：{ents.get('severity')}",
            f"- 恢复窗口：{ents.get('window_hours')} h",
            f"- RTO/RPO：{ents.get('rto_hours')} h / {ents.get('rpo_hours')} h",
            f"- 影响用户：{ents.get('affected_users')}",
            f"- 总人时：{compiled.get('total_effort_hours')} 人时",
            f"- 关键路径：{' → '.join(compiled['critical_path']['path'])}"
            f"（{compiled['critical_path']['hours']} h）",
            f"- 并行波次：{compiled.get('parallel_waves')} 层",
            "",
            "| 阶段 | 名称 | 依赖 | 人时 | 责任人 | 交付物 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for s in compiled.get("stages", []):
            lines.append(f"| {s['id']} | {s['name']} | {','.join(s['deps']) or '-'} | "
                         f"{s['effort_hours']} | {s['assignee']} | {s['deliverable']} |")
        lines += ["", f"> 拓扑序：{' → '.join(compiled.get('topo_order', []))}"]
        return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R20 L02 复合故障诉求 DAG 编译器")
    ap.add_argument("--text", required=True)
    ap.add_argument("--deadline", type=float, default=0.0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args(argv)
    comp = R20IntentCompiler()
    out = comp.compile_request(args.text, args.deadline or None)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    if args.md:
        os.makedirs(os.path.dirname(os.path.abspath(args.md)), exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(comp.render_markdown(out))
    print(json.dumps({"ok": out["ok"], "engine": out["engine"],
                      "stages": len(out["stages"]), "hours": out["total_effort_hours"]},
                     ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
