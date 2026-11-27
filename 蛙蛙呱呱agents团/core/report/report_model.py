# -*- coding: utf-8 -*-
"""core/report_model —— 报告系统的单一模型（语义层）与引用完整性审计。

问题不是「再加一条产线」，而是系统里同时存在五套部分重叠的词汇表：
    81 个问题 / 23 个维度 / 57 个方法 / 48 个图型 / 20 个角色报告规格
它们各自的配置文件也大多没接线（chart_type_by_question.json、report_policy.yaml、
role_report_specs.json 在 Python 里 0 引用）。

本模块把「问题 → 维度 → 方法 → 图型」连成一张可审计的图，回答三件事：
    1. 有没有孤儿（问题挂空维度、维度挂空方法、方法没人用）；
    2. 有没有悬空引用（配置文件写了但代码不读）；
    3. 一个业务域要接入，实际要改几处。

用法：
    python -m core.report.report_model --audit
    python -m core.report.report_model --json workspace/report_model.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from core.charts import chart_capabilities
from core import methods

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs"


def _chart_config() -> Dict[str, Any]:
    """P4：选图配置已换成按「数据关系」组织的 chart_by_relation.yaml。

    旧的 chart_type_by_question.json（84 条「问题→图型」）已归档到 _attic/：
    它与决策契约的对照类型不同构，属于第 6 套词汇表。
    """
    p = CONFIG / "chart_by_relation.yaml"
    if not p.exists():
        return {}
    try:
        import yaml
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}
    return {k: v for k, v in (doc.get("relations") or {}).items() if isinstance(v, dict)}


def _relation_charts() -> Dict[str, List[str]]:
    return {k: list(v.get("allowed") or []) for k, v in _chart_config().items()}


def _role_specs() -> Dict[str, Any]:
    p = CONFIG / "role_report_specs.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def build() -> Dict[str, Any]:
    reg = methods.REGISTRY
    charts = chart_capabilities.CATALOG

    method_keys = set(reg)
    chart_keys = {c["key"] for c in charts}
    chart_cfg = _chart_config()

    nodes = {
        "methods": len(reg),
        "charts": len(charts),
        "roles": len(__import__("core.base.registry", fromlist=["ROLES"]).ROLES),
        "chart_config": len(chart_cfg),
    }

    # 当前：静态维度层与静态题库已退场。调研要查什么由 core/research_protocol
    # 按任务动态生成，不再有一份固定清单可以「悬空」或「漏挂」。
    # 4) 图型配置：是否真的被选图代码读取（P4：decision 已读 chart_by_relation.yaml）
    from core import decision as _decision
    chart_cfg_types = {t for ts in _relation_charts().values() for t in ts}
    charts_unconfigured = sorted(chart_keys - chart_cfg_types - {"table_only"})
    policy_source = str(getattr(_decision, "CHART_POLICY_SOURCE", ""))
    read_by_code = (policy_source == "chart_by_relation.yaml")
    # 6) 角色规格里的 section 有没有对应图型规则
    role_secs = {s for v in _role_specs().values() for s in (v.get("sections") or [])}
    relation_keys = set(_relation_charts())
    role_secs_orphan = sorted(s for s in role_secs if s not in relation_keys)

    return {
        "schema": "dsh.report_model/v1",
        "nodes": nodes,
        "integrity": {
            "chart_config_keys": len(chart_cfg_types),
            "chart_config_read_by_code": read_by_code,
            "chart_types_not_in_config": charts_unconfigured,
            "role_sections_without_chart_rule": role_secs_orphan,
        },
        "wiring": {
            "chart_by_relation.yaml": (f"被 core/decision.py 读取（source={policy_source}）"
                                      if read_by_code else "未被读取"),
            "chart_type_by_question.json": "已归档到 _attic/（第 6 套词汇表，不再使用）",
            "report_policy.yaml": "0 处 Python 引用（P5 接门禁阈值）",
            "role_report_specs": "0 处 Python 引用（仅本模块读取）",
        },
    }


def audit() -> Dict[str, Any]:
    m = build()
    i = m["integrity"]
    issues = {
        "图型配置未被代码读取": 0 if i["chart_config_read_by_code"] else i["chart_config_keys"],
        "图型未进配置": len(i["chart_types_not_in_config"]),
        "角色章节无图型规则": len(i["role_sections_without_chart_rule"]),
    }
    m["issues"] = issues
    m["ok"] = sum(issues.values()) == 0
    return m


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="report_model")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    m = audit() if a.audit else build()
    if a.json:
        p = Path(a.json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {p}")
    print(json.dumps({k: m[k] for k in ("nodes", "issues") if k in m}
                     | {"integrity": {k: (len(v) if isinstance(v, (list, dict)) else v)
                                      for k, v in m["integrity"].items()}},
                     ensure_ascii=False, indent=2))
    return 0 if m.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
