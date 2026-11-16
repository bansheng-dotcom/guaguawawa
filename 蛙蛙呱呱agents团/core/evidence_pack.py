# -*- coding: utf-8 -*-
"""core/evidence_pack —— 把一次项目的全部输入，收成「可寻址的数字索引」。

为什么需要：报告要达到调研级（每节 600 字、每节 1 图、每句带数），
输入就不能是一份 result，而是一整个项目的观测（obs_*.json）、台账（ledger）、
派生指标（derived_metrics）、测算（sizing）、角色门禁结果（*_result.json）和 CSV。

本模块只做三件事：
  1. 扫目录，读 JSON / CSV，把每个数字摊成一条可寻址记录（id + name + value +
     unit + period + source；派生指标保留 formula 与 inputs）；
  2. 写 evidence_pack.json（写稿与校验共用同一份事实源）；
  3. 写 brief.md（给模型/人看的「可用数字清单」，按来源分组）。

写稿时引用 id（如 S01 / D01 / facts:sl25），校验时按 id 与数值双重比对，
所以「编一个数」会在两个地方同时被拦。
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SKIP_DIRS = {"raw", "screens", "__pycache__", "out", "node_modules", ".git",
             ".chrome8", "_archive"}
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_CSV_ROWS = 5000


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()[:12]


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _id_from(item: Dict[str, Any], prefix: str, i: int) -> str:
    for k in ("id", "code", "key", "metric_id"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return f"{prefix}{i:02d}"


def _push(out: List[Dict[str, Any]], seen: Dict[str, int], rec: Dict[str, Any]) -> None:
    """同 id 同值去重；同 id 不同值时递增后缀（#2/#3…），口径冲突可见、id 仍唯一。"""
    base = rec["id"]
    key = base
    k = 2
    while key in seen:
        first = out[seen[key]]
        if abs(float(first["value"]) - float(rec["value"])) < 1e-12:
            return
        key = f"{base}#{k}"
        k += 1
    rec["id"] = key
    if key != base:
        rec["conflict_with"] = base
    seen[key] = len(out)
    out.append(rec)


def _walk(obj: Any, path: str, rel: str, out: List, seen: Dict, depth: int = 0) -> None:
    if depth > 3:
        return
    if isinstance(obj, dict):
        v = _num(obj.get("value"))
        if v is not None and any(k in obj for k in ("indicator", "name", "id", "metric")):
            name = str(obj.get("name") or obj.get("indicator") or obj.get("metric")
                       or obj.get("id") or path)
            _push(out, seen, {
                "id": _id_from(obj, "N", len(out) + 1),
                "name": name, "value": v,
                "unit": str(obj.get("unit") or ""),
                "period": str(obj.get("period") or obj.get("date") or ""),
                "region": str(obj.get("region") or ""),
                "source_file": rel,
                "org": str(obj.get("source_org") or obj.get("org") or ""),
                "formula": str(obj.get("formula") or ""),
                "inputs": str(obj.get("inputs") or ""),
                "kind": path or "obs",
            })
            return
        for k, val in obj.items():
            if k in ("url", "quote", "source_title", "source_date", "note"):
                continue
            _walk(val, f"{path}.{k}" if path else str(k), rel, out, seen, depth + 1)
        return
    if isinstance(obj, list):
        for i, val in enumerate(obj[:200]):
            _walk(val, f"{path}[{i}]", rel, out, seen, depth + 1)
        return
    v = _num(obj)
    if v is not None and path:
        _push(out, seen, {
            "id": f"facts:{path}", "name": path, "value": v, "unit": "",
            "period": "", "region": "", "source_file": rel, "org": "",
            "formula": "", "inputs": "", "kind": "scalar",
        })


