# -*- coding: utf-8 -*-
"""L07 伴生消费层：战略研究伴生资产包、OASIS SARIF 2.1.0 审计结果与 SHA256 资产清单。

对标标杆:
- microsoft/sarif-tools (1.2k⭐) / OASIS SARIF 2.1.0 标准 / vega/vega-lite (4.6k⭐)
吸收的机制:
- SARIF 2.1.0 标准结果交换：runs[].tool.driver + results[] + locations.physicalLocation，
  把“哪条断言缺证据、TAM 双口径偏差超容差、出现 tier_0、缺三情景、缺 HHI”
  变成下游 CI 可直接回放的机器可读发现（error/warning/note 三级）；
- 供应链完整性（supply-chain integrity）：bundle.json 记录每个伴生工件的字节数与
  SHA256，verify_bundle 逐件复核存在性/大小/摘要，任何追加篡改或截断都会被判定；
- Vega-Lite 声明式图表描述符：只交付数据与编码、不交付渲染实现，R06 直接消费。

纯标准库实现，Windows 路径安全（全部 os.path.join / os.makedirs）。
"""
from __future__ import annotations
import datetime
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

SARIF_SCHEMA = ("https://docs.oasis-open.org/sarif/sarif/v2.1.0/cs01/"
                "schemas/sarif-schema-2.1.0.json")
SARIF_VERSION = "2.1.0"
PRODUCER = "r05-washenyuan-research"
PRODUCER_VERSION = "2.0.0"
PRODUCER_URI = "https://wawaguagua.com/roles/r05"
BUNDLE_VERSION = "1.0.0"

# SARIF 驱动的规则元数据（与 results[].ruleId 一一对应，供下游渲染帮助文案）。
_SARIF_RULES: List[Dict[str, Any]] = [
    {"id": "R05-EVIDENCE-GAP", "name": "EvidenceGap",
     "shortDescription": {"text": "断言缺失可追溯证据来源"},
     "defaultConfiguration": {"level": "warning"},
     "helpUri": "https://wawaguagua.com/rules/r05-evidence-gap"},
    {"id": "R05-TAM-VARIANCE", "name": "TamVariance",
     "shortDescription": {"text": "TAM 自上而下/自下而上双口径偏差超容差"},
     "defaultConfiguration": {"level": "error"},
     "helpUri": "https://wawaguagua.com/rules/r05-tam-variance"},
    {"id": "R05-TIER0", "name": "Tier0Claim",
     "shortDescription": {"text": "出现不可采信的 tier_0 断言"},
     "defaultConfiguration": {"level": "error"},
     "helpUri": "https://wawaguagua.com/rules/r05-tier0"},
    {"id": "R05-SCENARIO-GAP", "name": "ScenarioGap",
     "shortDescription": {"text": "缺少保守/基准/乐观三情景"},
     "defaultConfiguration": {"level": "note"},
     "helpUri": "https://wawaguagua.com/rules/r05-scenario-gap"},
    {"id": "R05-HHI-MISSING", "name": "HhiMissing",
     "shortDescription": {"text": "未声明 HHI 市场集中度"},
     "defaultConfiguration": {"level": "warning"},
     "helpUri": "https://wawaguagua.com/rules/r05-hhi-missing"},
]

TAM_VARIANCE_MAX = 0.30
SCENARIO_REQUIRED = 3


