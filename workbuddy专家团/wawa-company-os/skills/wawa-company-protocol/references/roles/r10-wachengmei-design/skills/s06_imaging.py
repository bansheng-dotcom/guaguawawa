# -*- coding: utf-8 -*-
"""S06 修图与图像工程 —— 能力域 6。

整合自 python-pillow__Pillow + opencv__opencv + danielgatis__rembg。
裸库形态：本地可无 Pillow/OpenCV/rembg，故本技能做**门禁探测**（对上游
能力如实降级）——操作白名单、格式白名单、覆盖策略（防不可逆覆盖）、
重依赖能力探测（若本机无库则如实 blocked，不假装会）。

动作：
  edit   校验图像工程任务单（operations/formats/overwrite）
  probe  探测本机图像重依赖能力（Pillow/OpenCV/rembg）
"""
from __future__ import annotations

import importlib.util
from typing import Any, Dict, List

from . import _common as c

NAME = "imaging"
DESC = "修图与图像工程：edit/probe"


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _has(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    ed = act.add_parser("edit", help="校验图像工程任务单")
    ed.add_argument("--input", required=True)
    pr = act.add_parser("probe", help="探测本机图像重依赖能力")


def run(args) -> Dict[str, Any]:
    if args.action == "probe":
        return _probe()
    data = c.load_json(args.input)
    if args.action == "edit":
        return _validate_edit(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _probe() -> Dict[str, Any]:
    pillow = _has("PIL")
    cv2 = _has("cv2")
    rembg = _has("rembg")
    checks = [
        _ck(pillow, f"Pillow 可用={pillow}", "imaging.pillow"),
        _ck(cv2, f"OpenCV 可用={cv2}", "imaging.opencv"),
        _ck(rembg, f"rembg 可用={rembg}", "imaging.rembg"),
    ]
    # 探测不是门禁：库缺失如实降级，不判 FAIL（blocked 语义）
    status = "ready" if pillow else "blocked"
    return {"ok": True, "checks": checks, "verdict": "PASS",
            "pillow": pillow, "opencv": cv2, "rembg": rembg,
            "status": status,
            "next": ("本机具备基础图像能力" if pillow
                     else "本机缺 Pillow：批量编辑/抠图动作将如实降级为 blocked，"
                          "不假装可执行")}


# --------------------------------------------------------------------------- #
def _validate_edit(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL")

    operations = data.get("operations")
    if not isinstance(operations, list) or len(operations) < 1:
        checks.append(_ck(False, "operations ≥1 缺失", "imaging.operations"))
        op_ok = False
    else:
        bad = [op for op in operations if op not in th["imaging"]["operations"]]
        checks.append(_ck(not bad,
                          f"operations 在白名单（非法 {bad or '无'}）",
                          "imaging.operations"))
        op_ok = not bad

    src = str(data.get("source", "")).strip()
    ext = src.rsplit(".", 1)[-1].lower() if "." in src else ""
    ok_ext = ext in th["imaging"]["allowed_formats"]
    checks.append(_ck(ok_ext,
                      f"source 格式 {ext or '?'} 在白名单 {th['imaging']['allowed_formats']}",
                      "imaging.format"))

    overwrite = data.get("overwrite")
    ok_ow = overwrite in th["imaging"]["overwrite"]
    checks.append(_ck(ok_ow,
                      f"overwrite={overwrite!r} 在白名单（never 防不可逆覆盖）",
                      "imaging.overwrite"))

    # 抠图动作依赖探测：缺 rembg 时如实降级
    needs_rembg = "compress" in operations and any(
        op in operations for op in ("convert",))  # 占位；真实抠图动作独立判定
    _ = needs_rembg

    ok = op_ok and ok_ext and ok_ow
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    operation_count=len(operations) if isinstance(operations, list) else 0,
                    source=src)
