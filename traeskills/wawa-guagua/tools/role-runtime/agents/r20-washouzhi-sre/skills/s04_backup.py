# -*- coding: utf-8 -*-
"""S04 加密增量备份 —— 能力域 4。

整合自 restic__restic：仓库（repository）、快照（snapshot）、保留策略
（keep_last/keep_hourly/keep_daily/keep_weekly/keep_monthly/keep_yearly）、
加密仓、排除规则、增量去重。把「备份什么、存哪里、怎么保留、怎么加密」
转成确定性校验：仓库非空、快照 ≥1、保留策略白名单、加密声明、排除规则
结构合法。

关键立场：**备份仓是「恢复的地基」不是「占空间的副本」**。本角色只校验
备份仓与快照清单结构是否成立，不实际执行 restic 备份、不持有仓库密码
（红线 1：凭据绝不出现在产出）。加密是备份的硬要求，未声明加密的备份仓
不可信。

动作：
  backup   备份仓结构校验
  snapshot 快照清单/保留策略校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "backup"
DESC = "加密增量备份：backup/snapshot"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("backup", "备份仓结构校验"), ("snapshot", "快照清单校验")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "backup":
        return _validate_backup(data)
    if args.action == "snapshot":
        return _validate_snapshot(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_backup(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["backup"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", repo="", snapshot_count=0)

    repo = str(data.get("repo", "")).strip()
    checks.append(_ck(bool(repo), "备份仓路径非空", "backup.repo"))

    # 加密是硬要求（restic 默认加密，未声明 = 不可信）
    encrypted = data.get("encrypted")
    checks.append(_ck(encrypted is True,
                      f"备份仓已声明加密（encrypted={encrypted!r}）",
                      "backup.encrypted"))

    # 排除规则结构合法（每项为字符串，避免误排整个目录）
    excludes = data.get("excludes") or []
    ok_exc = isinstance(excludes, list)
    bad_exc = [e for e in (excludes if isinstance(excludes, list) else [])
               if not isinstance(e, str) or not str(e).strip()]
    checks.append(_ck(ok_exc and not bad_exc,
                      f"排除规则为字符串列表（非法 {bad_exc or '无'}）",
                      "backup.excludes"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        repo=repo, snapshot_count=0,
        encrypted=encrypted is True,
        narrative=f"备份仓 {repo}：加密={encrypted is True}")


# --------------------------------------------------------------------------- #
def _validate_snapshot(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["backup"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", repo="", snapshot_count=0)

    repo = str(data.get("repo", "")).strip()
    checks.append(_ck(bool(repo), "备份仓路径非空", "snapshot.repo"))

    snapshots = data.get("snapshots") or []
    ok_snap = isinstance(snapshots, list) and len(snapshots) >= c._num(th.get("min_snapshots", 1))
    checks.append(_ck(ok_snap,
                      f"快照 ≥{c._num(th.get('min_snapshots', 1)):g}（实际 "
                      f"{len(snapshots) if isinstance(snapshots, list) else 0}）",
                      "snapshot.count"))

    # 每快照须含 snapshot_id/ts
    bad = [i for i, s in enumerate(snapshots if isinstance(snapshots, list) else [])
           if not isinstance(s, dict)
           or not str(s.get("snapshot_id", "")).strip()
           or not str(s.get("ts", "")).strip()]
    checks.append(_ck(not bad,
                      f"快照含 snapshot_id/ts（缺 {bad or '无'}）",
                      "snapshot.required"))

    # 快照 id 唯一
    ids = [s.get("snapshot_id") for s in (snapshots if isinstance(snapshots, list) else [])
           if isinstance(s, dict)]
    checks.append(_ck(len(ids) == len(set(ids)),
                      "快照 ID 唯一", "snapshot.unique"))

    # 保留策略白名单
    policy = data.get("retention_policy")
    if policy is not None:
        checks.append(_ck(policy in th["retention_policies"],
                          f"保留策略={policy!r} 在白名单 {th['retention_policies']}",
                          "snapshot.policy"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        repo=repo, snapshot_count=len(snapshots) if isinstance(snapshots, list) else 0,
        snapshot_id=(snapshots[0].get("snapshot_id") if isinstance(snapshots, list) and snapshots else ""),
        narrative=f"备份仓 {repo}："
                  f"{len(snapshots) if isinstance(snapshots, list) else 0} 快照")
