# -*- coding: utf-8 -*-
"""L01 工具实体层：ResearchRuntimeEngine 确定性研究算子沙箱。

对标标杆:
- OpenBB-finance/OpenBB (28k⭐)：可插拔 provider 注册表 + 逐 provider 健康探针
- Celery (25k⭐) / DuckDB (22k⭐)：算子级执行契约与 fail-closed 沙箱
- IEEE754 double 口径：全部算子为纯标准库纯函数，输出可复现（零漂移）

吸收的机制:
1. 算子注册表（provider registry）：算子以 name -> callable 实体登记，
   available_operators() 返回真实注册结果；未知算子 fail-closed 返回 ok=False。
2. 健康探针（probe）：返回 engines.base.EngineProbeResult，details 携带
   operator_count / operators / 精度与阈值底座事实，供 manager.probe_all 汇总。
3. 证据分级门禁（EvidenceTierValidator）：Tier0 直接拦截、孤立断言、
   置信度不足与覆盖率统计，为 L04 规范账本与 L07 审计工件提供确定性输入。
4. 单位经济 / 敏感性摆动 / 双口径三角测量三组精算算子，消除 skills/ 中的口径漂移。

所有算子均为真实计算（禁止假数据），非法输入一律 fail-closed 返回 errors，
不抛裸异常、不吞断言（仅捕获入参类型/取值类异常并转为结构化错误）。
"""
from __future__ import annotations

import math
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

from engines.base import BaseResearchEngine, EngineProbeResult, ExecutionResult

#: 证据分级最低置信度门槛（Tier0 证据一律 0.0，即不可作为结论依据）
TIER_MIN_CONFIDENCE: Dict[str, float] = {
    "tier_1": 0.90,
    "tier_2": 0.75,
    "tier_3": 0.60,
    "tier_0": 0.0,
}
#: 允许的断言类型（fact/estimate/opinion 之外的 rumor 等一律不进结论）
ALLOWED_CLAIM_KINDS: Sequence[str] = ("fact", "estimate", "opinion")
#: HHI 结构阈值（<1500 竞争型，<=2500 中度集中，>2500 寡头）
HHI_COMPETITIVE_MAX: float = 1500.0
HHI_MODERATE_MAX: float = 2500.0
#: 双口径规模方差容差
TAM_VARIANCE_TOLERANCE: float = 0.30


def _to_float(value: Any, field: str) -> float:
    """把入参安全转为有限浮点数；非法值抛出 ValueError（由 execute 转结构化错误）。"""
    if isinstance(value, bool):
        raise ValueError(f"{field} 必须为数值，收到布尔值 {value!r}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} 必须为数值，收到 {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} 必须为有限数值，收到 {value!r}")
    return number


def _positive(payload: Dict[str, Any], field: str) -> float:
    """读取必填正数入参。"""
    number = _to_float(payload.get(field), field)
    if number <= 0:
        raise ValueError(f"{field} 必须 > 0，收到 {number}")
    return number


