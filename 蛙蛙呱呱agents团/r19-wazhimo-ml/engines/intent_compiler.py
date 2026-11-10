# -*- coding: utf-8 -*-
"""L02 意图解构层 —— R19 复合模型工程诉求 → 5 阶段 Kahn 交付 DAG。

SOP v13.0 L02 体检病灶（R19 真实断点）：
    1. `_INTENT_ROUTES` 只有 14 条关键词硬匹配，只能回答「调哪个技能」，
       答不出**要动几个阶段、几步、几天、谁先谁后、瓶颈在哪**；
    2. 「紧急评估这个模型的准确率、延迟 P95<200ms，明天要发布」这类复合诉求
       被压扁成一个技能调用，阶段依赖、工时预算、关键路径全部丢失；
    3. 无拓扑排序、无环路检测：一旦依赖写错就是死循环，人类只能手工排。

对标开源标杆（Stars > 1k）：
    * stanfordnlp/dspy (>17k)      —— signature 编译与模块化 pipeline
    * ray-project/ray (>33k)       —— DAG 任务图与并行波次调度
    * apache/airflow (>36k)        —— DAG 拓扑、依赖与调度语义

落地的最低 3 项架构升级：
    1. 实体抽取：模型/数据集/指标阈值/延迟预算/截止工时/风险等级；
    2. 5 阶段标准 Kahn DAG：实验登记 → 运行追踪 → 评估评分 / 回归验证 → 发布裁决；
    3. 拓扑排序 + 并行波次 + 关键路径 + 总工时/并形增益预算，环即判非法。

用法：
    python -m engines.intent_compiler --text "紧急评估客服助手模型，准确率≥0.9，明天发布" \
        --out workspace/rounds/L02_dag.json --md workspace/rounds/L02_dag.md
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 5 阶段标准交付链（R19 模型工程特化）
STAGE_SPECS: List[Dict[str, Any]] = [
    {"id": "audit", "name": "实验登记", "skill": "tracking/experiment",
     "deps": [], "base_hours": 1.5, "owner": "R19 蛙智模",
     "deliverable": "experiment_id + tracking_uri + 实验类型"},
    {"id": "track", "name": "运行追踪", "skill": "tracking/run",
     "deps": ["audit"], "base_hours": 1.0, "owner": "R19 蛙智模",
     "deliverable": "run_id + 指标/参数/环境快照"},
    {"id": "evaluate", "name": "评估评分", "skill": "evaluation/scorer",
     "deps": ["track"], "base_hours": 2.0, "owner": "R19 蛙智模",
     "deliverable": "评估集 + 评分器 + accuracy/F1 精算"},
    {"id": "regression", "name": "回归验证", "skill": "release/regression",
     "deps": ["track"], "base_hours": 2.5, "owner": "R19 蛙智模",
     "deliverable": "fail-before/pass-after/existing_green 回归证据"},
    {"id": "decide", "name": "发布裁决", "skill": "release/candidate",
     "deps": ["evaluate", "regression"], "base_hours": 0.5, "owner": "R19 蛙智模",
     "deliverable": "PASS/BLOCK/NEEDS_REVIEW 三裁决 + 证据链"},
]

_URGENT_WORDS = ["紧急", "尽快", "今天", "立刻", "马上", "加急", "截止", "明天", "今晚"]


class R19IntentCompiler:
    """把复合模型工程自然语言诉求编译成可执行的 5 阶段交付 DAG。"""

    ENGINE = "R19IntentCompiler"
    LAYER = "L02"
    CAPABILITIES = [
        "复合诉求实体抽取 (模型/数据集/指标阈值/延迟预算/截止/风险)",
        "5 阶段 Kahn 拓扑 DAG 编译 (stages/deps/工时/责任人/交付物)",
        "拓扑排序 + 并行波次 + 关键路径 + 环路检测与工时预算",
        "[C2] CPM 正逆推 (ES/EF/LS/LF) 与总浮时/自由浮时定位近关键任务",
        "[C2] 截止期可行性裁决 + 关键路径赶工压缩建议 (crash plan)",
    ]

    # ------------------------------------------------------------------ #
    # 1. 实体抽取
    # ------------------------------------------------------------------ #
    def extract_entities(self, text: str) -> Dict[str, Any]:
        t = str(text or "")
        low = t.lower()
        model = ""
        m = re.search(r"(?:模型|model)\s*[:：]?\s*([A-Za-z0-9_.\-]*[\u4e00-\u9fa5A-Za-z0-9_\-]+)", t)
        if m:
            model = m.group(1).strip()
        dataset = ""
        d = re.search(r"(?:数据集|评估集|dataset)\s*[:：]?\s*([A-Za-z0-9_.\-]*[\u4e00-\u9fa5A-Za-z0-9_\-]+)", t)
        if d:
            dataset = d.group(1).strip()

        targets: Dict[str, float] = {}
        for mm in re.finditer(r"(accuracy|准确率|精确率|precision|召回率|recall|f1|F1)\s*"
                              r"(?:>=|≥|＞=|大于等于|达到|不低于)\s*(0?\.\d+|\d+(?:\.\d+)?%)",
                              t, re.IGNORECASE):
            key = mm.group(1).lower()
            key = {"准确率": "accuracy", "精确率": "precision", "召回率": "recall"}.get(key, key)
            raw = mm.group(2)
            val = float(raw[:-1]) / 100 if raw.endswith("%") else float(raw)
            targets[key] = round(val, 4)

        latency_ms = None
        lm = re.search(r"(?:p95|P95|延迟)\s*(?:<=|<|＜|不超过|低于)?\s*(\d+(?:\.\d+)?)\s*(ms|毫秒)",
                       t)
        if lm:
            latency_ms = float(lm.group(1))

        deadline_hours = None
        dm = re.search(r"(\d+(?:\.\d+)?)\s*(小时|h|H|天|d|D|分钟|min)", t)
        if dm:
            num = float(dm.group(1))
            unit = dm.group(2).lower()
            if unit in ("小时", "h"):
                deadline_hours = num
            elif unit in ("天", "d"):
                deadline_hours = num * 24.0
            else:
                deadline_hours = round(num / 60.0, 4)

        sample_size = None
        sm = re.search(r"(\d+)\s*(条样本|条|个样本|样本|cases?)", t)
        if sm:
            sample_size = int(sm.group(1))

        risk = "medium"
        if any(w in t for w in ("高风险", "高敏感", "医疗", "金融", "法律")):
            risk = "high"
        elif any(w in t for w in ("低风险", "内部工具", "玩具")):
            risk = "low"

        return {
            "model_name": model,
            "dataset": dataset,
            "metric_targets": targets,
            "latency_p95_ms": latency_ms,
            "deadline_hours": deadline_hours,
            "sample_size": sample_size,
            "is_urgent": any(w in t for w in _URGENT_WORDS) or bool(low and "urgent" in low),
            "risk_tier": risk,
            "intent_text": t.strip(),
            "text_length": len(t.strip()),
        }

    # ------------------------------------------------------------------ #
    # 2. 编译 5 阶段 DAG
    # ------------------------------------------------------------------ #
    def compile_intent(self, text: str) -> List[Dict[str, Any]]:
        ent = self.extract_entities(text)
        multiplier = 1.0
        if ent["is_urgent"]:
            multiplier *= 0.8
        if ent["risk_tier"] == "high":
            multiplier *= 1.3
        if (ent["sample_size"] or 0) > 1000:
            multiplier *= 1.2
        if ent["deadline_hours"] and ent["deadline_hours"] <= 8:
            multiplier *= 0.9

        stages: List[Dict[str, Any]] = []
        for spec in STAGE_SPECS:
            hours = round(spec["base_hours"] * multiplier, 2)
            if spec["id"] == "evaluate" and (ent["sample_size"] or 0) >= 500:
                hours = round(hours + 0.5, 2)
            stages.append({
                "id": spec["id"],
                "name": spec["name"],
                "skill": spec["skill"],
                "deps": list(spec["deps"]),
                "estimated_hours": hours,
                "owner": spec["owner"],
                "deliverable": spec["deliverable"],
            })
        return stages

    # ------------------------------------------------------------------ #
    # 3. 拓扑 / 波次 / 关键路径 / 工时预算
    # ------------------------------------------------------------------ #
    def topo_sort(self, stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        ids = [s["id"] for s in stages]
        idset = set(ids)
        unknown = [d for s in stages for d in s["deps"] if d not in idset]
        indeg = {i: 0 for i in ids}
        adj: Dict[str, List[str]] = {i: [] for i in ids}
        for s in stages:
            for d in s["deps"]:
                if d in idset:
                    adj[d].append(s["id"])
                    indeg[s["id"]] += 1
        queue = sorted([i for i in ids if indeg[i] == 0])
        order: List[str] = []
        waves: List[List[str]] = []
        current = list(queue)
        while current:
            waves.append(sorted(current))
            nxt: List[str] = []
            for node in sorted(current):
                order.append(node)
                for j in sorted(adj[node]):
                    indeg[j] -= 1
                    if indeg[j] == 0:
                        nxt.append(j)
            current = nxt
        is_valid = len(order) == len(ids) and not unknown
        return {"is_dag_valid": bool(is_valid), "topological_sequence": order,
                "waves": waves, "unknown_deps": unknown,
                "cycle_nodes": [i for i in ids if i not in order]}

    def evaluate_budget_and_schedule(self, stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        topo = self.topo_sort(stages)
        hours = {s["id"]: float(s["estimated_hours"]) for s in stages}
        deps = {s["id"]: list(s["deps"]) for s in stages}
        # 关键路径：按拓扑序做最长路径 DP
        dist: Dict[str, float] = {}
        prev: Dict[str, Optional[str]] = {}
        for node in topo["topological_sequence"]:
            best, best_prev = 0.0, None
            for d in deps.get(node, []):
                cand = dist.get(d, 0.0)
                if cand > best:
                    best, best_prev = cand, d
            dist[node] = round(best + hours.get(node, 0.0), 2)
            prev[node] = best_prev
        if dist:
            end = max(dist, key=lambda k: dist[k])
            path: List[str] = []
            cur: Optional[str] = end
            while cur:
                path.append(cur)
                cur = prev.get(cur)
            path.reverse()
            critical_hours = dist[end]
        else:
            path, critical_hours = [], 0.0
        total = round(sum(hours.values()), 2)
        return {
            "is_dag_valid": topo["is_dag_valid"],
            "topological_sequence": topo["topological_sequence"],
            "waves": topo["waves"],
            "wave_count": len(topo["waves"]),
            "critical_path": path,
            "critical_path_hours": round(float(critical_hours), 2),
            "total_estimated_hours": total,
            "parallel_gain_hours": round(total - float(critical_hours), 2),
            "stage_count": len(stages),
            "cycle_nodes": topo["cycle_nodes"],
            "unknown_deps": topo["unknown_deps"],
        }

    # ------------------------------------------------------------------ #
    # 3b. [Cycle 2] CPM 正逆推：ES/EF/LS/LF 与浮时
    # ------------------------------------------------------------------ #
    def compute_cpm(self, stages: List[Dict[str, Any]]) -> Dict[str, Any]:
        topo = self.topo_sort(stages)
        if not topo["is_dag_valid"]:
            return {"ok": False, "is_dag_valid": False,
                    "cycle_nodes": topo["cycle_nodes"],
                    "unknown_deps": topo["unknown_deps"],
                    "error": "DAG 非法（存在环或悬空依赖），CPM 不可计算"}
        hours = {s["id"]: float(s.get("estimated_hours", 0) or 0) for s in stages}
        deps = {s["id"]: list(s.get("deps") or []) for s in stages}
        succ: Dict[str, List[str]] = {s["id"]: [] for s in stages}
        for node, ds in deps.items():
            for d in ds:
                if d in succ:
                    succ[d].append(node)
        order = topo["topological_sequence"]
        es: Dict[str, float] = {}
        ef: Dict[str, float] = {}
        for node in order:
            es[node] = round(max([ef[d] for d in deps[node] if d in ef] or [0.0]), 4)
            ef[node] = round(es[node] + hours[node], 4)
        project = round(max(ef.values() or [0.0]), 4)
        ls: Dict[str, float] = {}
        lf: Dict[str, float] = {}
        for node in reversed(order):
            lf[node] = round(min([ls[s] for s in succ[node] if s in ls] or [project]), 4)
            ls[node] = round(lf[node] - hours[node], 4)
        rows: List[Dict[str, Any]] = []
        for node in order:
            total_float = round(ls[node] - es[node], 4)
            free_float = round(min([es[s] for s in succ[node] if s in es] or [project]) - ef[node], 4)
            rows.append({"id": node, "hours": hours[node], "es": es[node], "ef": ef[node],
                         "ls": ls[node], "lf": lf[node], "total_float": total_float,
                         "free_float": free_float, "critical": abs(total_float) <= 1e-9})
        critical = [r["id"] for r in rows if r["critical"]]
        return {"ok": True, "is_dag_valid": True, "project_duration_hours": project,
                "critical_path": critical, "critical_hours": project,
                "near_critical": [r["id"] for r in rows
                                  if 0 < r["total_float"] <= 1.0],
                "schedule": rows}

    # ------------------------------------------------------------------ #
    # 3c. [Cycle 2] 截止期可行性 + 赶工压缩建议
    # ------------------------------------------------------------------ #
    def assess_deadline(self, stages: List[Dict[str, Any]],
                        deadline_hours: Optional[float]) -> Dict[str, Any]:
        cpm = self.compute_cpm(stages)
        if not cpm.get("ok"):
            return {"ok": False, "feasible": False, "cpm": cpm,
                    "error": cpm.get("error", "CPM 不可计算")}
        critical = cpm["critical_hours"]
        if deadline_hours is None or float(deadline_hours) <= 0:
            return {"ok": True, "feasible": None, "deadline_hours": None,
                    "critical_hours": critical, "slack_hours": None,
                    "verdict": "NO_DEADLINE", "crash_plan": []}
        deadline = float(deadline_hours)
        slack = round(deadline - critical, 4)
        feasible = slack >= -1e-9
        crash_plan: List[Dict[str, Any]] = []
        compressible_total = 0.0
        if not feasible:
            need = round(-slack, 4)
            hours = {s["id"]: float(s.get("estimated_hours", 0) or 0) for s in stages}
            order = cpm["critical_path"]
            for node in sorted(order, key=lambda n: -hours.get(n, 0.0)):
                max_cut = round(hours.get(node, 0.0) * 0.5, 4)
                if max_cut <= 0:
                    continue
                take = round(min(max_cut, need), 4)
                compressible_total += take
                need = round(need - take, 4)
                crash_plan.append({"stage": node, "current_hours": hours.get(node, 0.0),
                                   "compress_hours": take,
                                   "after_hours": round(hours.get(node, 0.0) - take, 4),
                                   "owner": "R19 蛙智模"})
                if need <= 1e-9:
                    break
            compressible_total = round(compressible_total, 4)
        return {
            "ok": True, "feasible": feasible, "deadline_hours": deadline,
            "critical_hours": critical, "slack_hours": slack,
            "verdict": "FEASIBLE" if feasible else (
                "FEASIBLE_WITH_CRASH" if compressible_total >= round(-slack, 4)
                else "INFEASIBLE"),
            "crash_plan": crash_plan,
            "crash_total_hours": round(compressible_total, 4),
            "critical_path": cpm["critical_path"],
        }

    # ------------------------------------------------------------------ #
    # 4. 一键编译（含 Markdown 渲染）
    # ------------------------------------------------------------------ #
    def compile_request(self, text: str) -> Dict[str, Any]:
        entities = self.extract_entities(text)
        stages = self.compile_intent(text)
        summary = self.evaluate_budget_and_schedule(stages)
        return {
            "ok": bool(summary["is_dag_valid"] and len(stages) == 5),
            "engine": self.ENGINE, "layer": self.LAYER,
            "entities": entities, "stages": stages, "summary": summary,
            "capabilities": list(self.CAPABILITIES),
            "verdict": "PASS" if summary["is_dag_valid"] else "FAIL",
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    def render_markdown(self, dag: Dict[str, Any]) -> str:
        s = dag.get("summary", {})
        ent = dag.get("entities", {})
        lines = ["# R19 模型工程交付 DAG", "",
                 f"- 诉求：{ent.get('intent_text', '')}",
                 f"- 模型：{ent.get('model_name') or '未指定'} | "
                 f"数据集：{ent.get('dataset') or '未指定'} | "
                 f"风险：{ent.get('risk_tier')} | 紧急：{ent.get('is_urgent')}",
                 f"- 拓扑合法：**{s.get('is_dag_valid')}** | 波次 {s.get('wave_count')} | "
                 f"总工时 {s.get('total_estimated_hours')}h | 关键路径 "
                 f"{s.get('critical_path_hours')}h | 并行增益 {s.get('parallel_gain_hours')}h",
                 "", "## 阶段与依赖", "",
                 "| 阶段 | 技能 | 依赖 | 工时(h) | 交付物 |",
                 "| :--- | :--- | :--- | ---: | :--- |"]
        for st in dag.get("stages", []):
            lines.append(f"| {st['name']}({st['id']}) | {st['skill']} | "
                         f"{' / '.join(st['deps']) or '—'} | {st['estimated_hours']} | "
                         f"{st['deliverable']} |")
        lines += ["", "## 并行波次", ""]
        for i, wave in enumerate(s.get("waves", []), 1):
            lines.append(f"{i}. {', '.join(wave)}")
        lines += ["", f"## 关键路径", "", " → ".join(s.get("critical_path", [])) or "—", ""]
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R19 L02 意图解构与 Kahn DAG 编译")
    ap.add_argument("--text", required=True, help="复合模型工程诉求")
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args(argv)

    comp = R19IntentCompiler()
    out = comp.compile_request(args.text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    if args.md:
        os.makedirs(os.path.dirname(os.path.abspath(args.md)), exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(comp.render_markdown(out))
    print(json.dumps({"ok": out["ok"], "stages": len(out["stages"]),
                      "dag_valid": out["summary"]["is_dag_valid"],
                      "total_hours": out["summary"]["total_estimated_hours"],
                      "out": args.out}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
