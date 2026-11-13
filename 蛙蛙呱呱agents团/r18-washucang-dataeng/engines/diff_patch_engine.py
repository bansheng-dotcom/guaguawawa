# -*- coding: utf-8 -*-
"""L08 局部差量层 —— RFC 6902 JSON Patch + 增量门禁影响面重算。

病灶（体检结论）：升级前 R18 调整一个水位字段或重试次数，只能整条管道重交、
全量重验，既冲掉已通过的旧门禁结果，也回答不了「这次微调到底影响哪几个门禁」；
下游拿到的是全量重算，75% 的重复消耗无法省掉。

对标标杆（Stars > 1k）：
- RFC 6902（JSON Patch，IETF 标准）：add/remove/replace/move/copy/test 六算子；
- `google/diff-match-patch`（> 7k）：文本/结构差量；
- `dbt-labs/dbt`（> 14k）：partial parse + 受影响节点选择。

本引擎落地：
1. `create_patch` / `apply_patch`：标准指针语义、越界/缺路径/`test` 失败即抛错；
2. `plan_incremental_revalidation`：按指针前缀精确映射受影响门禁（G1~G8），
   未命中规则的未知指针**保守升级为全量重验**；
3. `apply_and_plan`：一次完成「应用补丁 + 影响面 + 未受影响门禁复用」。
"""
from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Optional, Tuple

# 指针前缀 → 受影响门禁（保守原则：未命中即全量重验）
_GATE_RULES: List[Tuple[str, List[str], str]] = [
    ("/streams", ["G2", "G6"], "流/同步口径变更影响连接与增量门禁"),
    ("/sync_mode", ["G2", "G6"], "同步模式变更影响连接与增量门禁"),
    ("/connection_id", ["G2"], "连接标识变更影响连接门禁"),
    ("/source_connector", ["G2"], "来源连接器变更影响连接门禁"),
    ("/destination_connector", ["G2"], "目的地连接器变更影响连接门禁"),
    ("/watermark_field", ["G6"], "水位字段变更影响增量门禁"),
    ("/idempotency_key", ["G6"], "幂等键变更影响增量门禁"),
    ("/partition", ["G6"], "分区口径变更影响增量门禁"),
    ("/mode", ["G6"], "增量模式变更影响增量门禁"),
    ("/materialized", ["G3"], "物化方式变更影响转换门禁"),
    ("/model_name", ["G3"], "模型名变更影响转换门禁"),
    ("/depends_on", ["G3"], "依赖变更影响转换门禁"),
    ("/tasks", ["G1"], "任务集合变更影响结构门禁"),
    ("/edges", ["G1"], "依赖边变更影响结构门禁"),
    ("/dag_id", ["G1"], "DAG 标识变更影响结构门禁"),
    ("/quality", ["G4", "G5"], "质量口径变更影响质量与新鲜度门禁"),
    ("/null_ratio", ["G4"], "空值口径变更影响质量门禁"),
    ("/dup_ratio", ["G4"], "重复口径变更影响质量门禁"),
    ("/row_count", ["G4"], "行数口径变更影响质量门禁"),
    ("/age_hours", ["G5"], "新鲜度口径变更影响新鲜度门禁"),
    ("/loaded_at", ["G5"], "加载时点变更影响新鲜度门禁"),
    ("/owner", ["G7"], "owner 变更影响目录门禁"),
    ("/fields", ["G7"], "字段结构变更影响目录门禁"),
    ("/tables", ["G7"], "血缘表集合变更影响目录门禁"),
    ("/lineage", ["G7"], "血缘变更影响目录门禁"),
    ("/handoff", ["G8"], "交接声明变更影响发布门禁"),
    ("/dri", ["G8"], "DRI 变更影响发布门禁"),
    ("/bundle", ["G8"], "伴生工件变更影响发布门禁"),
]
# 纯元数据指针：不影响任何门禁，可直接复用旧结果
_METADATA_PREFIXES = ("/total_effort_h", "/total_man_days", "/critical_path",
                      "/critical_path_h", "/meta", "/exported_at", "/narrative",
                      "/recommended_id", "/scenario", "/warnings", "/parallel_levels")
_ALL_GATES = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]


def _tokens(pointer: str) -> List[str]:
    if pointer in ("", "/"):
        return []
    if not pointer.startswith("/"):
        raise ValueError(f"非法 JSON Pointer：{pointer!r}（必须以 / 开头）")
    return [t.replace("~1", "/").replace("~0", "~") for t in pointer.split("/")[1:]]


