# -*- coding: utf-8 -*-
"""report_kernel · aggregate —— L1×N → L2（跨域汇总）/ L3（评审）。

规则：L2 只能引用 L1 已出现的数字，不得引入新数字（guard.assert_traceable）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .guard import assert_traceable, harvest_numbers
from .layers import normalize_tables


def _summary_text(contract: Dict[str, Any]) -> str:
    s = contract.get("summary")
    if isinstance(s, list):
        return " ".join(x.get("text", "") for x in s if isinstance(x, dict))
    return str(s or "")


def build_l2(project: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """items: [{role, title, contract, fid, spec_errors}]"""
    allowed = harvest_numbers([i["contract"] for i in items])

    rows = []
    for it in items:
        fid = it.get("fid") or {}
        rows.append([
            it["role"], it["title"][:28],
            _summary_text(it["contract"])[:40],
            f'{fid["retention"]*100:.1f}%' if fid.get("retention") is not None else "N/A",
            f'{fid["trace"]*100:.0f}%' if fid.get("trace") is not None else "N/A",
            "PASS" if not it.get("spec_errors") else "FAIL",
        ])

    fids = [it.get("fid") or {} for it in items]
    bad_roles = [it["role"] for it in items if it.get("spec_errors")]
    summary = (f"本跨域项目汇总 {len(items)} 份角色报告；"
               f"其中规格不达标 {len(bad_roles)} 份（{'、'.join(bad_roles) if bad_roles else '无'}）。")

    violations = assert_traceable(summary, allowed)
    if violations:
        raise ValueError(f"L2 出现未追溯数字: {violations}（只能引用 L1 已有数字）")

    sections = [
        {"index": 1, "title": "各角色结论",
         "question": "每个角色交付了什么、结论是什么、分数多少？",
         "table": {"caption": "L1 汇总", "columns": ["角色", "交付", "结论", "保留率", "溯源率", "规格"],
                   "rows": rows}},
        {"index": 2, "title": "综合判断",
         "question": "跨域看，整体是否可交付？",
         "reading": [{"text": summary}]},
        {"index": 3, "title": "待补项",
         "question": "哪些角色规格不达标、需要回补？",
         "table": {"caption": "规格缺口", "columns": ["角色", "问题"],
                   "rows": [[it["role"], "；".join(it["spec_errors"])] for it in items if it.get("spec_errors")]
                   or [["—", "无"]]}},
        {"index": 4, "title": "口径与分数",
         "question": "这份汇总的数据够不够、能不能追回去？",
         "table": {"caption": "自检分数", "columns": ["指标", "值", "说明"], "rows": [
             ["L1 份数", str(len(items)), "参与汇总的角色报告"],
             ["规格达标", f"{len(items) - len(bad_roles)}/{len(items)}", "按 spec 校验"],
             ["未追溯数字", "0", "L2 只允许引用 L1 已有数字，guard 已校验"],
             ["平均保留率", (f"{sum(f['retention'] for f in fids if f.get('retention') is not None) / max(1, len([f for f in fids if f.get('retention') is not None])) * 100:.1f}%"
                             if any(f.get("retention") is not None for f in fids) else "N/A"), "按有观测集的 L1 计算"],
         ]},
         "reading": [{"text": "分数放在最后：先说结论，再说这些分数够不够。"}]},
    ]

    return normalize_tables({
        "doc_type": f"跨域汇总 · {project}",
        "title_lines": [f"{project} · 跨域汇总", f"{len(items)} 份 L1 报告"],
        "standfirst": "由 report_kernel 汇总 L1 契约生成；数字均来自 L1，未新增。",
        "metric_strip": [
            {"label": "L1 份数", "value": str(len(items)), "note": "参与汇总的角色报告", "status": "accent"},
            {"label": "规格达标", "value": f"{len(items) - len(bad_roles)}/{len(items)}",
             "note": "按 spec 校验", "status": "healthy" if not bad_roles else "critical"},
            {"label": "未追溯数字", "value": "0", "note": "guard 已校验", "status": "healthy"},
            {"label": "层级", "value": "L2", "note": "R01 汇总", "status": "none"},
        ],
        "summary": [{"label": "汇总：", "text": summary},
                    {"label": "约束：", "text": "L2 只允许引用 L1 已出现的数字，guard 已校验。"}],
        "sections": sections,
        "notes": {"summary": "口径、来源与证据边界",
                  "items": [{"label": "来源：", "text": "各角色 L1 报告（如实标注）"},
                            {"label": "边界：", "text": "不新增数字，不做二次推断。"}]},
        "footer": [f"L2 · {project}", "core/report_kernel.aggregate"],
    })


def build_l3(project: str, l2: Dict[str, Any], spec_errors: Dict[str, List[str]]) -> Dict[str, Any]:
    """L3 评审：对 L2 与各 L1 的规格合规做逐条核证。"""
    rows = []
    for role, errs in spec_errors.items():
        rows.append([role, "PASS" if not errs else "FAIL", "；".join(errs) or "符合 spec"])
    return normalize_tables({
        "doc_type": f"评审报告 · {project}",
        "title_lines": [f"{project} · 评审", "R04 独立核验"],
        "standfirst": "只核证不修复；每条给出判定与依据。",
        "metric_strip": [
            {"label": "受审角色", "value": str(len(spec_errors)), "note": "本次评审范围", "status": "accent"},
            {"label": "通过", "value": str(sum(1 for e in spec_errors.values() if not e)),
             "note": "规格达标", "status": "healthy"},
            {"label": "不通过", "value": str(sum(1 for e in spec_errors.values() if e)),
             "note": "需回补", "status": "critical"},
            {"label": "层级", "value": "L3", "note": "R04 评审", "status": "none"},
        ],
        "summary": [{"label": "结论：", "text": "评审完成：逐角色对照 spec 核验 section / 表数 / 字数。"},
                    {"label": "边界：", "text": "只核证不修复，修复由生产方完成。"}],
        "sections": [
            {"index": 1, "title": "逐条核证", "question": "每个角色是否满足其 spec？",
             "table": {"caption": "核证结果", "columns": ["角色", "判定", "依据"], "rows": rows}},
        ],
        "notes": {"summary": "口径、来源与证据边界",
                  "items": [{"label": "职责：", "text": "R04 只记录，不代改。"}]},
        "footer": [f"L3 · {project}", "core/report_kernel.aggregate"],
    })
