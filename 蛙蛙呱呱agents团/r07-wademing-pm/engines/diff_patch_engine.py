# -*- coding: utf-8 -*-
"""engines/diff_patch_engine.py - L08 局部差量层 (RFC 6902 JSON Patch for PRD).

对标开源标杆（Stars > 1k）：
- RFC 6902 / RFC 6901 —— JSON Patch 与 JSON Pointer 规范（IETF 标准）；
- google/diff-match-patch —— 最小编辑差量思想。

解决 R07 历史断点：改一条验收标准即全量重生成整份 PRD，已评审通过的部分被冲掉。
本引擎把 PRD 视为可寻址文档，用 JSON Pointer 定位、用 JSON Patch 做条目级热修：
1. `JSONPointer`：RFC 6901 解析（~0/~1 转义、数组下标、`-` 追加）；
2. `PRDPatchEngine.apply()`：严格实现 add/remove/replace/move/copy/test 六算子，
   任何 test 失败即 `PatchTestFailed`，绝不「带病落盘」；
3. `PRDPatchEngine.diff()`：递归生成最小差量（replace/add/remove）；
4. `PRDPatchEngine.patch_and_export()`：落盘 `prd_patched.json` + `prd_patch.diff.json`
   （含前后 SHA256、改动路径、未改动占比、门禁复检结果），证明「局部热修、零漂移」。
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = ["JSONPointer", "PatchTestFailed", "PatchError", "PRDPatchEngine"]

PATCH_SCHEMA = "pm.prd.patch/v1"
_MISSING = object()


class PatchError(Exception):
    """JSON Patch 语义错误（路径不存在 / 非法算子等）。"""


class PatchTestFailed(PatchError):
    """RFC 6902 `test` 算子失败：文档与期望值不符，必须阻断。"""


class JSONPointer:
    """RFC 6901 JSON Pointer：解析、取值、写值、删值。"""

    def __init__(self, pointer: str = "") -> None:
        if pointer == "":
            self.tokens: List[str] = []
            return
        if not isinstance(pointer, str) or not pointer.startswith("/"):
            raise PatchError(f"非法 JSON Pointer（必须以 / 开头）：{pointer!r}")
        self.tokens = [t.replace("~1", "/").replace("~0", "~")
                       for t in pointer.split("/")[1:]]

    def __str__(self) -> str:
        return "/" + "/".join(t.replace("~", "~0").replace("/", "~1")
                              for t in self.tokens)

    @staticmethod
    def _index(token: str, length: int, allow_end: bool = False) -> int:
        if token == "-":
            if allow_end:
                return length
            raise PatchError("`-` 只能用于 add 的数组末尾")
        try:
            idx = int(token)
        except ValueError as exc:
            raise PatchError(f"数组下标非法：{token!r}") from exc
        if idx < 0 or idx > (length if allow_end else length - 1):
            raise PatchError(f"数组下标越界：{idx} (长度 {length})")
        return idx

    def resolve(self, document: Any) -> Any:
        node = document
        for token in self.tokens:
            if isinstance(node, dict):
                if token not in node:
                    raise PatchError(f"路径不存在：{self}（缺键 {token!r}）")
                node = node[token]
            elif isinstance(node, list):
                node = node[self._index(token, len(node))]
            else:
                raise PatchError(f"路径穿透到标量：{self}（在 {token!r} 处）")
        return node

    def parent_and_token(self, document: Any) -> Tuple[Any, str]:
        if not self.tokens:
            return None, ""
        token = self.tokens[-1]
        if len(self.tokens) == 1:
            return document, token
        parent_pointer = "".join("/" + _escape(t) for t in self.tokens[:-1])
        return JSONPointer(parent_pointer).resolve(document), token

    def add(self, document: Any, value: Any) -> None:
        if not self.tokens:
            raise PatchError("add 不支持根路径替换，请用 replace")
        parent, token = self.parent_and_token(document)
        if isinstance(parent, dict):
            parent[token] = value
        elif isinstance(parent, list):
            if token == "-":
                parent.append(value)
            else:
                parent.insert(self._index(token, len(parent), allow_end=True), value)
        else:
            raise PatchError(f"无法在标量上 add：{self}")

    def remove(self, document: Any) -> Any:
        parent, token = self.parent_and_token(document)
        if isinstance(parent, dict):
            if token not in parent:
                raise PatchError(f"remove 路径不存在：{self}")
            return parent.pop(token)
        if isinstance(parent, list):
            return parent.pop(self._index(token, len(parent)))
        raise PatchError(f"无法在标量上 remove：{self}")

    def replace(self, document: Any, value: Any) -> None:
        parent, token = self.parent_and_token(document)
        if isinstance(parent, dict):
            if token not in parent:
                raise PatchError(f"replace 目标不存在：{self}")
            parent[token] = value
        elif isinstance(parent, list):
            parent[self._index(token, len(parent))] = value
        else:
            raise PatchError(f"无法在标量上 replace：{self}")


class PRDPatchEngine:
    """RFC 6902 增量热修引擎（PRD 条目级）。"""

    OPS = ("add", "remove", "replace", "move", "copy", "test")

    def apply(self, document: Any, operations: List[Dict[str, Any]],
              strict: bool = True) -> Tuple[Any, List[Dict[str, Any]]]:
        """应用 JSON Patch，返回 (新文档, 执行日志)。原文档不被修改。"""
        doc = copy.deepcopy(document)
        log: List[Dict[str, Any]] = []
        for idx, op in enumerate(operations or []):
            if not isinstance(op, dict):
                raise PatchError(f"第 {idx} 个算子不是对象：{op!r}")
            name = op.get("op")
            path = op.get("path", "")
            if name not in self.OPS:
                raise PatchError(f"第 {idx} 个算子不支持：{name!r}")
            pointer = JSONPointer(path)
            try:
                if name == "add":
                    pointer.add(doc, copy.deepcopy(op.get("value")))
                elif name == "remove":
                    pointer.remove(doc)
                elif name == "replace":
                    pointer.replace(doc, copy.deepcopy(op.get("value")))
                elif name == "test":
                    actual = pointer.resolve(doc)
                    if actual != op.get("value"):
                        raise PatchTestFailed(
                            f"test 失败：{path} 期望 {op.get('value')!r} 实际 {actual!r}")
                elif name == "move":
                    src = JSONPointer(op.get("from", ""))
                    value = src.remove(doc)
                    pointer.add(doc, value)
                elif name == "copy":
                    src = JSONPointer(op.get("from", ""))
                    pointer.add(doc, copy.deepcopy(src.resolve(doc)))
                log.append({"index": idx, "op": name, "path": str(pointer),
                            "ok": True})
            except PatchError as exc:
                log.append({"index": idx, "op": name, "path": str(pointer),
                            "ok": False, "error": str(exc)})
                if strict:
                    raise
        return doc, log

    def diff(self, original: Any, modified: Any,
             pointer: str = "") -> List[Dict[str, Any]]:
        """递归求最小差量（对象按 key，数组按下标 + 末尾增删）。"""
        if type(original) is not type(modified):
            return [{"op": "replace", "path": pointer or "", "value": modified}]
        if isinstance(original, dict):
            ops: List[Dict[str, Any]] = []
            for key in original:
                child = f"{pointer}/{_escape(key)}"
                if key not in modified:
                    ops.append({"op": "remove", "path": child})
                else:
                    ops.extend(self.diff(original[key], modified[key], child))
            for key in modified:
                if key not in original:
                    ops.append({"op": "add", "path": f"{pointer}/{_escape(key)}",
                                "value": modified[key]})
            return ops
        if isinstance(original, list):
            ops = []
            for idx in range(min(len(original), len(modified))):
                ops.extend(self.diff(original[idx], modified[idx],
                                     f"{pointer}/{idx}"))
            for idx in range(len(original), len(modified)):
                ops.append({"op": "add", "path": f"{pointer}/-",
                            "value": modified[idx]})
            for idx in range(len(original) - 1, len(modified) - 1, -1):
                ops.append({"op": "remove", "path": f"{pointer}/{idx}"})
            return ops
        if original != modified:
            return [{"op": "replace", "path": pointer or "", "value": modified}]
        return []

    # ------------------------------------------------------------------ #
    # 统计与导出
    # ------------------------------------------------------------------ #
    @staticmethod
    def _leaf_map(node: Any, pointer: str = "",
                  out: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        out = out if out is not None else {}
        if isinstance(node, dict):
            for k, v in node.items():
                PRDPatchEngine._leaf_map(v, f"{pointer}/{_escape(k)}", out)
        elif isinstance(node, list):
            for idx, v in enumerate(node):
                PRDPatchEngine._leaf_map(v, f"{pointer}/{idx}", out)
        else:
            out[pointer] = node
        return out

    @staticmethod
    def _is_covered(path: str, op_paths: List[str]) -> bool:
        """被算子覆盖：路径相等、位于算子子树内、或算子作用在该路径的祖先上。"""
        for op_path in op_paths:
            if not op_path:
                return True
            if path == op_path:
                return True
            if path.startswith(op_path.rstrip("/") + "/"):
                return True
            if op_path.startswith(path.rstrip("/") + "/"):
                return True
        return False

    def stats(self, original: Any, patched: Any,
              operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """字段级零漂移证明：逐叶子比对，未被算子覆盖的改动一律计入 drift。"""
        before = self._leaf_map(original)
        after = self._leaf_map(patched)
        common = set(before) & set(after)
        changed_common = sorted(p for p in common if before[p] != after[p])
        added = set(after) - set(before)
        removed = set(before) - set(after)
        op_paths = [str(op.get("path", "")) for op in operations
                    if op.get("op") in ("add", "remove", "replace", "move", "copy")]
        drift = [p for p in changed_common if not self._is_covered(p, op_paths)]
        patch_bytes = len(json.dumps(operations, ensure_ascii=False).encode("utf-8"))
        full_bytes = len(json.dumps(patched, ensure_ascii=False).encode("utf-8"))
        return {
            "operations": len(operations),
            "touched_paths": sorted({p for p in op_paths}),
            "changed_paths": len(set(op_paths)),
            "common_leaves": len(common),
            "changed_common_leaves": changed_common,
            "added_leaves": len(added),
            "removed_leaves": len(removed),
            "untouched_drift": drift,
            "untouched_drift_count": len(drift),
            "untouched_ratio": round((len(common) - len(changed_common))
                                     / max(len(common), 1), 4),
            "unaffected_ratio": round(1.0 - len(set(op_paths))
                                      / max(len(self._leaf_map(patched)), 1), 4),
            "patch_bytes": patch_bytes,
            "full_document_bytes": full_bytes,
            "bytes_saved_ratio": round(max(0.0, 1.0 - patch_bytes / max(full_bytes, 1)), 4),
        }

    def patch_and_export(self, prd: Dict[str, Any], operations: List[Dict[str, Any]],
                         out_dir: str,
                         validate: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
                         generated_at: str = "") -> Dict[str, Any]:
        patched, log = self.apply(prd, operations)
        gate = validate(patched) if validate else None
        gate_ok = bool(gate.get("ok")) if isinstance(gate, dict) else None
        report = {
            "schema": PATCH_SCHEMA,
            "generated_at": generated_at or _now_iso(),
            "rfc": "RFC 6902 (JSON Patch) / RFC 6901 (JSON Pointer)",
            "source_sha256": _sha256(_canonical(prd)),
            "patched_sha256": _sha256(_canonical(patched)),
            "operations": operations,
            "operation_log": log,
            "stats": self.stats(prd, patched, operations),
            "gate_after_patch": ({"ok": gate_ok,
                                  "passed_gates": gate.get("passed_gates"),
                                  "failed_checks": [c["msg"] for c in gate.get("checks", [])
                                                    if not c.get("ok")]}
                                 if isinstance(gate, dict) else None),
        }
        os.makedirs(out_dir, exist_ok=True)
        patched_path = os.path.join(out_dir, "prd_patched.json")
        diff_path = os.path.join(out_dir, "prd_patch.diff.json")
        _write_json(patched_path, patched)
        report["patch_sha256"] = _sha256(_canonical(report))
        _write_json(diff_path, report)
        return {
            # ok 与门禁结论绑定：补丁把 PRD 改坏时必须为 False（工件仍落盘供取证）
            "ok": gate_ok is not False,
            "applied": True,
            "layer": "L08",
            "engine": "PRDPatchEngine",
            "gate_ok": gate_ok,
            "out_dir": os.path.abspath(out_dir),
            "patched": patched,
            "patched_path": os.path.abspath(patched_path),
            "diff_path": os.path.abspath(diff_path),
            "stats": report["stats"],
            "gate_after_patch": report["gate_after_patch"],
            "patch_sha256": report["patch_sha256"],
        }


def _escape(token: str) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
