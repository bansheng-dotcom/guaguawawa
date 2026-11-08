# -*- coding: utf-8 -*-
"""R07 蛙得明 · 报告映射（result → report contract 的精细桥）。

给 core/report_bridge.emit 的 specialist 参数。PRD 的「内容」在输入里（result
只含门禁结果 + checks），所以本桥额外接收 data=输入 JSON，把 PRD 的门禁结果与
输入内容拼成编辑级 contract：metric_strip 放北极星/目标/基线，sections 放
问题/用户/价值/范围/指标/验收/风险，证据表放 checks。

返回 None 时回退通用映射。
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def r07_contract(result: Dict[str, Any], skill: str, action: str,
                 intent: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    data = data or {}
    if skill == "prd" and action in ("prd", "story"):
        return _prd_contract(result, data, intent, action)
    if skill == "priority" and action in ("rice", "ice"):
        return _priority_contract(result, data, intent, action)
    if skill == "metrics" and action in ("northstar", "metrics"):
        return _metrics_contract(result, data, intent, action)
    return None  # 其余回退通用映射


def _checks_table(checks):
    return {
        "caption": "门禁检查明细",
        "columns": [{"text": "维度"}, {"text": "判定"}, {"text": "说明"}],
        "rows": [[{"text": c.get("dim", "")},
                  {"text": "✓" if c.get("ok") else "✗"},
                  {"text": c.get("msg", "")}] for c in checks],
    }


def _prd_contract(result, data, intent, action):
    ok = bool(result.get("ok", True))
    checks = result.get("checks", [])
    m = data.get("metrics", {})
    risk = data.get("risks", [])
    ac = data.get("acceptance_criteria", [])
    users = data.get("users", [])
    scope = data.get("scope", {})

    sections = [{
        "index": 1, "title": "问题与用户",
        "question": "要解决谁的真实问题？",
        "reading": [
            {"strong": "问题：", "text": data.get("problem_statement", "—")},
            {"strong": "用户：", "text": "；".join(
                f"{u.get('segment', '')}（{u.get('scenario', '')}）" for u in users) or "—"},
        ],
    }, {
        "index": 2, "title": "价值主张与范围",
        "question": "怎么做、做到什么边界？",
        "reading": [
            {"strong": "Before：", "text": data.get("value_proposition", {}).get("before", "—")},
            {"strong": "How：", "text": data.get("value_proposition", {}).get("how", "—")},
            {"strong": "After：", "text": data.get("value_proposition", {}).get("after", "—")},
            {"strong": "P0：", "text": "、".join(scope.get("p0", [])) or "—"},
            {"strong": "不做：", "text": "、".join(scope.get("non_goals", [])) or "—"},
        ],
    }, {
        "index": 3, "title": "指标与验收",
        "question": "怎么算成功？验收标准是什么？",
        "reading": [
            {"strong": "北极星：", "text": m.get("north_star", "—")},
            {"strong": "基线 → 目标：", "text": f"{m.get('baseline', '—')} → {m.get('target', '—')}"},
            {"strong": "护栏：", "text": "、".join(m.get("guardrail", [])) or "—"},
        ],
        "table": {
            "caption": "验收准则（Given/When/Then）",
            "columns": [{"text": "Given"}, {"text": "When"}, {"text": "Then"}],
            "rows": [[{"text": a.get("given", "")}, {"text": a.get("when", "")},
                      {"text": a.get("then", "")}] for a in ac],
        },
    }, {
        "index": 4, "title": "承重假设",
        "question": "哪些假设不成立会让方案崩塌？",
        "table": {
            "caption": "风险假设与验证方式",
            "columns": [{"text": "假设"}, {"text": "验证方式"}],
            "rows": [[{"text": r.get("hypothesis", "")}, {"text": r.get("validation", "")}]
                     for r in risk],
        },
    }, {
        "index": 5, "title": "门禁结果",
        "question": "PRD 八门禁是否全部通过？",
        "table": _checks_table(checks),
        "boundary": {"title": "证据边界",
                     "text": "PRD 门禁只校验结构完整性与口径可定义，不评估方案优劣。"},
    }]

    return {
        "doc_type": "产品需求报告 · 蛙得明",
        "title_lines": ["蛙得明 · PRD", data.get("problem_statement", intent)[:40]],
        "standfirst": data.get("executive_summary", "") or data.get("problem_statement", intent),
        "meta": ["角色 r07 蛙得明（产品经理）", "渲染器 core/report_renderer.py"],
        "metric_strip": [
            {"label": "门禁", "value": "PASS" if ok else "FAIL",
             "note": f"{result.get('passed_gates', 0)}/8 门禁",
             "status": "healthy" if ok else "critical"},
            {"label": "北极星", "value": m.get("north_star", "—"), "note": "NSM", "status": "accent"},
            {"label": "基线", "value": m.get("baseline", "—"), "note": "现状", "status": "none"},
            {"label": "目标", "value": m.get("target", "—"), "note": "预期", "status": "none"},
        ],
        "summary": [
            {"label": "结论：", "text": data.get("executive_summary", "") or
             ("PRD 八门禁通过，可进入开发。" if ok else "PRD 门禁未通过，需补齐。")},
            {"label": "承重：", "text": f"{len(risk)} 项承重假设待验证，未验证前方案仍处假设态。"},
        ],
        "sections": sections,
        "notes": {"summary": "口径、来源与证据边界",
                  "items": [{"label": "来源：", "text": "R07 skills/s03_prd.py 门禁 + PRD 输入 JSON。"},
                            {"label": "边界：", "text": "PRD 是需求假设，非数据结论；需 R06 验证、R04 评审。"}]},
        "footer": ["R07 蛙得明 · 产品经理", "core/report_renderer.py 确定性渲染"],
    }


def _priority_contract(result, data, intent, action):
    ranked = result.get("ranked", [])
    formula = result.get("formula", "")
    sections = [{
        "index": 1, "title": "优先级排序",
        "question": "先做哪个？为什么？",
        "reading": [{"strong": "公式：", "text": formula or "—"},
                    {"strong": "项数：", "text": f"{len(ranked)} 项"}],
        "table": {
            "caption": "排序明细",
            "columns": [{"text": "名称"}, {"text": "得分"}, {"text": "触达"}, {"text": "影响"}, {"text": "信心"}, {"text": "工作量"}],
            "rows": [[{"text": r.get("name", "")}, {"text": f"{r.get('score', 0):,.1f}"},
                      {"text": f"{r.get('reach', 0):,.0f}"}, {"text": f"{r.get('impact', 0):.2f}"},
                      {"text": f"{r.get('confidence', 0):.0f}"}, {"text": f"{r.get('effort', 0):,.1f}"}]
                     for r in ranked],
        },
    }]
    return {
        "doc_type": "优先级报告 · 蛙得明",
        "title_lines": ["蛙得明 · 优先级排序", intent],
        "standfirst": f"{action.upper()} 排序完成，共 {len(ranked)} 项。",
        "meta": ["角色 r07 蛙得明（产品经理）", "渲染器 core/report_renderer.py"],
        "metric_strip": [
            {"label": "门禁", "value": "PASS" if result.get("ok") else "FAIL",
             "note": "排序完成", "status": "healthy" if result.get("ok") else "critical"},
            {"label": "项数", "value": str(len(ranked)), "note": "候选", "status": "accent"},
            {"label": "最高分", "value": f"{ranked[0]['score']:,.1f}" if ranked else "—",
             "note": "优先做", "status": "none"},
            {"label": "公式", "value": action.upper(), "note": "排序法", "status": "none"},
        ],
        "summary": [{"label": "结论：", "text": f"最高优先为「{ranked[0]['name']}」。" if ranked else "无候选。"}],
        "sections": sections,
        "notes": {"summary": "口径", "items": [{"label": "来源：", "text": "R07 skills/s04_priority.py 实算排序。"}]},
        "footer": ["R07 蛙得明 · 产品经理", "core/report_renderer.py"],
    }


def _metrics_contract(result, data, intent, action):
    m = data
    sections = [{
        "index": 1, "title": "北极星与指标分层",
        "question": "怎么知道我们赢了？",
        "reading": [
            {"strong": "北极星：", "text": m.get("north_star", "—")},
            {"strong": "输入指标：", "text": "、".join(m.get("input_metrics", [])) or "—"},
            {"strong": "护栏：", "text": "、".join(m.get("guardrail", [])) or "—"},
            {"strong": "基线 → 目标：", "text": f"{m.get('baseline', '—')} → {m.get('target', '—')}"},
        ],
        "table": _checks_table(result.get("checks", [])),
    }]
    return {
        "doc_type": "指标报告 · 蛙得明",
        "title_lines": ["蛙得明 · 北极星指标", intent],
        "standfirst": f"北极星指标：{m.get('north_star', '—')}",
        "meta": ["角色 r07 蛙得明（产品经理）", "渲染器 core/report_renderer.py"],
        "metric_strip": [
            {"label": "门禁", "value": "PASS" if result.get("ok") else "FAIL",
             "note": "北极星 7 标准", "status": "healthy" if result.get("ok") else "critical"},
            {"label": "北极星", "value": m.get("north_star", "—"), "note": "NSM", "status": "accent"},
            {"label": "输入指标", "value": str(result.get("input_metric_count", 0)),
             "note": "3-5 个", "status": "none"},
            {"label": "目标", "value": m.get("target", "—"), "note": "预期", "status": "none"},
        ],
        "summary": [{"label": "结论：", "text": f"北极星「{m.get('north_star', '—')}」"
                     + ("通过 7 标准。" if result.get("ok") else "未通过 7 标准。")}],
        "sections": sections,
        "notes": {"summary": "口径", "items": [{"label": "来源：", "text": "R07 skills/s06_metrics.py。"}]},
        "footer": ["R07 蛙得明 · 产品经理", "core/report_renderer.py"],
    }
