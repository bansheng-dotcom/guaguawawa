# -*- coding: utf-8 -*-
"""core.collect_schema —— `collect schema --url`：网页 → 采集规格草稿（P2-5）。

三步（与方案 P2-5 一致）：
    1. 按 Policy 抓一页（robots/限速/超时/字节上限全走 `core.ingest`）
    2. 推断抽取结构（JSON 数组优先，其次 HTML 表格），生成源画像 + 采集规格草稿
    3. 试采 20 行过质量门（空值率 <10%、distinct ≥2、min_rows ≥3）

产物只写 `--out`（项目侧）：`<id>.source.yaml` + `<id>.collection.yaml`。
团内不落任何东西。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

from core import ingest
from core.ingest import extract as _ex
from core.ingest.store import dq_report


def _slug(url: str) -> str:
    u = urlsplit(url)
    raw = (u.hostname or "page") + "-" + (u.path or "/")
    s = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fa5]+", "-", raw).strip("-").lower()
    return (s or "collected")[:48]


def _ctype_guess(recs: List[Dict[str, Any]], col: str) -> str:
    vals = [str((r or {}).get(col) or "").strip() for r in recs[:50]]
    vals = [v for v in vals if v]
    if not vals:
        return "string"
    num = sum(1 for v in vals if re.match(r"^-?\d+(\.\d+)?$", v.replace(",", "")))
    if num >= len(vals) * 0.8:
        return "number"
    date = sum(1 for v in vals if re.match(r"^\d{4}(-\d{1,2}){0,2}", v))
    if date >= len(vals) * 0.8:
        return "date"
    return "string"


def _infer_json_path(node: Any, prefix: str = "") -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    """找第一个「元素是对象的数组」，返回 (点路径, 数组)。"""
    if isinstance(node, list) and node and isinstance(node[0], dict):
        return prefix, [x for x in node if isinstance(x, dict)]
    if isinstance(node, dict):
        for k, v in node.items():
            got = _infer_json_path(v, (prefix + "." + str(k)) if prefix else str(k))
            if got:
                return got
    return None


def _infer_extract(text: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    s = text.lstrip()
    if s[:1] in ("{", "["):
        try:
            doc = json.loads(text)
        except json.JSONDecodeError:
            doc = None
        if doc is not None:
            got = _infer_json_path(doc)
            if got:
                path, rows = got
                return {"format": "json", "path": path}, rows, warnings
            warnings.append("JSON 里没找到对象数组，退回表格抽取")
    p = _ex._TableParser()
    p.feed(text)
    header: List[str] = []
    if p.rows and p.th_rows:
        header = p.rows[0]
        rows = [r for i, r in enumerate(p.rows)
                if i not in p.th_rows and any(x for x in r)]
    elif p.rows:
        header, rows = p.rows[0], [r for r in p.rows[1:] if any(x for x in r)]
    else:
        rows = []
    if not header:
        warnings.append("没识别出表头；草稿需手工指定 extract.header")
        return {"format": "table", "header": []}, [], warnings
    recs = [{(header[i] if i < len(header) else "c%d" % i): v
             for i, v in enumerate(r)} for r in rows]
    return {"format": "table", "header": header}, recs, warnings


def _quality(rows: List[Dict[str, Any]], header: List[str]) -> Dict[str, Any]:
    dq = dq_report(rows)
    problems: List[str] = []
    if len(rows) < 3:
        problems.append("试采行数 %d < 3（min_rows）" % len(rows))
    for c in header:
        st = (dq["columns"] or {}).get(c) or {}
        if float(st.get("empty_rate") or 0) > 0.10:
            problems.append("%s 空值率 %.0f%% > 10%%" % (c, float(st["empty_rate"]) * 100))
    dim = header[0] if header else ""
    if dim and int(((dq["columns"] or {}).get(dim) or {}).get("distinct") or 0) < 2:
        problems.append("%s 只有 1 个不同值（distinct < 2）" % dim)
    return {"ok": not problems, "problems": problems, "dq": dq}


def draft(url: str, policy: Optional[Dict[str, Any]] = None,
          intent: str = "", max_rows: int = 20) -> Dict[str, Any]:
    """抓一页 → 推断结构 → 草稿 + 试采质量。不写盘。"""
    pol = policy or ingest.load_policy("default")
    res = ingest.http_get(url, pol, robots=ingest.fetch.RobotsCache(pol))
    if not res.ok:
        return {"ok": False, "stage": "fetch", "error": res.kind,
                "detail": res.error, "url": url}
    ex, rows, warnings = _infer_extract(res.body)
    header = list(ex.get("header") or (list(rows[0].keys()) if rows else []))
    q = _quality(rows[:max_rows], header)
    sid = _slug(url)

    u = urlsplit(url)
    pg_param = next((k for k in ("page", "p", "pageno", "pageNo") if k in parse_qs(u.query)),
                    "")
    time_like = any(str(c).lower() in ("date", "month", "year", "time", "week", "day")
                    or any(k in str(c) for k in ("日期", "月份", "年份", "时间", "周"))
                    for c in header)
    src = {"schema": "dsh.source/v1", "id": sid, "kind": "web_search",
           "atomic_grain": header or ["row"],
           "history": "historical" if (pg_param or time_like) else "snapshot_only",
           "fields": [{"name": c, "type": _ctype_guess(rows, c)} for c in header]
           or [{"name": "row", "type": "string"}]}
    dims = header[:2]
    measure_col = next((c for c in header
                        if _ctype_guess(rows, c) == "number"), "")
    rollups = []
    if dims and measure_col:
        rollups = [{"id": "main", "grain": dims,
                    "derive": {d: "field:%s" % d for d in dims},
                    "measures": {measure_col: {"agg": "sum", "expr": measure_col}}}]
    spec = {
        "schema": "dsh.collection_spec/v1", "id": sid, "source": sid,
        "mode": "raw", "intent": intent, "policy": str(pol.get("id") or "default"),
        "query": {"url": url},
        "extract": ex,
        "rollups": rollups, "claims": [],
    }
    if pg_param:
        spec["pagination"] = {"param": pg_param, "start": 1, "stop": 3}
    return {"ok": bool(q["ok"]), "stage": "ok" if q["ok"] else "quality",
            "source": src, "spec": spec, "quality": q,
            "rows": len(rows), "sample": rows[:max_rows],
            "warnings": warnings, "url": url}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="collect schema")
    ap.add_argument("--url", required=True, help="要采集的页面 URL")
    ap.add_argument("--intent", default="", help="这页数据用来回答什么（只写进草稿备注）")
    ap.add_argument("--out", required=True, help="项目侧输出目录（团内会被拒绝）")
    ap.add_argument("--policy", default="default")
    ap.add_argument("--rows", type=int, default=20)
    a = ap.parse_args(argv)

    out = Path(a.out)
    try:
        from core import paths
        paths.assert_writable(out)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=1))
        return 2
    pol = ingest.load_policy(a.policy)
    d = draft(a.url, policy=pol, intent=a.intent, max_rows=max(1, a.rows))
    if d.get("stage") == "fetch":
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return 2
    out.mkdir(parents=True, exist_ok=True)
    sid = d["source"]["id"]
    import yaml
    (out / (sid + ".source.yaml")).write_text(
        yaml.safe_dump(d["source"], allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    (out / (sid + ".collection.yaml")).write_text(
        yaml.safe_dump(d["spec"], allow_unicode=True, sort_keys=False),
        encoding="utf-8")
    # 用草稿自带源画像自检一遍（不依赖 configs/sources 里先有文件）
    from core import collection_spec as cs
    errs = cs.validate(d["spec"], source=d["source"], mode="raw")
    payload = {"ok": bool(d["ok"]) and not errs, "stage": d.get("stage"),
               "source": str(out / (sid + ".source.yaml")),
               "spec": str(out / (sid + ".collection.yaml")),
               "rows": d.get("rows"), "sample": d.get("sample", [])[:5],
               "quality": {"ok": d["quality"]["ok"],
                           "problems": d["quality"]["problems"]},
               "spec_errors": errs, "warnings": d.get("warnings")}
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
