# -*- coding: utf-8 -*-
"""拆卡线的 bundle 组装（卡信封 + expert_brief）。

**为什么单独一个模块**：`report_dispatch` 属于报告产线（`core/report_*.py`），
按隔离红线它不能 import 知识库。拆卡是「把意图变成卡」的编排动作，不是报告
渲染，因此把 bundle 组装下沉到这里，report_dispatch 只拿结果、不碰 brief。

对外只有 `issue()`：写 `<card_dir>/bundle.json`，返回问题清单。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.base import project as _project
from shared.knowledge import brief as _brief


def issue(card_dir: Path | str, role: str, task_id: str, question: str,
          root: Path | str | None = None, task_type: Optional[str] = None,
          skills: Optional[List[str]] = None,
          non_goals: Optional[List[str]] = None) -> Dict[str, Any]:
    """在 card_dir 生成 CardBundle；root 指向项目根时 brief 另落 project/briefs。"""
    proj = _project.load(root) if root is not None else None
    return _brief.issue_bundle(
        card_dir, role, task_id, question, project=proj,
        task_type=task_type, skills=skills, non_goals=non_goals)
