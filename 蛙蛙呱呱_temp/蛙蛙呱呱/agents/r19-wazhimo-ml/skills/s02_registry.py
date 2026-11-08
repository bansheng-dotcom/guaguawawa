# -*- coding: utf-8 -*-
"""S02 模型注册与版本 —— 能力域 2。

整合自 mlflow__mlflow 的 Model Registry 口径：候选模型、版本、阶段（stage）与
元数据管理。把「模型注册与版本」转成确定性校验：阶段白名单（none/staging/
production/archived）、版本号格式、来源声明、元数据完整、阶段迁移不越权。

关键立场：**注册 ≠ 部署**。候选模型登记到 registry 只是「候选入库」，
`production` 阶段是发布证据链的一环，不代表已上线。本角色只管理候选模型与
版本，**不把注册等同于生产部署**（边界：模型权重/推理服务另行准备）。

动作：
  register  模型注册记录校验
  version   模型版本清单校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "registry"
DESC = "模型注册与版本：register/version"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("register", "校验模型注册记录"), ("version", "校验模型版本清单")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "register":
        return _validate_register(data)
    if args.action == "version":
        return _validate_version(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_register(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["registry"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", model_name="")

    name = str(data.get("model_name", "")).strip()
    checks.append(_ck(bool(name), "模型名非空", "register.name"))

    # 版本号非空（registry 必填）
    version = str(data.get("version", "")).strip()
    checks.append(_ck(bool(version), "版本号非空", "register.version"))

    # 阶段白名单
    stage = data.get("stage")
    checks.append(_ck(stage in th["stages"],
                      f"阶段={stage!r} 在白名单 {th['stages']}",
                      "register.stage"))

    # 来源声明（模型从哪来，可追溯）
    source = data.get("source")
    checks.append(_ck(source in th["model_sources"],
                      f"来源={source!r} 在白名单 {th['model_sources']}",
                      "register.source"))

    # 元数据：run_id 关联（候选模型须绑定产生它的实验运行）
    checks.append(_ck(bool(str(data.get("run_id", "")).strip()),
                      "绑定 run_id（可追溯到实验运行）", "register.run_id"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        model_name=name, version=version, stage=stage,
        narrative=f"模型 {name} v{version}：阶段 {stage}")


# --------------------------------------------------------------------------- #
def _validate_version(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["registry"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", model_name="", version_count=0)

    name = str(data.get("model_name", "")).strip()
    checks.append(_ck(bool(name), "模型名非空", "version.name"))

    versions = data.get("versions") or []
    ok_versions = isinstance(versions, list) and len(versions) > 0
    checks.append(_ck(ok_versions,
                      f"版本 ≥1（实际 {len(versions) if isinstance(versions, list) else 0}）",
                      "version.count"))

    # 每个版本：版本号 + 阶段白名单
    bad = [v.get("version") for v in (versions if isinstance(versions, list) else [])
           if not isinstance(v, dict) or not str(v.get("version", "")).strip()
           or v.get("stage") not in th["stages"]]
    checks.append(_ck(not bad,
                      f"版本号非空且阶段在白名单（越界 {bad or '无'}）",
                      "version.valid"))

    # 版本号唯一
    vnums = [str(v.get("version", "")) for v in (versions if isinstance(versions, list) else [])
             if isinstance(v, dict)]
    checks.append(_ck(len(vnums) == len(set(vnums)) and all(x.strip() for x in vnums),
                      "版本号唯一", "version.unique"))

    # 至多一个 production（不能同时两个生产版本）
    prod = [v for v in (versions if isinstance(versions, list) else [])
            if isinstance(v, dict) and v.get("stage") == "production"]
    checks.append(_ck(len(prod) <= 1,
                      f"production 阶段 ≤1（实际 {len(prod)}）",
                      "version.single_prod"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        model_name=name,
        version_count=len(versions) if isinstance(versions, list) else 0,
        narrative=f"模型 {name} 版本清单：{len(versions) if isinstance(versions, list) else 0} 个")
