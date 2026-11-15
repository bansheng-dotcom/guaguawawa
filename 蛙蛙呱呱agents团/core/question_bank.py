# -*- coding: utf-8 -*-
"""core/question_bank —— 把「任务卡 + 数据画像」变成可判定的 brief。

这里**没有题库**：问题由 core.question_derive 按数据形状推导；
主表/主指标由模型写进 focus.json，core.focus_contract 只做规则校验。

  数据画像（扫描 CSV）  → 能问什么
  模型 focus.json       → 该问什么（主表/主指标/主维度）
  本模块                → 拼成 brief：问题、技能命令、判定规则、可推翻条件

没有 focus 也能跑，但 brief 会明确标注「主表未锁定」；
推导不出 3 道题就直接报错，不编题、不套模板。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

MIN_QUESTIONS = 3


def _focus_section(data: str, focus_path: str) -> tuple[Dict[str, Any] | None, str, str]:
    from core.data_profile import profile_dir
    from core.focus_contract import focus_note, load_focus, validate_focus

    prof = profile_dir(data)
    raw = load_focus(focus_path)
    errs = validate_focus(raw, prof)
    if errs:
        raise SystemExit("focus.json 校验失败：" + "；".join(errs))
    table = next(t for t in prof["tables"]
                 if Path(t["file"]).name == raw["table"] or t["file"].endswith(raw["table"]))
    focus = {"table": table, "measure": raw["measure"], "dimension": raw.get("dimension"),
             "reason": raw.get("reason"), "confidence": raw.get("confidence")}
    return focus, focus_note(raw, table), str(raw.get("task_title") or "")


def build_brief(role: str, intent: str, data_dir: str | Path, *,
                max_q: int = 6, focus_path: str | None = None) -> Dict[str, Any]:
    data = str(Path(data_dir).resolve()).replace("\\", "/")

    focus = None
    focus_text = "未提供 focus.json：主表未锁定，按数据画像通用推导。"
    if focus_path:
        focus, focus_text, card_title = _focus_section(data, focus_path)
        intent = intent or card_title or "按模型选定的主表分析"

    from core.question_derive import derive_questions
    derived = derive_questions(role, intent, data)
    if focus:
        ft, fm = focus["table"]["file"], focus["measure"]
        head = [q for q in derived if ft in q["command"]]
        head.sort(key=lambda q: 0 if fm in q["question"] else 1)
        derived = head + [q for q in derived if q not in head]

    if len(derived) < MIN_QUESTIONS:
        raise SystemExit(
            f"可推导的问题只有 {len(derived)} 道（少于 {MIN_QUESTIONS}），不编题。"
            "请提供可推导的数据表（CSV），或用 --focus 指定主表后重试。")

    questions = derived[:max_q]
    return {
        "role": role,
        "subject": intent,
        "_data_dir": data,
        "_origin": "derived",
        "_pool": [q for q in derived[max_q:]],
        "dataset": f"{focus_text} 数据画像推导（{len(questions)} 题）",
        "title": f"{intent}：{len(questions)} 个可判定的问题",
        "standfirst": (f"按数据画像推导出 {len(questions)} 个可判定问题，逐个调用技能验证；"
                       "每步留输入哈希与判定，跑完自动验收。"),
        "doc_type": f"推理驱动报告 · {role.upper()}",
        "meta": ["读者：创始人 / 经营分析",
                 f"意图：{intent}",
                 f"问题数：{len(questions)}（数据推导）",
                 "验收：分级 / 实质 / 字体 / 版式，跑完自动执行"],
        "evidence": [f"{data}/facts.json", f"{data}/derived_metrics.json"],
        "questions": [
            {**{k: v for k, v in q.items()},
             "command": [c.replace("{data}", data) for c in q["command"]]}
            for q in questions
        ],
        "footer": [f"{role.upper()} · 数据画像驱动的推理报告",
                   "core.question_derive → core.reasoning.Trace → core/report_renderer",
                   "生成时间 2026-11-15（Asia/Shanghai）"],
    }
