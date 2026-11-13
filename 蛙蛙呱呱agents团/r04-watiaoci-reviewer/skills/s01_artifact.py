# -*- coding: utf-8 -*-
"""s01 成品实体核验（artifact）：inventory / verify 两动作。

口径来源：Intense-Visions__harness-engineering · harness-verification（三级证据链）。
- inventory：逐项 {path, type, required} 检查存在/非空/大小；required 缺失 → BLOCKED。
- verify：L1 EXISTS → L2 SUBSTANTIVE → L3 WIRED 级别串行，每级不过即停；
  verdict COMPLETE / INCOMPLETE + gaps。评审只记录不修复。
阈值：thresholds.json → artifact.*。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from . import _common as c

NAME = "artifact"
DESC = "成品实体核验：inventory（存在/非空/大小）与 verify（EXISTS/SUBSTANTIVE/WIRED 三级证据链）"

ACTIONS = {
    "inventory": "逐项检查成品物料存在/非空/大小，required 缺失即 BLOCKED",
    "verify": "三级证据链核验：L1 存在 → L2 实质（stub 反模式扫描）→ L3 接线（被引用/被测试/入口豁免）",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# inventory
# --------------------------------------------------------------------------- #
def _inventory_core(data: Dict[str, Any], base_dir: Optional[str] = None) -> Dict[str, Any]:
    th = c.load_thresholds()["artifact"]
    min_bytes = th["min_file_bytes"]
    items_in = data.get("items") or []
    checks: List[Dict[str, Any]] = []
    items: List[Dict[str, Any]] = []
    missing_required: List[Dict[str, Any]] = []
    missing_optional: List[Dict[str, Any]] = []

    for it in items_in:
        path = str(it.get("path") or "")
        typ = str(it.get("type") or "file")
        required = bool(it.get("required", True))
        resolved = c.resolve_path(path, base_dir)
        exists = resolved is not None
        size_bytes = 0
        if resolved:
            try:
                size_bytes = os.path.getsize(resolved)
            except OSError:
                size_bytes = 0
        empty = exists and size_bytes < max(1, int(min_bytes))
        status = "ok" if exists and not empty else ("missing_optional" if not required else "missing")
        if not exists:
            entry = {"path": path, "type": typ, "required": required}
            (missing_optional if not required else missing_required).append(entry)
        items.append({
            "path": path, "type": typ, "required": required,
            "exists": exists, "resolved_to": resolved, "size_bytes": size_bytes,
            "empty": bool(empty), "status": status,
        })

    for it in items:
        if not it["exists"]:
            if it["required"]:
                checks.append(c.ck(False, f"物料缺失：{it['path']}", "artifact:exists",
                                   "CRITICAL", **{"path": it["path"], "required": True}))
            else:
                checks.append(c.ck(True, f"可选物料缺失（不阻断）：{it['path']}",
                                   "artifact:exists", "INFO", **{"path": it["path"], "required": False}))
        elif it["empty"]:
            sev = "CRITICAL" if it["required"] else "INFO"
            checks.append(c.ck(not it["required"], f"物料为空：{it['path']}",
                               "artifact:empty", sev, **{"path": it["path"]}))
        else:
            checks.append(c.ck(True, f"物料就绪：{it['path']}（{it['size_bytes']}B）",
                               "artifact:exists", **{"path": it["path"],
                                                    "size_bytes": it["size_bytes"]}))
    if not items_in:
        checks.append(c.ck(False, "物料清单为空，无实体可核验", "artifact:items", "CRITICAL"))

    verdict = "BLOCKED" if missing_required else "COMPLETE"
    out = c.result(checks,
                   items=items,
                   item_count=len(items),
                   missing_required=missing_required,
                   missing_required_count=len(missing_required),
                   missing_optional=missing_optional,
                   verdict=verdict,
                   next="补齐缺失的必需物料后重新 inventory" if missing_required else "物料齐备，可进入三级证据链 verify",
                   )
    out["ok"] = out["ok"] and verdict == "COMPLETE"
    return out


def inventory(data: Dict[str, Any], base_dir: Optional[str] = None) -> Dict[str, Any]:
    return _inventory_core(data, base_dir)


# --------------------------------------------------------------------------- #
# verify：三级证据链
# --------------------------------------------------------------------------- #
def _effective_content(art: Dict[str, Any], base_dir: Optional[str]) -> Dict[str, Any]:
    """返回 {exists, size_bytes, content}；content 声明优先，其次磁盘。"""
    path = str(art.get("path") or "")
    content = art.get("content")
    if content is not None:
        text = str(content)
        return {"exists": True, "size_bytes": len(text.encode("utf-8")), "content": text}
    resolved = c.resolve_path(path, base_dir)
    if resolved:
        try:
            with open(resolved, encoding="utf-8", errors="replace") as f:
                text = f.read()
            return {"exists": True, "size_bytes": os.path.getsize(resolved), "content": text}
        except OSError:
            pass
    declared_size = art.get("size_bytes")
    declared_exists = art.get("exists")
    if declared_exists:
        text = "" if declared_size is None else ""
        return {"exists": bool(declared_exists), "size_bytes": int(declared_size or 0), "content": text}
    return {"exists": False, "size_bytes": 0, "content": ""}


def _scan_stub(content: str, typ: str, th: Dict[str, Any]) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    lines = content.splitlines()
    for i, ln in enumerate(lines, 1):
        for marker in th["stub_markers"]:
            if marker in ln:
                hits.append({"rule": "stub_marker", "marker": marker, "line": i,
                             "text": ln.strip()[:80]})
                break
    lowered = content.strip().lower()
    if typ == "test":
        for marker in th["test_skip_markers"]:
            if marker in content:
                hits.append({"rule": "test_skip_marker", "marker": marker, "line": None,
                             "text": f"测试含跳过标记 {marker}"})
                break
    else:
        for i, ln in enumerate(lines):
            s = ln.strip()
            if s.lower() == "raise notimplementederror":
                hits.append({"rule": "raise_not_implemented", "marker": "raise NotImplementedError",
                             "line": i + 1, "text": s[:80]})
        for i in range(len(lines) - 1):
            if lines[i].strip().startswith(("def ", "function ")):
                nxt = lines[i + 1].strip()
                if nxt == "pass":
                    hits.append({"rule": "empty_function_body", "marker": "pass",
                                 "line": i + 2, "text": f"空函数体：{lines[i].strip()[:60]}"})
        if lowered and lowered in [p.strip().lower() for p in th["stub_code_patterns"]]:
            hits.append({"rule": "sole_stub_statement", "marker": lowered,
                         "line": None, "text": f"全文仅一句桩代码：{lowered}"})
    return hits


def _verify_core(data: Dict[str, Any], base_dir: Optional[str] = None) -> Dict[str, Any]:
    th = c.load_thresholds()["artifact"]
    arts_in = data.get("artifacts") or []
    checks: List[Dict[str, Any]] = []
    level_results: Dict[str, Dict[str, Any]] = {lv: {"per_artifact": {}, "failed": []}
                                               for lv in th["levels"]}
    gaps: List[Dict[str, Any]] = []
    per_artifact: Dict[str, Dict[str, Any]] = {}

    if not arts_in:
        checks.append(c.ck(False, "manifest 为空，无工件可核验", "artifact:manifest", "CRITICAL"))

    for art in arts_in:
        path = str(art.get("path") or "")
        typ = str(art.get("type") or "code")
        entry_point = bool(art.get("entry_point", False))
        references = list(art.get("references") or [])
        tested = list(art.get("tested") or [])
        eff = _effective_content(art, base_dir)

        # L1 EXISTS
        l1_ok = bool(path) and eff["exists"] and eff["size_bytes"] >= max(1, th["min_file_bytes"])
        rec: Dict[str, Any] = {
            "path": path, "type": typ, "entry_point": entry_point,
            "l1_exists": {"ok": l1_ok, "size_bytes": eff["size_bytes"], "exists": eff["exists"]},
            "l2_substantive": None, "l3_wired": None, "passed": False,
        }
        level_results["L1_EXISTS"]["per_artifact"][path] = rec["l1_exists"]
        if not l1_ok:
            reason = "路径为空" if not path else ("文件不存在" if not eff["exists"] else "文件为空")
            level_results["L1_EXISTS"]["failed"].append({"path": path, "reason": reason})
            gaps.append({"path": path, "level": "L1_EXISTS", "reason": reason})
            rec["failed_level"] = "L1_EXISTS"
            per_artifact[path] = rec
            checks.append(c.ck(False, f"L1 不达：{path}（{reason}）", "artifact:L1", "CRITICAL", **{"path": path}))
            continue

        # L2 SUBSTANTIVE（L1 过才进）
        hits = _scan_stub(eff["content"], typ, th)
        l2_ok = not hits
        rec["l2_substantive"] = {"ok": l2_ok, "stub_hits": hits}
        level_results["L2_SUBSTANTIVE"]["per_artifact"][path] = rec["l2_substantive"]
        if not l2_ok:
            level_results["L2_SUBSTANTIVE"]["failed"].append(
                {"path": path, "hits": hits})
            gaps.append({"path": path, "level": "L2_SUBSTANTIVE",
                         "reason": f"stub 反模式 {len(hits)} 处", "stub_hits": hits})
            rec["failed_level"] = "L2_SUBSTANTIVE"
            per_artifact[path] = rec
            checks.append(c.ck(False, f"L2 不达：{path}（stub 反模式 {len(hits)} 处）",
                               "artifact:L2", "CRITICAL", **{"path": path, "stub_hits": hits[:5]}))
            continue

        # L3 WIRED（L2 过才进）
        wired_reason = None
        if entry_point:
            wired_reason = "entry_point"
        elif references:
            wired_reason = f"referenced_by:{len(references)}"
        elif tested:
            wired_reason = f"tested_by:{len(tested)}"
        l3_ok = wired_reason is not None
        rec["l3_wired"] = {"ok": l3_ok, "reason": wired_reason,
                           "references": references, "tested": tested,
                           "entry_point": entry_point}
        level_results["L3_WIRED"]["per_artifact"][path] = rec["l3_wired"]
        if not l3_ok:
            level_results["L3_WIRED"]["failed"].append({"path": path, "reason": "无引用且无测试且非入口"})
            gaps.append({"path": path, "level": "L3_WIRED", "reason": "未被任何其它文件引用/测试覆盖，且不是入口点"})
            rec["failed_level"] = "L3_WIRED"
            per_artifact[path] = rec
            checks.append(c.ck(False, f"L3 不达：{path}（孤岛工件，未接线）", "artifact:L3", "CRITICAL", **{"path": path}))
            continue

        rec["passed"] = True
        per_artifact[path] = rec
        checks.append(c.ck(True, f"三级全过：{path}（{wired_reason}）", "artifact:verify",
                           **{"path": path, "wired_reason": wired_reason}))

    complete = bool(arts_in) and all(r.get("passed") for r in per_artifact.values())
    verdict = "COMPLETE" if complete else "INCOMPLETE"
    passed_count = sum(1 for r in per_artifact.values() if r.get("passed"))
    stub_total = sum(len((r.get("l2_substantive") or {}).get("stub_hits") or []) for r in per_artifact.values())
    out = c.result(checks,
                   level_results=level_results,
                   per_artifact=per_artifact,
                   artifact_count=len(arts_in),
                   passed_count=passed_count,
                   stub_hit_count=stub_total,
                   gaps=gaps,
                   verdict=verdict,
                   next="补齐 gaps 后重新 verify（评审只记录，不代改）" if verdict == "INCOMPLETE" else "工件链完整，可出核验结论",
                   )
    out["ok"] = out["ok"] and verdict == "COMPLETE"
    return out


def verify(data: Dict[str, Any], base_dir: Optional[str] = None) -> Dict[str, Any]:
    return _verify_core(data, base_dir)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    base_dir = os.path.dirname(os.path.abspath(args.input))
    if args.action == "inventory":
        return inventory(data, base_dir)
    if args.action == "verify":
        return verify(data, base_dir)
    raise SystemExit(f"未知动作：{args.action}")
