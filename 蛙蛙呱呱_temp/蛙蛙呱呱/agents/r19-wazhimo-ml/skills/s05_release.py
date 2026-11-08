# -*- coding: utf-8 -*-
"""S05 回归与发布候选 —— 能力域 5。

整合自 mlflow__mlflow 的 mlflow-agent-improvement（EXPLORE→PLAN→IMPLEMENT→
VERIFY 四步、回归测试、fail-before/pass-after、诊断层）+ mlflow-evaluation
（advanced-evaluation 的版本比较）。把「回归与发布候选」转成确定性校验：
新旧版本比较、诊断层白名单、回归测试 fail-before/pass-after、发布候选三裁决
（PASS/BLOCK/NEEDS_REVIEW）、证据链完整。

关键立场：**「效果看起来不错」不能直接上线**（R19 定位核心）。回归必须证明
「旧版失败、新版通过」；发布候选必须给出三裁决之一 + 证据，不许「凭感觉放行」。
本角色只产出回归报告与发布候选工件，**不把发布候选等同于生产部署**。

动作：
  regression  回归报告校验（fail-before/pass-after）
  candidate   发布候选校验（三裁决 + 证据）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "release"
DESC = "回归与发布候选：regression/candidate"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("regression", "校验回归报告"), ("candidate", "校验发布候选")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "regression":
        return _validate_regression(data)
    if args.action == "candidate":
        return _validate_candidate(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_regression(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["release"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", candidate_id="", check_count=0)

    cid = str(data.get("candidate_id", "")).strip()
    checks.append(_ck(bool(cid), "候选 ID 非空", "regression.candidate_id"))

    # 诊断层白名单（mlflow-agent-improvement 六类根因）
    layer = data.get("diagnosis_layer")
    checks.append(_ck(layer in th["diagnosis_layers"],
                      f"诊断层={layer!r} 在白名单 {th['diagnosis_layers']}",
                      "regression.diagnosis_layer"))

    # 新旧版本比较：必须有 old/new 版本号
    old_v = str(data.get("old_version", "")).strip()
    new_v = str(data.get("new_version", "")).strip()
    checks.append(_ck(bool(old_v) and bool(new_v),
                      f"声明新旧版本（old={old_v or '?'} / new={new_v or '?'}）",
                      "regression.versions"))

    # fail-before / pass-after 是回归的核心证据
    checks.append(_ck(data.get("fail_before") is True,
                      f"回归证明旧版失败（fail_before={data.get('fail_before')!r}）",
                      "regression.fail_before"))
    checks.append(_ck(data.get("pass_after") is True,
                      f"回归证明新版通过（pass_after={data.get('pass_after')!r}）",
                      "regression.pass_after"))

    # 现有测试不回退（不破坏已有行为）
    checks.append(_ck(data.get("existing_green") is True,
                      f"既有测试不回退（existing_green={data.get('existing_green')!r}）",
                      "regression.existing_green"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        candidate_id=cid, diagnosis_layer=layer,
        check_count=len(checks),
        narrative=f"回归 {cid}：{old_v} → {new_v}（fail-before / pass-after）")


# --------------------------------------------------------------------------- #
def _validate_candidate(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["release"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", candidate_id="")

    cid = str(data.get("candidate_id", "")).strip()
    checks.append(_ck(bool(cid), "候选 ID 非空", "candidate.id"))

    # 三裁决白名单
    verdict = data.get("verdict")
    checks.append(_ck(verdict in th["verdicts"],
                      f"发布裁决={verdict!r} 在白名单 {th['verdicts']}",
                      "candidate.verdict"))

    # 证据链：必须挂评估/回归结果（不许「凭感觉放行」）
    evidence = data.get("evidence") or []
    ok_evidence = isinstance(evidence, list) and len(evidence) > 0
    checks.append(_ck(ok_evidence,
                      f"证据 ≥1（实际 {len(evidence) if isinstance(evidence, list) else 0}）",
                      "candidate.evidence"))

    # 若裁决为 PASS，必须有回归证据且无 BLOCK（不许「效果不错」直接放行）
    if verdict == "PASS":
        checks.append(_ck(bool(str(data.get("regression_id", "")).strip()),
                          "PASS 裁决须挂回归报告", "candidate.regression_required"))
    else:
        checks.append(_ck(True, f"{verdict} 裁决不强制挂回归", "candidate.regression_required"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict=verdict if ok else "FAIL",
        candidate_id=cid,
        narrative=f"发布候选 {cid}：裁决 {verdict}，"
                  f"{len(evidence) if isinstance(evidence, list) else 0} 条证据")
