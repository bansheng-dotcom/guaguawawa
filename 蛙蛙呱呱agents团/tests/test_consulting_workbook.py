# -*- coding: utf-8 -*-
"""咨询工作簿测试：8 阶段 happy path + 门禁拒绝。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.consulting import checks, workbook  # noqa: E402

EID = "_test_consult"


def _payloads() -> dict[int, dict]:
    return {
        1: {"decision": "是否在呼市做苹果产地直采，12 个月内单公斤成本降 8%",
            "decision_maker": "创始人", "success_metric": "单公斤成本降 8% 且损耗 ≤5%",
            "scope_out": "不做全国扩张，不新增品类"},
        2: {"branches": [
            {"name": "经济性", "question": "直采能否降本", "hypothesis": "降 0.6 元/公斤",
             "data": "TCO 与损耗台账", "method": "单位经济 + 三情景", "falsifier": "损耗 >10% 连续两周"},
            {"name": "供给", "question": "产地能否稳定供货", "hypothesis": "周 2 车可行",
             "data": "合作社产能", "method": "产能核对", "falsifier": "到货率 <80%"},
            {"name": "渠道", "question": "门店能否消化", "hypothesis": "动销 ≥85%",
             "data": "POS", "method": "动销测算", "falsifier": "连续 2 周动销 <75%"}],
            "critical_branch": "经济性"},
        3: {"focus": ["经济性", "供给"],
            "excluded_reasons": {"渠道": "现有门店动销数据已足够，暂不单独立项"}},
        4: {"workstreams": [
            {"name": "TCO", "data_source": "报价 + 运价", "method": "TCO 对比",
             "owner": "r15", "output": "有效单位成本", "fallback": "人工报价"},
            {"name": "损耗", "data_source": "温控记录", "method": "损耗核算",
             "owner": "r06", "output": "损耗率区间", "fallback": "行业区间"}]},
        5: {"findings": [
            {"claim": "直采有效成本 5.23 元/公斤", "evidence": "r15 TCO", "confidence": "A",
             "falsifier": "实际到货损耗 >10%"},
            {"claim": "同规格区域溢价 3.09 元/公斤", "evidence": "新发地分规格", "confidence": "B",
             "falsifier": "匹配后差 <1 元"},
            {"claim": "损耗 8%→5% 可省 0.22 元", "evidence": "成本卡", "confidence": "C",
             "falsifier": "实际损耗不降"}],
            "conflicts": [{"item": "呼市 14.00 vs 零售 13.88", "reason": "规格不同"}], "gaps": []},
        6: {"messages": [
            {"message": "直采能降本，但前提是损耗可控", "mechanism": "去一道批发 + 预冷",
             "competing_explanations": ["价格下行而非直采"]}]},
        7: {"options": [
            {"name": "全量直采", "economics": "降 0.62 元/公斤", "risks": "断供", "preconditions": "合作社产能"},
            {"name": "试点直采", "economics": "降 0.3 元/公斤", "risks": "规模不足", "preconditions": "2 车/周"},
            {"name": "维持现采", "economics": "0", "risks": "成本不动", "preconditions": "无"}],
            "recommendation": {"choice": "试点直采", "owner": "r15", "kpi": "损耗 ≤8%",
                               "rollback": "连续 2 周损耗 >10% 回现采"}},
        8: {"deliverables": {"summary": "一页纸", "main": "建议书", "appendix": "证据台账"},
            "value_tracking": {"baseline": "6.74", "target": "6.12", "metric": "单公斤成本",
                               "review_date": "2026-12-31"}},
    }


def test_happy_path_all_stages() -> None:
    import shutil
    shutil.rmtree(workbook.PROJECTS / EID, ignore_errors=True)
    workbook.start(EID, "测试客户", "是否直采", "r01", "r05")
    payloads = _payloads()
    for stage in range(1, 9):
        r = workbook.submit(EID, stage, payloads[stage])
        assert r["ok"], (stage, r["errors"])
        workbook.sign(EID, stage, "r01")
        workbook.advance(EID)
    assert workbook.load(EID).get("status") == "completed"


def test_stage2_rejects_non_mece() -> None:
    errs = checks.check(2, {"branches": [
        {"name": "A", "question": "q", "hypothesis": "h", "data": "d", "method": "m", "falsifier": "f"},
        {"name": "A", "question": "q", "hypothesis": "h", "data": "d", "method": "m", "falsifier": "f"}],
        "critical_branch": "A"})
    assert any("至少 3 支" in e for e in errs)
    assert any("重复" in e for e in errs)


def test_stage5_requires_four_fields() -> None:
    errs = checks.check(5, {"findings": [{"claim": "x"}], "conflicts": [], "gaps": []})
    assert any("缺 evidence" in e for e in errs)
    assert any("confidence" in e for e in errs)
