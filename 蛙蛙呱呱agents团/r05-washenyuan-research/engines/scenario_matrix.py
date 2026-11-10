# -*- coding: utf-8 -*-
"""L06 横向决策层：战略三维情景规划、MCDA 评分与 ROI 横向比选看板。

对标标杆:
- Scenario Planning（Shell/Gartner 三情景推演：不押单点，呈现可权衡选项）
- apache/superset（多维 ROI 评分看板：同一张表横向比较，避免单指标误判）
- vega/vega-lite（声明式矩阵数据，下游 R06 可直接渲染）

吸收机制:
1. MCDA 多准则决策：市场空间/毛利/成本风险/速度四维固定权重（和=1.0），
   每个情景输出 0~100 综合评分，避免“拍脑袋选最大 TAM”；
2. 单位经济与 ROI 矩阵：ROI、LTV/CAC、回收期由 price/cogs/份额确定性推导，
   同一输入永远得到同一结果，可被复现与审计；
3. 输入驱动份额：obtainable_shares / serviceable_fractions 可由调用方覆盖，
   不再把三档份额写死在代码里；ranking + recommended 给出可解释推荐序。
"""
from __future__ import annotations
from typing import Any, Dict, List, Sequence


class ScenarioMatrixExplorer:
    """战略三维情景看板与 MCDA 横向决策引擎。"""

    # MCDA 权重（四维之和恒为 1.0）
    WEIGHTS: Dict[str, float] = {
        "market_upside": 0.35,
        "margin": 0.30,
        "cost_risk": 0.20,
        "speed": 0.15,
    }
    DEFAULT_OBTAINABLE_SHARES: Sequence[float] = (0.03, 0.08, 0.15)
    DEFAULT_SERVICEABLE_FRACTIONS: Sequence[float] = (0.25, 0.40, 0.60)
    TAM_FACTORS: Sequence[float] = (0.8, 1.0, 1.3)
    MARGIN_ADJUSTMENTS: Sequence[float] = (-5.0, 0.0, 5.0)
    COST_MULTIPLIERS: Sequence[float] = (0.95, 1.0, 1.05)
    SCENARIO_TEMPLATES: Sequence[Dict[str, Any]] = (
        {
            "id": "scenario_conservative",
            "name": "保守防御型 (Downside)",
            "assumption": "宏观承压、大厂挤压、获客转化取行业低位",
            "target_margin": "60%",
            "action_priority": "控制研发开支，聚焦高价值粘性 KA 客户",
        },
        {
            "id": "scenario_benchmark",
            "name": "基准稳健型 (Base)",
            "assumption": "行业正常增速发展，保持差异化产品力",
            "target_margin": "75%",
            "action_priority": "推进 MVP 快速验证，平衡 LTV/CAC 在 3.0 以上",
        },
        {
            "id": "scenario_aggressive",
            "name": "乐观突击型 (Upside)",
            "assumption": "迎来技术红利或网络效应爆发，产品快速出圈",
            "target_margin": "85%",
            "action_priority": "扩大渠道投放，建立生态壁垒加速规模化",
        },
    )

    # ------------------------------------------------------------------
    # 输入解析与安全数学
    # ------------------------------------------------------------------
    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
        return round(max(low, min(high, value)), 2)

    @staticmethod
    def _resolve_vector(base_inputs: Dict[str, Any], key: str,
                        default: Sequence[float]) -> List[float]:
        """三元素向量优先取调用方输入，长度/类型不合法时回退默认口径。"""
        raw = base_inputs.get(key)
        if isinstance(raw, (list, tuple)) and len(raw) == 3:
            try:
                return [float(item) for item in raw]
            except (TypeError, ValueError):
                return [float(item) for item in default]
        return [float(item) for item in default]

    # ------------------------------------------------------------------
    # 矩阵生成
    # ------------------------------------------------------------------
    def generate_matrix(self, base_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """根据基础研究输入生成三情景 MCDA 评分、ROI 矩阵与推荐序。"""
        base_inputs = base_inputs if isinstance(base_inputs, dict) else {}
        tam = float(base_inputs.get("tam", 100.0))
        cogs = float(base_inputs.get("cogs", 300.0))
        price = float(base_inputs.get("price", 1200.0))
        shares = self._resolve_vector(base_inputs, "obtainable_shares",
                                      self.DEFAULT_OBTAINABLE_SHARES)
        fractions = self._resolve_vector(base_inputs, "serviceable_fractions",
                                         self.DEFAULT_SERVICEABLE_FRACTIONS)

        unit_margin = max(price - cogs, 1.0)
        gross_margin_pct = (unit_margin / price * 100.0) if price > 0 else 0.0
        cost_ratio_pct = (cogs / price * 100.0) if price > 0 else 100.0
        # 获客成本随所需份额抬升，回收期与 LTV/CAC 由 price/cogs/份额确定性推导
        cac = max(cogs * (1.0 + share) for share in shares) if shares else 1.0

        raw_scenarios: List[Dict[str, Any]] = []
        for index, template in enumerate(self.SCENARIO_TEMPLATES):
            share = shares[index]
            fraction = fractions[index]
            tam_i = tam * self.TAM_FACTORS[index]
            sam_i = tam_i * fraction
            som_i = sam_i * share

            cac_i = max(cogs * (1.0 + share), 1.0)
            ltv = unit_margin * 12.0                      # 12 个月生命周期毛利
            ltvcac = round(ltv / cac_i, 2)
            payback = round(12.0 * cac_i / unit_margin, 2)

            # ROI(%) 采用量纲一致的口径：SOM（亿元）先按单价换算成可服务件数，
            # 再与单件获客成本/单件毛利相乘，得到「营销投入回报率」：
            #   ROI = (毛利总额 − 获客投入) / 获客投入 × 100
            # 该口径只随价格/成本/份额变化，不随 TAM 规模无意义膨胀。
            units = som_i * 1e8 / price if price > 0 else 0.0
            marketing_spend = units * cac_i
            gross_profit = units * unit_margin
            roi = round(
                (gross_profit - marketing_spend) / max(marketing_spend, 1.0) * 100.0,
                2)

            cost_score = self._clamp(
                100.0 - cost_ratio_pct * self.COST_MULTIPLIERS[index])
            speed_score = self._clamp(100.0 - payback * 4.0)
            margin_score = self._clamp(
                gross_margin_pct + self.MARGIN_ADJUSTMENTS[index])

            raw_scenarios.append({
                "id": template["id"],
                "name": template["name"],
                "assumption": template["assumption"],
                "serviceable_fraction": fraction,
                "obtainable_share": share,
                "tam": round(tam_i, 1),
                "sam": round(sam_i, 2),
                "som": round(som_i, 3),
                "target_margin": template["target_margin"],
                "action_priority": template["action_priority"],
                "roi": roi,
                "ltv_cac_ratio": ltvcac,
                "payback_months": payback,
                "cost_score": cost_score,
                "speed_score": speed_score,
                "_margin_score": margin_score,
                "_cac": cac_i,
            })

        max_som = max((scenario["som"] for scenario in raw_scenarios), default=0.0)
        scenarios: List[Dict[str, Any]] = []
        for scenario in raw_scenarios:
            market_upside = self._clamp(
                scenario["som"] / max_som * 100.0 if max_som > 0 else 0.0)
            dimension_scores = {
                "market_upside": round(market_upside, 2),
                "margin": round(scenario.pop("_margin_score"), 2),
                "cost_risk": round(scenario["cost_score"], 2),
                "speed": round(scenario["speed_score"], 2),
            }
            scenario.pop("_cac", None)
            scenario["dimension_scores"] = dimension_scores
            scenario["score"] = self._clamp(sum(
                self.WEIGHTS[key] * dimension_scores[key] for key in self.WEIGHTS))
            scenarios.append(scenario)

        ranking = [
            {"name": item["name"], "score": item["score"], "roi": item["roi"]}
            for item in sorted(scenarios, key=lambda item: item["score"], reverse=True)
        ]
        recommended = ranking[0]["name"] if ranking else ""
        board_md = self._render_board(scenarios, ranking, recommended, cac)
        return {
            "scenarios": scenarios,
            "weights": dict(self.WEIGHTS),
            "ranking": ranking,
            "recommended": recommended,
            "board_markdown": board_md,
        }

    # ------------------------------------------------------------------
    # 看板渲染
    # ------------------------------------------------------------------
    def _render_board(self, scenarios: List[Dict[str, Any]],
                      ranking: List[Dict[str, Any]], recommended: str,
                      cac: float) -> str:
        header = ("# 战略研究三维情景横向比选看板 (Strategic Scenario Matrix)")

        def row(label: str, key: str, fmt: str) -> str:
            cells = " | ".join(fmt.format(scenario[key]) for scenario in scenarios)
            return f"| {label} | {cells} |"

        lines = [
            header,
            "",
            "| 决策维度 | 保守防御型 (Downside) | 基准稳健型 (Base) | 乐观突击型 (Upside) |",
            "| :--- | :--- | :--- | :--- |",
            "| **前置假设** | " + " | ".join(
                scenario["assumption"] for scenario in scenarios) + " |",
            row("**测算 TAM**", "tam", "{} 亿"),
            row("**服务 SAM**", "sam", "{} 亿"),
            row("**可获 SOM**", "som", "{} 亿"),
            row("**可获份额**", "obtainable_share", "{:.2%}"),
            row("**毛利率预期**", "target_margin", "{}"),
            row("**ROI（%）**", "roi", "{:.2f}%"),
            row("**LTV / CAC（倍）**", "ltv_cac_ratio", "{:.2f}×"),
            row("**回收期（月）**", "payback_months", "{:.2f} 个月"),
            row("**MCDA 综合评分（0~100）**", "score", "{:.2f}"),
            "| **首选推进动作** | " + " | ".join(
                scenario["action_priority"] for scenario in scenarios) + " |",
            "",
            "## 多维 ROI 权衡矩阵",
            "",
            "| MCDA 维度 | 权重 | 保守防御型 (Downside) | 基准稳健型 (Base) | 乐观突击型 (Upside) |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
        dimension_labels = {
            "market_upside": "市场空间 (market_upside)",
            "margin": "毛利质量 (margin)",
            "cost_risk": "成本韧性 (cost_risk)",
            "speed": "回收速度 (speed)",
        }
        for key, weight in self.WEIGHTS.items():
            cells = " | ".join(
                f"{scenario['dimension_scores'][key]:.2f}" for scenario in scenarios)
            lines.append(f"| {dimension_labels[key]} | {weight:.0%} | {cells} |")
        lines.append(
            "| **加权综合评分** | 100% | " +
            " | ".join(f"{scenario['score']:.2f}" for scenario in scenarios) + " |")

        rank_text = " → ".join(
            f"{item['name']}（{item['score']:.2f} 分 / ROI {item['roi']:.2f}%）"
            for item in ranking)
        lines.extend([
            "",
            "> **推荐结论**：综合 MCDA 加权评分，推荐【{}】作为首选情景；"
            "横向排序为：{}。".format(recommended, rank_text),
            "> **R05 研报权衡建议**：不替决策层直接拍板。以推荐情景作为资源配置主路径，"
            "同时保留保守情景止损线与乐观情景加速探针，按季度用真实 CAC"
            "（当前测算口径 max 约 {:.2f} 元）复算 ROI 并滚动修正。".format(cac),
        ])
        return "\n".join(lines)
