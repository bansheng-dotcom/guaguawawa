# -*- coding: utf-8 -*-
"""engines/asset_bundle.py - L07 伴生消费层 (Downstream Machine-Consumable Asset Bundle).

对标开源标杆（Stars > 1k）：
- microsoft/sarif-tools —— OASIS SARIF v2.1.0 静态分析结果交换格式；
- vega/vega-lite —— 声明式图表规格，前端图表引擎可直接渲染；
- OpenAPI / Style Dictionary —— 结构化契约与设计令牌的机器可读导出。

核心职责（解决 R07 历史断点：PRD 只有 Markdown，R08/R09 无法机器消费）：
1. `PRDASTBuilder`：把 PRD 字典编译为带 gate 状态的确定性 AST（pm.prd.ast/v1）；
2. `SARIFReporter`：把八门禁判据导出为标准 SARIF 2.1.0 日志（含规则表/定位/等级）；
3. `VegaChartBuilder`：导出 Vega-Lite v5 门禁得分图；
4. `AssetBundleExporter`：一次性落盘 `prd_bundle.json` / `prd_ast.json` /
   `prd_audit.sarif.json` / `prd_gates_chart.vega.json`，并给出每个工件的 SHA256，
   供下游做内容寻址与幂等装配。

设计约束：纯标准库、零网络、确定性（同一输入 → 同一字节流，时间戳可注入）。
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional

__all__ = ["PRDASTBuilder", "SARIFReporter", "VegaChartBuilder", "AssetBundleExporter"]

BUNDLE_SCHEMA = "pm.prd.bundle/v1"
AST_SCHEMA = "pm.prd.ast/v1"
GATE_ENGINE = "r07-pm-gate"
GATE_ENGINE_VERSION = "1.0.0"
SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
VEGA_SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"

_GATE_META: Dict[str, Dict[str, str]] = {
    "problem": {"title": "问题与场景", "rule": "PM001", "dim": "problem"},
    "user": {"title": "目标用户", "rule": "PM002", "dim": "user"},
    "value": {"title": "价值主张", "rule": "PM003", "dim": "value"},
    "scope": {"title": "范围与不做", "rule": "PM004", "dim": "scope"},
    "metric": {"title": "指标与口径", "rule": "PM005", "dim": "metric"},
    "acceptance": {"title": "验收标准", "rule": "PM006", "dim": "acceptance"},
    "risk": {"title": "承重假设", "rule": "PM007", "dim": "risk"},
    "read": {"title": "结论可读性", "rule": "PM008", "dim": "read"},
}
# 汇总类判据（PRD 整体门禁结论）必须有独立规则，不能借用某一条门禁的规则号
_SUMMARY_RULE = {"rule": "PM000", "title": "PRD 八门禁汇总", "dim": "summary"}
_GATE_ORDER = tuple(_GATE_META)
_RULES = ({_SUMMARY_RULE["rule"]: _SUMMARY_RULE["title"]}
          | {meta["rule"]: meta["title"] for meta in _GATE_META.values()})
_RULE_ORDER = list(_RULES)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _canonical(obj: Any) -> str:
    """确定性 JSON 序列化（键排序、无空格、保留中文），用于内容寻址。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _write_json(path: str, payload: Any) -> Dict[str, Any]:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return {"path": path, "sha256": _sha256_text(text),
            "bytes": len(text.encode("utf-8"))}


class PRDASTBuilder:
    """PRD → 机器可读 AST（gate 节点携带状态、证据与判据明细）。"""

    def build(self, prd: Dict[str, Any], gate_ok: Optional[Dict[str, bool]] = None,
              checks: Optional[List[Dict[str, Any]]] = None,
              passed_gates: Optional[int] = None) -> Dict[str, Any]:
        prd = prd if isinstance(prd, dict) else {}
        gate_ok = gate_ok or {}
        checks = checks or []
        by_gate: Dict[str, List[Dict[str, Any]]] = {}
        for c in checks:
            if not isinstance(c, dict):
                continue
            dim = str(c.get("dim") or "")
            by_gate.setdefault(dim, []).append({
                "ok": bool(c.get("ok")),
                "severity": str(c.get("sev") or "OK"),
                "message": str(c.get("msg") or ""),
            })

        nodes = []
        for gate in _GATE_ORDER:
            meta = _GATE_META[gate]
            nodes.append({
                "id": gate,
                "kind": "GATE",
                "rule_id": meta["rule"],
                "title": meta["title"],
                "status": "PASS" if gate_ok.get(gate) else "FAIL",
                "evidence": [c for c in by_gate.get(meta["dim"], [])],
            })

        root = {
            "id": "prd",
            "kind": "DOCUMENT",
            "title": str(prd.get("title") or prd.get("problem_statement") or "PRD"),
            "sections": [{"id": k, "kind": "SECTION",
                          "title": k, "present": bool(prd.get(k))}
                         for k in ("problem_statement", "users", "value_proposition",
                                   "scope", "metrics", "acceptance_criteria",
                                   "risks", "executive_summary")],
            "gates": nodes,
        }
        ast = {
            "schema": AST_SCHEMA,
            "summary": {
                "passed_gates": int(passed_gates if passed_gates is not None
                                    else sum(1 for g in gate_ok.values() if g)),
                "total_gates": len(_GATE_ORDER),
                "ok": all(gate_ok.get(g) for g in _GATE_ORDER),
            },
            "root": root,
            "source_sha256": _sha256_text(_canonical(prd)),
        }
        ast["ast_sha256"] = _sha256_text(_canonical(ast))
        return ast


