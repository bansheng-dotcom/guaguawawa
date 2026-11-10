# -*- coding: utf-8 -*-
"""L08 局部差量层：完整 RFC 6902 JSON Patch 算子、JSON Pointer 转义与差量反推。

对标标杆:
- RFC 6902 / RFC 6901 / evanphx/json-patch (2.5k⭐) / google/diff-match-patch (7k⭐)
吸收的机制:
- RFC 6902 六算子（add/remove/replace/move/copy/test）与 RFC 6901 JSON Pointer：
  `~1` → `/`、`~0` → `~` 逐 token 反转义，数组下标语义与 `-` 末尾追加；
- json-patch 的“整包原子性”：任一算子失败即抛 PatchError/PatchTestFailed，
  不会留下半截文档；test 算子用于变更前的前置断言（乐观并发控制）；
- diff-match-patch 的最小补丁思想：create_patch 递归比对两个版本文档，只产出
  必要的最小算子序列（新增键 add、删除键 remove、标量 replace、数组下标
  replace/追加 add/截断 remove），并用规范化 JSON 的 SHA256 记录改前/改后摘要。

纯标准库实现（copy/json/hashlib），Windows 路径安全。
"""
from __future__ import annotations
import copy
import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple


class PatchError(Exception):
    """RFC 6902 补丁执行失败（路径非法、目标缺失、算子未知等）。"""


class PatchTestFailed(PatchError):
    """test 算子前置断言不成立（当前值与期望值不一致）。"""


def _unescape_token(token: str) -> str:
    """按 RFC 6901 反转义：先 ~1 → '/'，再 ~0 → '~'（顺序不可颠倒）。"""
    return token.replace("~1", "/").replace("~0", "~")


def _escape_token(token: str) -> str:
    """按 RFC 6901 转义：先 ~ → ~0，再 / → ~1（顺序不可颠倒）。"""
    return token.replace("~", "~0").replace("/", "~1")


def _parse_pointer(path: Any) -> List[str]:
    """把 JSON Pointer 解析为 token 列表；空串表示整个文档根。"""
    if not isinstance(path, str):
        raise PatchError(f"path 必须是字符串，收到 {type(path).__name__}")
    if path == "":
        return []
    if not path.startswith("/"):
        raise PatchError(f"非法 JSON Pointer（必须以 '/' 开头）：{path!r}")
    return [_unescape_token(token) for token in path.split("/")[1:]]


def _list_index(token: str, length: int, allow_end: bool = False) -> int:
    """把数组 token 解析为下标；"-" 追加语义单独处理。"""
    if token != "-" and not token.lstrip("-").isdigit():
        raise PatchError(f"非法数组下标：{token!r}")
    if token == "-":
        if not allow_end:
            raise PatchError("'-' 仅允许用于 add 的末尾追加")
        return length
    index = int(token)
    upper = length if allow_end else length - 1
    if index < 0 or index > upper:
        raise PatchError(f"数组下标越界：{index}（长度 {length}）")
    return index


