# -*- coding: utf-8 -*-
"""S03 评估数据集与评分器 —— 能力域 3。

整合自 mlflow__mlflow 的 mlflow-evaluation（数据集准备、scorer 设计、judge
对齐、评估运行）+ mlflow-agent-improvement（评分器断言）。把「评估数据集与
评分器」转成确定性校验：评估集结构（inputs/expectations）、评分器类型白名单、
评分器必要字段、反馈来源白名单、评估模式。

关键立场：**评估是「效果看起来不错」进不了上线关卡的唯一钥匙**。评分器必须
有类型 + 必要字段（缺字段 = 评不出来）；数据集必须带 ground truth（expectations）
否则正确性 scorer 无标可对。本角色只产出评估集/评分器/评分规则工件，
**不产出「这个模型好不好」的结论**（结论来自评估运行结果，见 s05 release）。

动作：
  dataset  评估数据集校验
  scorer   评分器校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "evaluation"
DESC = "评估数据集与评分器：dataset/scorer"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("dataset", "校验评估数据集"), ("scorer", "校验评分器")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "dataset":
        return _validate_dataset(data)
    if args.action == "scorer":
        return _validate_scorer(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_dataset(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", dataset_id="", record_count=0)

    ds_id = str(data.get("dataset_id", "")).strip()
    checks.append(_ck(bool(ds_id), "数据集 ID 非空", "dataset.id"))

    records = data.get("records") or []
    ok_records = isinstance(records, list) and len(records) > 0
    checks.append(_ck(ok_records,
                      f"记录 ≥1（实际 {len(records) if isinstance(records, list) else 0}）",
                      "dataset.records"))

    # 每条记录必须有 inputs（预测入参）
    no_input = [i for i, r in enumerate(records if isinstance(records, list) else [])
                if not isinstance(r, dict) or not isinstance(r.get("inputs"), dict)
                or not r["inputs"]]
    checks.append(_ck(not no_input,
                      f"记录含 inputs（缺 {no_input or '无'}）",
                      "dataset.inputs"))

    # ground truth：expectations 非空（正确性 scorer 的标）
    no_exp = [i for i, r in enumerate(records if isinstance(records, list) else [])
              if not isinstance(r, dict) or not isinstance(r.get("expectations"), dict)
              or not r["expectations"]]
    checks.append(_ck(not no_exp,
                      f"记录含 expectations（ground truth，缺 {no_exp or '无'}）",
                      "dataset.expectations"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        dataset_id=ds_id,
        record_count=len(records) if isinstance(records, list) else 0,
        narrative=f"评估集 {ds_id}：{len(records) if isinstance(records, list) else 0} 条记录")


# --------------------------------------------------------------------------- #
def _validate_scorer(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["evaluation"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", scorer_name="")

    name = str(data.get("scorer_name", "")).strip()
    checks.append(_ck(bool(name), "评分器名非空", "scorer.name"))

    # 评分器类型白名单
    stype = data.get("scorer_type")
    checks.append(_ck(stype in th["scorer_types"],
                      f"评分器类型={stype!r} 在白名单 {th['scorer_types']}",
                      "scorer.type"))

    # 评分目标（评什么维度）非空
    checks.append(_ck(bool(str(data.get("target", "")).strip()),
                      "声明评分目标（评什么维度）", "scorer.target"))

    # 评分标准非空（确定性 scorer 或 judge 的判据）
    checks.append(_ck(bool(str(data.get("criteria", "")).strip()),
                      "评分标准非空（判据）", "scorer.criteria"))

    # 反馈来源白名单（评分结果从哪来）
    source = data.get("feedback_source")
    checks.append(_ck(source in th["feedback_sources"],
                      f"反馈来源={source!r} 在白名单 {th['feedback_sources']}",
                      "scorer.feedback_source"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        scorer_name=name, scorer_type=stype, feedback_source=source,
        narrative=f"评分器 {name}：{stype} / 来源 {source}")