class EvidenceTierValidator:
    """三级证据链门禁（Tier0 拦截 / 孤立断言 / 置信度不足 / 覆盖率）。

    对标 OpenBB 的 data-validator provider 与 great_expectations 的 expectation
    suite：把「断言是否可作为结论依据」变成可复现的确定性判定，而不是人肉口径。
    """

    def tier_min(self, tier: str) -> float:
        """返回指定证据等级的最低置信度门槛（未知等级按 0.0 处理）。"""
        key = str(tier or "").strip().lower()
        return float(TIER_MIN_CONFIDENCE.get(key, 0.0))

    def validate(self, claims: Any) -> Dict[str, Any]:
        """逐条校验断言，返回与 evidence_chain 算子完全一致的结构。"""
        if claims is None:
            claims = []
        if not isinstance(claims, (list, tuple)):
            raise ValueError("claims 必须为列表")

        tier_distribution: Dict[str, int] = {
            "tier_0": 0, "tier_1": 0, "tier_2": 0, "tier_3": 0,
        }
        tier0_blocked: List[str] = []
        orphan_claims: List[str] = []
        low_confidence: List[str] = []
        invalid_kind: List[str] = []
        violations: List[Dict[str, Any]] = []
        qualified = 0

        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                raise ValueError(f"claims[{index}] 必须为对象，收到 {type(claim).__name__}")
            claim_id = str(claim.get("id") or f"claim_{index + 1}")
            tier = str(claim.get("tier") or "tier_3").strip().lower()
            tier_distribution[tier] = tier_distribution.get(tier, 0) + 1

            sources = claim.get("sources")
            if sources is None:
                sources = claim.get("evidence_refs")
            if isinstance(sources, str):
                sources = [sources] if sources.strip() else []
            if sources is None:
                sources = []
            if not isinstance(sources, (list, tuple)):
                raise ValueError(f"claims[{index}].sources 必须为列表")

            kind = str(claim.get("kind") or "").strip().lower()
            confidence = _to_float(claim.get("confidence", 0.0), f"claims[{index}].confidence")

            codes: List[Dict[str, Any]] = []
            if tier == "tier_0":
                tier0_blocked.append(claim_id)
                codes.append({"claim_id": claim_id, "code": "TIER0_BLOCKED",
                              "severity": "critical",
                              "message": f"Tier0 断言 [{claim_id}] 必须拦截，禁止进入研究结论"})
            if not sources:
                orphan_claims.append(claim_id)
                codes.append({"claim_id": claim_id, "code": "ORPHAN_CLAIM",
                              "severity": "warning",
                              "message": f"断言 [{claim_id}] 无 sources/evidence_refs，属孤立断言"})
            floor = self.tier_min(tier)
            if confidence < floor:
                low_confidence.append(claim_id)
                codes.append({"claim_id": claim_id, "code": "LOW_CONFIDENCE",
                              "severity": "warning",
                              "message": f"断言 [{claim_id}] 置信度 {confidence} 低于 "
                                         f"{tier} 门槛 {floor}"})
            if kind not in ALLOWED_CLAIM_KINDS:
                invalid_kind.append(claim_id)
                codes.append({"claim_id": claim_id, "code": "INVALID_KIND",
                              "severity": "warning",
                              "message": f"断言 [{claim_id}] 类型 {kind or '未声明'} 不在 "
                                         f"{list(ALLOWED_CLAIM_KINDS)} 内"})
            if not codes:
                qualified += 1
            violations.extend(codes)

        claim_count = len(claims)
        coverage_rate = round(qualified / claim_count, 4) if claim_count else 0.0
        return {
            "tier_distribution": tier_distribution,
            "tier0_blocked": tier0_blocked,
            "orphan_claims": orphan_claims,
            "low_confidence": low_confidence,
            "invalid_kind": invalid_kind,
            "coverage_rate": coverage_rate,
            "qualified_count": qualified,
            "claim_count": claim_count,
            "gate_ok": len(violations) == 0,
            "violations": violations,
        }