class ResearchDiffPatchEngine:
    """战略研究文档的 RFC 6902 差量引擎（apply / create_patch / 完整性摘要）。"""

    # ------------------------------------------------------------------
    # 文档读取
    # ------------------------------------------------------------------
    def _get(self, doc: Any, tokens: Sequence[str]) -> Any:
        current = doc
        walked: List[str] = []
        for token in tokens:
            if isinstance(current, dict):
                if token not in current:
                    raise PatchError(
                        f"路径不存在：/{'/'.join(_escape_token(t) for t in walked + [token])}")
                current = current[token]
            elif isinstance(current, list):
                current = current[_list_index(token, len(current))]
            else:
                raise PatchError(f"路径穿越到标量节点：/{'/'.join(walked)}")
            walked.append(token)
        return current

    def _add(self, doc: Any, tokens: Sequence[str], value: Any) -> Any:
        if not tokens:
            return value
        parent = self._get(doc, tokens[:-1])
        last = tokens[-1]
        if isinstance(parent, dict):
            parent[last] = value
            return doc
        if isinstance(parent, list):
            if last == "-":
                parent.append(value)
            else:
                parent.insert(_list_index(last, len(parent), allow_end=True), value)
            return doc
        raise PatchError("add 的父节点既不是对象也不是数组")

    def _remove(self, doc: Any, tokens: Sequence[str]) -> Tuple[Any, Any]:
        if not tokens:
            raise PatchError("不允许 remove 文档根节点")
        parent = self._get(doc, tokens[:-1])
        last = tokens[-1]
        if isinstance(parent, dict):
            if last not in parent:
                raise PatchError(f"remove 目标不存在：{last!r}")
            return doc, parent.pop(last)
        if isinstance(parent, list):
            index = _list_index(last, len(parent))
            return doc, parent.pop(index)
        raise PatchError("remove 的父节点既不是对象也不是数组")

    def _replace(self, doc: Any, tokens: Sequence[str], value: Any) -> Any:
        if not tokens:
            return value
        parent = self._get(doc, tokens[:-1])
        last = tokens[-1]
        if isinstance(parent, dict):
            if last not in parent:
                raise PatchError(f"replace 目标不存在：{last!r}")
            parent[last] = value
            return doc
        if isinstance(parent, list):
            parent[_list_index(last, len(parent))] = value
            return doc
        raise PatchError("replace 的父节点既不是对象也不是数组")

    # ------------------------------------------------------------------
    # 单算子/整包应用
    # ------------------------------------------------------------------
    def _apply_op(self, doc: Any, op: Any) -> Any:
        if not isinstance(op, dict):
            raise PatchError(f"算子必须是对象，收到 {type(op).__name__}")
        action = op.get("op")
        if not isinstance(action, str) or action not in (
                "add", "remove", "replace", "move", "copy", "test"):
            raise PatchError(f"未知算子：{action!r}")
        if "path" not in op:
            raise PatchError(f"算子 {action} 缺少 path")
        tokens = _parse_pointer(op["path"])

        if action == "add":
            return self._add(doc, tokens, copy.deepcopy(op.get("value")))
        if action == "remove":
            doc, _ = self._remove(doc, tokens)
            return doc
        if action == "replace":
            return self._replace(doc, tokens, copy.deepcopy(op.get("value")))
        if action in ("move", "copy"):
            if "from" not in op:
                raise PatchError(f"算子 {action} 缺少 from")
            from_tokens = _parse_pointer(op["from"])
            source = copy.deepcopy(self._get(doc, from_tokens))
            if action == "move":
                # 同路径 move 是合法空操作；目标位于源路径内部则违反 RFC 6902 §4.4。
                if list(tokens) == list(from_tokens):
                    return doc
                if len(tokens) > len(from_tokens) and \
                        list(tokens[:len(from_tokens)]) == list(from_tokens):
                    raise PatchError("move 的目标不得位于源路径内部")
                doc, _ = self._remove(doc, from_tokens)
            return self._add(doc, tokens, source)
        # action == "test"
        current = self._get(doc, tokens)
        expected = op.get("value")
        if current != expected:
            raise PatchTestFailed(
                f"test 失败：path={op.get('path')!r} expected={expected!r} "
                f"actual={current!r}")
        return doc

    def apply(self, doc: Any, ops: Sequence[Dict[str, Any]]) -> Any:
        """应用 RFC 6902 算子序列，返回新文档（深拷贝，绝不污染原文档）。"""
        if not isinstance(ops, (list, tuple)):
            raise PatchError(f"补丁必须是算子数组，收到 {type(ops).__name__}")
        working = copy.deepcopy(doc)
        for index, op in enumerate(ops):
            try:
                working = self._apply_op(working, op)
            except PatchTestFailed:
                raise
            except PatchError as exc:
                raise PatchError(f"第 {index} 个算子失败（{op!r}）：{exc}") from exc
        return working

    # ------------------------------------------------------------------
    # 差量反推
    # ------------------------------------------------------------------
    def _diff(self, source: Any, target: Any, path: str,
              ops: List[Dict[str, Any]]) -> None:
        if isinstance(source, dict) and isinstance(target, dict):
            for key in source:
                if key not in target:
                    ops.append({"op": "remove",
                                "path": f"{path}/{_escape_token(str(key))}"})
            for key in target:
                if key not in source:
                    ops.append({"op": "add",
                                "path": f"{path}/{_escape_token(str(key))}",
                                "value": copy.deepcopy(target[key])})
            for key in source:
                if key in target:
                    self._diff(source[key], target[key],
                               f"{path}/{_escape_token(str(key))}", ops)
            return

        if isinstance(source, list) and isinstance(target, list):
            common = min(len(source), len(target))
            for index in range(common):
                self._diff(source[index], target[index], f"{path}/{index}", ops)
            if len(target) > len(source):
                for index in range(len(source), len(target)):
                    ops.append({"op": "add", "path": f"{path}/-",
                                "value": copy.deepcopy(target[index])})
            elif len(source) > len(target):
                for index in range(len(source) - 1, len(target) - 1, -1):
                    ops.append({"op": "remove", "path": f"{path}/{index}"})
            return

        if type(source) is not type(target) or source != target:
            ops.append({"op": "replace", "path": path,
                        "value": copy.deepcopy(target)})

    def create_patch(self, source: Any, target: Any) -> List[Dict[str, Any]]:
        """递归比对两个版本文档，反推满足 apply(source, patch) == target 的补丁。"""
        ops: List[Dict[str, Any]] = []
        self._diff(source, target, "", ops)
        return ops

    # ------------------------------------------------------------------
    # 完整性摘要
    # ------------------------------------------------------------------
    @staticmethod
    def _canonical_sha256(doc: Any) -> str:
        """规范化 JSON（ensure_ascii=False, sort_keys=True）后取 SHA256。"""
        canonical = json.dumps(doc, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _describe(op: Dict[str, Any]) -> str:
        action = op.get("op")
        if action in ("move", "copy"):
            return f"{action.upper()} {op.get('from')} -> {op.get('path')}"
        if action == "test":
            return f"TEST {op.get('path')} == {op.get('value')!r}"
        if action == "remove":
            return f"REMOVE {op.get('path')}"
        return f"{str(action).upper()} {op.get('path')} -> {op.get('value')!r}"

    def apply_with_integrity(self, doc: Any,
                             ops: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """应用补丁并返回改前/改后 SHA256 与人类可读的算子执行日志。"""
        ops_list = list(ops) if isinstance(ops, (list, tuple)) else []
        sha_before = self._canonical_sha256(doc)
        patched = self.apply(doc, ops_list)
        sha_after = self._canonical_sha256(patched)
        return {
            "doc": patched,
            "applied": [self._describe(op) for op in ops_list],
            "sha256_before": sha_before,
            "sha256_after": sha_after,
            "changed": sha_before != sha_after,
        }
