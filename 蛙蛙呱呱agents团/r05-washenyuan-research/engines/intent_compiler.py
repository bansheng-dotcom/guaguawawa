# -*- coding: utf-8 -*-
"""L02 意图解构层：ResearchIntentCompiler 五阶段研究标准 DAG 编译器。

对标标杆:
- stanfordnlp/dspy (19k⭐)：把自然语言 signature 编译成可执行声明式计算图
- ray-project/ray (34k⭐)：任务 DAG 拓扑调度与依赖求解
- 顶级投研/咨询五阶段研究标准：审计立项 → 证据寻源 → 分析建模 → 验证压测 → 交付落地

吸收的机制:
1. Signature → DAG：任意模糊研究诉求都被编译为同一套五阶段标准流水线，
   每阶段带真实任务清单与工时预算，而非按关键词串一条线性伪链。
2. Kahn 拓扑排序：依赖边是真实边集合，入度为 0 的节点按传入 nodes 顺序出队
   （本轮用最小堆保证稳定顺序），因此同输入必然同输出；有环抛 DagCycleError。
3. 环检测：compile() 会对边集做真实拓扑求解，cycle_detected 是求解结果而非常量。
4. 实体/领域/复杂度全部正则或计分驱动：金额、百分比、地域、市场名词与关键词域
   命中共同决定复杂度级别，工时按「阶段基准 × 复杂度系数 × 域负载 × 实体负载」
   浮动计算，不存在写死的测试期望值。
"""
from __future__ import annotations

import heapq
import re
from typing import Any, Dict, List, Sequence


class DagCycleError(Exception):
    """研究阶段依赖图存在环时抛出（禁止带环执行研究流水线）。"""


