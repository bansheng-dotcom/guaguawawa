# -*- coding: utf-8 -*-
"""L04 领域账本层：机器可读 SSOT 解析与 8 维加权发布门禁。

对标标杆:
- dbt-labs/dbt-core（语义层单一可信源：指标/阈值集中声明，机器可读消费）
- great-expectations/great_expectations（声明式 Expectation Suite + 加权门禁评分）
- standard/standard（规范文本即协议，禁止把口径散落在实现里）

吸收机制:
1. SSOT 单一信任源：版本、TAM 方差容差、HHI 区间、证据等级置信度与 8 维门禁全部
   从 RESEARCH_SPEC.md 的第一个 ```json 围栏块解析，改文档即改运行口径；
2. 声明式门禁：每个 gate 只声明 metric / rule / threshold / weight，算子按 rule
   做 min/max 比较，权重和恒为 1.0，输出 100 分制加权得分与 PASS/FAIL 判定；
3. 可回放快照：export_json() 落盘带 exported_at 与 source 的 spec 快照，
   多轮/多 Agent 口径漂移可被审计追溯。
"""
from __future__ import annotations
import copy
import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional

# 解析器只认第一个 json 围栏块（RESEARCH_SPEC.md 为唯一 SSOT）
_JSON_FENCE_RE = re.compile(r"```json[ \t]*\r?\n(.*?)```", re.DOTALL)

