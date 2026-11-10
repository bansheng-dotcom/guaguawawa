# -*- coding: utf-8 -*-
"""L02 意图解构层 —— 把一句人话编译成 5 阶段 Kahn 拓扑交付 DAG。

病灶（体检结论）：升级前 R18 的「意图路由」是 `_INTENT_ROUTES` 里 14 条关键词
硬匹配（`if "回填" in intent`），只能回答「调哪个技能」，无法回答三个真实问题：
要动几张表、要多久、哪几步有先后依赖、哪一步是瓶颈。复杂需求（"把 orders 和
dwd_orders 最近 30 天增量做成看板，2 小时内要新鲜"）在旧实现下被压成一次
`quality/check`，工时与依赖全丢。

对标标杆（Stars > 1k）：
- `stanfordnlp/dspy`（> 17k）：声明式签名 + 编译式流水线；
- `ray-project/ray`（> 33k）：DAG 拓扑调度与关键路径；
- `apache/airflow`（> 36k）：TaskInstance 依赖图与 DAG 无环强约束。

本引擎落地：
1. 结构化实体抽取（表 / 时间窗 / SLA / 模式 / 目的地），零随机、可复现；
2. 编译固定 5 阶段交付 DAG【审计探查 → 建模转换 → 编排调度 → 质量门禁 → 发布交付】，
   并用 Kahn 算法做拓扑排序 + 环检测；
3. 基于表数量 / 模式 / SLA / 时间窗的确定性工时模型，输出关键路径与人天预算。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

# 5 阶段标准（SOP L02：数据工程版）
STAGES: List[Dict[str, Any]] = [
    {"id": "01_profile", "stage": "audit", "title": "数据探查与审计",
     "owner": "蛙数仓", "gate": "源表可达 + 字段画像 + 空值/重复基线",
     "base_effort_h": 2.0},
    {"id": "02_model", "stage": "transform", "title": "建模与转换",
     "owner": "蛙数仓", "gate": "物化方式合法 + ref 不悬空 + 不自引用",
     "base_effort_h": 6.0},
    {"id": "03_orchestrate", "stage": "schedule", "title": "编排与调度",
     "owner": "蛙数仓", "gate": "DAG 无环 + 任务状态无 failed + 重试≤3",
     "base_effort_h": 4.0},
    {"id": "04_gate", "stage": "quality", "title": "质量门禁",
     "owner": "蛙数仓", "gate": "空值率≤0.10 + 重复率≤0.05 + 新鲜度≤SLA",
     "base_effort_h": 3.0},
    {"id": "05_publish", "stage": "publish", "title": "发布与交付",
     "owner": "蛙数仓", "gate": "伴生 bundle/SARIF 落盘 + handoff 声明",
     "base_effort_h": 2.0},
]

# 拓扑依赖（真实工程顺序，非链式占位）：
# 探查→建模、探查→编排、建模→编排、建模→门禁、编排→门禁、门禁→发布
DEPENDENCIES: List[Tuple[str, str, str]] = [
    ("01_profile", "02_model", "源表画像决定建模口径"),
    ("01_profile", "03_orchestrate", "源表分区字段决定调度窗口"),
    ("02_model", "03_orchestrate", "编排依赖模型产物"),
    ("02_model", "04_gate", "门禁绑定模型输出列"),
    ("03_orchestrate", "04_gate", "门禁需在调度后按批次执行"),
    ("04_gate", "05_publish", "门禁不过不得发布"),
]

_STOPWORDS = {
    "dbt", "dag", "sql", "cdc", "api", "csv", "json", "parquet", "sla", "kpi",
    "etl", "elt", "table", "view", "full", "incremental", "sync", "select",
    "from", "where", "join", "the", "and", "for", "with", "bi", "id", "uuid",
}
_TABLE_TOKEN_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]{1,63})`")
_TABLE_SUFFIX_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]{2,63})\s*表")
_LATIN_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,63}")
_WINDOW_DAYS_RE = re.compile(r"(?:最近|近|过去|前)\s*(\d{1,3})\s*(天|日|个月|月|周|小时)")
_WINDOW_LAST_RE = re.compile(r"上(?:个)?(周|月|季度)")
_WINDOW_RANGE_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s*(?:到|至|~|—|-)\s*(\d{4}-\d{2}-\d{2})")
_SLA_HOURS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:小时|h|H)\s*(?:内|以内|之内)?")
_SLA_MINUTES_RE = re.compile(r"(\d+(?:\.\d+)?)\s*分钟\s*(?:内|以内|之内)?")


def _slug(text: str) -> str:
    return hashlib.sha1(str(text).encode("utf-8")).hexdigest()[:12]


def _dedup(seq: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


class DataEngIntentCompiler:
    """L02 意图编译器：自然语言 → 实体 + 5 阶段 Kahn DAG + 工时预算。"""

    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        self.thresholds = thresholds or {}

    # ------------------------------------------------------------------ #
    # 实体抽取
    # ------------------------------------------------------------------ #
    def extract_entities(self, text: str) -> Dict[str, Any]:
        raw = str(text or "")
        warnings: List[str] = []

        tables = [m.group(1) for m in _TABLE_TOKEN_RE.finditer(raw)]
        tables += [m.group(1) for m in _TABLE_SUFFIX_RE.finditer(raw)]
        for tok in _LATIN_TOKEN_RE.findall(raw):
            low = tok.lower()
            if low in _STOPWORDS:
                continue
            # 纯小写或含下划线的标识符更像表名；排除纯技术缩写
            if tok.islower() or "_" in tok:
                tables.append(tok)
        tables = _dedup(tables)[:10]
        if not tables:
            warnings.append("未识别到源表标识符，需人工确认 source（不猜表名）")

        window_days: Optional[int] = None
        window_source = ""
        m = _WINDOW_DAYS_RE.search(raw)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            factor = {"天": 1, "日": 1, "小时": 0, "周": 7, "个月": 30, "月": 30}[unit]
            window_days = n * factor if factor else max(1, round(n / 24))
            window_source = m.group(0)
        if window_days is None:
            m = _WINDOW_LAST_RE.search(raw)
            if m:
                window_days = {"周": 7, "月": 30, "季度": 90}[m.group(1)]
                window_source = m.group(0)
        if window_days is None:
            m = _WINDOW_RANGE_RE.search(raw)
            if m:
                try:
                    d0 = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                    d1 = datetime.strptime(m.group(2), "%Y-%m-%d").date()
                    window_days = max(1, (d1 - d0).days + 1)
                    window_source = m.group(0)
                except ValueError:
                    warnings.append(f"时间区间解析失败：{m.group(0)}")

        sla_hours: Optional[float] = None
        m = _SLA_HOURS_RE.search(raw)
        if m:
            sla_hours = float(m.group(1))
        else:
            m2 = _SLA_MINUTES_RE.search(raw)
            if m2:
                sla_hours = round(float(m2.group(1)) / 60.0, 3)

        mode = "unspecified"
        if re.search(r"cdc|实时|流式|binlog", raw, re.I):
            mode = "cdc"
        elif re.search(r"全量|全表|重跑|重算", raw):
            mode = "full"
        elif re.search(r"增量|水位|watermark|append", raw, re.I):
            mode = "incremental"
        else:
            warnings.append("未显式声明增量/全量/cdc 模式，按 unspecified 输出待人工确认")

        destination = "table"
        if re.search(r"看板|dashboard|bi|指标卡", raw, re.I):
            destination = "dashboard"
        elif re.search(r"报表|report|日报|周报", raw, re.I):
            destination = "report"
        elif re.search(r"api|接口|服务化", raw, re.I):
            destination = "api"
        elif re.search(r"特征|feature|训练集", raw, re.I):
            destination = "feature"

        thresholds = {}
        m = re.search(r"空值(?:率)?\s*(?:≤|<=|<|不超过)\s*(0?\.\d+|\d+%)", raw)
        if m:
            thresholds["max_null_ratio"] = self._pct(m.group(1))
        m = re.search(r"重复(?:率)?\s*(?:≤|<=|<|不超过)\s*(0?\.\d+|\d+%)", raw)
        if m:
            thresholds["max_dup_ratio"] = self._pct(m.group(1))

        return {
            "tables": tables,
            "table_count": len(tables),
            "window_days": window_days,
            "window_source": window_source,
            "sla_hours": sla_hours,
            "mode": mode,
            "destination": destination,
            "thresholds": thresholds,
            "warnings": warnings,
        }

    @staticmethod
    def _pct(token: str) -> float:
        if token.endswith("%"):
            return round(float(token[:-1]) / 100.0, 6)
        return float(token)

    # ------------------------------------------------------------------ #
    # 拓扑
    # ------------------------------------------------------------------ #
    @staticmethod
    def topological_order(node_ids: Sequence[str],
                          edges: Sequence[Dict[str, str]]) -> Dict[str, Any]:
        """Kahn 拓扑排序 + 环检测；结果确定性（同层按 id 升序）。"""
        ids = list(node_ids)
        indeg = {n: 0 for n in ids}
        adj: Dict[str, List[str]] = {n: [] for n in ids}
        for e in edges:
            a, b = e["from"], e["to"]
            if a not in indeg or b not in indeg:
                raise ValueError(f"依赖边引用了不存在的节点：{a}->{b}")
            adj[a].append(b)
            indeg[b] += 1
        ready = sorted([n for n in ids if indeg[n] == 0])
        order: List[str] = []
        while ready:
            cur = ready.pop(0)
            order.append(cur)
            for nxt in sorted(adj[cur]):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    ready.append(nxt)
            ready.sort()
        acyclic = len(order) == len(ids)
        cycle_nodes = [] if acyclic else sorted([n for n in ids if n not in order])
        return {"order": order, "acyclic": acyclic, "cycle_nodes": cycle_nodes}

    @staticmethod
    def parallel_levels(node_ids: Sequence[str],
                        edges: Sequence[Dict[str, str]]) -> List[List[str]]:
        """按最长前驱链分层，供并行执行计划使用。"""
        level = {n: 0 for n in node_ids}
        changed = True
        while changed:
            changed = False
            for e in edges:
                if level[e["to"]] < level[e["from"]] + 1:
                    level[e["to"]] = level[e["from"]] + 1
                    changed = True
        groups: Dict[int, List[str]] = {}
        for n in node_ids:
            groups.setdefault(level[n], []).append(n)
        return [sorted(groups[k]) for k in sorted(groups)]

    # ------------------------------------------------------------------ #
    # 工时与关键路径
    # ------------------------------------------------------------------ #
    def _effort(self, entities: Dict[str, Any]) -> Dict[str, float]:
        n_tables = max(1, int(entities.get("table_count") or 1))
        table_mult = min(3.0, 1 + 0.4 * (n_tables - 1))
        mode_mult = {"incremental": 1.0, "full": 1.5, "cdc": 1.4,
                     "unspecified": 1.1}[entities.get("mode", "unspecified")]
        sla = entities.get("sla_hours")
        sla_mult = 1.25 if sla is not None and sla <= 2 else (1.1 if sla is not None and sla <= 6 else 1.0)
        days = entities.get("window_days") or 0
        window_mult = 1.4 if days >= 90 else (1.2 if days >= 30 else 1.0)
        mult = table_mult * mode_mult * sla_mult * window_mult
        return {s["id"]: round(s["base_effort_h"] * mult, 2) for s in STAGES}

    def _critical_path(self, efforts: Dict[str, float],
                       edges: Sequence[Dict[str, str]]) -> Dict[str, Any]:
        dist = {n: efforts[n] for n in efforts}
        prev: Dict[str, Optional[str]] = {n: None for n in efforts}
        for node in self.topological_order(list(efforts), edges)["order"]:
            for e in edges:
                if e["from"] != node:
                    continue
                cand = dist[node] + efforts[e["to"]]
                if cand > dist[e["to"]]:
                    dist[e["to"]] = cand
                    prev[e["to"]] = node
        end = max(dist, key=lambda n: (dist[n], n))
        path: List[str] = []
        cur: Optional[str] = end
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return {"path": path, "hours": round(dist[end], 2)}

    # ------------------------------------------------------------------ #
    # 编译
    # ------------------------------------------------------------------ #
    def compile_intent(self, text: str) -> Dict[str, Any]:
        entities = self.extract_entities(text)
        efforts = self._effort(entities)
        warnings = list(entities["warnings"])
        if entities.get("sla_hours") is None:
            warnings.append("未识别到新鲜度 SLA，按经验值 24h 兜底（须人工确认）")

        nodes = []
        for s in STAGES:
            nodes.append({
                "id": s["id"], "stage": s["stage"], "title": s["title"],
                "owner": s["owner"], "gate": s["gate"],
                "effort_h": efforts[s["id"]],
            })
        edges = [{"from": a, "to": b, "reason": why} for a, b, why in DEPENDENCIES]
        topo = self.topological_order([n["id"] for n in nodes], edges)
        if not topo["acyclic"]:
            raise ValueError(f"[DAG BLOCKED] 交付 DAG 出现环：{topo['cycle_nodes']}")
        crit = self._critical_path(efforts, edges)
        total_h = round(sum(efforts.values()), 2)
        return {
            "ok": True,
            "intent_id": _slug(text),
            "raw_intent": text,
            "entities": entities,
            "nodes": nodes,
            "edges": edges,
            "topological_order": topo["order"],
            "acyclic": True,
            "parallel_levels": self.parallel_levels([n["id"] for n in nodes], edges),
            "critical_path": crit["path"],
            "critical_path_h": crit["hours"],
            "total_effort_h": total_h,
            "total_man_days": round(total_h / 8.0, 2),
            "stage_count": len(nodes),
            "warnings": _dedup(warnings),
        }

    # 兼容别名：技能层按 compile 调用
    def compile(self, text: str) -> Dict[str, Any]:
        return self.compile_intent(text)

    def render_markdown(self, dag: Dict[str, Any]) -> str:
        e = dag["entities"]
        lines = [
            f"# 数据工程交付 DAG · {dag['intent_id']}", "",
            f"- 原始意图：{dag['raw_intent']}",
            f"- 源表：{', '.join(e['tables']) or '（未识别）'}（{e['table_count']} 张）",
            f"- 时间窗：{e['window_days'] if e['window_days'] is not None else '未知'} 天"
            f"（来源：{e['window_source'] or '—'}）",
            f"- 新鲜度 SLA：{e['sla_hours']} 小时" if e["sla_hours"] is not None
            else "- 新鲜度 SLA：未声明",
            f"- 模式：{e['mode']} · 目的地：{e['destination']}",
            f"- 总工时：{dag['total_effort_h']} h（{dag['total_man_days']} 人天）",
            f"- 关键路径：{' → '.join(dag['critical_path'])}（{dag['critical_path_h']} h）",
            "", "## 阶段", "",
            "| 阶段 | 标题 | 工时(h) | 门禁 |", "|---|---|---|---|",
        ]
        for n in dag["nodes"]:
            lines.append(f"| {n['id']} | {n['title']} | {n['effort_h']} | {n['gate']} |")
        lines += ["", "## 依赖边", ""]
        for ed in dag["edges"]:
            lines.append(f"- {ed['from']} → {ed['to']}：{ed['reason']}")
        if dag["warnings"]:
            lines += ["", "## 待确认", ""] + [f"- {w}" for w in dag["warnings"]]
        return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# CLI：python -m engines.intent_compiler --text "..." --out dag.json
# --------------------------------------------------------------------------- #
def _cli(argv=None) -> int:
    ap = argparse.ArgumentParser(description="R18 L02 意图编译器（5 阶段 Kahn DAG）")
    ap.add_argument("--text", required=True, help="自然语言数据工程需求")
    ap.add_argument("--out", default="", help="DAG JSON 输出路径")
    ap.add_argument("--md", default="", help="DAG Markdown 输出路径")
    args = ap.parse_args(argv)

    c = DataEngIntentCompiler()
    dag = c.compile_intent(args.text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(dag, f, ensure_ascii=False, indent=2)
    if args.md:
        os.makedirs(os.path.dirname(os.path.abspath(args.md)), exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(c.render_markdown(dag))
    print("__AGENT_RESULT__ " + json.dumps({
        "ok": True, "intent_id": dag["intent_id"],
        "stage_count": dag["stage_count"],
        "topological_order": dag["topological_order"],
        "total_effort_h": dag["total_effort_h"],
        "critical_path": dag["critical_path"],
        "out": args.out, "md": args.md,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