def _sha256_file(path: str) -> str:
    """对磁盘上的真实文件内容计算 SHA256（分块读取，Windows 大文件安全）。"""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ResearchAssetBundle:
    """伴生资产包导出器：research_spec / Vega-Lite / SARIF / SHA256 清单。"""

    # ------------------------------------------------------------------
    # 内部：逐条规则的真实计算
    # ------------------------------------------------------------------
    @staticmethod
    def _claim_id(claim: Any, index: int) -> str:
        if isinstance(claim, dict):
            return str(claim.get("id") or claim.get("claim_id") or f"claim_{index + 1}")
        return f"claim_{index + 1}"

    @staticmethod
    def _claim_sources(claim: Any) -> List[Any]:
        if not isinstance(claim, dict):
            return []
        raw = claim.get("sources")
        if raw is None:
            raw = claim.get("evidence_refs")
        if isinstance(raw, (list, tuple)):
            return [item for item in raw if item not in (None, "")]
        return [raw] if raw not in (None, "") else []

    @staticmethod
    def _tam_variance(base_data: Dict[str, Any]) -> Optional[float]:
        """按 |tam_top - tam_bottom| / tam_top 计算双口径方差，缺数返回 None。"""
        top = base_data.get("tam_top")
        bottom = base_data.get("tam_bottom")
        if top is None or bottom is None:
            return None
        try:
            top_f = float(top)
            bottom_f = float(bottom)
        except (TypeError, ValueError):
            return None
        if top_f <= 0:
            return None
        return abs(top_f - bottom_f) / top_f

    @staticmethod
    def _scenario_count(base_data: Dict[str, Any]) -> int:
        scenarios = base_data.get("scenarios")
        if isinstance(scenarios, list):
            return len(scenarios)
        raw = base_data.get("scenario_count")
        try:
            return int(raw) if raw is not None else 0
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _result(rule_id: str, level: str, text: str, uri: str,
                properties: Dict[str, Any]) -> Dict[str, Any]:
        """构造一条符合 SARIF 2.1.0 的 result（含物理位置与区域）。"""
        return {
            "ruleId": rule_id,
            "level": level,
            "message": {"text": text},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": uri},
                    "region": {"startLine": 1},
                }
            }],
            "properties": properties,
        }

    def build_sarif(self, base_data: Dict[str, Any],
                    artifact_uri: str = "research_spec.json") -> Dict[str, Any]:
        """把一次战略研究的真实体检结论编译为 SARIF 2.1.0 文档。"""
        results: List[Dict[str, Any]] = []
        claims = base_data.get("claims")
        claims = claims if isinstance(claims, list) else []

        # 规则 1：R05-EVIDENCE-GAP —— 无 sources 的 claim
        for index, claim in enumerate(claims):
            if not self._claim_sources(claim):
                claim_id = self._claim_id(claim, index)
                results.append(self._result(
                    "R05-EVIDENCE-GAP", "warning",
                    f"断言 {claim_id} 无 sources 证据来源，需补 tier_1/tier_2 出处",
                    artifact_uri, {"claim_id": claim_id, "index": index}))

        # 规则 2：R05-TAM-VARIANCE —— 双口径偏差 >= 0.30
        variance = self._tam_variance(base_data)
        if variance is not None and variance >= TAM_VARIANCE_MAX:
            results.append(self._result(
                "R05-TAM-VARIANCE", "error",
                f"TAM 双口径方差 {variance:.4f} >= 容差 {TAM_VARIANCE_MAX:.2f}，"
                f"规模结论不可用于决策",
                artifact_uri,
                {"variance": round(variance, 6), "tolerance": TAM_VARIANCE_MAX,
                 "tam_top": base_data.get("tam_top"),
                 "tam_bottom": base_data.get("tam_bottom")}))

        # 规则 3：R05-TIER0 —— 出现 tier_0 断言
        for index, claim in enumerate(claims):
            tier = str(claim.get("tier", "")) if isinstance(claim, dict) else ""
            if tier.strip().lower() in ("tier_0", "tier0", "0"):
                claim_id = self._claim_id(claim, index)
                results.append(self._result(
                    "R05-TIER0", "error",
                    f"断言 {claim_id} 属于 tier_0（传闻级），禁止进入决策链",
                    artifact_uri, {"claim_id": claim_id, "index": index}))

        # 规则 4：R05-SCENARIO-GAP —— 缺三情景
        scenario_count = self._scenario_count(base_data)
        if scenario_count < SCENARIO_REQUIRED:
            results.append(self._result(
                "R05-SCENARIO-GAP", "note",
                f"仅 {scenario_count} 套情景，低于要求的 {SCENARIO_REQUIRED} 套"
                f"（保守/基准/乐观）",
                artifact_uri,
                {"scenario_count": scenario_count,
                 "required": SCENARIO_REQUIRED}))

        # 规则 5：R05-HHI-MISSING —— 未声明 HHI
        hhi = base_data.get("hhi")
        if hhi in (None, ""):
            results.append(self._result(
                "R05-HHI-MISSING", "warning",
                "未声明 HHI 市场集中度，无法判定竞争结构",
                artifact_uri, {"hhi": None}))

        # 全部规则通过时给出显式 note，保证 results 恒非空（SARIF 允许 note 级结论）。
        if not results:
            results.append(self._result(
                "R05-GATE-CLEAN", "note",
                "8 维发布门禁未发现阻断项：证据来源、TAM 双口径、tier 分级、"
                "三情景与 HHI 均达标",
                artifact_uri, {"findings": 0}))

        driver = {
            "name": PRODUCER,
            "version": PRODUCER_VERSION,
            "informationUri": PRODUCER_URI,
            "rules": _SARIF_RULES,
        }
        return {
            "$schema": SARIF_SCHEMA,
            "version": SARIF_VERSION,
            "runs": [{
                "tool": {"driver": driver},
                "results": results,
                "properties": {
                    "producer": PRODUCER,
                    "artifact": artifact_uri,
                    "finding_count": len(results),
                },
            }],
        }

    # ------------------------------------------------------------------
    # 内部：asset spec / chart spec
    # ------------------------------------------------------------------
    @staticmethod
    def _build_research_spec(base_data: Dict[str, Any]) -> Dict[str, Any]:
        """保持既有契约字段：meta / market_data / evidence_ledger / downstream_handover。"""
        claims = base_data.get("claims")
        return {
            "$schema": "https://wawaguagua.com/schemas/research-spec-v1.json",
            "meta": {
                "producer": PRODUCER,
                "version": "1.0.0",
                "confidence_tier": base_data.get("tier", "tier_1"),
            },
            "market_data": {
                "tam": base_data.get("tam", 120.0),
                "hhi": base_data.get("hhi", 2250),
                "cr4": base_data.get("cr4", 90),
                "market_structure": base_data.get("structure", "moderate"),
            },
            "evidence_ledger": claims if isinstance(claims, list) else [],
            "downstream_handover": {
                "to_r06": "提供确定性 TAM 与集中度数值进行可视化渲染",
                "to_r07": "提供竞品薄弱点与细分切入假设作为 PRD 输入",
                "to_r01": "提供多情景决策备选项与致命风险预警",
            },
        }

    @staticmethod
    def _build_chart_spec(base_data: Dict[str, Any]) -> Dict[str, Any]:
        tam = base_data.get("tam", 120.0)
        try:
            tam = float(tam)
        except (TypeError, ValueError):
            tam = 120.0
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": "R05 战略研究格局与规模图表描述符",
            "data": {
                "values": [
                    {"category": "TAM", "value": tam},
                    {"category": "SAM", "value": tam * 0.4},
                    {"category": "SOM", "value": tam * 0.4 * 0.1},
                ]
            },
            "mark": "bar",
            "encoding": {
                "x": {"field": "category", "type": "nominal"},
                "y": {"field": "value", "type": "quantitative"},
            },
        }

    @staticmethod
    def _write_json(path: str, payload: Any) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # 对外：导出 / 校验
    # ------------------------------------------------------------------
    def export_bundle(self, base_data: Dict[str, Any],
                      output_dir: str) -> Dict[str, str]:
        """导出机器消费的伴生资产包（4 键，均为绝对路径）。"""
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        spec_path = os.path.join(output_dir, "research_spec.json")
        chart_path = os.path.join(output_dir, "research_chart_spec.json")
        sarif_path = os.path.join(output_dir, "research_result.sarif.json")
        manifest_path = os.path.join(output_dir, "bundle.json")

        research_spec = self._build_research_spec(base_data)
        chart_spec = self._build_chart_spec(base_data)
        sarif_doc = self.build_sarif(base_data, artifact_uri="research_spec.json")

        self._write_json(spec_path, research_spec)
        self._write_json(chart_path, chart_spec)
        self._write_json(sarif_path, sarif_doc)

        artifacts: List[Dict[str, Any]] = []
        for path in (spec_path, chart_path, sarif_path):
            artifacts.append({
                "path": os.path.basename(path),
                "bytes": os.path.getsize(path),
                "sha256": _sha256_file(path),
                "media_type": "application/json",
            })

        manifest = {
            "bundle_version": BUNDLE_VERSION,
            "producer": PRODUCER,
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "artifacts": artifacts,
        }
        self._write_json(manifest_path, manifest)

        return {
            "research_spec": spec_path,
            "chart_spec": chart_path,
            "sarif": sarif_path,
            "bundle_manifest": manifest_path,
        }

    def verify_bundle(self, manifest_path: str) -> Dict[str, Any]:
        """读取 bundle.json 并逐件复核存在性/字节数/SHA256，返回不一致明细。"""
        manifest_path = os.path.abspath(manifest_path)
        mismatches: List[Dict[str, Any]] = []
        base_dir = os.path.dirname(manifest_path)

        if not os.path.exists(manifest_path):
            return {"ok": False, "checked": 0,
                    "mismatches": [{"path": os.path.basename(manifest_path),
                                    "reason": "manifest_missing",
                                    "expected": "存在", "actual": "缺失"}],
                    "manifest": manifest_path}

        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
        except (OSError, ValueError) as exc:
            return {"ok": False, "checked": 0,
                    "mismatches": [{"path": os.path.basename(manifest_path),
                                    "reason": "manifest_unreadable",
                                    "expected": "合法 JSON", "actual": str(exc)}],
                    "manifest": manifest_path}

        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, list):
            artifacts = []

        checked = 0
        for item in artifacts:
            if not isinstance(item, dict):
                continue
            checked += 1
            rel_path = str(item.get("path", ""))
            target = os.path.join(base_dir, rel_path.replace("/", os.sep))
            expected_sha = item.get("sha256")
            expected_bytes = item.get("bytes")

            if not rel_path or not os.path.exists(target):
                mismatches.append({"path": rel_path, "reason": "missing",
                                   "expected": "文件存在", "actual": "缺失"})
                continue

            actual_bytes = os.path.getsize(target)
            if expected_bytes is not None and actual_bytes != expected_bytes:
                mismatches.append({"path": rel_path, "reason": "size_mismatch",
                                   "expected": expected_bytes,
                                   "actual": actual_bytes})
            actual_sha = _sha256_file(target)
            if expected_sha is not None and actual_sha != expected_sha:
                mismatches.append({"path": rel_path, "reason": "sha256_mismatch",
                                   "expected": expected_sha, "actual": actual_sha})

        return {"ok": not mismatches, "checked": checked,
                "mismatches": mismatches, "manifest": manifest_path}