class SARIFReporter:
    """八门禁判据 → OASIS SARIF v2.1.0（失败项即 finding，含规则映射与逻辑定位）。"""

    def build(self, result: Dict[str, Any], artifact_uri: str = "examples/prd.json") -> Dict[str, Any]:
        result = result if isinstance(result, dict) else {}
        checks = [c for c in (result.get("checks") or []) if isinstance(c, dict)]
        results: List[Dict[str, Any]] = []
        failed = 0
        for c in checks:
            if c.get("ok"):
                continue
            failed += 1
            dim = str(c.get("dim") or "summary")
            rule = _GATE_META.get(dim, {}).get("rule", _SUMMARY_RULE["rule"])
            results.append({
                "ruleId": rule,
                "ruleIndex": _RULE_ORDER.index(rule),
                "level": "error" if c.get("sev", "BLOCKER") == "BLOCKER" else "warning",
                "message": {"text": str(c.get("msg") or "gate failed")},
                "locations": [{
                    # 不伪造源码行号：本引擎不解析 PRD 源文件，只给逻辑定位（gate 维度），
                    # 由消费方按 artifactLocation + 逻辑位置去映射真实行号。
                    "physicalLocation": {
                        "artifactLocation": {"uri": artifact_uri, "uriBaseId": "SRCROOT"},
                    },
                    "logicalLocations": [{"name": dim, "kind": "gate",
                                          "fullyQualifiedName": f"prd.gate.{dim}"}],
                }],
                "properties": {"gate": dim, "severity": str(c.get("sev") or "BLOCKER")},
            })

        sarif = {
            "version": "2.1.0",
            "$schema": SARIF_SCHEMA,
            "runs": [{
                "tool": {"driver": {
                    "name": GATE_ENGINE,
                    "version": GATE_ENGINE_VERSION,
                    "informationUri": "https://github.com/microsoft/sarif-tools",
                    "rules": [{
                        "id": rule_id,
                        "name": _gate_camel(rule_id),
                        "shortDescription": {"text": title},
                        "helpUri": "PM_SPEC.md#gates",
                    } for rule_id, title in _RULES.items()],
                }},
                "invocations": [{
                    "executionSuccessful": bool(result.get("ok", True)),
                    "exitCode": 0 if result.get("ok", True) else 1,
                    "properties": {"checksTotal": len(checks), "checksFailed": failed},
                }],
                "results": results,
                "properties": {
                    "passedGates": int(result.get("passed_gates", 0)),
                    "totalGates": len(_GATE_ORDER),
                    "role": "r07-wademing-pm",
                    "gateEngine": GATE_ENGINE,
                },
            }],
        }
        return sarif


class VegaChartBuilder:
    """门禁结果 → Vega-Lite v5 柱状图（前端图表引擎可直接渲染）。"""

    def build(self, result: Dict[str, Any], title: str = "R07 PRD 八门禁得分") -> Dict[str, Any]:
        result = result if isinstance(result, dict) else {}
        gate_ok = result.get("gate_ok") or {}
        values = [{"gate": gate, "title": _GATE_META[gate]["title"],
                   "pass": 1 if gate_ok.get(gate) else 0}
                  for gate in _GATE_ORDER]
        return {
            "$schema": VEGA_SCHEMA,
            "description": title,
            "title": {"text": title, "subtitle": f"passed {result.get('passed_gates', 0)}/8"},
            "data": {"values": values},
            "mark": {"type": "bar", "tooltip": True},
            "encoding": {
                "x": {"field": "title", "type": "nominal", "sort": None,
                      "axis": {"labelAngle": -30, "title": "门禁"}},
                "y": {"field": "pass", "type": "quantitative",
                      "axis": {"title": "是否通过", "tickMinStep": 1}},
                "color": {"field": "pass", "type": "nominal",
                          "scale": {"domain": [0, 1], "range": ["#c0392b", "#27ae60"]}},
            },
        }