class ResearchRuntimeEngine(BaseResearchEngine):
    """战略研究确定性算子运行时（L01 工具实体层）。

    算子注册表 + 健康探针 + fail-closed 执行契约，全部为真实计算。
    """

    def __init__(self) -> None:
        super().__init__("research_runtime_engine")
        self._validator = EvidenceTierValidator()
        self._operators: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "calc_hhi": self._op_calc_hhi,
            "verify_tam_variance": self._op_verify_tam_variance,
            "evidence_chain": self._op_evidence_chain,
            "unit_economics": self._op_unit_economics,
            "sensitivity_swing": self._op_sensitivity_swing,
            "tam_triangulate": self._op_tam_triangulate,
        }

    # ------------------------------------------------------------------ #
    # 注册表与探针
    # ------------------------------------------------------------------ #
    def available_operators(self) -> List[str]:
        """返回已真实注册的研究算子名（确定性顺序）。"""
        return list(self._operators.keys())

    def register_operator(self, name: str,
                          operator: Callable[[Dict[str, Any]], Dict[str, Any]]) -> List[str]:
        """运行时注册新算子（供下游 L07 伴生算子扩展），返回最新算子表。"""
        key = str(name or "").strip()
        if not key or not callable(operator):
            raise ValueError("register_operator 需要非空 name 与可调用 operator")
        self._operators[key] = operator
        return self.available_operators()

    def probe(self) -> EngineProbeResult:
        """对算子注册表与数学底座做真实健康探针。"""
        started = time.perf_counter()
        operators = self.available_operators()
        latency_ms = (time.perf_counter() - started) * 1000
        healthy = len(operators) >= 6
        return EngineProbeResult(
            engine_name=self.name,
            available=healthy,
            status_code=200 if healthy else 500,
            latency_ms=round(latency_ms, 3),
            details={
                "operator_count": len(operators),
                "operators": operators,
                "math_core": "python_native",
                "precision": "IEEE754_double",
                "evidence_tier_gate": "active",
                "tier_min_confidence": dict(TIER_MIN_CONFIDENCE),
                "hhi_thresholds": {"competitive_max": HHI_COMPETITIVE_MAX,
                                   "moderate_max": HHI_MODERATE_MAX},
                "tam_variance_tolerance": TAM_VARIANCE_TOLERANCE,
            },
        )

    def execute(self, action: str, payload: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """执行指定算子；未知算子与非法入参一律 fail-closed。"""
        started = time.perf_counter()
        body: Dict[str, Any] = payload if isinstance(payload, dict) else {}
        operator = self._operators.get(str(action or ""))
        if operator is None:
            return ExecutionResult(
                ok=False, data={},
                errors=[f"未知研究算子: {action!r}（已注册: {', '.join(self.available_operators())}）"],
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                engine=self.name,
            )
        try:
            data = operator(body)
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            return ExecutionResult(
                ok=False, data={},
                errors=[f"{action} 计算失败: {type(exc).__name__}: {exc}"],
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                engine=self.name,
            )
        return ExecutionResult(
            ok=True, data=data, errors=[],
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            engine=self.name,
        )

    # ------------------------------------------------------------------ #
    # 算子实现：集中度
    # ------------------------------------------------------------------ #
    def _op_calc_hhi(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """HHI=Σshare²、CR4/CR8 与结构判定（1500/2500 阈值）。"""
        raw_shares = payload.get("shares")
        if not isinstance(raw_shares, (list, tuple)) or not raw_shares:
            raise ValueError("calc_hhi 需要非空 shares 列表")
        shares = [_to_float(value, f"shares[{index}]")
                  for index, value in enumerate(raw_shares)]
        if any(share < 0 for share in shares):
            raise ValueError("calc_hhi 的 shares 不得为负数")
        total_share = sum(shares)
        if total_share <= 0:
            raise ValueError("calc_hhi 的 shares 总和必须 > 0")

        hhi = sum(share ** 2 for share in shares)
        ordered = sorted(shares, reverse=True)
        cr4 = sum(ordered[:4])
        cr8 = sum(ordered[:8])
        if hhi < HHI_COMPETITIVE_MAX:
            structure = "competitive"
        elif hhi <= HHI_MODERATE_MAX:
            structure = "moderate"
        else:
            structure = "oligopoly"
        return {
            "hhi": round(hhi, 4),
            "cr4": round(cr4, 4),
            "cr8": round(cr8, 4),
            "structure": structure,
            "thresholds": {"competitive_max": HHI_COMPETITIVE_MAX,
                           "moderate_max": HHI_MODERATE_MAX},
            "total_share": round(total_share, 4),
            "share_count": len(shares),
        }

    # ------------------------------------------------------------------ #
    # 算子实现：双口径规模方差
    # ------------------------------------------------------------------ #
    def _op_verify_tam_variance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """校验 top-down / bottom-up 双口径相对方差是否收敛于 30% 容差内。"""
        top_down = _positive(payload, "top_down")
        bottom_up = _to_float(payload.get("bottom_up"), "bottom_up")
        if bottom_up < 0:
            raise ValueError("bottom_up 不得为负数")
        variance = abs(top_down - bottom_up) / top_down
        return {
            "top_down": round(top_down, 4),
            "bottom_up": round(bottom_up, 4),
            "variance": round(variance, 4),
            "converged": variance < TAM_VARIANCE_TOLERANCE,
            "threshold": TAM_VARIANCE_TOLERANCE,
            "gap": round(abs(top_down - bottom_up), 4),
        }

    # ------------------------------------------------------------------ #
    # 算子实现：证据链分级
    # ------------------------------------------------------------------ #
    def _op_evidence_chain(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """对 claims 逐条做证据分级门禁，输出与 EvidenceTierValidator 同构。"""
        claims = payload.get("claims")
        if claims is None:
            raise ValueError("evidence_chain 需要 claims 列表")
        return self._validator.validate(claims)

    # ------------------------------------------------------------------ #
    # 算子实现：单位经济
    # ------------------------------------------------------------------ #
    def _op_unit_economics(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """单位经济精算：毛利/用户、LTV、LTV/CAC、回收月数、健康判定。"""
        arpu = _positive(payload, "arpu")
        gross_margin = _to_float(payload.get("gross_margin"), "gross_margin")
        churn_rate = _to_float(payload.get("churn_rate"), "churn_rate")
        cac = _to_float(payload.get("cac"), "cac")
        if not 0 < gross_margin <= 1:
            raise ValueError(f"gross_margin 必须位于 (0, 1]，收到 {gross_margin}")
        if churn_rate <= 0:
            raise ValueError("churn_rate 必须 > 0（否则 LTV 无意义）")
        if cac <= 0:
            raise ValueError("cac 必须 > 0（否则 LTV/CAC 无意义）")

        gross_profit_per_user = round(arpu * gross_margin, 2)
        if gross_profit_per_user <= 0:
            raise ValueError("毛利/用户必须 > 0，请检查 arpu 与 gross_margin")
        ltv = round(gross_profit_per_user / churn_rate, 2)
        ltv_cac_ratio = round(ltv / cac, 2)
        payback_months = round(cac / gross_profit_per_user, 2)
        healthy = ltv_cac_ratio >= 3.0 and payback_months <= 12.0
        return {
            "arpu": arpu,
            "gross_margin": gross_margin,
            "churn_rate": churn_rate,
            "cac": cac,
            "gross_profit_per_user": gross_profit_per_user,
            "ltv": ltv,
            "ltv_cac_ratio": ltv_cac_ratio,
            "payback_months": payback_months,
            "healthy": healthy,
            "thresholds": {"ltv_cac_min": 3.0, "payback_months_max": 12.0},
        }

    # ------------------------------------------------------------------ #
    # 算子实现：敏感性摆动排序
    # ------------------------------------------------------------------ #
    def _op_sensitivity_swing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """逐驱动计算上下摆动与摆动占比，按 swing_abs 降序排名并给致命断点。"""
        base_value = _positive(payload, "base_value")
        raw_drivers = payload.get("drivers")
        if not isinstance(raw_drivers, (list, tuple)) or not raw_drivers:
            raise ValueError("sensitivity_swing 需要非空 drivers 列表")

        rows: List[Dict[str, Any]] = []
        for index, driver in enumerate(raw_drivers):
            if not isinstance(driver, dict):
                raise ValueError(f"drivers[{index}] 必须为对象")
            name = str(driver.get("name") or f"driver_{index + 1}")
            low_pct = _to_float(driver.get("low_pct", 0.0), f"drivers[{index}].low_pct")
            high_pct = _to_float(driver.get("high_pct", 0.0), f"drivers[{index}].high_pct")
            weight = _to_float(driver.get("weight", 1.0), f"drivers[{index}].weight")
            low_impact = round(base_value * low_pct * weight, 4)
            high_impact = round(base_value * high_pct * weight, 4)
            swing_abs = round(abs(high_impact - low_impact), 4)
            rows.append({
                "name": name,
                "low_pct": low_pct,
                "high_pct": high_pct,
                "weight": weight,
                "low_impact": low_impact,
                "high_impact": high_impact,
                "swing_abs": swing_abs,
                "swing_pct": round(swing_abs / base_value, 4),
                "_order": index,
            })

        rows.sort(key=lambda row: (-row["swing_abs"], row["_order"]))
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
            row.pop("_order", None)

        top = rows[0]
        swing_total = round(sum(row["swing_abs"] for row in rows), 4)
        deadly_point = (
            f"致命摆点：{top['name']} 是最大敏感驱动，基准 {base_value:g} 下摆动 "
            f"{top['swing_abs']:g}（{top['swing_pct']:.2%}），须优先做情景压测与对冲"
        )
        return {
            "base_value": base_value,
            "drivers": rows,
            "top_driver": top["name"],
            "swing_total": swing_total,
            "deadly_point": deadly_point,
            "driver_count": len(rows),
        }

    # ------------------------------------------------------------------ #
    # 算子实现：双口径 TAM 三角测量
    # ------------------------------------------------------------------ #
    def _op_tam_triangulate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """自下而上与自上而下双向三角测量 TAM，输出收敛判定与中值。"""
        top_down = payload.get("top_down")
        if not isinstance(top_down, dict):
            raise ValueError("tam_triangulate 需要 top_down 对象")
        components = top_down.get("components")
        if not isinstance(components, (list, tuple)) or not components:
            raise ValueError("tam_triangulate 需要非空 top_down.components")
        tam_top = 0.0
        for index, component in enumerate(components):
            if not isinstance(component, dict):
                raise ValueError(f"top_down.components[{index}] 必须为对象")
            tam_top += _to_float(component.get("value"), f"components[{index}].value")
        if tam_top <= 0:
            raise ValueError("tam_top 必须 > 0")

        bottom_up = payload.get("bottom_up")
        if not isinstance(bottom_up, dict):
            raise ValueError("tam_triangulate 需要 bottom_up 对象")
        customer_count = _to_float(bottom_up.get("customer_count"), "customer_count")
        addressable_fraction = _to_float(bottom_up.get("addressable_fraction"),
                                         "addressable_fraction")
        annual_quantity = _to_float(bottom_up.get("annual_quantity"), "annual_quantity")
        price_per_unit = _to_float(bottom_up.get("price_per_unit"), "price_per_unit")
        if customer_count <= 0:
            raise ValueError("customer_count 必须 > 0")
        if not 0 < addressable_fraction <= 1:
            raise ValueError(f"addressable_fraction 必须位于 (0, 1]，收到 {addressable_fraction}")
        if annual_quantity <= 0:
            raise ValueError("annual_quantity 必须 > 0")
        if price_per_unit <= 0:
            raise ValueError("price_per_unit 必须 > 0")

        tam_bottom = customer_count * addressable_fraction * annual_quantity * price_per_unit
        variance = abs(tam_top - tam_bottom) / tam_top
        return {
            "tam_top": round(tam_top, 4),
            "tam_bottom": round(tam_bottom, 4),
            "variance": round(variance, 4),
            "converged": variance < TAM_VARIANCE_TOLERANCE,
            "tolerance": TAM_VARIANCE_TOLERANCE,
            "tam": round((tam_top + tam_bottom) / 2, 2),
            "component_count": len(components),
            "gap": round(abs(tam_top - tam_bottom), 4),
        }
