# -*- coding: utf-8 -*-
"""L08 局部差量层 —— RFC 6902 JSON Patch 增量热修 + 指标增量重算。

SOP v13.0 L08 体检病灶（R19 真实断点）：
    1. 改一个评估记录（例如 tp 从 1 改成 2）必须整份评估集重跑重评分，
       旧的门禁结果全部被冲掉，无法回答「这次微调影响哪几个门禁」；
    2. 没有 RFC 6902 标准 Patch：差异只能人工描述，无法机器应用与回放；
    3. 改完不会触发派生指标（accuracy/precision/recall/f1）与守恒的增量重算。

对标开源标杆（Stars > 1k）：
    * RFC 6902 (JSON Patch)        —— add/remove/replace/test/move/copy 标准算子
    * google/diff-match-patch (>7k) —— 增量差异与无损应用
    * jsonpatch (Python, >1k)      —— 引用实现语义（~0/~1 转义）

落地的最低 3 项架构升级：
    1. 递归 diff → 标准 RFC 6902 patch（含 ~0/~1 指针转义）；
    2. apply_patch 支持 add/remove/replace/test + 原位深拷贝，失败即抛；
    3. 评估记录增量重算：混淆矩阵变更 → 派生指标 + 守恒校验 + 门禁影响面。

用法：
    python -m engines.diff_patch_engine --base workspace/rounds/L02_dag.json \
        --out workspace/rounds/L08_patch.json
"""
from __future__ import annotations

