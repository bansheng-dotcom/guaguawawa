# -*- coding: utf-8 -*-
"""Runner 层：一条采集规格 = 策略 → 分页取数 → 抽取 → 校验 → staging + DQ。

硬规则：
  * 单源失败不中断（C-2）：`run()` 返回 `ok=False` 但把每个 URL 的失败分类留下；
    批量用 `run_many()`，一个源挂了不影响其它源。
  * 不落团内：staging 走 `core.paths.write_artifact`（写团内抛 BoundaryError）。
  * 不做并发/代理池/分布式队列——需要的是可复现，不是吞吐。
"""
from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional

from core.data import data_model
from core.base import paths
from core.sources import source_profile

from . import extract as _ex
from .fetch import RateLimiter, RobotsCache, http_get
from .policy import load_policy, validate_policy
from .store import dq_report, write_staging


def _source_id(spec: Dict[str, Any], src: Dict[str, Any]) -> str:
    return str(src.get("id") or spec.get("source") or spec.get("id") or "source")


def _unit_unverified(records: Iterable[Dict[str, Any]]) -> int:
    n = 0
    for r in records:
        for k in ("unit", "单位"):
            if k in r:
                _base, _scale, ok = data_model.normalize_unit(str(r.get(k) or ""))
                if not ok:
                    n += 1
                break
    return n


def _check_required(rec: Dict[str, Any], required: List[str]) -> Optional[str]:
    miss = [k for k in required if str(rec.get(k) or "").strip() == ""]
    return ("missing:" + ",".join(miss)) if miss else None


def run(spec: Dict[str, Any], project_dir: str = "",
        persist: bool = True,
        policy: Optional[Dict[str, Any]] = None,
        sleep=time.sleep) -> Dict[str, Any]:
    """执行一条采集规格；返回结果（不抛异常）。"""
    if not isinstance(spec, dict):
        return {"ok": False, "stage": "spec", "error": "采集规格必须是 dict"}
    src = source_profile.load(str(spec.get("source") or "")) or {}
    pol = policy or load_policy(str(spec.get("policy") or "default"))
    perrs = validate_policy(pol)
    if perrs:
        return {"ok": False, "stage": "policy", "errors": perrs}

    urls = _ex.iter_page_urls(spec.get("query") or {},
                              spec.get("pagination") or {},
                              int(pol.get("max_pages") or 20))
    if not urls:
        return {"ok": False, "stage": "query", "error": "没有可抓 URL（缺 url/urls/url_template）"}

    limiter = RateLimiter(float(pol.get("rps") or 1.0))
    robots = RobotsCache(pol)
    records: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    pages: List[Dict[str, Any]] = []
    rows_in = 0
    ex_schema = spec.get("extract") or {}
    required = [str(x) for x in (ex_schema.get("required") or [])]

    for url in urls:
        res = http_get(url, pol, limiter=limiter, robots=robots, sleep=sleep)
        info = res.to_dict()
        pages.append(info)
        if not res.ok:
            continue
        recs, drops = _ex.extract_records(res.body, ex_schema)
        rows_in += len(recs) + len(drops)
        dropped.extend([{**d, "url": url} for d in drops])
        for i, r in enumerate(recs):
            why = _check_required(r, required) if required else None
            if why:
                dropped.append({"reason": "schema_drift", "detail": why,
                                "row": i, "url": url})
                continue
            records.append(r)

    ok_pages = sum(1 for p in pages if p.get("kind") == "ok")
    dq = dq_report(records, rows_in=rows_in, dropped=dropped, sources=pages,
                   unit_unverified=_unit_unverified(records))
    out: Dict[str, Any] = {
        "ok": bool(ok_pages and records),
        "source": _source_id(spec, src),
        "stage": "ok" if ok_pages else "fetch",
        "pages": pages,
        "rows_in": dq["rows_in"],
        "rows_out": dq["rows_out"],
        "dropped": dq["dropped"]["total"],
        "drop_reasons": dq["dropped"]["reasons"],
        "dq": dq,
    }
    if not ok_pages:
        out["error"] = "全部 URL 失败：" + ",".join(
            sorted({str(p.get("kind")) for p in pages})) or "unknown"
    if persist and project_dir:
        try:
            st = write_staging(project_dir, out["source"], records, dq=dq,
                               state={"urls": len(urls), "ok_pages": ok_pages})
            out["staging"] = st["dir"]
            out["dq_path"] = st["dq"]
        except paths.BoundaryError as exc:      # 落点越界必须显式失败
            out["ok"] = False
            out["stage"] = "store"
            out["error"] = str(exc)
    return out


def run_many(specs: Iterable[Dict[str, Any]], project_dir: str = "",
             persist: bool = True, policy: Optional[Dict[str, Any]] = None,
             sleep=time.sleep) -> Dict[str, Any]:
    """多源采集：单源失败隔离，汇总每个源的状态。"""
    results = []
    for s in specs:
        try:
            results.append(run(s, project_dir=project_dir, persist=persist,
                               policy=policy, sleep=sleep))
        except Exception as exc:  # noqa: BLE001 一个源的实现错误不拖垮整批
            results.append({"ok": False, "stage": "runner",
                            "source": str((s or {}).get("id") or ""),
                            "error": "%s: %s" % (type(exc).__name__, exc)})
    return {"ok": any(r.get("ok") for r in results), "results": results,
            "ok_sources": sum(1 for r in results if r.get("ok")),
            "total_sources": len(results)}