# 文件缺失/损坏时的内置默认口径（与 RESEARCH_SPEC.md v2.0.0 保持一致，仅作容灾兜底）
DEFAULT_SPEC: Dict[str, Any] = {
    "version": "2.0.0",
    "tam_variance_max": 0.30,
    "hhi": {
        "competitive_max": 1500,
        "moderate_max": 2500,
        "oligopoly_min": 2500,
    },
    "evidence_tiers": {
        "tier_1": {"sources_required": 1, "min_confidence": 0.90},
        "tier_2": {"sources_required": 2, "min_confidence": 0.75},
        "tier_3": {"sources_required": 2, "min_confidence": 0.60},
        "tier_0": {"sources_required": 0, "min_confidence": 0.0},
    },
    "north_star": {"name": "证据覆盖率", "target": 1.0},
    "gates": [
        {"id": "evidence_coverage", "metric": "evidence_coverage", "rule": "min",
         "threshold": 1.0, "weight": 0.15,
         "description": "证据覆盖率必须达到 100%，每条断言均可回溯到登记来源"},
        {"id": "tier0_free", "metric": "tier0_count", "rule": "max",
         "threshold": 0, "weight": 0.10,
         "description": "Tier 0 匿名/不可溯源断言数量必须为 0，出现即红线拦截"},
        {"id": "tam_convergence", "metric": "tam_variance", "rule": "max",
         "threshold": 0.30, "weight": 0.15,
         "description": "TAM 自上而下与自下而上双口径相对方差必须 <= 0.30"},
        {"id": "hhi_declared", "metric": "hhi_declared", "rule": "min",
         "threshold": 1, "weight": 0.10,
         "description": "必须显式声明 HHI 与市场结构判定，未声明视为未完成研究"},
        {"id": "scenario_three", "metric": "scenario_count", "rule": "min",
         "threshold": 3, "weight": 0.10,
         "description": "必须给出保守/基准/乐观三情景横向比选，少于 3 个不可发布"},
        {"id": "redline_clean", "metric": "redline_clean", "rule": "min",
         "threshold": 1, "weight": 0.15,
         "description": "决策越权与跨角色红线扫描必须全部通过（1=干净）"},
        {"id": "slop_score", "metric": "slop_score", "rule": "min",
         "threshold": 80, "weight": 0.15,
         "description": "质感去劣评分必须 >= 80，且不得残留占位套话与无证据断言"},
        {"id": "bundle_manifest", "metric": "bundle_manifest", "rule": "min",
         "threshold": 1, "weight": 0.10,
         "description": "必须落盘带 SHA256 的伴生资产清单，保证下游可回放（1=已生成）"},
    ],
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并：标量与列表以 override 为准，字典逐键下沉合并。"""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _as_float(value: Any) -> Optional[float]:
    """把门禁指标安全转换为 float；不可比较时返回 None（按不通过处理，不伪造数据）。"""
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ResearchSpecLedger:
    """领域账本 SSOT 解析器与 8 维发布门禁执行器。"""

    def __init__(self, spec_path: Optional[str] = None):
        if spec_path is None:
            role_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            spec_path = os.path.join(role_root, "RESEARCH_SPEC.md")
        self.spec_path = spec_path
        self.source = "builtin_default"
        self.rules_loaded = False
        self._cache: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # SSOT 解析
    # ------------------------------------------------------------------
    def _parse_spec_file(self) -> Optional[Dict[str, Any]]:
        """读取 RESEARCH_SPEC.md 并解析第一个 json 围栏块；不可用返回 None。"""
        if not os.path.isfile(self.spec_path):
            return None
        try:
            with open(self.spec_path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return None

        match = _JSON_FENCE_RE.search(content)
        if match is None:
            return None
        try:
            parsed = json.loads(match.group(1))
        except (TypeError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None

    def load(self) -> Dict[str, Any]:
        """加载机器可读 SSOT；文件缺失或损坏时回退内置默认口径。"""
        if self._cache is not None:
            return self._cache

        parsed = self._parse_spec_file()
        if parsed is None:
            spec = copy.deepcopy(DEFAULT_SPEC)
            self.source = "builtin_default"
            self.rules_loaded = False
        else:
            # 文件中的阈值优先；未声明的次要字段用默认口径补齐，保证下游键稳定
            spec = _deep_merge(DEFAULT_SPEC, parsed)
            self.source = self.spec_path
            self.rules_loaded = True

        # 门禁结构做最小完整性校验：缺失/空/非列表时回退内置 8 维默认，绝不让下游拿到半截 SSOT
        if not isinstance(spec.get("gates"), list) or not spec["gates"]:
            spec["gates"] = copy.deepcopy(DEFAULT_SPEC["gates"])
        self._cache = spec
        return spec

    def gates(self) -> List[Dict[str, Any]]:
        """返回 SSOT 中声明的 8 维发布门禁（每项附带以 metric 命名的自描述键）。

        自描述键让门禁在被下游按 metric 名直接索引时无需再查表，
        同时保持 id/metric/rule/threshold/weight/description 六段声明结构不变。
        """
        gates: List[Dict[str, Any]] = []
        for gate in self.load().get("gates", []):
            item = copy.deepcopy(gate)
            metric = str(item.get("metric", ""))
            if metric and metric not in item:
                item[metric] = item.get("threshold")
            gates.append(item)
        return gates

    # ------------------------------------------------------------------
    # 门禁评估
    # ------------------------------------------------------------------
    def evaluate(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """按 SSOT 逐门禁评估指标，输出加权得分、逐项明细与 PASS/FAIL 判定。"""
        artifact = artifact if isinstance(artifact, dict) else {}
        metrics = artifact.get("metrics", artifact)
        if not isinstance(metrics, dict):
            metrics = {}

        gate_results: List[Dict[str, Any]] = []
        for gate in self.gates():
            metric = str(gate.get("metric", ""))
            raw_value = metrics.get(metric)
            threshold = _as_float(gate.get("threshold", 0.0))
            weight = _as_float(gate.get("weight", 0.0)) or 0.0
            rule = str(gate.get("rule", "min"))
            numeric = _as_float(raw_value)

            if threshold is None or numeric is None:
                ok = False
            elif rule == "max":
                ok = numeric <= threshold
            else:  # min 为默认规则，未知规则按 min 保守处理
                ok = numeric >= threshold

            gate_results.append({
                "id": str(gate.get("id", metric)),
                "metric": metric,
                "ok": bool(ok),
                "value": raw_value,
                "threshold": gate.get("threshold", 0.0),
                "rule": rule,
                "weight": round(weight, 6),
                "points": round(weight * 100.0, 2),
            })

        passed = bool(gate_results) and all(result["ok"] for result in gate_results)
        score = round(sum(result["points"] for result in gate_results if result["ok"]), 2)
        return {
            "passed": passed,
            "score": score,
            "verdict": "PASS" if passed else "FAIL",
            "weight_total": round(sum(result["weight"] for result in gate_results), 6),
            "gates": gate_results,
        }

    # ------------------------------------------------------------------
    # 快照导出
    # ------------------------------------------------------------------
    def export_json(self, path: str) -> str:
        """把当前 SSOT 连同 8 维门禁导出为可审计快照。"""
        spec = self.load()
        payload: Dict[str, Any] = copy.deepcopy(spec)
        payload["gates"] = copy.deepcopy(spec.get("gates", []))
        payload["exported_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        payload["source"] = self.spec_path

        target = os.path.abspath(path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return target
