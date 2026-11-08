# -*- coding: utf-8 -*-
"""S05 恢复演练 —— 能力域 5。

整合自 restic__restic 的 restore 语义 + 恢复演练纪律：恢复目标（file/
directory/snapshot/config）、定期验证能否恢复文件、配置和关键业务资产。
把「恢复什么、能否恢复、演练证据」转成确定性校验：恢复目标白名单、
恢复结果非空、演练证据（文件数/校验和）实算一致。

关键立场：**备份存在 ≠ 恢复成功**（能力全景 R20 边界原话）。本角色只校验
恢复请求结构与演练记录是否成立，不实际执行 restic restore、不声称
「一定能恢复」（必须演练出证据才算数）。恢复演练必须产出可验证证据，
「声明恢复成功」却无文件数/校验和 = 不可信。

动作：
  restore  恢复请求校验
  drill    恢复演练记录校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "restore"
DESC = "恢复演练：restore/drill"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("restore", "恢复请求校验"), ("drill", "恢复演练记录校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "restore":
        return _validate_restore(data)
    if args.action == "drill":
        return _validate_drill(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_restore(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["restore"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", restore_id="")

    restore_id = str(data.get("restore_id", "")).strip()
    checks.append(_ck(bool(restore_id), "恢复请求 ID 非空", "restore.id"))

    target = data.get("target")
    checks.append(_ck(target in th["restore_targets"],
                      f"恢复目标={target!r} 在白名单 {th['restore_targets']}",
                      "restore.target"))

    # 恢复必须指向真实快照（无源快照 = 凭空恢复）
    snapshot_id = str(data.get("snapshot_id", "")).strip()
    checks.append(_ck(bool(snapshot_id), "源快照 ID 非空", "restore.snapshot"))

    # 恢复是高风险动作，必须带授权/演练声明（红线 2：不擅自恢复生产）
    declared = bool(data.get("authorized")) or bool(data.get("drill")) or \
        bool(str(data.get("approver", "")).strip()) or bool(data.get("handoff"))
    checks.append(_ck(declared,
                      "恢复已声明授权/演练/审批（不擅自恢复生产）",
                      "restore.authorized"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        restore_id=restore_id, target=target,
        narrative=f"恢复请求 {restore_id}：目标 {target}")


# --------------------------------------------------------------------------- #
def _validate_drill(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["restore"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", drill_id="", restored_count=0)

    drill_id = str(data.get("drill_id", "")).strip()
    checks.append(_ck(bool(drill_id), "演练 ID 非空", "drill.id"))

    # 演练结果必须带可验证证据：恢复文件数 > 0 且校验和一致
    restored = c._num(data.get("restored_count"))
    checks.append(_ck(restored > 0,
                      f"恢复文件数 > 0（实际 {restored:g}）", "drill.restored"))

    result = data.get("result")
    checks.append(_ck(result in ("success", "failure"),
                      f"演练结果={result!r} ∈ {{success,failure}}",
                      "drill.result"))

    # 恢复成功必须带校验和一致性证据（声明成功却无 checksum 匹配 = 不可信）
    if result == "success":
        checks.append(_ck(bool(str(data.get("checksum_match", "")).strip())
                           or data.get("checksum_match") is True,
                          "成功演练带校验和一致性证据", "drill.checksum"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        drill_id=drill_id, restored_count=restored, result=result,
        narrative=f"恢复演练 {drill_id}：恢复 {restored:g} 文件，结果 {result}")
