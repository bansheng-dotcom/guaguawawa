# -*- coding: utf-8 -*-
"""L08 局部差量层 —— RFC 6902 JSON Patch + 监控/告警配置不变量复核。

SOP v13.0 L08 体检病灶（R20 真实断点）：
    调整单个告警阈值或新增一个监控项，必须整份配置重生成、整轮门禁重跑，
    原有已满足的规则被冲掉；没有标准 Patch 可机器应用/回放；
    改完也不复核「升级链仍单调、监控 ID 不重复、阈值仍在白名单」。

对标开源标杆（Stars > 1k）：
    * RFC 6902 (JSON Patch) —— 标准增量补丁算子
    * google/diff-match-patch (>7k) —— 差量生成与语义
    * jsonpatch / python-json-patch (>1k) —— 引用实现与指针转义

落地的最低 3 项架构升级：
    1. RFC 6902 递归 diff（add/remove/replace + `~0`/`~1` 转义）；
    2. apply_patch 深拷贝无损应用（add/remove/replace/test 语义）；
    3. 配置不变量复核（告警严重度白名单/升级链单调/监控 ID 唯一/间隔下限）。

用法：
    python agent.py evolve patch --out workspace/rounds/L08_patch.json
"""
from __future__ import annotations

import copy
import os
import sys
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)


class PatchError(ValueError):
    """Patch 非法或应用失败。"""


def _escape(token: Any) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def _unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _pointer(path: str) -> List[str]:
    if not path:
        return []
    if not path.startswith("/"):
        raise PatchError(f"JSON Pointer 必须以 / 开头: {path}")
    return [_unescape(t) for t in path.split("/")[1:]]


