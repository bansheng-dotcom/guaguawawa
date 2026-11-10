# -*- coding: utf-8 -*-
"""L07 伴生消费层：OASIS 标准 SARIF (Static Analysis Results Interchange Format) 与系统机读导出器。
对标开源标杆：microsoft/sarif-tools (Stars: 1k+), github/codeql (SARIF standard)

功能：
1. 摆脱仅面向人类眼睛阅读的纯文本/Markdown 报告；
2. 将 R04 审查发现的所有反模式、断言失效、证据缺失与门禁风险，
   全量伴生导出为符合 OASIS SARIF v2.1.0 标准 JSON 描述符 (review_result.sarif.json)；
3. 下游系统（GitHub Code Scanning、GitLab Security Dashboard、SonarQube、VS Code SARIF Viewer 等）
   可无需人肉转译直接摄取消费、在 PR/MR 上自动加注行内批注 (Inline Annotations)。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


class SarifExporter:
    """SARIF v2.1.0 标准格式伴生导出器"""

    SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
    SARIF_VERSION = "2.1.0"

    def export_sarif(self, run_results: List[Dict[str, Any]], tool_name: str = "r04-watiaoci-reviewer", tool_version: str = "6.0.0") -> Dict[str, Any]:
        """将内部 findings/checks 格式转化为标准 SARIF 格式"""
        rules_map: Dict[str, Dict[str, Any]] = {}
        sarif_results: List[Dict[str, Any]] = []

        for item in run_results:
            rule_id = str(item.get("type") or item.get("id") or item.get("rule_id") or "R04-GENERIC")
            severity = str(item.get("severity") or item.get("status") or "warning").lower()
            message_text = str(item.get("message") or item.get("desc") or item.get("comment") or "")
            target_file = str(item.get("target") or item.get("file") or item.get("path") or "unknown.py")
            line = int(item.get("line") or 1)

            # 映射 SARIF level (error, warning, note, none)
            if severity in ("blocker", "critical", "fail", "error"):
                level = "error"
            elif severity in ("warn", "warning", "at-risk"):
                level = "warning"
            else:
                level = "note"

            # 注册规则
            if rule_id not in rules_map:
                rules_map[rule_id] = {
                    "id": rule_id,
                    "name": rule_id.replace("_", "-"),
                    "shortDescription": {"text": f"R04 审查规则: {rule_id}"},
                    "defaultConfiguration": {"level": level},
                }

            # 构造 result
            sarif_results.append({
                "ruleId": rule_id,
                "level": level,
                "message": {"text": message_text},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": target_file.replace("\\", "/")},
                        "region": {
                            "startLine": line,
                            "startColumn": 1,
                        },
                    }
                }],
            })

        sarif_doc = {
            "$schema": self.SARIF_SCHEMA,
            "version": self.SARIF_VERSION,
            "runs": [{
                "tool": {
                    "driver": {
                        "name": tool_name,
                        "version": tool_version,
                        "informationUri": "https://github.com/wawa-guagua/r04-watiaoci-reviewer",
                        "rules": list(rules_map.values()),
                    }
                },
                "results": sarif_results,
            }],
        }

        return sarif_doc

    def dump_sarif_file(self, sarif_doc: Dict[str, Any], file_path: str) -> None:
        """导出到指定物理 JSON 文件"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(sarif_doc, f, indent=2, ensure_ascii=False)
