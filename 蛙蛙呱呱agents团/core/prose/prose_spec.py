# -*- coding: utf-8 -*-
"""core.prose.prose_spec —— 每节 11 字段的固定契约（spec 9 + facts 2）。

为什么固定：v3 能写出“机理 + 反方 + 判别 + 停止线”，靠的不是模型自由发挥，
而是每节先把这 11 个字段写死。少一个字段，这一节就会退回三段套话。

    facts.SECTIONS 必填：verdict、question
    prose_specs     必填：fact、evidence、mechanism、alternative、signal、
                          implication、action、stop、boundary
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

FIELDS = ("fact", "evidence", "mechanism", "alternative", "signal",
          "implication", "action", "stop", "boundary")
SECTION_FIELDS = ("verdict", "question")
LABELS = {
    "verdict": "判断", "question": "这一节回答谁的问题",
    "fact": "事实", "evidence": "证据", "mechanism": "机理",
    "alternative": "替代解释", "signal": "判别信号", "implication": "含义",
    "action": "动作", "stop": "停止线", "boundary": "边界",
}
MIN_TEXT = 4


def validate(specs: Dict[str, Dict[str, Any]],
             sections: Iterable[Dict[str, Any]]) -> List[str]:
    """返回问题清单；空列表才算 11 字段齐。"""
    errs: List[str] = []
    secs = list(sections)
    ids = {str(s.get("id") or "") for s in secs}
    unknown = sorted(set(specs) - ids)
    if unknown:
        errs.append("spec 有 facts 里不存在的节：" + "、".join(unknown))
    for s in secs:
        sid = str(s.get("id") or "")
        for f in SECTION_FIELDS:
            if len(str(s.get(f) or "").strip()) < MIN_TEXT:
                errs.append(f"{sid}: facts 缺 {f}（{LABELS[f]}）")
        sp = specs.get(sid)
        if sp is None:
            errs.append(f"{sid}: 缺 spec")
            continue
        for f in FIELDS:
            if len(str(sp.get(f) or "").strip()) < MIN_TEXT:
                errs.append(f"{sid}: spec 缺 {f}（{LABELS[f]}）")
    return errs
