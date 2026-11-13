# -*- coding: utf-8 -*-
"""S01 数据连接与 ELT —— 能力域 1。

整合自 airbytehq__airbyte：`airbyte-integrations/connectors/` 下的
`source-*`（数据来源连接器）与 `destination-*`（目的地连接器）命名约定、
连接器目录内的 `metadata.yaml`（connectorType / dockerRepository /
releaseStage）与 sync mode 口径。把「来源 → 目的地」的连接配置与同步任务
转成确定性校验：连接器命名约定、sync mode 白名单、stream 集合、去重。

关键立场：**连接配置是资质的载体**。连接器名字不符合 `source-`/`destination-`
约定的配置不可路由；sync mode 不在白名单的同步不可执行（口径漂移的头号来源）。
本角色只产出连接与同步工件，**绝不在输出里携带任何连接凭据**（红线 1，
api_key/secret/password 一律不出现，由 review 的 credential_gate 兜底）。

动作：
  connection  连接（来源↔目的地）配置校验
  sync        同步任务校验
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "elt"
DESC = "数据连接与 ELT：connection/sync"

_CRED_WORDS = ["api_key", "apikey", "secret", "password", "token", "私钥",
               "密钥", "密码", "连接串", "connection_string", "client_secret"]


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in (("connection", "校验连接配置"), ("sync", "校验同步任务")):
        pa = act.add_parser(a, help=h)
        pa.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "connection":
        return _validate_connection(data)
    if args.action == "sync":
        return _validate_sync(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _has_credential(data: Any) -> List[str]:
    """扫描连接配置里的字段名（不是值）：字段名出现凭据词即命中。"""
    hits: List[str] = []
    if isinstance(data, dict):
        for k in data.keys():
            lk = str(k).lower()
            if any(w in lk for w in _CRED_WORDS):
                hits.append(str(k))
    return hits


# --------------------------------------------------------------------------- #
def _validate_connection(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["elt"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", connection_id="")

    cid = str(data.get("connection_id", "")).strip()
    src = str(data.get("source_connector", "")).strip()
    dst = str(data.get("destination_connector", "")).strip()
    checks.append(_ck(bool(cid), "连接 ID 非空", "elt.connection_id"))

    # 连接器命名约定：来源必须 source- 前缀、目的地必须 destination- 前缀
    checks.append(_ck(bool(src) and src.startswith(th["source_prefix"]),
                      f"来源连接器 {src or '空'} 以 {th['source_prefix']} 开头",
                      "elt.source_prefix"))
    checks.append(_ck(bool(dst) and dst.startswith(th["destination_prefix"]),
                      f"目的地连接器 {dst or '空'} 以 {th['destination_prefix']} 开头",
                      "elt.destination_prefix"))

    # 来源≠目的地（自己同步到自己是配置错误的头号来源）
    checks.append(_ck(bool(src) and bool(dst) and src != dst,
                      "来源与目的地不同", "elt.distinct"))

    # 红线 1：连接配置字段名不得出现凭据词（凭据走环境变量/密钥管理，不落工件）
    cred = _has_credential(data)
    checks.append(_ck(not cred,
                      f"连接配置不含凭据字段（命中 {cred or '无'}）",
                      "elt.no_credential"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        connection_id=cid, source_connector=src, destination_connector=dst,
        narrative=f"连接 {cid}：{src} → {dst}")


# --------------------------------------------------------------------------- #
def _validate_sync(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["elt"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", stream_count=0)

    cid = str(data.get("connection_id", "")).strip()
    checks.append(_ck(bool(cid), "同步任务归属连接非空", "sync.connection_id"))

    mode = data.get("sync_mode")
    checks.append(_ck(mode in th["sync_modes"],
                      f"sync mode={mode!r} 在白名单 {th['sync_modes']}",
                      "sync.mode"))

    streams = data.get("streams") or []
    ok_streams = isinstance(streams, list) and len(streams) > 0
    checks.append(_ck(ok_streams,
                      f"stream ≥1（实际 "
                      f"{len(streams) if isinstance(streams, list) else 0}）",
                      "sync.streams"))

    # 增量模式必须声明 cursor 字段（否则无法定位增量边界）
    if mode in ("incremental_append", "incremental_dedup"):
        missing_cursor = [s for s in (streams if isinstance(streams, list) else [])
                          if not isinstance(s, dict)
                          or not str(s.get("cursor_field", "")).strip()]
        checks.append(_ck(not missing_cursor,
                          f"增量 stream 声明 cursor_field（缺 "
                          f"{len(missing_cursor)} 个）", "sync.cursor"))
    else:
        checks.append(_ck(True, f"{mode} 模式不要求 cursor", "sync.cursor"))

    # 计划频率非空
    sched = str(data.get("schedule", "")).strip()
    checks.append(_ck(bool(sched), f"同步频率非空（{sched or '空'}）", "sync.schedule"))

    cred = _has_credential(data)
    checks.append(_ck(not cred, f"同步配置不含凭据字段（命中 {cred or '无'}）",
                      "sync.no_credential"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        connection_id=cid, stream_count=len(streams) if isinstance(streams, list) else 0,
        mode=mode,
        narrative=f"同步 {cid}：{mode}，"
                  f"{len(streams) if isinstance(streams, list) else 0} 个 stream")
