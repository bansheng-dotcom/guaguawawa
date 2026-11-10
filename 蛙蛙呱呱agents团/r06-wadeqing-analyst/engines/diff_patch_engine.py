# -*- coding: utf-8 -*-
"""L08 局部差量层 (RFC 6901/6902 Differential Patch & Recalculation Layer)
对标开源: RFC 6901 (JSON Pointer) / RFC 6902 (JSON Patch) / Immer / diff-match-patch
架构跃迁 (本轮新增):
1. RFC 6901 指针递归差量：嵌套对象与数组下标精准定位，支持 '-' 数组追加，转义 '~0'/'~1'；
2. RFC 6902 全算子：add/remove/replace/move/copy/test，test 不符即抛错，杜绝静默错改；
3. 逆补丁与回放校验：可把差量无损回滚到旧快照，并保留局部切片差量重算能力。
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional


class PatchApplyError(RuntimeError):
    """JSON Patch 应用失败。"""


class PatchTestFailed(PatchApplyError):
    """test 算子断言失败。"""


def _escape(token: str) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def _unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


class AnalysisDiffPatchEngine:
    """局部差量重算与 JSON Patch 补丁引擎。"""

    # ------------------------------------------------------------------ #
    # RFC 6901 指针
    # ------------------------------------------------------------------ #
    @staticmethod
    def parse_pointer(pointer: str) -> List[str]:
        if pointer in ("", None):
            return []
        if not pointer.startswith("/"):
            raise PatchApplyError(f"Invalid JSON Pointer: {pointer}")
        return [_unescape(t) for t in pointer.split("/")[1:]]

    @staticmethod
    def build_pointer(tokens: List[str]) -> str:
        return "".join(f"/{_escape(t)}" for t in tokens)

    def _get(self, root: Any, tokens: List[str]) -> Any:
        node = root
        for token in tokens:
            if isinstance(node, list):
                if token == "-":
                    raise PatchApplyError("'-' is only valid in add operation")
                node = node[int(token)]
            elif isinstance(node, dict):
                node = node[token]
            else:
                raise PatchApplyError(f"Cannot traverse token '{token}'")
        return node

    # ------------------------------------------------------------------ #
    # 差量生成
    # ------------------------------------------------------------------ #
    def create_patch(self, old_state: Any, new_state: Any,
                     path: str = "") -> List[Dict[str, Any]]:
        """递归计算两份快照之间的 RFC 6902 差量 Patch。"""
        patches: List[Dict[str, Any]] = []

        if isinstance(old_state, dict) and isinstance(new_state, dict):
            for key, new_val in new_state.items():
                child_path = f"{path}/{_escape(key)}"
                if key not in old_state:
                    patches.append({"op": "add", "path": child_path, "value": copy.deepcopy(new_val)})
                else:
                    patches.extend(self.create_patch(old_state[key], new_val, child_path))
            for key in old_state:
                if key not in new_state:
                    patches.append({"op": "remove", "path": f"{path}/{_escape(key)}"})
            return patches

        if isinstance(old_state, list) and isinstance(new_state, list):
            for i in range(min(len(old_state), len(new_state))):
                patches.extend(self.create_patch(old_state[i], new_state[i], f"{path}/{i}"))
            for i in range(len(old_state) - 1, len(new_state) - 1, -1):
                patches.append({"op": "remove", "path": f"{path}/{i}"})
            for item in new_state[len(old_state):]:
                patches.append({"op": "add", "path": f"{path}/-", "value": copy.deepcopy(item)})
            return patches

        if old_state != new_state:
            patches.append({"op": "replace", "path": path, "value": copy.deepcopy(new_state)})
        return patches

    # ------------------------------------------------------------------ #
    # 算子实现
    # ------------------------------------------------------------------ #
    def _add(self, root: Any, tokens: List[str], value: Any) -> Any:
        if not tokens:
            return copy.deepcopy(value)
        parent = self._get(root, tokens[:-1])
        last = tokens[-1]
        if isinstance(parent, list):
            if last == "-":
                parent.append(copy.deepcopy(value))
            else:
                idx = int(last)
                if idx > len(parent):
                    raise PatchApplyError(f"Array index out of range: {idx}")
                parent.insert(idx, copy.deepcopy(value))
        elif isinstance(parent, dict):
            parent[last] = copy.deepcopy(value)
        else:
            raise PatchApplyError("add target parent is not container")
        return root

    def _remove(self, root: Any, tokens: List[str]) -> Any:
        if not tokens:
            raise PatchApplyError("Cannot remove root")
        parent = self._get(root, tokens[:-1])
        last = tokens[-1]
        if isinstance(parent, list):
            del parent[int(last)]
        elif isinstance(parent, dict):
            if last not in parent:
                raise PatchApplyError(f"Path not found: {self.build_pointer(tokens)}")
            del parent[last]
        else:
            raise PatchApplyError("remove target parent is not container")
        return root

    def _apply_one(self, root: Any, patch: Dict[str, Any]) -> Any:
        op = patch.get("op")
        tokens = self.parse_pointer(patch.get("path", ""))
        if op == "add":
            return self._add(root, tokens, patch.get("value"))
        if op == "remove":
            return self._remove(root, tokens)
        if op == "replace":
            self._get(root, tokens)  # replace 要求目标已存在
            if not tokens:
                return copy.deepcopy(patch.get("value"))
            return self._add(root, tokens, patch.get("value"))
        if op == "move":
            src = self.parse_pointer(patch["from"])
            value = copy.deepcopy(self._get(root, src))
            root = self._remove(root, src)
            return self._add(root, tokens, value)
        if op == "copy":
            src = self.parse_pointer(patch["from"])
            value = self._get(root, src)
            return self._add(root, tokens, value)
        if op == "test":
            actual = self._get(root, tokens)
            if actual != patch.get("value"):
                raise PatchTestFailed(
                    f"test op failed at {patch.get('path')}: {actual!r} != {patch.get('value')!r}")
            return root
        raise PatchApplyError(f"Unsupported op: {op}")

    def apply_patch(self, target: Any, patches: List[Dict[str, Any]]) -> Any:
        """将补丁应用到目标状态上（RFC 6902 完整语义）。"""
        res = copy.deepcopy(target)
        for patch in patches:
            res = self._apply_one(res, patch)
        return res

    # ------------------------------------------------------------------ #
    # 逆补丁
    # ------------------------------------------------------------------ #
    def _resolved_add_path(self, state: Any, tokens: List[str]) -> str:
        """把 add 的 '-' 追加指针解析为具体下标，便于生成可回放的逆补丁。"""
        if tokens and tokens[-1] == "-":
            parent = self._get(state, tokens[:-1])
            if isinstance(parent, list):
                return self.build_pointer(tokens[:-1] + [str(len(parent))])
        return self.build_pointer(tokens)

    def invert_patch(self, old_state: Any, patches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成逆补丁，可把 new_state 无损回滚为 old_state。"""
        state = copy.deepcopy(old_state)
        inverses: List[Dict[str, Any]] = []
        for patch in patches:
            op = patch.get("op")
            tokens = self.parse_pointer(patch.get("path", ""))
            if op == "add":
                inverses.append({"op": "remove",
                                 "path": self._resolved_add_path(state, tokens)})
            elif op == "remove":
                prev = copy.deepcopy(self._get(state, tokens))
                inverses.append({"op": "add", "path": patch["path"], "value": prev})
            elif op == "replace":
                prev = copy.deepcopy(self._get(state, tokens))
                inverses.append({"op": "replace", "path": patch["path"], "value": prev})
            elif op == "move":
                inverses.append({"op": "move", "from": patch["path"], "path": patch["from"]})
            elif op == "copy":
                inverses.append({"op": "remove",
                                 "path": self._resolved_add_path(state, tokens)})
            state = self._apply_one(state, patch)
        inverses.reverse()
        return inverses

    def apply_and_verify(self, target: Any, patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """应用差量并生成逆补丁，返回可回滚的变更凭据。"""
        new_state = self.apply_patch(target, patches)
        inverse = self.invert_patch(target, patches)
        restored = self.apply_patch(new_state, inverse)
        return {
            "new_state": new_state,
            "inverse_patch": inverse,
            "roundtrip_exact": restored == target,
            "ops_count": len(patches),
        }

    # ------------------------------------------------------------------ #
    # 局部切片重算
    # ------------------------------------------------------------------ #
    def recalculate_slice(self, dataset: List[Dict[str, Any]], filter_col: str,
                          filter_val: Any, metric_col: str) -> Dict[str, Any]:
        """局部切片下钻差量计算：仅计算满足过滤条件的局部切片指标。"""
        matched = [r for r in dataset if str(r.get(filter_col, "")) == str(filter_val)]
        if not matched:
            return {"slice_filter": {filter_col: filter_val}, "count": 0, "sum": 0.0, "mean": 0.0}

        vals = [float(r.get(metric_col, 0.0)) for r in matched if r.get(metric_col) is not None]
        total = sum(vals)
        mean_val = (total / len(vals)) if vals else 0.0
        return {
            "slice_filter": {filter_col: filter_val},
            "count": len(vals),
            "sum": round(total, 4),
            "mean": round(mean_val, 4),
            "differential_recalculated": True,
        }