class AssetBundleExporter:
    """L07 主引擎：一次性导出四件套工件 + 内容寻址清单。"""

    def __init__(self, out_dir: Optional[str] = None) -> None:
        here = os.path.dirname(os.path.abspath(__file__))
        self.default_out_dir = out_dir or os.path.join(os.path.dirname(here),
                                                       "workspace", "bundles")
        self.ast_builder = PRDASTBuilder()
        self.sarif_reporter = SARIFReporter()
        self.vega_builder = VegaChartBuilder()

    def export(self, prd: Dict[str, Any], result: Dict[str, Any],
               out_dir: Optional[str] = None,
               artifact_uri: str = "examples/prd.json",
               generated_at: Optional[str] = None) -> Dict[str, Any]:
        prd = prd if isinstance(prd, dict) else {}
        result = result if isinstance(result, dict) else {}
        target = out_dir or self.default_out_dir
        os.makedirs(target, exist_ok=True)
        generated_at = generated_at or time.strftime("%Y-%m-%dT%H:%M:%S")

        ast = self.ast_builder.build(prd, gate_ok=result.get("gate_ok"),
                                     checks=result.get("checks"),
                                     passed_gates=result.get("passed_gates"))
        sarif = self.sarif_reporter.build(result, artifact_uri=artifact_uri)
        vega = self.vega_builder.build(result)

        artifacts: List[Dict[str, Any]] = []
        artifacts.append(dict(name="prd_ast", **self._write(
            os.path.join(target, "prd_ast.json"), ast)))
        artifacts.append(dict(name="prd_audit_sarif", **self._write(
            os.path.join(target, "prd_audit.sarif.json"), sarif)))
        artifacts.append(dict(name="prd_gates_chart", **self._write(
            os.path.join(target, "prd_gates_chart.vega.json"), vega)))

        bundle = {
            "schema": BUNDLE_SCHEMA,
            "generated_at": generated_at,
            "role": "r07-wademing-pm",
            "source": {"artifact_uri": artifact_uri,
                       "prd_sha256": _sha256_text(_canonical(prd))},
            "summary": {
                "ok": bool(result.get("ok")),
                "passed_gates": int(result.get("passed_gates", 0)),
                "total_gates": len(_GATE_ORDER),
                "checks_total": len(result.get("checks") or []),
                "checks_failed": sum(1 for c in (result.get("checks") or [])
                                     if isinstance(c, dict) and not c.get("ok")),
                "sarif_results": len(sarif["runs"][0]["results"]),
            },
            "handoff": {
                "downstream": ["r08-wajiancheng-mvp", "r09-wawenma-engineer",
                               "r04-watiaoci-reviewer"],
                "contracts": {"prd_bundle": BUNDLE_SCHEMA, "prd_ast": AST_SCHEMA,
                              "audit": "SARIF 2.1.0", "chart": "vega-lite v5"},
                "notes": "下游按 artifact_manifest.json 的 sha256 做内容寻址与幂等装配",
            },
            # manifest 只登记子工件（不含自身），避免自指哈希永远陈旧的悖论
            "artifacts": artifacts,
        }
        bundle_info = self._write(os.path.join(target, "prd_bundle.json"), bundle)
        bundle_info["name"] = "prd_bundle"
        manifest = {
            "schema": "pm.prd.manifest/v1",
            "generated_at": generated_at,
            "bundle": dict(bundle_info),
            "artifacts": artifacts,
        }
        manifest_info = self._write(os.path.join(target, "artifact_manifest.json"),
                                    manifest)
        manifest_info["name"] = "artifact_manifest"
        files = [a["path"] for a in artifacts] + [bundle_info["path"],
                                                  manifest_info["path"]]
        gate_ok = bool(result.get("ok"))
        return {
            # ok 反映「工件是否可交付」：门禁未过时即使已落盘取证也判 False，
            # 避免 API 消费者只看 out["ok"] 时误判为绿灯。
            "ok": gate_ok,
            "exported": True,
            "layer": "L07",
            "engine": "AssetBundleExporter",
            "gate_ok": gate_ok,
            "passed_gates": int(result.get("passed_gates", 0)),
            "out_dir": target,
            "files": files,
            "manifest_path": manifest_info["path"],
            "bundle_sha256": bundle_info["sha256"],
            "summary": bundle["summary"],
            "sarif_results": bundle["summary"]["sarif_results"],
        }

    @staticmethod
    def _write(path: str, payload: Any) -> Dict[str, Any]:
        info = _write_json(path, payload)
        info["path"] = os.path.abspath(info["path"])
        return info


def _gate_camel(rule_id: str) -> str:
    return "Gate" + "".join(part.capitalize() for part in rule_id.split("-"))
