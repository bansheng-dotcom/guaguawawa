# -*- coding: utf-8 -*-
"""engines/asset_bundle.py - L07 伴生消费层 (Downstream Consumption & Content Asset Bundle).

对标标杆: OASIS SARIF v2.1.0 / Content-AST / OpenTelemetry (Stars > 10k)
核心功能:
1. 伴生导出下游机器可消费的资产包 content_bundle.json
2. 导出 OASIS SARIF v2.1.0 格式质检审计规范 copy_audit.sarif.json，供 CI/CD 自动拦截
3. 导出多平台发布元数据 platform_meta.json
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional


class ContentAssetBundle:
    """内容运营下游伴生消费资产包生成器。"""

    def __init__(self, workspace_dir: Optional[str] = None) -> None:
        if not workspace_dir:
            here = os.path.dirname(os.path.abspath(__file__))
            agent_root = os.path.dirname(here)
            workspace_dir = os.path.join(agent_root, "workspace", "bundles")
        self.workspace_dir = workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)

    def export_bundle(self, run_id: str, content_data: Dict[str, Any]) -> Dict[str, str]:
        """打包导出机器可直接消费的结构化内容资产工件。"""
        run_bundle_dir = os.path.join(self.workspace_dir, run_id)
        os.makedirs(run_bundle_dir, exist_ok=True)

        # 1. content_bundle.json: 包含全量正文、AST、指标、平台配置
        bundle_path = os.path.join(run_bundle_dir, "content_bundle.json")
        bundle_payload = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "title": content_data.get("title", "未命名内容资产"),
            "content": content_data.get("content", content_data.get("text", "")),
            "metrics": content_data.get("metrics", {}),
            "channels": content_data.get("channels", ["微信公众号", "小红书笔记"]),
            "tags": content_data.get("tags", ["#内容复利", "#增长运营"]),
        }
        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(bundle_payload, f, ensure_ascii=False, indent=2)

        # 2. copy_audit.sarif.json: 遵循 OASIS SARIF v2.1.0 的质量门禁工件
        sarif_path = os.path.join(run_bundle_dir, "copy_audit.sarif.json")
        sarif_payload = self._build_sarif_spec(run_id, content_data)
        with open(sarif_path, "w", encoding="utf-8") as f:
            json.dump(sarif_payload, f, ensure_ascii=False, indent=2)

        # 3. platform_meta.json: 下游多渠道发布引擎分发配置
        meta_path = os.path.join(run_bundle_dir, "platform_meta.json")
        meta_payload = {
            "run_id": run_id,
            "distribution_plan": [
                {
                    "platform": "wechat_mp",
                    "channel_name": "微信公众号",
                    "article_type": "long_form",
                    "cover_ratio": "2.35:1",
                    "tags": content_data.get("tags", ["#干货"]),
                    "ready_for_review": True,
                },
                {
                    "platform": "xiaohongshu",
                    "channel_name": "小红书",
                    "article_type": "image_text_note",
                    "cover_ratio": "3:4",
                    "tags": ["#运营干货", "#爆款文案"],
                    "ready_for_review": True,
                },
            ],
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_payload, f, ensure_ascii=False, indent=2)

        return {
            "bundle_dir": run_bundle_dir,
            "bundle_path": bundle_path,
            "sarif_path": sarif_path,
            "platform_meta_path": meta_path,
        }

    def _build_sarif_spec(self, run_id: str, content_data: Dict[str, Any]) -> Dict[str, Any]:
        issues = content_data.get("issues", [])
        results = []
        for i, issue in enumerate(issues, start=1):
            results.append({
                "ruleId": f"R11-GATE-{i:03d}",
                "level": "warning" if "建议" in str(issue) else "error",
                "message": {"text": str(issue)},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": "content_bundle.json"},
                        "region": {"startLine": 1},
                    }
                }],
            })

        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "R11-CopyAuditEngine",
                        "version": "1.0.0",
                        "informationUri": "https://github.com/wawaguagua/r11-wadianti",
                    }
                },
                "results": results,
            }],
        }
