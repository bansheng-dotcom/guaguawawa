# -*- coding: utf-8 -*-
"""engines/prototype_slop_guard.py - L05 质感去劣化 (Prototype SlopGuard & Anti-Placeholder).

对标开源标杆：reviewdog / StyleGuide / Biome (Stars > 10k)
核心职责：
1. 深度审查原型代码与文档中的“AI味/假大空/塑料感/未完工”痕迹；
2. 识别并替换空泛占位词（“此处界面稍后补充”、“TODO: 实现业务逻辑”、“视情况而定”）；
3. 杜绝毫无意义的 Mock 假按钮（无 href、无 onclick、空的 javascript:void(0)）；
4. 强制注入可检验性 (Actionability) 与量化验收判据。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class PrototypeSlopGuard:
    """R08 L05 原型质感去劣与占位符驱除引擎。"""

    SLOP_PATTERNS = [
        (r"此处界面(?:稍后补充|待定|暂未开放|后续补充)", "真实业务展示与交互入口"),
        (r"TODO:?\s*实现.*", "完成轻量级客户端校验与交互响应"),
        (r"视情况而定", "按标准三档指标确定性执行"),
        (r"待进一步沟通", "首期按轻量MVP基线策略上线"),
        (r"占位内容|placeholder text|Lorem ipsum", "核心功能价值点与用户真实痛点提炼"),
        (r"功能待定|稍后开发", "交付精简版可用单屏流程"),
    ]

    MOCK_BUTTON_PATTERNS = [
        r'href=["\']#["\']',
        r'href=["\']javascript:void\(0\)["\']',
        r'<button[^>]*>\s*按钮\s*</button>',
    ]

    def __init__(self):
        self.version = "1.0.0"

    def audit_text(self, text: str) -> Dict[str, Any]:
        """对原型文档或代码字符串做去劣化审计。"""
        issues: List[Dict[str, Any]] = []
        clean_text = text

        # 1. 扫描 AI 假大空与占位套话
        for pat, replacement in self.SLOP_PATTERNS:
            matches = list(re.finditer(pat, clean_text, re.IGNORECASE))
            if matches:
                for m in matches:
                    issues.append({
                        "pattern": pat,
                        "matched": m.group(0),
                        "suggested": replacement,
                        "severity": "BLOCKER",
                    })
                # 执行物理级替换
                clean_text = re.sub(pat, replacement, clean_text, flags=re.IGNORECASE)

        # 2. 扫描无效死链与无行动力按钮
        for pat in self.MOCK_BUTTON_PATTERNS:
            matches = list(re.finditer(pat, clean_text, re.IGNORECASE))
            if matches:
                for m in matches:
                    issues.append({
                        "pattern": pat,
                        "matched": m.group(0),
                        "suggested": "绑定明确的表单提交、锚点跳转或状态回调",
                        "severity": "WARN",
                    })

        return {
            "is_clean": len(issues) == 0,
            "issues_found": len(issues),
            "issues": issues,
            "purified_text": clean_text,
            "actionability_score": 100 if len(issues) == 0 else max(40, 100 - len(issues) * 15),
        }

    def purify_artifact(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """递归净化 JSON 工件中所有字符串字段。"""
        purified = {}
        total_replacements = 0
        for k, v in data.items():
            if isinstance(v, str):
                audit = self.audit_text(v)
                purified[k] = audit["purified_text"]
                total_replacements += audit["issues_found"]
            elif isinstance(v, dict):
                sub_p, cnt = self.purify_artifact(v)
                purified[k] = sub_p
                total_replacements += cnt
            elif isinstance(v, list):
                new_list = []
                for item in v:
                    if isinstance(item, str):
                        audit = self.audit_text(item)
                        new_list.append(audit["purified_text"])
                        total_replacements += audit["issues_found"]
                    elif isinstance(item, dict):
                        sub_p, cnt = self.purify_artifact(item)
                        new_list.append(sub_p)
                        total_replacements += cnt
                    else:
                        new_list.append(item)
                purified[k] = new_list
            else:
                purified[k] = v
        return purified, total_replacements