class R20DiffPatchEngine:
    """RFC 6902 差量热修 + SRE 配置不变量复核。"""

    ENGINE = "R20DiffPatchEngine"
    LAYER = "L08"
    CAPABILITIES = [
        "RFC 6902 递归 diff (add/remove/replace + ~0/~1 指针转义)",
        "apply_patch 深拷贝无损应用 (test/remove/add/replace 语义)",
        "SRE 配置不变量复核 (严重度白名单/升级链单调/监控唯一/间隔下限)",
    ]

    # ------------------------------------------------------------------ #
    # diff
    # ------------------------------------------------------------------ #
    def diff(self, old: Any, new: Any, path: str = "") -> List[Dict[str, Any]]:
        ops: List[Dict[str, Any]] = []
        if type(old) is not type(new) and not (isinstance(old, (int, float))
                                              and isinstance(new, (int, float))):
            ops.append({"op": "replace", "path": path or "/", "value": new})
            return ops
        if isinstance(old, dict) and isinstance(new, dict):
            for k in old:
                if k not in new:
                    ops.append({"op": "remove", "path": f"{path}/{_escape(k)}"})
            for k in new:
                sub = f"{path}/{_escape(k)}"
                if k not in old:
                    ops.append({"op": "add", "path": sub, "value": new[k]})
                else:
                    ops.extend(self.diff(old[k], new[k], sub))
            return ops
        if isinstance(old, list) and isinstance(new, list):
            for i in range(min(len(old), len(new))):
                ops.extend(self.diff(old[i], new[i], f"{path}/{i}"))
            if len(new) > len(old):
                for i in range(len(old), len(new)):
                    ops.append({"op": "add", "path": f"{path}/{i}", "value": new[i]})
            elif len(old) > len(new):
                for i in range(len(old) - 1, len(new) - 1, -1):
                    ops.append({"op": "remove", "path": f"{path}/{i}"})
            return ops
        if old != new:
            ops.append({"op": "replace", "path": path or "/", "value": new})
        return ops

    # ------------------------------------------------------------------ #
    # apply
    # ------------------------------------------------------------------ #
    def apply_patch(self, doc: Any, ops: List[Dict[str, Any]]) -> Any:
        cur = copy.deepcopy(doc)
        for op in ops or []:
            kind = op.get("op")
            parts = _pointer(op.get("path", ""))
            if not parts:
                if kind in ("replace", "add"):
                    cur = copy.deepcopy(op.get("value"))
                    continue
                if kind == "remove":
                    cur = None
                    continue
            parent = cur
            for token in parts[:-1]:
                if isinstance(parent, list):
                    try:
                        parent = parent[int(token)]
                    except (IndexError, ValueError):
                        raise PatchError(f"数组下标越界: {op.get('path')}")
                elif isinstance(parent, dict):
                    if token not in parent:
                        raise PatchError(f"路径不存在: {op.get('path')}")
                    parent = parent[token]
                else:
                    raise PatchError(f"路径父节点不可达: {op.get('path')}")
            last = parts[-1]
            if isinstance(parent, list):
                idx = len(parent) if kind == "add" and last == "-" else int(last)
                if kind == "add":
                    parent.insert(idx, copy.deepcopy(op.get("value")))
                elif kind == "replace":
                    parent[idx] = copy.deepcopy(op.get("value"))
                elif kind == "remove":
                    parent.pop(idx)
                elif kind == "test":
                    if parent[idx] != op.get("value"):
                        raise PatchError(f"test 失败: {op.get('path')}")
                else:
                    raise PatchError(f"未知 op: {kind}")
            elif isinstance(parent, dict):
                if kind == "add" or kind == "replace":
                    parent[last] = copy.deepcopy(op.get("value"))
                elif kind == "remove":
                    if last not in parent:
                        raise PatchError(f"删除不存在的键: {last}")
                    del parent[last]
                elif kind == "test":
                    if parent.get(last) != op.get("value"):
                        raise PatchError(f"test 失败: {op.get('path')}")
                else:
                    raise PatchError(f"未知 op: {kind}")
            else:
                raise PatchError(f"父节点不是容器: {op.get('path')}")
        return cur

    # ------------------------------------------------------------------ #
    # 不变量复核
    # ------------------------------------------------------------------ #
    def verify_invariants(self, doc: Any, kind: str = "alert") -> Dict[str, Any]:
        doc = doc or {}
        checks: List[Dict[str, Any]] = []
        if kind == "alert":
            sevs = {"critical", "warning", "info"}
            rules = doc.get("rules") or doc.get("alerts") or []
            bad = [r.get("id") for r in rules
                   if isinstance(r, dict) and str(r.get("severity", "")).lower() not in sevs]
            checks.append({"ok": not bad, "msg": f"严重度白名单违规={bad}",
                           "dim": "invariant.alert.severity"})
            chain = doc.get("escalation") or []
            levels = [x.get("level") for x in chain if isinstance(x, dict)]
            mono = all(isinstance(x, int) for x in levels) and all(
                levels[i] < levels[i + 1] for i in range(len(levels) - 1))
            checks.append({"ok": mono, "msg": f"升级链单调递增 levels={levels}",
                           "dim": "invariant.alert.escalation"})
        else:
            monitors = doc.get("monitors") or []
            ids = [m.get("id") for m in monitors if isinstance(m, dict)]
            checks.append({"ok": len(ids) == len(set(ids)), "msg": f"监控 ID 唯一 ids={ids}",
                           "dim": "invariant.monitor.unique"})
            bad_interval = [m.get("id") for m in monitors
                            if isinstance(m, dict) and int(m.get("interval_seconds", 60) or 0) < 10]
            checks.append({"ok": not bad_interval, "msg": f"探测间隔 >= 10s 违规={bad_interval}",
                           "dim": "invariant.monitor.interval"})
        return {"ok": all(c["ok"] for c in checks), "checks": checks, "kind": kind}

    # ------------------------------------------------------------------ #
    # 端到端
    # ------------------------------------------------------------------ #
    def patch_with_recheck(self, old: Any, new: Any, kind: str = "alert") -> Dict[str, Any]:
        patch = self.diff(old, new)
        applied = self.apply_patch(old, patch)
        before = self.verify_invariants(old, kind)
        after = self.verify_invariants(applied, kind)
        return {
            "ok": bool(applied == new and after["ok"]),
            "engine": self.ENGINE, "layer": self.LAYER,
            "kind": kind, "patch": patch, "op_count": len(patch),
            "applied_equals_new": applied == new,
            "applied": applied,
            "invariants_before": before, "invariants_after": after,
            "capabilities": list(self.CAPABILITIES),
        }

    def demo(self) -> Dict[str, Any]:
        old = {"monitors": [{"id": "mon-pay-01", "interval_seconds": 60},
                            {"id": "mon-order-01", "interval_seconds": 30}],
               "rules": [{"id": "r1", "severity": "critical", "threshold": 0.95},
                         {"id": "r2", "severity": "warning", "threshold": 0.90}],
               "escalation": [{"level": 1, "to": "值班"}, {"level": 2, "to": "R20"},
                              {"level": 3, "to": "R01"}]}
        new = copy.deepcopy(old)
        new["rules"][0]["threshold"] = 0.98
        new["monitors"].append({"id": "mon-db-01", "interval_seconds": 15})
        out = self.patch_with_recheck(old, new, "alert")
        out["monitor_invariants"] = self.verify_invariants(new, "monitor")
        out["ok"] = out["ok"] and out["monitor_invariants"]["ok"]
        return out


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="R20 L08 RFC6902 差量热修")
    ap.add_argument("--base", default=None)
    ap.add_argument("--new", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    eng = R20DiffPatchEngine()
    if args.base and args.new:
        with open(args.base, encoding="utf-8-sig") as f:
            old = json.load(f)
        with open(args.new, encoding="utf-8-sig") as f:
            new = json.load(f)
        out = eng.patch_with_recheck(old, new)
    else:
        out = eng.demo()
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": out["ok"], "ops": out["op_count"],
                      "engine": eng.ENGINE}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
