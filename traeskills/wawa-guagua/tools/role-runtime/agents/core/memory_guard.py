# -*- coding: utf-8 -*-
"""记忆池体积护栏（Memory Guard）。

目标：让 ``rXX-*/workspace/session_state.json`` 这类记忆池**无论跑多久都不会失控**，
对应 ``PROTOCOL.md`` 第六节「会话记忆与快照」的硬性契约。

三层防护：

1. **加载前置限额**（HARD_LIMIT_BYTES，默认 100 MB）
   超过上限的文件**不解析**——直接隔离为 ``*.oversize-<时间戳>.bak`` 并回落默认值。
   历史事故里 966 MB 的嵌套 JSON 一旦被 ``json.load`` 就会拖垮进程，这一层是熔断。
2. **快照保留策略**（KEEP_LAST，默认 50 条）
   拍完快照后只保留最近 N 条；文件超过 SOFT_LIMIT_BYTES（默认 2 MB）时再兜底裁剪一次。
3. **全局 GC**（``python guagua.py gc``）
   扫描全部角色记忆池：软超限裁剪快照，硬超限隔离整份文件（保留 .bak 可人工取证）。

用法：
    python -m core.memory_guard --dry-run      # 只看报告
    python -m core.memory_guard                # 执行裁剪 / 隔离
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

# 100 MB：超过即隔离，绝不送进 json.load
HARD_LIMIT_BYTES = 100 * 1024 * 1024
# 2 MB：超过即裁剪历史快照
SOFT_LIMIT_BYTES = 2 * 1024 * 1024
# 保留最近多少条快照
KEEP_LAST = 50

QUARANTINE_MARK = ".oversize-"
DEFAULT_PATTERNS = ("session_state*.json",)


def file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def quarantine(path: str, tag: str = "guard") -> str:
    """把异常文件改名保留，绝不直接删除（取证与人工恢复都靠它）。"""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = f"{path}.{tag}-{stamp}.bak"
    n = 1
    while os.path.exists(target):
        target = f"{path}.{tag}-{stamp}-{n}.bak"
        n += 1
    os.replace(path, target)
    return target


def trim_snapshots(state: Dict[str, Any], key: str = "snapshots",
                   keep_last: Optional[int] = None) -> int:
    """把快照容器裁到最近 keep_last 条，返回被裁掉的数量。

    同时支持 list（按时间顺序追加）与 dict（键即快照 ID）两种结构：
    list 删除头部；dict 依赖 JSON 保留的插入顺序删除最早的键。
    """
    keep_last = KEEP_LAST if keep_last is None else max(1, int(keep_last))
    snaps = state.get(key)
    if isinstance(snaps, list):
        excess = len(snaps) - keep_last
        if excess > 0:
            del snaps[:excess]
            return excess
    elif isinstance(snaps, dict):
        excess = len(snaps) - keep_last
        if excess > 0:
            for k in list(snaps.keys())[:excess]:
                snaps.pop(k, None)
            return excess
    return 0


def trim_history(state: Dict[str, Any], key: str = "history",
                 keep_last: int = 200) -> int:
    """兜底裁剪对话历史（仅 GC 在软超限且快照裁剪无效时使用）。"""
    hist = state.get(key)
    if isinstance(hist, list):
        excess = len(hist) - keep_last
        if excess > 0:
            del hist[:excess]
            return excess
    return 0


def load_json_guarded(path: str,
                      default_factory: Callable[[], Any] = dict,
                      limit: Optional[int] = None) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """带体积熔断的 JSON 读取。

    返回 ``(data, notice)``。``notice`` 为 None 表示正常读取；
    否则说明发生了隔离/重置，供调用方打日志。
    """
    limit = HARD_LIMIT_BYTES if limit is None else int(limit)
    if not os.path.exists(path):
        return default_factory(), None
    size = file_size(path)
    if size > limit:
        backup = quarantine(path, "oversize")
        return default_factory(), {
            "action": "quarantined",
            "path": path,
            "size_bytes": size,
            "quarantine_path": backup,
            "reason": f"file exceeds {limit} bytes, refusing to json.load",
        }
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, ValueError) as exc:
        return default_factory(), {
            "action": "reset",
            "path": path,
            "size_bytes": size,
            "reason": f"unreadable json: {exc}",
        }


def enforce(path: str, state: Dict[str, Any],
            keep_last: Optional[int] = None,
            soft_limit: Optional[int] = None) -> int:
    """拍完快照后调用：体积超过软上限就裁快照，返回被裁数量。"""
    soft_limit = SOFT_LIMIT_BYTES if soft_limit is None else int(soft_limit)
    if file_size(path) <= soft_limit:
        return 0
    return trim_snapshots(state, keep_last=keep_last)


def guard_file(path: str,
               keep_last: Optional[int] = None,
               soft_limit: Optional[int] = None,
               hard_limit: Optional[int] = None,
               dry_run: bool = False) -> Dict[str, Any]:
    """对单个文件执行一次护栏检查（GC 的核心单元）。"""
    keep_last = KEEP_LAST if keep_last is None else max(1, int(keep_last))
    soft_limit = SOFT_LIMIT_BYTES if soft_limit is None else int(soft_limit)
    hard_limit = HARD_LIMIT_BYTES if hard_limit is None else int(hard_limit)
    report: Dict[str, Any] = {
        "path": path,
        "size_before": file_size(path),
        "snapshots_before": None,
        "snapshots_after": None,
        "action": "ok",
        "note": "",
    }
    if report["size_before"] == 0:
        report["action"] = "missing"
        return report

    if report["size_before"] > hard_limit:
        report["action"] = "quarantine"
        if not dry_run:
            report["quarantine_path"] = quarantine(path, "oversize")
        report["note"] = (f"{report['size_before'] / 1048576:.1f} MB > "
                          f"{hard_limit / 1048576:.0f} MB 硬上限，拒绝解析并隔离")
        return report

    try:
        with open(path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, ValueError) as exc:
        report["action"] = "quarantine"
        if not dry_run:
            report["quarantine_path"] = quarantine(path, "corrupt")
        report["note"] = f"JSON 无法解析：{exc}"
        return report

    if not isinstance(state, dict):
        report["note"] = "顶层不是对象，跳过"
        return report

    snaps = state.get("snapshots")
    report["snapshots_before"] = len(snaps) if isinstance(snaps, (list, dict)) else 0

    if report["size_before"] <= soft_limit:
        report["snapshots_after"] = report["snapshots_before"]
        return report

    pruned = trim_snapshots(state, keep_last=keep_last)
    trimmed_history = 0
    if file_size(path) > soft_limit and pruned >= 0:
        # 快照裁完仍超软限：多半是 history 撑爆的，兜底裁历史
        trimmed_history = trim_history(state, keep_last=200)
        if trimmed_history:
            report["trimmed_history"] = trimmed_history

    payload = json.dumps(state, ensure_ascii=False, indent=2)
    size_after = len(payload.encode("utf-8"))
    if not dry_run:
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)

    report["snapshots_after"] = len(state.get("snapshots") or [])
    report["size_after"] = size_after if not dry_run else None
    report["pruned"] = pruned
    report["action"] = "trimmed" if (pruned or trimmed_history) else "ok"
    if not pruned and not trimmed_history:
        report["note"] = "超软限但无可裁剪项（可能是单个大字段），建议人工确认"
    return report


def iter_memory_files(root: str, patterns: Tuple[str, ...] = DEFAULT_PATTERNS) -> List[str]:
    """遍历所有角色的记忆池文件，跳过隔离备份与临时文件。"""
    hits: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in ("__pycache__", ".git", ".pytest_cache", "node_modules")]
        for name in filenames:
            if any(_match(name, p) for p in patterns):
                if QUARANTINE_MARK in name or name.endswith(".tmp"):
                    continue
                hits.append(os.path.join(dirpath, name))
    return sorted(hits)


def _match(name: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(name, pattern)


def gc(root: str, keep_last: Optional[int] = None,
       dry_run: bool = False) -> Dict[str, Any]:
    """扫描并处理整棵仓库里的记忆池。"""
    reports = [guard_file(p, keep_last=keep_last, dry_run=dry_run)
               for p in iter_memory_files(root)]
    return {
        "root": root,
        "dry_run": dry_run,
        "scanned": len(reports),
        "quarantined": [r for r in reports if r["action"] == "quarantine"],
        "trimmed": [r for r in reports if r["action"] == "trimmed"],
        "total_bytes": sum(r["size_before"] for r in reports),
        "reports": reports,
    }


def format_report(summary: Dict[str, Any]) -> str:
    lines = []
    mode = "DRY-RUN（不落盘）" if summary["dry_run"] else "执行"
    lines.append(f"记忆池护栏 · {mode}")
    lines.append(f"扫描 {summary['scanned']} 个文件，合计 "
                 f"{summary['total_bytes'] / 1024:.1f} KB")
    for key, label in (("quarantined", "已隔离"), ("trimmed", "已裁剪")):
        for r in summary[key]:
            size = r["size_before"] / 1024
            extra = ""
            if r.get("pruned"):
                extra = f"，快照 {r['snapshots_before']} → {r['snapshots_after']}"
            if r.get("quarantine_path"):
                extra += f"，备份 {os.path.basename(r['quarantine_path'])}"
            lines.append(f"  [{label}] {r['path']}  {size:.1f} KB{extra}")
            if r.get("note"):
                lines.append(f"         {r['note']}")
    if summary["scanned"] and not summary["quarantined"] and not summary["trimmed"]:
        lines.append("  全部在软上限（2 MB）以内，无需处理。")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m core.memory_guard",
        description="记忆池体积护栏：裁剪过期快照 / 隔离异常体积文件")
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        help="仓库根目录（默认本文件所在仓库）")
    parser.add_argument("--keep-last", type=int, default=KEEP_LAST,
                        help=f"保留最近多少条快照（默认 {KEEP_LAST}）")
    parser.add_argument("--dry-run", action="store_true", help="只出报告，不改文件")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = parser.parse_args(argv)

    summary = gc(args.root, keep_last=args.keep_last, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(format_report(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
