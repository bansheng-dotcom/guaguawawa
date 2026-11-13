# -*- coding: utf-8 -*-
"""L04 领域账本层 (Metrics Spec Ledger Layer)
对标开源: dbt MetricFlow (Stars > 11k) / Cube.js (Stars > 18k) / awesome-design-md
架构跃迁 (本轮新增):
1. 账本指纹与完整性：METRICS_SPEC.md 的 SHA256 指纹 + 必填 schema 校验，杜绝残缺账本静默生效；
2. 口径漂移门禁：基线快照对比，阈值/容差漂移超限即告警，防止跨轮对话口径漂移；
3. 规则包编译导出：把统一真理源编译为下游可消费的 `metrics_rules.json`（含指纹与导出时间）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional


class MetricsSpecLedgerParser:
    """领域业务账本解析器，保证分析口径绝对一致。"""

    REQUIRED_SECTIONS = [
        "stat_thresholds", "hhi_thresholds", "tam_variance_max",
        "reconciliation_tolerance", "quality_dimensions", "metric_definitions",
    ]

    DRIFT_TOLERANCE = 0.0  # 口径阈值默认零漂移

    def __init__(self, spec_path: str = None, workspace_dir: str = None):
        here = os.path.dirname(os.path.abspath(__file__))
        role_dir = os.path.dirname(here)
        if not spec_path:
            spec_path = os.path.join(role_dir, "METRICS_SPEC.md")
        self.spec_path = spec_path
        self.workspace_dir = workspace_dir or os.path.join(role_dir, "workspace")
        self.baseline_path = os.path.join(self.workspace_dir, "metrics_spec_baseline.json")

    # ------------------------------------------------------------------ #
    # 解析与完整性
    # ------------------------------------------------------------------ #
    def _fingerprint(self, content: str) -> Dict[str, Any]:
        return {
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "bytes": len(content.encode("utf-8")),
            "path": self.spec_path,
        }

    def parse(self) -> Dict[str, Any]:
        """读取并结构化解析 METRICS_SPEC.md（含指纹与 schema 校验）。"""
        if not os.path.exists(self.spec_path):
            spec = self._fallback_spec()
            spec["integrity"] = {"sha256": "", "bytes": 0, "path": self.spec_path, "missing_file": True}
            spec["schema"] = self.validate(spec)
            return spec

        with open(self.spec_path, "r", encoding="utf-8") as f:
            content = f.read()

        spec = {
            "rules_loaded": True,
            "version": "1.0.0",
            "stat_thresholds": {
                "alpha": 0.05,
                "power_min": 0.80,
                "srm_alpha": 0.001,
            },
            "hhi_thresholds": {
                "competitive_max": 1500,
                "moderate_max": 2500,
            },
            "tam_variance_max": 0.30,
            "reconciliation_tolerance": 0.01,
            "quality_dimensions": ["completeness", "uniqueness", "timeliness", "consistency", "compliance", "accuracy"],
            "metric_definitions": {},
        }

        m_alpha = re.search(r"显著性水平.*?`([0-9\.]+)`", content)
        if m_alpha:
            spec["stat_thresholds"]["alpha"] = float(m_alpha.group(1))

        m_power = re.search(r"统计功效.*?`([0-9\.]+)`", content)
        if m_power:
            spec["stat_thresholds"]["power_min"] = float(m_power.group(1))

        m_tam = re.search(r"tam_variance_max.*?`([0-9\.]+)`", content)
        if m_tam:
            spec["tam_variance_max"] = float(m_tam.group(1))

        m_recon = re.search(r"对账容差.*?`([0-9\.]+)`", content)
        if m_recon:
            spec["reconciliation_tolerance"] = float(m_recon.group(1))

        for metric in ["GMV", "UV", "CVR", "LTV", "MRR"]:
            pattern = rf"- \*\*{metric}.*?\*\*:(.*?)(?=\n-|\n##|$)"
            m = re.search(pattern, content, re.DOTALL)
            if m:
                spec["metric_definitions"][metric] = m.group(1).strip()

        spec["integrity"] = self._fingerprint(content)
        spec["schema"] = self.validate(spec)
        return spec

    def validate(self, spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """账本 schema 完整性校验。"""
        spec = spec or self.parse()
        missing = [k for k in self.REQUIRED_SECTIONS if k not in spec or spec.get(k) in (None, {}, [])]
        if not spec.get("metric_definitions"):
            missing.append("metric_definitions[GMV]")
        return {
            "valid": not missing,
            "missing_sections": sorted(set(missing)),
            "checked_sections": len(self.REQUIRED_SECTIONS),
        }

    def get_threshold(self, dotted_path: str, default: Any = None) -> Any:
        """按点号路径取阈值，供技能与引擎统一读取，避免散落硬编码。"""
        node: Any = self.parse()
        for part in dotted_path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    # ------------------------------------------------------------------ #
    # 漂移门禁
    # ------------------------------------------------------------------ #
    def _numeric_thresholds(self, spec: Dict[str, Any]) -> Dict[str, float]:
        flat: Dict[str, float] = {}

        def _walk(node: Any, prefix: str) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    _walk(v, f"{prefix}.{k}" if prefix else k)
            elif isinstance(node, (int, float)) and not isinstance(node, bool):
                flat[prefix] = float(node)

        for key in ("stat_thresholds", "hhi_thresholds", "tam_variance_max", "reconciliation_tolerance"):
            if key in spec:
                _walk(spec[key], key)
        return flat

    def detect_drift(self, spec: Optional[Dict[str, Any]] = None,
                     tolerance: Optional[float] = None) -> Dict[str, Any]:
        """与基线快照对比，检测口径漂移；首次运行自动建立基线。"""
        spec = spec or self.parse()
        tolerance = self.DRIFT_TOLERANCE if tolerance is None else tolerance
        current = self._numeric_thresholds(spec)

        baseline_created = False
        baseline: Dict[str, Any] = {}
        if os.path.exists(self.baseline_path):
            try:
                with open(self.baseline_path, "r", encoding="utf-8") as f:
                    baseline = json.load(f)
            except Exception:
                baseline = {}
        if not baseline.get("thresholds"):
            baseline = {
                "spec_sha256": spec.get("integrity", {}).get("sha256", ""),
                "thresholds": current,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            }
            os.makedirs(os.path.dirname(self.baseline_path), exist_ok=True)
            with open(self.baseline_path, "w", encoding="utf-8") as f:
                json.dump(baseline, f, ensure_ascii=False, indent=2)
            baseline_created = True

        base_thresholds = baseline.get("thresholds", {})
        drift: List[Dict[str, Any]] = []
        for key, val in current.items():
            if key not in base_thresholds:
                continue
            base_val = float(base_thresholds[key])
            if abs(val - base_val) > tolerance:
                drift.append({
                    "key": key,
                    "baseline": base_val,
                    "current": val,
                    "delta": round(val - base_val, 6),
                })

        return {
            "baseline_created": baseline_created,
            "baseline_path": self.baseline_path,
            "compared_thresholds": len(current),
            "drift_count": len(drift),
            "drift": drift,
            "within_tolerance": len(drift) == 0,
            "tolerance": tolerance,
        }

    # ------------------------------------------------------------------ #
    # 下游规则包导出
    # ------------------------------------------------------------------ #
    def export_rule_bundle(self, bundle_dir: Optional[str] = None) -> str:
        """编译账本为下游系统可直接消费的规则包。"""
        bundle_dir = bundle_dir or os.path.join(self.workspace_dir, "bundles")
        os.makedirs(bundle_dir, exist_ok=True)
        spec = self.parse()
        payload = {
            "schema_version": "1.0.0",
            "source": "METRICS_SPEC.md",
            "source_sha256": spec.get("integrity", {}).get("sha256", ""),
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "stat_thresholds": spec["stat_thresholds"],
            "hhi_thresholds": spec["hhi_thresholds"],
            "tam_variance_max": spec["tam_variance_max"],
            "reconciliation_tolerance": spec["reconciliation_tolerance"],
            "quality_dimensions": spec["quality_dimensions"],
            "metric_definitions": spec["metric_definitions"],
        }
        path = os.path.join(bundle_dir, "metrics_rules.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def _fallback_spec(self) -> Dict[str, Any]:
        return {
            "rules_loaded": False,
            "version": "1.0.0-fallback",
            "stat_thresholds": {"alpha": 0.05, "power_min": 0.80, "srm_alpha": 0.001},
            "hhi_thresholds": {"competitive_max": 1500, "moderate_max": 2500},
            "tam_variance_max": 0.30,
            "reconciliation_tolerance": 0.01,
            "quality_dimensions": ["completeness", "uniqueness", "timeliness", "consistency", "compliance", "accuracy"],
            "metric_definitions": {},
        }
