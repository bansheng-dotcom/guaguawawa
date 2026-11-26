# -*- coding: utf-8 -*-
"""core.claims.contract —— 合并后 claims 文档的契约单一出处（P5-1）。

为什么集中：`claims_v4`（映射层）、`cells_claims`（按格交）、
`claim_consistency`（交叉质询）各自写过一遍字段名与契约版本。
字段一改，三处就会悄悄错位；这里只放**常量与纯读法**，不放业务逻辑。

约定：
    - 本模块不 import 任何其它 core 模块，避免循环；
    - 所有函数只做 `.get(...)` 归一，不修改入参、不补默认值；
    - 产物 JSON 逐字节不变：调用方只是用这里的常量替换字面量。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

#: 合并后 claims 文档的 schema（cells_claims / report_flow 共用）
SCHEMA = "dsh.agent.claims/v1"

#: 两条产出路径的契约版本：v2 = card_spec 按卡交；v3 = 按格交
CONTRACT_CARD = "v2"
CONTRACT_CELLS = "v3"

#: 顶层键（报告产线读的只有这些）
TOP_KEYS = ("numbers", "sources", "sections", "standfirst",
            "boundaries", "conflicts")

#: 数字条目必读字段（派生量另走 derived，不在此列）
NUMBER_FIELDS = ("id", "name", "value", "unit", "period",
                 "source_file", "quote", "grade", "falsifier", "boundary")

#: 来源条目必读字段
SOURCE_FIELDS = ("file", "grade")

#: 节条目必读字段
SECTION_FIELDS = ("title", "question", "answers", "refs",
                  "boundary", "reading", "chart", "falsifier")

#: 口径冲突登记字段
CONFLICT_FIELDS = ("name", "reason")


def numbers(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(doc.get("numbers") or [])


def sources(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(doc.get("sources") or [])


def sections(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(doc.get("sections") or [])


def boundaries(doc: Dict[str, Any]) -> List[Any]:
    return list(doc.get("boundaries") or [])


def conflicts(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(doc.get("conflicts") or [])


def grades(doc: Dict[str, Any]) -> Dict[str, str]:
    """来源等级表：file → S/A/B/C/D（缺省 C，大写）。"""
    return {str(s.get("file")): str(s.get("grade") or "C").upper()
            for s in sources(doc)}


def norm_name(name: Any) -> str:
    """指标名归一：去空白、下划线、括号与间隔符，用于跨来源对齐。"""
    return re.sub(r"[\s_（）()：:·]", "", str(name or ""))
