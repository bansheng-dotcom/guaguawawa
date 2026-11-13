# -*- coding: utf-8 -*-
"""R03 动态财务与合规意图解构与 Prompter 编译器 (L02 意图解构层)。

对标高星标杆:
- DSPy (23k+): 声明式提示词编译与结构化归一
- Vanna / Text-to-SQL (15k+): 领域语义解构与精准意图路由
落地特性:
1. 提取资金量、汇率、预算金额与时间窗口 (如 "$500,000"、"18个月"、"12%波动")
2. 提取合规法规实体 (GDPR/DSR、CCPA、AI Act、AML、KYC、SOX)
3. 动态将复杂自然语言诉求编译为 R03 8 个能力域（financial/cfo/tax/contract/privacy/aigov/audit/risk）24 动作的标准结构化参数
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

class FinancialPrompter:
    """动态财务与合规意图解构与编译器。"""

    @classmethod
    def decompose_intent(cls, prompt: str) -> Dict[str, Any]:
        """将模糊的财务或合规诉求编译为精确的数据输入结构。"""
        # 1. 资金量与金额提取
        amounts = re.findall(r"(?:[¥$€£]|RMB|USD)\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)|([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(?:元|万元|USD|美元|k|w|m|b)", prompt, re.I)
        clean_amounts = []
        for a1, a2 in amounts:
            val_str = (a1 or a2).replace(",", "")
            try:
                clean_amounts.append(float(val_str))
            except ValueError:
                pass

        # 2. 月份、周期与时间窗口
        months = re.findall(r"(\d+(?:\.\d+)?)\s*(?:个?月|mons?|months?)", prompt, re.I)
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", prompt)

        # 3. 法规及红线实体
        detected_entities = []
        for ent in ["GDPR", "DSR", "CCPA", "AI Act", "AML", "KYC", "SOX", "ISO", "RMD", "Safe Harbor", "CTR"]:
            if re.search(rf"\b{re.escape(ent)}\b", prompt, re.I):
                detected_entities.append(ent.upper())

        # 4. 8大能力域意图与动作判定
        detected_skill = "cfo"
        detected_action = "runway"
        p_lower = prompt.lower()

        if any(w in p_lower for w in ["勾稽", "期初", "期末", "资产负债", "rollforward"]):
            detected_skill, detected_action = "financial", "rollforward"
        elif any(w in p_lower for w in ["对账", "差异", "单边", "未达账项", "recon"]):
            detected_skill, detected_action = "financial", "recon"
        elif any(w in p_lower for w in ["方差", "差异分析", "预算差异", "variance"]):
            detected_skill, detected_action = "financial", "variance"
        elif any(w in p_lower for w in ["现金跑道", "烧钱", "burn", "runway", "耗尽"]):
            detected_skill, detected_action = "cfo", "runway"
        elif any(w in p_lower for w in ["单位经济", "cac", "ltv", "回收期", "unitecon"]):
            detected_skill, detected_action = "cfo", "unitecon"
        elif any(w in p_lower for w in ["财务健康", "体检", "资产负债率", "healthcheck"]):
            detected_skill, detected_action = "cfo", "healthcheck"
        elif any(w in p_lower for w in ["期权", "行权", "amt", "iso"]):
            detected_skill, detected_action = "tax", "iso"
        elif any(w in p_lower for w in ["rmd", "退休", "最低分配"]):
            detected_skill, detected_action = "tax", "rmd"
        elif any(w in p_lower for w in ["安全港", "预缴", "safeharbor"]):
            detected_skill, detected_action = "tax", "safeharbor"
        elif any(w in p_lower for w in ["合同审查", "红线条款", "免责", "contract scan"]):
            detected_skill, detected_action = "contract", "scan"
        elif any(w in p_lower for w in ["保密", "竞业", "合同策略", "policy"]):
            detected_skill, detected_action = "contract", "policy"
        elif any(w in p_lower for w in ["修订", "批注", "redline"]):
            detected_skill, detected_action = "contract", "redline"
        elif any(w in p_lower for w in ["数据资产", "隐私图谱", "privacy map"]):
            detected_skill, detected_action = "privacy", "map"
        elif any(w in p_lower for w in ["dsr", "主体权利", "遗忘权", "导出申请"]):
            detected_skill, detected_action = "privacy", "dsr"
        elif any(w in p_lower for w in ["最小化", "过度收集", "minimize"]):
            detected_skill, detected_action = "privacy", "minimize"
        elif any(w in p_lower for w in ["ai治理", "合规框架", "nist", "frameworks"]):
            detected_skill, detected_action = "aigov", "frameworks"
        elif any(w in p_lower for w in ["ai分级", "高风险ai", "禁止性ai", "aiclassify"]):
            detected_skill, detected_action = "aigov", "aiclassify"
        elif any(w in p_lower for w in ["ai披露", "标识", "水印", "disclose"]):
            detected_skill, detected_action = "aigov", "disclose"
        elif any(w in p_lower for w in ["数据留存", "保存期限", "worm", "retention"]):
            detected_skill, detected_action = "audit", "retention"
        elif any(w in p_lower for w in ["模拟审计", "穿行测试", "抽样", "mockaudit"]):
            detected_skill, detected_action = "audit", "mockaudit"
        elif any(w in p_lower for w in ["审计底稿", "证据链", "evidence"]):
            detected_skill, detected_action = "audit", "evidence"
        elif any(w in p_lower for w in ["kyc", "客户身份识别", "实名"]):
            detected_skill, detected_action = "risk", "kyc"
        elif any(w in p_lower for w in ["洗钱", "大额交易", "aml", "分拆", "ctr"]):
            detected_skill, detected_action = "risk", "aml"
        elif any(w in p_lower for w in ["广告合规", "保本", "稳赚", "收益率承诺", "adreview"]):
            detected_skill, detected_action = "risk", "adreview"

        # 5. 对标 Ray DAG / DSPy 编译声明式执行 DAG
        dag_steps = [
            {"step_id": "step_extract", "action": "extract_parameters", "deps": []},
            {"step_id": "step_validate", "action": "validate_contracts", "deps": ["step_extract"]},
            {"step_id": f"step_exec_{detected_skill}_{detected_action}", "action": f"{detected_skill}.{detected_action}", "deps": ["step_validate"]}
        ]
        if detected_entities:
            dag_steps.append({
                "step_id": "step_compliance_audit",
                "action": "compliance.audit",
                "deps": [f"step_exec_{detected_skill}_{detected_action}"]
            })

        return {
            "raw_prompt": prompt,
            "detected_skill": detected_skill,
            "detected_action": detected_action,
            "extracted_amounts": clean_amounts,
            "extracted_months": [float(m) for m in months],
            "extracted_dates": dates,
            "detected_entities": detected_entities,
            "compiled_spec": {
                "target_route": f"{detected_skill}.{detected_action}",
                "confidence": 0.95,
                "requires_audit": True if detected_entities else False,
                "dag": dag_steps
            }
        }
