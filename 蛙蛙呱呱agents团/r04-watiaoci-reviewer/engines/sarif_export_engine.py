# -*- coding: utf-8 -*-
"""L07 伴生消费层：OASIS SARIF v2.1.0 标准伴生消费导出引擎。
对标开源项目：microsoft/sarif-tools (Stars > 1.2k), OASIS SARIF v2.1.0 规范。
解决病灶：审查结果仅输出纯文本或终端打印，下游 CI/CD (GitHub Actions / GitLab CI) 与 IDE 插件无法直接物理消费解析。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List


class SarifExportEngine:
    """导出标准的 OASIS SARIF v2.1.0 评审发现格式。"""

    SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
    SARIF_VERSION = "2.1.0"

    SEVERITY_TO_SARIF_LEVEL = {
        "CRITICAL": "error",
        "HIGH": "error",
        "MEDIUM": "warning",
        "LOW": "note",
        "INFO": "note",
    }

    @classmethod
    def export_sarif(cls, findings: List[Dict[str, Any]], tool_version: str = "7.0.0", output_file: str | None = None) -> Dict[str, Any]:
        """将 R04 审查发现转换为标准的 SARIF 字典，并支持物理落盘。"""
        rules: Dict[str, Dict[str, Any]] = {}
        results: List[Dict[str, Any]] = []

        for idx, item in enumerate(findings):
            rule_id = item.get("pattern") or item.get("rule_id") or f"RULE-{idx+1:03d}"
            message = item.get("message") or item.get("content") or "Issue detected by R04 Reviewer"
            severity = str(item.get("severity", "MEDIUM")).upper()
            sarif_level = cls.SEVERITY_TO_SARIF_LEVEL.get(severity, "warning")
            file_path = item.get("file_path") or item.get("source") or "unknown_file"
            line = int(item.get("line") or item.get("line_number") or 1)

            if rule_id not in rules:
                rules[rule_id] = {
                    "id": rule_id,
                    "shortDescription": {"text": f"Rule {rule_id}"},
                    "defaultConfiguration": {"level": sarif_level},
                }

            result_obj = {
                "ruleId": rule_id,
                "level": sarif_level,
                "message": {"text": message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": file_path.replace("\\", "/")},
                            "region": {"startLine": line, "startColumn": 1},
                        }
                    }
                ],
            }
            results.append(result_obj)

        sarif_log = {
            "$schema": cls.SARIF_SCHEMA,
            "version": cls.SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "r04-watiaoci-reviewer",
                            "semanticVersion": tool_version,
                            "rules": list(rules.values()),
                        }
                    },
                    "results": results,
                }
            ],
        }

        if output_file:
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(sarif_log, f, ensure_ascii=False, indent=2)

        return sarif_log
