# -*- coding: utf-8 -*-
"""core.cards.pipeline —— 发卡 / 验卡 / 收卡的唯一对外入口（P5-3，2026-11-27 转正）。

外部（report_cli / preflight / 文档示例）只从这里进，实现仍在：
    report_dispatch  发卡（write_plan / issue）、验卡（load_issued / verify_claims）
    card_issue       拆卡五轴（prepare）、老路径入口（bootstrap）、探源卡
    card_probe       探源可行性（probe）、降级格读取（degraded_cells）
    dispatch         收卡合并（collect）

三个实现模块之间的内部调用保持直接，避免 pipeline ↔ 实现 的循环依赖。

删除条件：`report_dispatch + card_issue + dispatch.collect` 的实现逐文件搬入
本模块后，三个模块退场；在此之前只许新增转发，不许另建第二个外部入口。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.cards import card_issue as _card_issue
from core.cards import card_probe as _card_probe
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


def probe(project, mode: str = "report",
          sources: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """探源可行性测试；mode=degrade 时同时更新 grid.json。"""
    return _card_probe.probe(str(project), mode=mode, sources=sources)


def degraded_cells(project) -> List[Dict[str, Any]]:
    """采集后/报告前读降级结果，供 report_flow 保留空节。"""
    return _card_probe.degraded_cells(str(project))


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
