# -*- coding: utf-8 -*-
"""core.method_params —— 项目侧方法参数（业务词隔离的唯一载体）。

为什么要有它（方案 §3.6 / P1-7）：
    损耗、物流成本、价格单位、品类表、产地标签，本质是**某个项目的数据**，
    不是通用方法的一部分。写在 core 里，换一条业务线就带着上一条的口径走。

约定：
    * 缺参数 → 走通用默认：单位取数据里的、损耗 0、无物流成本；
      报告必须脚注「未提供 method_params」，**不许用某条业务线的默认值顶上**。
    * 项目文件：`<PROJECT>/method_params.yaml`（项目资产，只在项目里）。
    * 团内只放 schema 与默认值，不放任何业务线词。
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = "dsh.method_params/v1"

#: 通用默认：全部中性值；`missing=True` 让报告能写清「未提供参数」
DEFAULT: Dict[str, Any] = {
    "schema": SCHEMA,
    "price_unit": "",            # 空 = 用数据里的单位
    "unit_scales": {},           # {源单位: 换算系数}，如 {"公斤": 0.5}
    "freight": 0.0,
    "loss_default": 0.0,
    "cold_default": 0.0,
    "categories": [],            # [{key, loss, cold, shelf}]
    "origin_ban": [],
    "origin_prefer": {},
    "missing": True,
}

_CURRENT: Dict[str, Any] = copy.deepcopy(DEFAULT)


def _yaml(p: Path) -> Dict[str, Any]:
    try:
        import yaml
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def validate(params: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(params, dict):
        return ["method_params 必须是 dict"]
    if params.get("schema") and params.get("schema") != SCHEMA:
        errs.append("schema 必须是 %s" % SCHEMA)
    for k in ("freight", "loss_default", "cold_default"):
        try:
            if float(params.get(k) or 0) < 0:
                errs.append("%s 不能为负" % k)
        except (TypeError, ValueError):
            errs.append("%s 不是数值" % k)
    us = params.get("unit_scales") or {}
    if not isinstance(us, dict):
        errs.append("unit_scales 必须是对象")
    else:
        for k, v in us.items():
            try:
                float(v)
            except (TypeError, ValueError):
                errs.append("unit_scales.%s 不是数值" % k)
    cats = params.get("categories") or []
    if not isinstance(cats, list):
        errs.append("categories 必须是列表")
    else:
        for i, c in enumerate(cats):
            if not isinstance(c, dict) or not c.get("key"):
                errs.append("categories[%d] 缺 key" % i)
    return errs


def load(project_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """读项目方法参数；文件不存在返回默认（missing=True）。"""
    out = copy.deepcopy(DEFAULT)
    if not project_dir:
        return out
    p = Path(project_dir) / "method_params.yaml"
    if not p.is_file():
        return out
    got = _yaml(p)
    if not got:
        return out
    out.update(got)
    out["missing"] = False
    out["source"] = str(p)
    return out


def configure(project_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """切换当前生效的参数（返回新参数，便于调用方写脚注）。"""
    global _CURRENT
    _CURRENT = load(project_dir)
    return _CURRENT


def current() -> Dict[str, Any]:
    return _CURRENT


def reset() -> None:
    global _CURRENT
    _CURRENT = copy.deepcopy(DEFAULT)


def footnote(params: Optional[Dict[str, Any]] = None) -> str:
    """报告脚注：参数从哪来。缺参数时必须出现（不许静默用默认值）。"""
    p = params if params is not None else _CURRENT
    if p.get("missing"):
        return ("未提供 method_params：损耗按 0、物流成本按 0、单位按数据原样显示；"
                "以上为通用默认，不是本项目的真实口径。")
    return "方法参数来自 %s。" % (p.get("source") or "项目 method_params.yaml")
