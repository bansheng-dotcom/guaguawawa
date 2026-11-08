# -*- coding: utf-8 -*-
"""S01 实验追踪 —— 能力域 1。

整合自 mlflow__mlflow 的 mlflow-onboarding（实验/用例类型判定）与 MLflow
Tracking 口径：实验记录参数/指标/工件/运行环境，`experimentKind` 标签区分
GenAI 与经典 ML 用例。把「实验追踪」转成确定性校验：实验类型白名单、
用例类型白名单、指标记录完整性、运行环境声明。

关键立场：**实验必须可复现**。参数/指标/环境缺一不可——缺了就无法追溯
「这个结果是哪次运行、什么配置跑出来的」。本角色只产出实验记录工件，
**不把实验追踪等同于生产部署**（边界：模型权重/推理服务/GPU 另行准备）。

动作：
  experiment  实验记录校验（参数/指标/工件/环境）
  run         单次运行记录校验（指标完整性 + 环境可复现）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "tracking"
DESC = "实验追踪：experiment/run"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("experiment", "校验实验记录"), ("run", "校验单次运行记录")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "experiment":
        return _validate_experiment(data)
    if args.action == "run":
        return _validate_run(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_experiment(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["tracking"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", experiment_id="")

    exp_id = str(data.get("experiment_id", "")).strip()
    checks.append(_ck(bool(exp_id), "实验 ID 非空", "experiment.id"))

    name = str(data.get("name", "")).strip()
    checks.append(_ck(bool(name), "实验名非空", "experiment.name"))

    # 用例类型白名单：GenAI 或经典 ML（mlflow-onboarding 二选一）
    use_case = data.get("use_case")
    checks.append(_ck(use_case in th["use_cases"],
                      f"用例类型={use_case!r} 在白名单 {th['use_cases']}",
                      "experiment.use_case"))

    # 实验类型标签（mlflow.experimentKind）
    kind = data.get("experiment_kind")
    checks.append(_ck(kind in th["experiment_kinds"],
                      f"实验类型={kind!r} 在白名单 {th['experiment_kinds']}",
                      "experiment.kind"))

    # 实验必须声明追踪后端（tracking_uri），否则无法复现
    checks.append(_ck(bool(str(data.get("tracking_uri", "")).strip()),
                      "声明 tracking_uri（可复现后端）", "experiment.tracking_uri"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        experiment_id=exp_id, use_case=use_case, experiment_kind=kind,
        narrative=f"实验 {name}（{exp_id}）：{use_case} / {kind}")


# --------------------------------------------------------------------------- #
def _validate_run(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", run_id="", metric_count=0)

    run_id = str(data.get("run_id", "")).strip()
    checks.append(_ck(bool(run_id), "运行 ID 非空", "run.id"))

    # 实验归属非空
    checks.append(_ck(bool(str(data.get("experiment_id", "")).strip()),
                      "运行归属实验非空", "run.experiment_id"))

    # 指标记录非空（追踪的核心：至少记录一个指标）
    metrics = data.get("metrics") or {}
    ok_metrics = isinstance(metrics, dict) and len(metrics) > 0
    checks.append(_ck(ok_metrics,
                      f"指标 ≥1（实际 {len(metrics) if isinstance(metrics, dict) else 0}）",
                      "run.metrics"))

    # 指标值必须为数值（否则无法比较/排序）
    bad_metric = [k for k, v in (metrics if isinstance(metrics, dict) else {}).items()
                  if not isinstance(v, (int, float)) or isinstance(v, bool)]
    checks.append(_ck(not bad_metric,
                      f"指标值为数值（非数值 {bad_metric or '无'}）",
                      "run.metric_numeric"))

    # 运行环境声明（可复现：框架/版本/参数）
    params = data.get("params") or {}
    checks.append(_ck(isinstance(params, dict) and len(params) > 0,
                      f"参数 ≥1（实际 {len(params) if isinstance(params, dict) else 0}）",
                      "run.params"))
    checks.append(_ck(bool(str(data.get("environment", "")).strip()),
                      "声明运行环境（框架/版本）", "run.environment"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        run_id=run_id,
        metric_count=len(metrics) if isinstance(metrics, dict) else 0,
        param_count=len(params) if isinstance(params, dict) else 0,
        narrative=f"运行 {run_id}：{len(metrics) if isinstance(metrics, dict) else 0} 指标")