def _resolve(doc: Any, pointer: str) -> Tuple[Any, str]:
    tokens = _tokens(pointer)
    if not tokens:
        return None, ""
    node = doc
    for tok in tokens[:-1]:
        if isinstance(node, dict):
            if tok not in node:
                raise KeyError(f"路径不存在：{pointer}")
            node = node[tok]
        elif isinstance(node, list):
            idx = _index(tok, node, pointer)
            node = node[idx]
        else:
            raise KeyError(f"路径不可达：{pointer}")
    return node, tokens[-1]


def _index(token: str, seq: List[Any], pointer: str) -> int:
    if token == "-":
        return len(seq)
    try:
        idx = int(token)
    except ValueError as exc:
        raise ValueError(f"数组下标非法：{pointer}") from exc
    if idx < 0 or idx > len(seq):
        raise IndexError(f"数组下标越界：{pointer}（len={len(seq)}）")
    return idx


class DataEngDiffPatchEngine:
    """L08 RFC 6902 差量引擎 + 增量门禁影响面重算。"""

    # ------------------------------------------------------------------ #
    # 六算子
    # ------------------------------------------------------------------ #
    def apply_patch(self, document: Any, patch: List[Dict[str, Any]]) -> Any:
        if not isinstance(patch, list):
            raise ValueError("patch 必须是操作数组")
        doc = copy.deepcopy(document)
        for i, op in enumerate(patch):
            if not isinstance(op, dict) or "op" not in op:
                raise ValueError(f"第 {i} 个操作缺少 op")
            kind = op["op"]
            path = op.get("path", "")
            if kind == "test":
                node, last = _resolve(doc, path)
                actual = doc if not _tokens(path) else (
                    node[last] if isinstance(node, dict) else node[_index(last, node, path)])
                if actual != op.get("value"):
                    raise ValueError(f"test 失败：{path} 实际 {actual!r} != {op.get('value')!r}")
            elif kind == "add":
                doc = self._add(doc, path, copy.deepcopy(op.get("value")))
            elif kind == "replace":
                self._require(doc, path)
                doc = self._replace(doc, path, copy.deepcopy(op.get("value")))
            elif kind == "remove":
                self._require(doc, path)
                doc = self._remove(doc, path)
            elif kind == "copy":
                value = copy.deepcopy(self._get(doc, op.get("from", "")))
                doc = self._add(doc, path, value)
            elif kind == "move":
                value = copy.deepcopy(self._get(doc, op.get("from", "")))
                doc = self._remove(doc, op.get("from", ""))
                doc = self._add(doc, path, value)
            else:
                raise ValueError(f"不支持的 op：{kind}")
        return doc

    def _get(self, doc: Any, pointer: str) -> Any:
        if not _tokens(pointer):
            return doc
        node, last = _resolve(doc, pointer)
        if isinstance(node, dict):
            if last not in node:
                raise KeyError(f"路径不存在：{pointer}")
            return node[last]
        return node[_index(last, node, pointer)]

    def _require(self, doc: Any, pointer: str) -> None:
        self._get(doc, pointer)

    def _add(self, doc: Any, pointer: str, value: Any) -> Any:
        tokens = _tokens(pointer)
        if not tokens:
            return value
        node, last = _resolve(doc, pointer)
        if isinstance(node, dict):
            node[last] = value
        elif isinstance(node, list):
            if last == "-":
                node.append(value)
            else:
                node.insert(_index(last, node, pointer), value)
        else:
            raise TypeError(f"无法在标量上 add：{pointer}")
        return doc

    def _replace(self, doc: Any, pointer: str, value: Any) -> Any:
        tokens = _tokens(pointer)
        if not tokens:
            return value
        node, last = _resolve(doc, pointer)
        if isinstance(node, dict):
            node[last] = value
        else:
            node[_index(last, node, pointer)] = value
        return doc

    def _remove(self, doc: Any, pointer: str) -> Any:
        tokens = _tokens(pointer)
        if not tokens:
            raise ValueError("不能删除根节点")
        node, last = _resolve(doc, pointer)
        if isinstance(node, dict):
            del node[last]
        else:
            node.pop(_index(last, node, pointer))
        return doc

    # ------------------------------------------------------------------ #
    # 差量生成
    # ------------------------------------------------------------------ #
    def create_patch(self, old: Any, new: Any, pointer: str = "") -> List[Dict[str, Any]]:
        ops: List[Dict[str, Any]] = []
        if isinstance(old, dict) and isinstance(new, dict):
            for key in old:
                if key not in new:
                    ops.append({"op": "remove", "path": f"{pointer}/{_escape(key)}"})
            for key in new:
                child = f"{pointer}/{_escape(key)}"
                if key not in old:
                    ops.append({"op": "add", "path": child, "value": new[key]})
                else:
                    ops.extend(self.create_patch(old[key], new[key], child))
            return ops
        if isinstance(old, list) and isinstance(new, list):
            common = min(len(old), len(new))
            for i in range(common):
                ops.extend(self.create_patch(old[i], new[i], f"{pointer}/{i}"))
            for i in range(common, len(new)):
                ops.append({"op": "add", "path": f"{pointer}/{i}", "value": new[i]})
            for i in range(len(old) - 1, len(new) - 1, -1):
                ops.append({"op": "remove", "path": f"{pointer}/{i}"})
            return ops
        if old != new:
            ops.append({"op": "replace" if _tokens(pointer) else "replace",
                        "path": pointer or "", "value": new})
        return ops

    # ------------------------------------------------------------------ #
    # 增量门禁影响面
    # ------------------------------------------------------------------ #
    def plan_incremental_revalidation(self, patch: List[Dict[str, Any]]) -> Dict[str, Any]:
        affected: Dict[str, str] = {}
        metadata_only = True
        unknown: List[str] = []
        for op in patch:
            path = op.get("path") or ""
            if any(path == p or path.startswith(p + "/") for p in _METADATA_PREFIXES):
                continue
            metadata_only = False
            matched = False
            for prefix, gates, reason in _GATE_RULES:
                if path == prefix or path.startswith(prefix + "/"):
                    for g in gates:
                        affected.setdefault(g, reason)
                    matched = True
                    break
            if not matched:
                unknown.append(path)
        if metadata_only and patch:
            return {
                "ok": True,
                "affected_gates": [],
                "reuse_gates": list(_ALL_GATES),
                "requires_full_revalidation": False,
                "unknown_pointers": [],
                "reason": "仅元数据变更（工时/叙述/导出时间），8 维门禁结果可全部复用",
            }
        if unknown:
            return {
                "ok": True,
                "affected_gates": list(_ALL_GATES),
                "reuse_gates": [],
                "requires_full_revalidation": True,
                "unknown_pointers": unknown,
                "reason": f"存在未登记指针 {unknown}，按保守原则全量重验",
            }
        affected_list = sorted(affected)
        return {
            "ok": True,
            "affected_gates": affected_list,
            "reuse_gates": [g for g in _ALL_GATES if g not in affected],
            "requires_full_revalidation": False,
            "unknown_pointers": [],
            "reasons": {g: affected[g] for g in affected_list},
            "reason": "按指针前缀精确映射受影响门禁",
        }

    # ------------------------------------------------------------------ #
    # 一次完成
    # ------------------------------------------------------------------ #
    def apply_and_plan(self, base: Any,
                       patch: List[Dict[str, Any]]) -> Dict[str, Any]:
        patched = self.apply_patch(base, patch)
        plan = self.plan_incremental_revalidation(patch)
        return {"ok": True, "patched": patched, "patch": patch,
                "plan": plan, "op_count": len(patch),
                "pointers": [op.get("path") for op in patch]}


