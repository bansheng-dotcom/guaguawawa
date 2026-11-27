# -*- coding: utf-8 -*-
"""core.claims.contract —— 合并后 claims 文档的契约单一出处（P5-1）。

为什么集中：`claims`（论证层 + 映射层，原 `claims_v4` 已并入）、
`cells_claims`（按格交）、`claim_consistency`（交叉质询）各自写过一遍
字段名与契约版本。
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

#: 历史卡片的落盘 schema（v2 按卡交）：只做读入识别，新写盘不再产出
LEGACY_SCHEMA = "dsh.claims/v2"

#: 判断格 schema（cell_claim）：与 claims 文档同一处声明，防止两处漂移
CELL_SCHEMA = "dsh.cell_claim/v1"

#: 两条产出路径的契约版本：v2 = card_spec 按卡交；v3 = 按格交
#: P5-4（2026-11-27）：统一发 v4；v2/v3 只作为历史卡片的读入版本。
CONTRACT = "v4"
LEGACY_CONTRACTS = ("v2", "v3")

#: 需要走严格结构门禁的版本（缺省/未知版本不追溯）
STRICT_CONTRACTS = LEGACY_CONTRACTS + (CONTRACT,)


def is_strict(doc: Dict[str, Any]) -> bool:
    """这张卡是否按新结构契约收：v2/v3/v4 都要，旧的无版本卡不追溯。"""
    return (str(doc.get("schema") or "") == LEGACY_SCHEMA
            or str(doc.get("contract") or "") in STRICT_CONTRACTS)

#: 顶层键（报告产线读的只有这些）
TOP_KEYS = ("numbers", "sources", "sections", "standfirst",
            "boundaries", "conflicts")

#: 每张卡都必须有的顶层键（P5-4：两种交付形态同一形状）
#: 层专属字段（cells / datasets / claims / contract_gaps）不在此列，按输入可有可无。
CARD_KEYS = ("schema", "contract", "layer", "role", "dispatch", "meta",
             "numbers", "sources", "sections", "unanswered", "boundaries",
             "explore")

#: 每条数字必须有的字段（P5-4：按格交与按卡交出同一套）
NUMBER_KEYS = ("id", "name", "value", "unit", "entity", "period",
               "measure_id", "grain_id", "caliber", "value_from",
               "source_file", "grade")

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
