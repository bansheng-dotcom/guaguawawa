# -*- coding: utf-8 -*-
"""core.report.report_ir —— 富语义 IR（dsh.report_ir/v1）。SOP v3.0 S0 的锚点。

中心：作者只交「事实 + 问题 + 大纲」，系统做其余。
本模块定义 IR 的字段契约与 validate()：parse-time 字段级报错，不靠运行时崩溃。

关系（复用已有资产，不重造）：
  - Fact         ≈ data_model.Row 的干净投影（+ derived_from 派生边）
  - ChartIntent  ≈ chart_contract.normalize 的产物（relation/intent/chosen/dims）
  - 溯源         = fact.source + fact.derived_from 内在边，不建全局账
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

IR_SCHEMA = "dsh.report_ir/v1"

REQUIRED_META = ("title", "audience")
REQUIRED_FACT = ("id", "metric", "value", "unit")
FACT_KEYS = ("id", "metric", "entity", "period", "value", "unit",
             "source", "derived_from", "history")
REQUIRED_SOURCE = ("file",)
SOURCE_KEYS = ("file", "kind", "title", "org", "url", "grade", "quote")
REQUIRED_SECTION = ("title", "question", "outline")
SECTION_KEYS = ("title", "question", "outline", "readings", "actions",
                "boundary", "falsifier", "chart")
READING_ELEMENTS = ("事实", "机理", "反例", "信号", "所以")

# 图表意图 → relation 的弱推断（种子：从 question 推断，作者可覆盖）
# 关系名必须与 configs/chart_by_relation.yaml 的九类关系一致（单一出处）
_INTENT_HINTS = (
    ("change_over_time", ("趋势", "走势", "变化", "增长", "下降", "环比", "同比", "逐月", "周期")),
    ("composition", ("占比", "构成", "份额", "结构", "比例")),
    ("deviation", ("价差", "高于", "低于", "差距", "偏离")),
    ("ranking", ("排名", "最贵", "最便宜", "最高", "最低", "第几", "哪个最", "排序")),
    ("correlation", ("相关", "伴随", "联动")),
    ("distribution", ("分布", "区间", "波动", "离散", "极值")),
)


def infer_relation(question: str, dims: Optional[List[Dict[str, Any]]] = None) -> str:
    """从问题文本 + 数据形状弱推断 relation。作者可显式覆盖。

    这是 SOP §5「自动选型」的根解种子：意图在问题里，不在单独字段里。
    与 HCI「推荐器看不到意图」不矛盾——这里读的是 question 文本，不是字段类型。
    """
    q = str(question or "")
    for rel, keys in _INTENT_HINTS:
        if any(k in q for k in keys):
            return rel
    dims = dims or []
    names = {d.get("name") for d in dims}
    if "period" in names:
        return "change_over_time"
    if "entity" in names:
        return "ranking"
    return "magnitude"


def validate(ir: Dict[str, Any]) -> List[str]:
    """parse-time 字段级校验。返回错误清单（空 = 合法）。"""
    errs: List[str] = []
    if not isinstance(ir, dict):
        return ["IR 必须是 dict"]
    if ir.get("schema") != IR_SCHEMA:
        errs.append(f"schema 必须是 {IR_SCHEMA}（当前 {ir.get('schema')!r}）")

    meta = ir.get("meta") or {}
    for k in REQUIRED_META:
        if not str(meta.get(k) or "").strip():
            errs.append(f"meta 缺 {k}")

    facts = ir.get("facts") or []
    if not facts:
        errs.append("facts 为空")
    seen: set = set()
    for i, f in enumerate(facts):
        if not isinstance(f, dict):
            errs.append(f"facts[{i}] 不是 dict")
            continue
        fid = str(f.get("id") or "")
        if not fid:
            errs.append(f"facts[{i}] 缺 id")
        elif fid in seen:
            errs.append(f"facts[{i}].id 重复: {fid}")
        seen.add(fid)
        for k in REQUIRED_FACT:
            if f.get(k) in (None, ""):
                errs.append(f"facts[{i}] 缺 {k}")
        if "value" in f and not isinstance(f.get("value"), (int, float)):
            errs.append(f"facts[{i}].value 不是数字: {f.get('value')!r}")
        # 溯源：source 缺失告警（不强拦，允许后续补）
        if not f.get("source"):
            errs.append(f"facts[{i}] 缺 source（溯源边断裂）")
        # derived_from 若给，必须是 list
        if f.get("derived_from") is not None and not isinstance(f.get("derived_from"), list):
            errs.append(f"facts[{i}].derived_from 必须是 list")

    # sources：溯源边的另一端；fact.source 应指向合法 source.file
    sources = ir.get("sources") or []
    src_ids = set()
    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            errs.append(f"sources[{i}] 不是 dict")
            continue
        fid = str(s.get("file") or "")
        if not fid:
            errs.append(f"sources[{i}] 缺 file")
        else:
            src_ids.add(fid)
    if src_ids:
        for f in facts:
            src = str(f.get("source") or "")
            if src and src not in src_ids:
                errs.append(f"fact {f.get('id')} 的 source 指向不存在的来源: {src}")

    sections = ir.get("sections") or []
    if not sections:
        errs.append("sections 为空")
    for i, s in enumerate(sections):
        if not isinstance(s, dict):
            errs.append(f"sections[{i}] 不是 dict")
            continue
        for k in REQUIRED_SECTION:
            if not str(s.get(k) or "").strip():
                errs.append(f"sections[{i}] 缺 {k}")
        chart = s.get("chart") or {}
        if chart:
            # data_refs 应指向 facts；chosen 应可被 relation 校验（S5 做）
            for ref in (chart.get("data_refs") or []):
                if ref not in seen:
                    errs.append(f"sections[{i}].chart.data_refs 指向不存在的 fact: {ref}")
        # 注：文案五要素（事实/机理/反例/信号/所以）是 S5 文案门禁的事，
        # 不是 IR schema 的事——这里不查，避免把"结构校验"和"内容完整度"混为一谈。

    return errs
