# -*- coding: utf-8 -*-
"""core/research_intake —— 新业务研究的「采集 → 校验 → 台账 → 成稿」入口。

它把「新业务研究报告」的前三步产品化（v6）：

    ① 计划    问题树由报告纲领决定（market_entry: 规模/增长/集中度/单位经济/闸门）
    ② 采集    项目目录里的 data/sources.json（每条带 url + quote）
    ③ 校验    回抓原文，quote 必须能在正文里找到；找不到就标 unverified，不许当证据
    ④ 台账    claims.json + sources.json → r05 research ledger（覆盖率/悬空引用/类型白名单）
    ⑤ 成稿    交给 report_compose（market_entry 纲领）→ 同一套过账与渲染

采集本身仍由 agent/人完成（找来源、写 quote），本模块只负责「不信你，回抓核对」。
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core import report_compose, report_flow, runner

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _norm(s: str) -> str:
    s = html.unescape(str(s or ""))
    s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", "", s)


def _fetch(url: str, timeout: int = 25) -> Tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        enc = (r.headers.get("Content-Encoding") or "").lower()
    if "gzip" in enc:
        import gzip
        raw = gzip.decompress(raw)
    elif "deflate" in enc:
        import zlib
        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    elif "br" in enc:
        try:
            import brotli  # type: ignore
            raw = brotli.decompress(raw)
        except Exception:  # noqa: BLE001
            pass
    for charset in ("utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(charset), ""
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), ""


def load_sources(project: str) -> List[Dict[str, Any]]:
    p = Path(project) / "data" / "sources.json"
    if not p.exists():
        return []
    obj = json.loads(p.read_text(encoding="utf-8-sig"))
    return list(obj.get("sources") or [])


def verify(project: str, write_raw: bool = True) -> Dict[str, Any]:
    """回抓每条来源，核对 quote；结果写 data/quote_check.json。"""
    base = Path(project)
    sources = load_sources(project)
    raw_dir = base / "raw"
    if write_raw:
        raw_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for s in sources:
        sid, url, quote = s.get("id"), s.get("url", ""), s.get("quote", "")
        rec = {"id": sid, "url": url, "quote": quote, "status": "unverified"}
        try:
            text, err = _fetch(url)
            if write_raw:
                (raw_dir / f"{sid}.txt").write_text(text[:400000], encoding="utf-8")
            if quote and _norm(quote) in _norm(text):
                rec["status"] = "ok"
            else:
                rec["status"] = "mismatch"
                rec["detail"] = "quote 未在原文命中（页面可能改版或需登录）"
            rec["chars"] = len(text)
        except Exception as exc:  # noqa: BLE001  抓取失败标 unverified，不伪造
            rec["status"] = "unreachable"
            rec["detail"] = f"{type(exc).__name__}: {exc}"[:200]
        out.append(rec)
    summary = {
        "schema": "dsh.quote_check/v1",
        "checked_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "total": len(out),
        "ok": sum(1 for r in out if r["status"] == "ok"),
        "mismatch": sum(1 for r in out if r["status"] == "mismatch"),
        "unreachable": sum(1 for r in out if r["status"] == "unreachable"),
        "items": out,
    }
    (base / "data" / "quote_check.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def ledger(project: str) -> Dict[str, Any]:
    """claims + sources → r05 research ledger；结果写 gates/r05_ledger.json。"""
    base = Path(project)
    sources = load_sources(project)
    cp = base / "data" / "claims.json"
    claims = []
    if cp.exists():
        claims = list(json.loads(cp.read_text(encoding="utf-8-sig")).get("claims") or [])
    payload = {"claims": claims, "sources": [
        {"id": s.get("id"), "name": s.get("title", ""), "type": s.get("type", "")}
        for s in sources]}
    tmp = base / "data" / "_ledger_input.json"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        r = runner.invoke("r05", ["research", "ledger", "--input", str(tmp)])
        js = r.get("json") or {}
    except Exception as exc:  # noqa: BLE001
        js = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    out = {"schema": "dsh.research_ledger/v1",
           "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
           "source_count": len(sources), "claim_count": len(claims),
           "verdict": js.get("verdict") or ("PASS" if js.get("ok") else "FAIL"),
           "coverage_rate": js.get("coverage_rate"),
           "orphan_claims": js.get("orphan_claims") or [],
           "checks": js.get("checks") or []}
    (base / "gates").mkdir(parents=True, exist_ok=True)
    (base / "gates" / "r05_ledger.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def run(topic: str, project: str, out_dir: str, thesis: str = "market_entry",
        theme: str = "paper", pdf: bool = False, skip_verify: bool = False,
        skip_ledger: bool = False) -> Dict[str, Any]:
    base = Path(project)
    if not base.exists():
        raise report_flow.FlowError(f"项目目录不存在: {project}")
    q = {"total": 0, "ok": 0, "skipped": True} if skip_verify else verify(project)
    led = {"verdict": "SKIP", "coverage_rate": None} if skip_ledger else ledger(project)
    if not skip_verify and q.get("mismatch"):
        bad = [r["id"] for r in q["items"] if r["status"] == "mismatch"]
        raise report_flow.FlowError(
            f"quote 校验失败：{bad} 的引文未能在原文命中，先修正来源再出报告")
    res = report_compose.build(intent=topic, project_dir=project, out_dir=out_dir,
                               thesis=thesis, theme=theme, pdf=pdf)
    man_path = os.path.join(out_dir, "manifest.json")
    if os.path.exists(man_path):
        man = json.loads(Path(man_path).read_text(encoding="utf-8"))
        man["research"] = {"quotes": q, "ledger": led}
        with open(man_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(man, f, ensure_ascii=False, indent=2)
    res.update({"quotes": {"ok": q.get("ok"), "total": q.get("total"),
                           "mismatch": q.get("mismatch", 0)},
                "ledger": {"verdict": led.get("verdict"),
                           "coverage": led.get("coverage_rate")}})
    return res
