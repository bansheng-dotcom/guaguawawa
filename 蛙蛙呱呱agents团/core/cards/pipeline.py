# -*- coding: utf-8 -*-
"""core.cards.pipeline —— 发卡 / 验卡 / 收卡的单一编排入口（P5-3）。

本模块**只做转发，不实现业务**。实现分别在：

    report_dispatch  发卡（write_plan / issue）、验卡（load_issued / verify_claims）
    card_issue       拆卡五轴（prepare）、老路径入口（bootstrap）、探源卡
    dispatch         收卡合并（collect）

外部调用方（report_cli / preflight）只从这里进；三个实现模块之间的内部调用
保持直接，避免 pipeline ↔ 实现 的循环依赖。

删除条件：`report_dispatch + card_issue + dispatch.collect` 合并为
`cards/pipeline` 单一实现后，本文件升级为唯一实现，三个模块退场。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.cards import card_issue as _card_issue
from core.cards import dispatch as _dispatch
from core.cards import report_dispatch as _report_dispatch


# --------------------------------------------------------------------------- #
# 发卡
# --------------------------------------------------------------------------- #
def write_plan(base: str, confirm: bool = False,
               roster_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """把意图映射成问题→角色计划（不落卡）。"""
    return _report_dispatch.write_plan(base, confirm=confirm,
                                       roster_data=roster_data)


def prepare(project, intent: str = "") -> Dict[str, Any]:
    """拆卡五轴 + 发卡前门禁（S1–S12）。"""
    return _card_issue.prepare(Path(project), intent=intent)


def bootstrap(project, intent: str,
              only: Optional[List[str]] = None) -> Dict[str, Any]:
    """老路径 / 并行调研的统一入口：澄清 → 语义层 → 五轴门禁 → 发卡。"""
    return _card_issue.bootstrap(Path(project), intent, only)


def prepare_probe_cards(project) -> Dict[str, Any]:
    """两段发卡的第一段：给探测层发探源卡。"""
    return _card_issue.prepare_probe_cards(Path(project))


def issue(base: str, only: Optional[List[str]] = None) -> Dict[str, Any]:
    """按已确认的映射表发卡（nonce + 签名）。"""
    return _report_dispatch.issue(base, only=only)


# --------------------------------------------------------------------------- #
# 验卡
# --------------------------------------------------------------------------- #
def load_issued(base: str) -> Optional[Dict[str, Any]]:
    return _report_dispatch.load_issued(base)


def verify_claims(claims: Dict[str, Any], role: str,
                  issued: Dict[str, Any]):
    """一张 claims 是不是这张卡被别人执行出来的。"""
    return _report_dispatch.verify_claims(claims, role, issued)


# --------------------------------------------------------------------------- #
# 收卡
# --------------------------------------------------------------------------- #
def collect(out_dir: str, *args, **kwargs):
    """收卡：归一/去重/冲突/覆盖 + 能力级别，合并成 claims_merged。"""
    return _dispatch.collect(out_dir, *args, **kwargs)
