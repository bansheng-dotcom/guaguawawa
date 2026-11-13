# -*- coding: utf-8 -*-
"""L02 意图解构层 (Intent Decompilation & DAG Compilation Layer)
对标开源: DSPy / Ray DAG / LangGraph / Vanna.ai
架构跃迁 (本轮新增):
1. 真实 Kahn 拓扑编译：显式声明节点依赖，执行入度削减排序，检测环路并输出并行波次 (waves)；
2. 实体消歧与标准化：指标/维度别名归一、相对时间窗语义化、冲突检测与告警；
3. 工时预算估算：按切片粒度与数据量估算人时、关键路径与并行度，输出可审计的 plan。
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple


class AnalysisIntentDecompiler:
    """自然语言意图编译与分析工作流 DAG 编排器。"""

    DOMAIN_KEYWORDS = {
        "quality": ["清洗", "脏数据", "异常值", "质检", "去重", "缺失率", "clean", "audit"],
        "describe": ["分布", "均值", "中位数", "概况", "描述", "离散", "describe", "summary"],
        "explore": ["趋势", "分组", "漏斗", "留存", "cohort", "rfm", "saas", "转化率", "trend", "groupby"],
        "rootcause": ["为什么", "下降", "归因", "贡献", "根因", "下钻", "异动", "drilldown", "decompose"],
        "statistics": ["abtest", "显著性", "假设检验", "t检验", "卡方", "方差分析", "回归", "因果", "功效"],
        "selfmedia": ["公众号", "自媒体", "抖音", "小红书", "知乎", "平台", "粉丝", "播放量", "dashboard"],
        "viz": ["图表", "可视化", "看板", "报告", "大屏", "spec", "chart", "report"],
    }

    ACTION_MAP = {
        "quality": "clean",
        "describe": "describe",
        "explore": "trend",
        "rootcause": "decompose",
        "statistics": "abtest",
        "selfmedia": "dashboard",
        "viz": "report",
    }

    # 依赖声明（viz 依赖在编译期动态指向所有分析节点）
    NODE_DEPS = {
        "quality": [],
        "describe": ["quality"],
        "explore": ["quality"],
        "rootcause": ["quality", "explore"],
        "statistics": ["quality", "explore"],
        "selfmedia": ["quality"],
    }

    BASE_EFFORT_HOURS = {
        "quality": 0.5,
        "describe": 0.5,
        "explore": 1.0,
        "rootcause": 2.0,
        "statistics": 1.5,
        "selfmedia": 1.0,
        "viz": 1.0,
    }

    METRIC_ALIAS = {
        "gmv": "gmv", "成交额": "gmv", "销售额": "gmv",
        "收入": "revenue", "revenue": "revenue",
        "客单价": "arpu", "arpu": "arpu",
        "转化率": "cvr", "cvr": "cvr",
        "uv": "uv", "pv": "pv",
        "粉丝数": "followers", "mrr": "mrr", "arr": "arr",
        "订单量": "order_count", "订单数": "order_count",
        "退款率": "refund_rate", "成本": "cost", "cost": "cost",
    }

    DIMENSION_ALIAS = {
        "渠道": "channel", "channel": "channel",
        "城市": "city", "city": "city",
        "省份": "province", "province": "province",
        "用户类型": "user_type", "人群": "user_segment",
        "平台": "platform", "platform": "platform",
        "月份": "month", "日期": "date", "date": "date",
        "品类": "category", "category": "category",
    }

    TIME_SEMANTICS = [
        (re.compile(r"上周"), "last_7d"),
        (re.compile(r"上个月|上月"), "last_30d"),
        (re.compile(r"去年同期|同比"), "yoy_same_period"),
        (re.compile(r"环比"), "mom"),
        (re.compile(r"最近\s*(\d+)\s*天"), "last_nd"),
        (re.compile(r"过去\s*(\d+)\s*个月"), "last_n_month"),
        (re.compile(r"Q([1-4])"), "quarter"),
        (re.compile(r"(\d{4})年"), "year"),
        (re.compile(r"(\d{1,2})月"), "month"),
    ]

    def compile_intent(self, text: str, data_rows: int = 0) -> Dict[str, Any]:
        """将自然语言输入解构并编译为可执行分析 DAG。"""
        normalized_text = (text or "").strip()
        matched_domains: List[str] = []

        for domain, kws in self.DOMAIN_KEYWORDS.items():
            if any(kw.lower() in normalized_text.lower() for kw in kws):
                matched_domains.append(domain)

        if not matched_domains:
            matched_domains = ["describe"]

        entities, warnings = self._extract_entities(normalized_text)
        steps = self._build_dag(matched_domains, entities)
        topo = self._kahn_topo_sort(steps)

        plan = self._estimate_effort(steps, entities, data_rows)

        return {
            "raw_query": normalized_text,
            "primary_domain": matched_domains[0],
            "matched_domains": matched_domains,
            "extracted_entities": entities,
            "entity_warnings": warnings,
            "dag_steps": steps,
            "step_count": len(steps),
            "is_complex_dag": len(steps) > 1,
            "execution_order": topo["order"],
            "execution_waves": topo["waves"],
            "dag_validation": {
                "valid": topo["valid"],
                "cycle_nodes": topo["cycle_nodes"],
                "node_count": len(steps),
                "edge_count": sum(len(s["depends_on"]) for s in steps),
            },
            "effort_budget": plan,
        }

    # ------------------------------------------------------------------ #
    # 实体抽取与标准化
    # ------------------------------------------------------------------ #
    def _extract_entities(self, text: str) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        metrics: List[str] = []
        dimensions: List[str] = []
        lower = text.lower()

        for kw, std in self.METRIC_ALIAS.items():
            if kw.lower() in lower and std not in metrics:
                metrics.append(std)

        for kw, std in self.DIMENSION_ALIAS.items():
            if kw.lower() in lower and std not in dimensions:
                dimensions.append(std)

        time_window: Optional[str] = None
        time_semantic: Optional[str] = None
        for pat, semantic in self.TIME_SEMANTICS:
            m = pat.search(text)
            if m:
                time_window = m.group(0)
                time_semantic = semantic
                # 继续扫描，最后一个时间窗生效，并记录冲突告警
        all_windows = [m.group(0) for pat, _ in self.TIME_SEMANTICS for m in [pat.search(text)] if m]
        if len(all_windows) > 1:
            warnings.append(f"multiple_time_windows:{'|'.join(all_windows)} -> 采用 '{all_windows[-1]}'")

        slices: List[str] = re.findall(r"按([\u4e00-\u9fa5]{1,6})(?:维度|分组|看|拆)", text)
        numbers = [float(x) for x in re.findall(r"\b(\d+(?:\.\d+)?)\b", text)]
        comparison = "yoy" if ("同比" in text or "去年同期" in text) else ("mom" if "环比" in text else None)

        entities = {
            "metrics": metrics,
            "dimensions": dimensions,
            "time_window": time_window,
            "time_window_semantic": time_semantic,
            "comparison_type": comparison,
            "slices": slices,
            "numbers": numbers,
        }
        return entities, warnings

    # ------------------------------------------------------------------ #
    # DAG 构建（显式依赖）
    # ------------------------------------------------------------------ #
    def _build_dag(self, domains: List[str], entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        order = ["quality", "describe", "explore", "rootcause", "statistics", "selfmedia", "viz"]
        selected = [d for d in order if d in domains]
        if not selected:
            selected = ["describe"]

        analysis_nodes = [d for d in selected if d != "viz"]
        domain_to_step = {dom: f"step_{i + 1}_{dom}" for i, dom in enumerate(selected)}
        steps: List[Dict[str, Any]] = []
        for dom in selected:
            step_id = domain_to_step[dom]
            if dom == "viz":
                deps = [domain_to_step[d] for d in analysis_nodes]
            else:
                declared = [d for d in self.NODE_DEPS.get(dom, []) if d in selected]
                deps = [domain_to_step[d] for d in declared]
            steps.append({
                "step_id": step_id,
                "domain": dom,
                "action": self.ACTION_MAP.get(dom, "run"),
                "depends_on": deps,
                "params": {
                    "metrics": entities["metrics"],
                    "dimensions": entities["dimensions"],
                    "time_window": entities["time_window"],
                    "time_window_semantic": entities.get("time_window_semantic"),
                },
            })
        return steps

    # ------------------------------------------------------------------ #
    # Kahn 拓扑排序 + 环路检测 + 并行波次
    # ------------------------------------------------------------------ #
    def _kahn_topo_sort(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        ids = [s["step_id"] for s in steps]
        indeg = {sid: 0 for sid in ids}
        children: Dict[str, List[str]] = {sid: [] for sid in ids}
        for s in steps:
            for dep in s["depends_on"]:
                if dep not in indeg:
                    continue
                indeg[s["step_id"]] += 1
                children[dep].append(s["step_id"])

        level = {sid: 0 for sid in ids}
        queue = sorted([sid for sid in ids if indeg[sid] == 0])
        order: List[str] = []
        while queue:
            cur = queue.pop(0)
            order.append(cur)
            for child in sorted(children[cur]):
                level[child] = max(level[child], level[cur] + 1)
                indeg[child] -= 1
                if indeg[child] == 0:
                    queue.append(child)
            queue.sort()

        cycle_nodes = sorted([sid for sid in ids if indeg[sid] > 0])
        waves: Dict[int, List[str]] = {}
        for sid in order:
            waves.setdefault(level[sid], []).append(sid)

        return {
            "valid": not cycle_nodes,
            "order": order,
            "waves": {str(k): v for k, v in sorted(waves.items())},
            "cycle_nodes": cycle_nodes,
        }

    # ------------------------------------------------------------------ #
    # 工时预算估算
    # ------------------------------------------------------------------ #
    def _estimate_effort(self, steps: List[Dict[str, Any]],
                         entities: Dict[str, Any], data_rows: int) -> Dict[str, Any]:
        metric_factor = 1.0 + 0.15 * max(0, len(entities.get("metrics", [])) - 1)
        dim_factor = 1.0 + 0.10 * max(0, len(entities.get("dimensions", [])) - 1)
        volume_factor = 1.0
        if data_rows > 0:
            volume_factor = round(1.0 + min(1.0, math.log10(max(1, data_rows)) / 8.0), 3)

        per_step: Dict[str, float] = {}
        for s in steps:
            base = self.BASE_EFFORT_HOURS.get(s["domain"], 1.0)
            per_step[s["step_id"]] = round(base * metric_factor * dim_factor * volume_factor, 2)

        # 关键路径：沿依赖链累积
        longest: Dict[str, float] = {}
        for sid in [s["step_id"] for s in steps]:
            step = next(s for s in steps if s["step_id"] == sid)
            upstream = max([longest.get(d, 0.0) for d in step["depends_on"]] or [0.0])
            longest[sid] = round(upstream + per_step[sid], 2)

        total = round(sum(per_step.values()), 2)
        critical = max(longest.values()) if longest else 0.0
        parallelism = round(total / critical, 2) if critical else 1.0
        return {
            "per_step_hours": per_step,
            "total_hours": total,
            "person_days": round(total / 8.0, 2),
            "critical_path_hours": critical,
            "parallelism_gain": parallelism,
            "factors": {
                "metric_factor": round(metric_factor, 3),
                "dimension_factor": round(dim_factor, 3),
                "volume_factor": volume_factor,
            },
        }