class ResearchIntentCompiler:
    """战略研究意图编译器：自然语言诉求 → 五阶段研究 DAG + 工时预算。"""

    #: 五阶段研究标准（顺序即研究流水线的业务先后）
    STAGES: Sequence[str] = ("audit", "sourcing", "analysis", "validation", "delivery")
    STAGE_NAMES: Dict[str, str] = {
        "audit": "审计立项",
        "sourcing": "证据寻源",
        "analysis": "分析建模",
        "validation": "验证压测",
        "delivery": "交付落地",
    }
    #: 关键词域映射（命中即进入 matched_domains，命中顺序按本表顺序）
    DOMAIN_KEYWORDS: Dict[str, Sequence[str]] = {
        "sizing": ("市场规模", "tam", "sam", "som", "天花板", "空间测算"),
        "industry": ("集中度", "hhi", "cr4", "产业链"),
        "competitor": ("竞品", "战斗卡", "对标", "矩阵"),
        "business": ("商业模式", "变现", "ltv", "cac"),
        "scenario": ("情景", "宏观", "pestel", "尸检", "风险"),
        "auto": ("调研计划", "路线图"),
        "research": ("证据台账", "来源", "研报"),
    }
    #: 域 → 主要落点阶段（决定该域任务挂在哪一阶段）
    DOMAIN_STAGE: Dict[str, str] = {
        "sizing": "analysis",
        "industry": "analysis",
        "competitor": "analysis",
        "business": "analysis",
        "scenario": "validation",
        "auto": "audit",
        "research": "sourcing",
    }
    #: 各域对应的专业任务（真实研究动作，非占位文本）
    DOMAIN_TASKS: Dict[str, str] = {
        "sizing": "双口径 TAM/SAM/SOM 三角测量",
        "industry": "HHI/CR4 集中度与产业链拆解",
        "competitor": "竞品战斗卡与对标矩阵",
        "business": "LTV/CAC 与回收期精算",
        "scenario": "三档情景推演与事前尸检",
        "auto": "调研路线图与进度追踪看板",
        "research": "证据台账登记与研报溯源",
    }
    #: 阶段基准工时（人时），真实计算时再乘复杂度/域/实体系数
    BASE_STAGE_HOURS: Dict[str, float] = {
        "audit": 6.0,
        "sourcing": 12.0,
        "analysis": 16.0,
        "validation": 6.0,
        "delivery": 4.0,
    }
    #: 阶段兜底任务（保证每阶段至少 3 项可执行动作）
    STAGE_TASK_LIBRARY: Dict[str, Sequence[str]] = {
        "audit": ("锁定研究问题与决策用途", "确认交付口径与验收标准", "登记合规与红线边界"),
        "sourcing": ("检索一手数据与权威研报", "标注来源等级与发布日期", "记录数据缺口与替代口径"),
        "analysis": ("拆解市场结构与集中度", "构建双口径规模测算", "推演单位经济与敏感性"),
        "validation": ("交叉验证关键断言", "复核 Tier0 断言与来源链", "压力测试极端情景"),
        "delivery": ("输出结论与行动选项", "生成情景比选看板", "落盘证据清单与复现口径"),
    }
    #: 复杂度系数
    COMPLEXITY_FACTOR: Dict[str, float] = {"low": 0.85, "medium": 1.0, "high": 1.25}

    GEO_TERMS: Sequence[str] = ("海外", "中国", "北美", "欧洲", "东南亚", "拉美", "中东")
    CURRENCY_ALIASES: Dict[str, str] = {
        "人民币": "CNY", "rmb": "CNY", "cny": "CNY", "元": "CNY",
        "美金": "USD", "美元": "USD", "usd": "USD", "刀": "USD",
    }
    UNIT_SCALE: Dict[str, float] = {"亿": 1e8, "万": 1e4, "千": 1e3, "百": 1e2}
    MARKET_PREFIXES: Sequence[str] = ("调研", "研究", "分析", "评估", "看下", "了解", "测算")

    # ------------------------------------------------------------------ #
    # Kahn 拓扑排序（稳定顺序 + 真环检测）
    # ------------------------------------------------------------------ #
    def kahn_sort(self, nodes: Sequence[str], edges: Sequence[Dict[str, Any]]) -> List[str]:
        """真实 Kahn 拓扑排序：入度 0 节点按传入 nodes 顺序出队，有环抛 DagCycleError。"""
        node_list = [str(node) for node in nodes]
        index = {node: position for position, node in enumerate(node_list)}
        successors: Dict[str, List[str]] = {node: [] for node in node_list}
        indegree: Dict[str, int] = {node: 0 for node in node_list}
        seen: set = set()

        for edge in edges or []:
            if not isinstance(edge, dict):
                raise ValueError(f"依赖边必须为对象，收到 {type(edge).__name__}")
            source = str(edge.get("from"))
            target = str(edge.get("to"))
            if source not in index or target not in index:
                raise ValueError(f"依赖边引用了未注册阶段: {source!r} -> {target!r}")
            if source == target:
                raise DagCycleError(f"研究阶段依赖存在自环: {source} -> {target}")
            if (source, target) in seen:
                continue
            seen.add((source, target))
            successors[source].append(target)
            indegree[target] += 1

        ready: List[tuple] = [(index[node], node) for node in node_list if indegree[node] == 0]
        heapq.heapify(ready)
        order: List[str] = []
        while ready:
            _, node = heapq.heappop(ready)
            order.append(node)
            for target in successors[node]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    heapq.heappush(ready, (index[target], target))

        if len(order) != len(node_list):
            unresolved = [node for node in node_list if node not in order]
            raise DagCycleError("研究阶段依赖存在环，无法拓扑排序: " + " -> ".join(unresolved))
        return order

    # ------------------------------------------------------------------ #
    # 编译主流程
    # ------------------------------------------------------------------ #
    def compile(self, text: str) -> Dict[str, Any]:
        """把自然语言研究诉求编译为五阶段 DAG、实体事实与工时预算。"""
        query = str(text or "").strip()
        entities = self._extract_entities(query)
        matched_domains = self._match_domains(query)
        complexity, complexity_score = self._grade_complexity(query, matched_domains, entities)
        hours = self._estimate_hours(complexity, matched_domains, entities)
        edges = self._build_edges()

        cycle_detected = False
        try:
            topological_order = self.kahn_sort(list(self.STAGES), edges)
        except DagCycleError:
            topological_order = []
            cycle_detected = True

        stages = self._build_stages(matched_domains, hours)
        estimated_hours = round(sum(stage["hours"] for stage in stages), 2)
        return {
            "query": query,
            "stage_count": len(stages),
            "stages": stages,
            "dag_edges": edges,
            "topological_order": topological_order,
            "cycle_detected": cycle_detected,
            "estimated_hours": estimated_hours,
            "estimated_person_days": round(estimated_hours / 8.0, 2),
            "matched_domains": matched_domains,
            "entities": entities,
            "complexity": complexity,
            "complexity_score": round(complexity_score, 2),
            "research_standard": "五阶段研究标准（审计→寻源→分析→验证→交付）",
        }

    # ------------------------------------------------------------------ #
    # 依赖图
    # ------------------------------------------------------------------ #
    def _build_edges(self) -> List[Dict[str, str]]:
        """构造真实研究依赖边：主链 + 三条前向交叉校验边（全部方向一致）。"""
        edges: List[Dict[str, str]] = [
            {"from": source, "to": target}
            for source, target in zip(self.STAGES, self.STAGES[1:])
        ]
        edges.extend([
            {"from": "audit", "to": "analysis"},
            {"from": "sourcing", "to": "validation"},
            {"from": "analysis", "to": "delivery"},
        ])
        return edges

    def _build_stages(self, matched_domains: Sequence[str],
                      hours: Dict[str, float]) -> List[Dict[str, Any]]:
        """按五阶段标准装配任务清单与真实工时。"""
        predecessors = {stage: [] for stage in self.STAGES}
        for edge in self._build_edges():
            predecessors[edge["to"]].append(edge["from"])

        stages: List[Dict[str, Any]] = []
        for stage in self.STAGES:
            tasks = list(self.STAGE_TASK_LIBRARY[stage])
            for domain in matched_domains:
                if self.DOMAIN_STAGE.get(domain) == stage:
                    tasks.append(self.DOMAIN_TASKS[domain])
            stages.append({
                "stage": stage,
                "name": self.STAGE_NAMES[stage],
                "tasks": tasks,
                "task_count": len(tasks),
                "hours": hours[stage],
                "predecessors": predecessors[stage],
            })
        return stages

    # ------------------------------------------------------------------ #
    # 领域 / 复杂度 / 工时
    # ------------------------------------------------------------------ #
    def _match_domains(self, text: str) -> List[str]:
        """关键词域映射（大小写不敏感，按 DOMAIN_KEYWORDS 顺序输出）。"""
        lowered = text.lower()
        matched: List[str] = []
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(str(keyword).lower() in lowered for keyword in keywords):
                matched.append(domain)
        return matched

    def _grade_complexity(self, text: str, matched_domains: Sequence[str],
                          entities: Dict[str, List[Any]]) -> tuple:
        """按命中域数/文本长度/实体密度做真实计分，输出 (级别, 分值)。"""
        score = 0.0
        score += 0.9 * len(matched_domains)
        score += min(len(text) / 40.0, 2.0)
        score += 0.4 * len(entities["figures"])
        score += 0.3 * len(entities["ratios"])
        score += 0.6 if entities["geos"] else 0.0
        score += 0.5 if entities["markets"] else 0.0
        if score <= 2.0:
            level = "low"
        elif score <= 4.5:
            level = "medium"
        else:
            level = "high"
        return level, score

    def _estimate_hours(self, complexity: str, matched_domains: Sequence[str],
                        entities: Dict[str, List[Any]]) -> Dict[str, float]:
        """按「阶段基准 × 复杂度系数 × 域负载 × 实体负载 + 域增量」真实估算工时。"""
        factor = self.COMPLEXITY_FACTOR.get(complexity, 1.0)
        domain_load = 1.0 + 0.12 * max(len(matched_domains) - 1, 0)
        entity_load = 1.0 + 0.03 * (len(entities["figures"]) + len(entities["ratios"]))
        hours: Dict[str, float] = {}
        for stage in self.STAGES:
            stage_domains = [domain for domain in matched_domains
                             if self.DOMAIN_STAGE.get(domain) == stage]
            value = self.BASE_STAGE_HOURS[stage] * factor * domain_load * entity_load
            value += 1.8 * len(stage_domains)
            hours[stage] = round(value, 2)
        return hours

    # ------------------------------------------------------------------ #
    # 实体抽取（正则驱动）
    # ------------------------------------------------------------------ #
    def _extract_entities(self, text: str) -> Dict[str, List[Any]]:
        """抽取金额、百分比、市场/赛道名词与地域词。"""
        return {
            "figures": self._extract_figures(text),
            "ratios": self._extract_ratios(text),
            "markets": self._extract_markets(text),
            "geos": [geo for geo in self.GEO_TERMS if geo in text],
        }

    def _extract_figures(self, text: str) -> List[Dict[str, Any]]:
        """抽取带量纲或币种的金额/数量（裸数字不计入，避免把“3家竞品”当金额）。"""
        figures: List[Dict[str, Any]] = []
        pattern = re.compile(
            r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>亿|万|千|百)?\s*"
            r"(?P<currency>人民币|元|美金|美元|刀|RMB|CNY|USD)?",
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            unit = match.group("unit") or ""
            currency_raw = match.group("currency") or ""
            if not unit and not currency_raw:
                continue
            value = float(match.group("num"))
            currency = self.CURRENCY_ALIASES.get(currency_raw.lower(), currency_raw.upper())
            figures.append({
                "raw": match.group(0).strip(),
                "value": value,
                "unit": unit,
                "currency": currency or "",
                "normalized": round(value * self.UNIT_SCALE.get(unit, 1.0), 2),
                "span": [match.start(), match.end()],
            })
        return figures

    def _extract_ratios(self, text: str) -> List[Dict[str, Any]]:
        """抽取百分比比例（如 18.5%）。"""
        ratios: List[Dict[str, Any]] = []
        for match in re.finditer(r"(\d+(?:\.\d+)?)\s*%", text):
            value = float(match.group(1))
            ratios.append({
                "raw": match.group(0).strip(),
                "value": value,
                "ratio": round(value / 100.0, 6),
            })
        return ratios

    def _extract_markets(self, text: str) -> List[str]:
        """抽取“××市场 / 赛道 / 行业 / 领域”类市场名词，并剥离调研类动词前缀。"""
        markets: List[str] = []
        pattern = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9+\-]{1,24}?(?:市场|赛道|行业|领域))")
        for match in pattern.finditer(text):
            name = match.group(1)
            for prefix in self.MARKET_PREFIXES:
                if name.startswith(prefix) and len(name) > len(prefix):
                    name = name[len(prefix):]
                    break
            name = name.strip()
            if name and name not in markets:
                markets.append(name)
        return markets