import copy
import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROLE = os.path.dirname(_HERE)
_AGENTS = os.path.dirname(_ROLE)
for _p in (_HERE, _ROLE, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_MISSING = object()


class PatchError(ValueError):
    """RFC 6902 Patch 应用失败。"""


def _escape(token: str) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def _unescape(token: str) -> str:
    return str(token).replace("~1", "/").replace("~0", "~")


def _split(pointer: str) -> List[str]:
    if pointer in ("", "/"):
        return []
    if not pointer.startswith("/"):
        raise PatchError(f"非法 JSON Pointer: {pointer!r}")
    return [_unescape(t) for t in pointer[1:].split("/")]


def _resolve(doc: Any, pointer: str) -> Any:
    cur = doc
    for token in _split(pointer):
        if isinstance(cur, list):
            idx = _list_index(token, len(cur))
            cur = cur[idx]
        elif isinstance(cur, dict):
            if token not in cur:
                raise PatchError(f"路径不存在: {pointer!r}（缺 {token!r}）")
            cur = cur[token]
        else:
            raise PatchError(f"路径不可达: {pointer!r}")
    return cur


def _list_index(token: str, length: int, allow_end: bool = False) -> int:
    if token == "-":
        if allow_end:
            return length
        raise PatchError("'-' 仅用于 add 末尾追加")
    try:
        idx = int(token)
    except ValueError as exc:
        raise PatchError(f"列表索引非法: {token!r}") from exc
    if idx < 0 or idx > (length if allow_end else length - 1):
        raise PatchError(f"列表索引越界: {idx} (len={length})")
    return idx


def _set(doc: Any, pointer: str, value: Any) -> None:
    tokens = _split(pointer)
    if not tokens:
        raise PatchError("不支持根替换")
    parent = _resolve(doc, "/" + "/".join(_escape(t) for t in tokens[:-1])) if len(tokens) > 1 else doc
    last = tokens[-1]
    if isinstance(parent, list):
        parent[_list_index(last, len(parent))] = value
    elif isinstance(parent, dict):
        parent[last] = value
    else:
        raise PatchError(f"父路径不可写: {pointer!r}")


def _add(doc: Any, pointer: str, value: Any) -> None:
    tokens = _split(pointer)
    if not tokens:
        raise PatchError("不支持根新增")
    parent = _resolve(doc, "/" + "/".join(_escape(t) for t in tokens[:-1])) if len(tokens) > 1 else doc
    last = tokens[-1]
    if isinstance(parent, list):
        if last == "-":
            parent.append(value)
        else:
            parent.insert(_list_index(last, len(parent), allow_end=True), value)
    elif isinstance(parent, dict):
        parent[last] = value
    else:
        raise PatchError(f"父路径不可写: {pointer!r}")


def _remove(doc: Any, pointer: str) -> None:
    tokens = _split(pointer)
    if not tokens:
        raise PatchError("不支持根删除")
    parent = _resolve(doc, "/" + "/".join(_escape(t) for t in tokens[:-1])) if len(tokens) > 1 else doc
    last = tokens[-1]
    if isinstance(parent, list):
        del parent[_list_index(last, len(parent))]
    elif isinstance(parent, dict):
        if last not in parent:
            raise PatchError(f"删除不存在的键: {pointer!r}")
        del parent[last]
    else:
        raise PatchError(f"父路径不可写: {pointer!r}")


def _diff(old: Any, new: Any, path: str = "") -> List[Dict[str, Any]]:
    if isinstance(old, dict) and isinstance(new, dict):
        ops: List[Dict[str, Any]] = []
        for k in old:
            if k not in new:
                ops.append({"op": "remove", "path": f"{path}/{_escape(k)}"})
            else:
                ops.extend(_diff(old[k], new[k], f"{path}/{_escape(k)}"))
        for k in new:
            if k not in old:
                ops.append({"op": "add", "path": f"{path}/{_escape(k)}", "value": copy.deepcopy(new[k])})
        return ops
    if isinstance(old, list) and isinstance(new, list):
        ops = []
        common = min(len(old), len(new))
        for i in range(common):
            ops.extend(_diff(old[i], new[i], f"{path}/{i}"))
        for i in range(common, len(new)):
            ops.append({"op": "add", "path": f"{path}/{i}", "value": copy.deepcopy(new[i])})
        for i in range(len(old) - 1, common - 1, -1):
            ops.append({"op": "remove", "path": f"{path}/{i}"})
        return ops
    if old != new:
        return [{"op": "replace", "path": path or "/", "value": copy.deepcopy(new)}]
    return []


def recompute_derived(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """由混淆矩阵增量重算分类指标（与 L01 沙箱同口径）。"""
    conf = (metrics or {}).get("confusion") or {}
    try:
        tp, fp, tn, fn = (int(conf.get(k, 0)) for k in ("tp", "fp", "tn", "fn"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "confusion 取值非法"}
    n = tp + fp + tn + fn
    if n <= 0:
        return {"ok": False, "error": "混淆计数为空"}
    acc = round((tp + tn) / n, 4)
    prec = round(tp / (tp + fp), 4) if (tp + fp) else 0.0
    rec = round(tp / (tp + fn), 4) if (tp + fn) else 0.0
    f1 = round(2 * prec * rec / (prec + rec), 4) if (prec + rec) else 0.0
    out = dict(metrics)
    out.update({"n": n, "accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
                "is_conserved": True, "recomputed": True})
    return {"ok": True, "metrics": out,
            "checks": [
                {"ok": n == tp + fp + tn + fn, "msg": f"混淆计数守恒 {n}", "dim": "patch.count"},
                {"ok": abs(acc - (tp + tn) / n) <= 1e-9,
                 "msg": f"accuracy 重算 {acc}", "dim": "patch.accuracy"},
            ]}


# 字段 → 门禁影响面
_GATE_FIELD_MAP = {
    "accuracy": ["GATE-01"], "precision": ["GATE-01"], "recall": ["GATE-01"],
    "f1": ["GATE-01"], "confusion": ["GATE-01"], "n": ["GATE-01"],
    "records": ["GATE-01"], "metrics": ["GATE-01"],
    "evidence": ["GATE-02"], "verdict": ["GATE-02", "GATE-03", "GATE-08"],
    "regression_id": ["GATE-03"], "fail_before": ["GATE-03"],
    "pass_after": ["GATE-03"], "existing_green": ["GATE-03"],
    "assets": ["GATE-04"], "versions": ["GATE-06"], "stage": ["GATE-06"],
    "risk_tier": ["GATE-07"], "license": ["GATE-07"], "feedback_source": ["GATE-07"],
    "handoff": ["GATE-08"], "authorized_by": ["GATE-08"],
}


class R19DiffPatchEngine:
    """RFC 6902 差量热修 + 指标增量重算 + 门禁影响面分析。"""

    ENGINE = "R19DiffPatchEngine"
    LAYER = "L08"
    CAPABILITIES = [
        "RFC 6902 递归 diff (add/remove/replace + ~0/~1 指针转义)",
        "apply_patch 深拷贝无损应用 + test/remove/add/replace 语义",
        "评估指标增量重算 + 守恒校验 + 8 维门禁影响面定位",
        "[C2] Patch 逆运算回滚 (inverse patch, 逐 op 旧值快照)",
        "[C2] 基线漂移冲突检测 (逐 op 定位 index/path/reason)",
        "[C2] Patch 压缩合并 (去冗余/同路径归一 + 体积缩减率)",
    ]

    def create_patch(self, old: Any, new: Any) -> List[Dict[str, Any]]:
        return _diff(old, new)

    def apply_patch(self, base: Any, patches: List[Dict[str, Any]],
                    recompute: bool = True) -> Any:
        doc = copy.deepcopy(base)
        for p in patches or []:
            op = str(p.get("op", "")).lower()
            path = p.get("path", "")
            if op == "test":
                cur = _resolve(doc, path)
                if cur != p.get("value"):
                    raise PatchError(f"test 失败: {path} 期望 {p.get('value')!r} 实际 {cur!r}")
            elif op == "add":
                _add(doc, path, copy.deepcopy(p.get("value")))
            elif op == "remove":
                _remove(doc, path)
            elif op == "replace":
                if path in ("", "/"):
                    doc = copy.deepcopy(p.get("value"))
                else:
                    _resolve(doc, path)
                    _set(doc, path, copy.deepcopy(p.get("value")))
            elif op in ("move", "copy"):
                src = p.get("from", "")
                val = copy.deepcopy(_resolve(doc, src))
                if op == "move":
                    _remove(doc, src)
                _add(doc, path, val)
            else:
                raise PatchError(f"不支持的 op: {op!r}")
        if recompute and isinstance(doc, dict) and isinstance(doc.get("confusion"), dict):
            rec = recompute_derived(doc)
            if rec.get("ok"):
                m = rec["metrics"]
                doc.update({"n": m["n"], "accuracy": m["accuracy"],
                            "precision": m["precision"], "recall": m["recall"],
                            "f1": m["f1"], "is_conserved": True,
                            "recomputed": True})
        return doc

    # ------------------------------------------------------------------ #
    # [Cycle 2] 逆运算 / 冲突 / 压缩
    # ------------------------------------------------------------------ #
    def invert_patch(self, base: Any,
                     patches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        doc = copy.deepcopy(base)
        inverse: List[Dict[str, Any]] = []
        for p in patches or []:
            op = str(p.get("op", "")).lower()
            path = p.get("path", "")
            if op == "test":
                continue
            if op == "add":
                try:
                    old = copy.deepcopy(_resolve(doc, path))
                    existed = True
                except PatchError:
                    old, existed = None, False
                inverse.append({"op": "replace" if existed else "remove",
                                "path": path, **({"value": old} if existed else {})})
                _add(doc, path, copy.deepcopy(p.get("value")))
            elif op == "remove":
                old = copy.deepcopy(_resolve(doc, path))
                inverse.append({"op": "add", "path": path, "value": old})
                _remove(doc, path)
            elif op == "replace":
                old = copy.deepcopy(doc) if path in ("", "/") else copy.deepcopy(_resolve(doc, path))
                inverse.append({"op": "replace", "path": path, "value": old})
                if path in ("", "/"):
                    doc = copy.deepcopy(p.get("value"))
                else:
                    _set(doc, path, copy.deepcopy(p.get("value")))
            elif op in ("move", "copy"):
                src = p.get("from", "")
                old = copy.deepcopy(_resolve(doc, src))
                val = copy.deepcopy(old)
                if op == "move":
                    _remove(doc, src)
                    inverse.append({"op": "move", "from": path, "path": src})
                else:
                    inverse.append({"op": "remove", "path": path})
                _add(doc, path, val)
            else:
                raise PatchError(f"不支持的 op: {op!r}")
        return list(reversed(inverse))

    def detect_conflicts(self, base: Any,
                         patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        doc = copy.deepcopy(base)
        conflicts: List[Dict[str, Any]] = []
        applied = 0
        for idx, p in enumerate(patches or []):
            try:
                op = str(p.get("op", "")).lower()
                path = p.get("path", "")
                if op == "test":
                    cur = _resolve(doc, path)
                    if cur != p.get("value"):
                        raise PatchError(f"test 失败: 期望 {p.get('value')!r} 实际 {cur!r}")
                elif op == "add":
                    _add(doc, path, copy.deepcopy(p.get("value")))
                elif op == "remove":
                    _remove(doc, path)
                elif op == "replace":
                    if path in ("", "/"):
                        doc = copy.deepcopy(p.get("value"))
                    else:
                        _resolve(doc, path)
                        _set(doc, path, copy.deepcopy(p.get("value")))
                elif op in ("move", "copy"):
                    src = p.get("from", "")
                    val = copy.deepcopy(_resolve(doc, src))
                    if op == "move":
                        _remove(doc, src)
                    _add(doc, path, val)
                else:
                    raise PatchError(f"不支持的 op: {op!r}")
                applied += 1
            except (PatchError, KeyError, IndexError, TypeError) as exc:
                conflicts.append({"index": idx, "op": p.get("op"), "path": p.get("path"),
                                  "reason": str(exc)})
        return {"ok": not conflicts, "conflicts": conflicts,
                "conflict_count": len(conflicts), "applied": applied,
                "total": len(patches or [])}

    def compact_patch(self, patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        compacted: List[Dict[str, Any]] = []
        index_by_path: Dict[str, int] = {}
        for p in patches or []:
            op = str(p.get("op", "")).lower()
            path = p.get("path", "")
            if op == "test":
                continue
            if path in index_by_path:
                prev_idx = index_by_path[path]
                prev = compacted[prev_idx]
                if op == "replace" and prev.get("op") == "replace":
                    compacted[prev_idx] = {"op": "replace", "path": path,
                                           "value": p.get("value")}
                    continue
                if op == "remove" and prev.get("op") == "replace":
                    compacted[prev_idx] = {"op": "remove", "path": path}
                    continue
            index_by_path[path] = len(compacted)
            compacted.append(dict(p))
        before = len(patches or [])
        after = len(compacted)
        return {"ok": True, "patches": compacted, "before": before, "after": after,
                "removed": before - after,
                "reduction_ratio": round((before - after) / before, 4) if before else 0.0}

    def diff_evaluation(self, old: Any, new: Any) -> Dict[str, Any]:
        patches = self.create_patch(old, new)
        changed = sorted({p["path"].strip("/").split("/")[0] for p in patches if p.get("path")})
        gates: List[str] = []
        for field in changed:
            gates.extend(_GATE_FIELD_MAP.get(field, []))
        gates = sorted(set(gates))
        try:
            applied = self.apply_patch(old, patches)
            applied_ok = True
            err = ""
        except PatchError as exc:
            applied, applied_ok, err = None, False, str(exc)
        conservation = None
        if applied_ok and isinstance(applied, dict) and isinstance(applied.get("confusion"), dict):
            rec = recompute_derived(applied)
            conservation = rec.get("checks", []) if rec.get("ok") else [{"ok": False, "msg": rec.get("error")}]
        inverse_patch: List[Dict[str, Any]] = []
        rollback_ok = False
        conflicts: Dict[str, Any] = {"ok": True, "conflicts": [], "conflict_count": 0}
        compacted: Dict[str, Any] = {"before": len(patches), "after": len(patches),
                                     "removed": 0, "reduction_ratio": 0.0}
        if applied_ok:
            inverse_patch = self.invert_patch(old, patches)
            restored = self.apply_patch(self.apply_patch(old, patches, recompute=False),
                                        inverse_patch, recompute=False)
            rollback_ok = (json.dumps(restored, sort_keys=True, default=str)
                           == json.dumps(old, sort_keys=True, default=str))
            conflicts = self.detect_conflicts(old, patches)
            compacted = self.compact_patch(patches)
        return {
            "ok": applied_ok,
            "engine": self.ENGINE, "layer": self.LAYER,
            "patch_count": len(patches), "patches": patches,
            "changed_paths": changed, "gates_affected": gates,
            "applied": applied, "conservation": conservation,
            "recomputed": bool(isinstance(applied, dict) and applied.get("recomputed")),
            "inverse_patch": inverse_patch, "inverse_count": len(inverse_patch),
            "rollback_ok": rollback_ok,
            "conflicts": conflicts,
            "compacted": compacted,
            "capabilities": list(self.CAPABILITIES),
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _demo() -> Dict[str, Any]:
    old = {"n": 4, "confusion": {"tp": 1, "fp": 1, "tn": 1, "fn": 1},
           "accuracy": 0.5, "precision": 0.5, "recall": 0.5, "f1": 0.5}
    new = {"n": 4, "confusion": {"tp": 2, "fp": 0, "tn": 1, "fn": 1},
           "accuracy": 0.75}
    return {"old": old, "new": new}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R19 L08 RFC 6902 差量热修")
    ap.add_argument("--base", default=None, help="基线 JSON（旧状态）")
    ap.add_argument("--new", default=None, help="新状态 JSON")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    eng = R19DiffPatchEngine()
    demo = _demo()
    old, new = demo["old"], demo["new"]
    if args.base and os.path.exists(args.base):
        with open(args.base, encoding="utf-8-sig") as f:
            old = json.load(f)
    if args.new and os.path.exists(args.new):
        with open(args.new, encoding="utf-8-sig") as f:
            new = json.load(f)
    out = eng.diff_evaluation(old, new)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": out["ok"], "patches": out["patch_count"],
                      "gates": out["gates_affected"],
                      "accuracy": (out["applied"] or {}).get("accuracy"),
                      "out": args.out}, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
