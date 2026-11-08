# -*- coding: utf-8 -*-
"""S07 模型卡与资产证据 —— 能力域 7。

整合自 mlflow__mlflow 的模型元数据口径（模型卡：用途/限制/风险/许可）+ 实验
追踪的 artifact（运行产物：模型文件/评估报告/图表）。把「模型卡与资产」转成
确定性校验：模型卡五要素（用途/限制/风险分层/许可/已知偏差）、风险分层白名单、
许可白名单、资产证据（artifact 路径可追溯）、资产与运行绑定。

关键立场：**模型卡是「交付给下游的说明书」，不是营销页**。模型卡必须写清
「不能用来干什么」（限制）与风险分层；资产必须能追溯到产生它的运行。
本角色只产出模型卡与资产证据工件，**不打包分发模型**（分发归 R09 服务集成）。

动作：
  card   模型卡校验
  asset  资产证据校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "modelcard"
DESC = "模型卡与资产证据：card/asset"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("card", "校验模型卡"), ("asset", "校验资产证据")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "card":
        return _validate_card(data)
    if args.action == "asset":
        return _validate_asset(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_card(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["modelcard"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", model_name="", risk_tier="")

    name = str(data.get("model_name", "")).strip()
    checks.append(_ck(bool(name), "模型名非空", "card.model_name"))

    # 用途（intended use）非空
    checks.append(_ck(bool(str(data.get("intended_use", "")).strip()),
                      "声明用途（intended use）", "card.intended_use"))

    # 限制（limitations）非空 —— 模型卡的核心：写清「不能干什么」
    checks.append(_ck(bool(str(data.get("limitations", "")).strip()),
                      "声明限制（limitations）", "card.limitations"))

    # 风险分层白名单
    tier = data.get("risk_tier")
    checks.append(_ck(tier in th["risk_tiers"],
                      f"风险分层={tier!r} 在白名单 {th['risk_tiers']}",
                      "card.risk_tier"))

    # 许可白名单
    lic = data.get("license")
    checks.append(_ck(lic in th["license_types"],
                      f"许可={lic!r} 在白名单 {th['license_types']}",
                      "card.license"))

    # 已知偏差非空（伦理/合规的必填项）
    checks.append(_ck(bool(str(data.get("known_bias", "")).strip()),
                      "声明已知偏差（known bias）", "card.known_bias"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        model_name=name, risk_tier=tier, license_type=lic,
        narrative=f"模型卡 {name}：风险 {tier} / 许可 {lic}")


# --------------------------------------------------------------------------- #
def _validate_asset(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", asset_count=0)

    # 资产清单非空
    assets = data.get("assets") or []
    ok_assets = isinstance(assets, list) and len(assets) > 0
    checks.append(_ck(ok_assets,
                      f"资产 ≥1（实际 {len(assets) if isinstance(assets, list) else 0}）",
                      "asset.count"))

    # 每个资产：路径非空（可定位）
    no_path = [i for i, a in enumerate(assets if isinstance(assets, list) else [])
               if not isinstance(a, dict) or not str(a.get("path", "")).strip()]
    checks.append(_ck(not no_path,
                      f"资产路径非空（缺 {no_path or '无'}）",
                      "asset.path"))

    # 每个资产：绑定 run_id（可追溯到产生它的运行）
    no_run = [i for i, a in enumerate(assets if isinstance(assets, list) else [])
              if not isinstance(a, dict) or not str(a.get("run_id", "")).strip()]
    checks.append(_ck(not no_run,
                      f"资产绑定 run_id（缺 {no_run or '无'}）",
                      "asset.run_binding"))

    # 资产类型声明（模型文件/评估报告/图表）
    bad_type = [a.get("type") for a in (assets if isinstance(assets, list) else [])
                if isinstance(a, dict) and a.get("type") not in
                ("model_file", "eval_report", "chart", "dataset_snapshot", "config")]
    checks.append(_ck(not bad_type,
                      f"资产类型合法（越界 {bad_type or '无'}）",
                      "asset.type"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        asset_count=len(assets) if isinstance(assets, list) else 0,
        narrative=f"资产证据：{len(assets) if isinstance(assets, list) else 0} 项")