def _csv_numbers(path: Path, rel: str) -> List[Dict[str, Any]]:
    """CSV：每个数值列出 4 条（末值 / 最大 / 最小 / 均值），列名即指标名。"""
    out: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))[:MAX_CSV_ROWS]
    except (OSError, UnicodeDecodeError, csv.Error):
        return out
    if not rows:
        return out
    for col in rows[0].keys():
        vals = []
        for r in rows:
            try:
                vals.append(float(str(r.get(col, "")).replace(",", "")))
            except (TypeError, ValueError):
                continue
        if len(vals) < 2:
            continue
        base = f"csv:{path.stem}:{col}"
        for tag, v in (("last", vals[-1]), ("max", max(vals)),
                       ("min", min(vals)), ("mean", sum(vals) / len(vals))):
            out.append({"id": f"{base}:{tag}", "name": f"{col}({tag})", "value": v,
                        "unit": "", "period": "", "region": "", "source_file": rel,
                        "org": "", "formula": "", "inputs": "", "kind": "csv"})
    return out


def build(root: str, exclude_raw: bool = True) -> Dict[str, Any]:
    base = Path(root).resolve()
    if not base.exists():
        raise FileNotFoundError(f"项目目录不存在: {root}")
    numbers: List[Dict[str, Any]] = []
    seen: Dict[str, int] = {}
    sources: List[Dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            rel = str(p.relative_to(base)).replace("\\", "/")
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
            if p.suffix.lower() == ".json":
                try:
                    obj = json.loads(p.read_text(encoding="utf-8-sig"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                before = len(numbers)
                _walk(obj, "", rel, numbers, seen)
                if len(numbers) > before:
                    sources.append({"file": rel, "kind": "json", "hash": _sha(p),
                                    "numbers": len(numbers) - before})
            elif p.suffix.lower() == ".csv":
                got = _csv_numbers(p, rel)
                if got:
                    numbers.extend(got)
                    sources.append({"file": rel, "kind": "csv", "hash": _sha(p),
                                    "numbers": len(got)})
    pack = {
        "schema": "dsh.evidence_pack/v1",
        "project": base.name,
        "root": str(base),
        "numbers": numbers,
        "sources": sources,
        "counts": {"files": len(sources), "numbers": len(numbers)},
    }
    return pack


def write(pack: Dict[str, Any], out_dir: str) -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    pj = os.path.join(out_dir, "evidence_pack.json")
    with open(pj, "w", encoding="utf-8", newline="\n") as f:
        json.dump(pack, f, ensure_ascii=False, indent=1)
    bm = os.path.join(out_dir, "brief.md")
    with open(bm, "w", encoding="utf-8", newline="\n") as f:
        f.write(_brief(pack))
    return {"pack": pj, "brief": bm}


def _brief(pack: Dict[str, Any]) -> str:
    L = [f"# 证据包 · {pack['project']}", "",
         f"{pack['counts']['files']} 个来源文件 / {pack['counts']['numbers']} 个数字。",
         "写稿时引用 id；正文里的数字必须能在下表找到。", ""]
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for n in pack["numbers"]:
        by_file.setdefault(n["source_file"], []).append(n)
    for fn, items in by_file.items():
        L.append(f"## {fn}（{len(items)}）")
        L.append("")
        L.append("| id | 指标 | 值 | 单位 | 期 | 来源 |")
        L.append("|---|---|---|---|---|---|")
        for n in items[:60]:
            L.append(f"| `{n['id']}` | {n['name']} | {n['value']} | {n['unit']} | "
                     f"{n['period']} | {n['org']} |")
        if len(items) > 60:
            L.append(f"| … | 另有 {len(items) - 60} 条 | | | | |")
        L.append("")
    return "\n".join(L)


def load(path: str) -> Dict[str, Any]:
    p = Path(path)
    if p.is_dir():
        p = p / "evidence_pack.json"
    return json.loads(p.read_text(encoding="utf-8-sig"))


def values(pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    """给校验器用：{text, value, id, source} 列表（供溯源比对）。"""
    out = []
    for n in pack.get("numbers", []):
        out.append({"id": n["id"], "value": n["value"], "text": _fmt(n["value"]),
                    "source": n.get("org") or n.get("source_file") or "",
                    "file": n.get("source_file", "")})
    return out


def _fmt(v: float) -> str:
    f = float(v)
    if f.is_integer():
        return str(int(f))
    if abs(f) >= 1000:
        return f"{f:.0f}"
    return f"{f:.4g}"