def _escape(token: str) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


# --------------------------------------------------------------------------- #
# CLI：python -m engines.diff_patch_engine --base x.json --out ...
# --------------------------------------------------------------------------- #
def _cli(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="R18 L08 RFC 6902 差量引擎")
    ap.add_argument("--base", required=True, help="基线 JSON")
    ap.add_argument("--patch", default="", help="补丁 JSON（缺省则演示自动生成）")
    ap.add_argument("--out", default="", help="结果 JSON 输出路径")
    args = ap.parse_args(argv)

    with open(args.base, encoding="utf-8") as f:
        base = json.load(f)
    engine = DataEngDiffPatchEngine()
    if args.patch:
        with open(args.patch, encoding="utf-8") as f:
            patch = json.load(f)
    else:
        # 演示：微调工时 + 改一条依赖原因（元数据 + 结构各一条），验证精确影响面
        target = copy.deepcopy(base)
        if "total_effort_h" in target:
            target["total_effort_h"] = round(float(target["total_effort_h"]) + 1.0, 2)
        if isinstance(target.get("edges"), list) and target["edges"]:
            target["edges"][0]["reason"] = "源表画像决定建模口径（已精确到字段级）"
        target.setdefault("meta", {})["patched_by"] = "engines.diff_patch_engine"
        patch = engine.create_patch(base, target)

    result = engine.apply_and_plan(base, patch)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    print("__AGENT_RESULT__ " + json.dumps(
        {"ok": result["ok"], "op_count": result["op_count"],
         "affected_gates": result["plan"]["affected_gates"],
         "reuse_gates": result["plan"]["reuse_gates"],
         "requires_full_revalidation": result["plan"]["requires_full_revalidation"],
         "out": args.out}, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
