# -*- coding: utf-8 -*-
"""core/research_intake —— 新业务研究的「采集 → 校验 → 台账 → 成稿」入口。

它把「新业务研究报告」的前三步产品化（v6）：

    ① 计划    问题树由报告纲领决定（market_entry: 规模/增长/集中度/单位经济/闸门）
    ② 采集    项目目录里的 data/sources.json（每条带 url + quote）
    ③ 校验    回抓原文，quote 必须能在正文里找到；找不到就标 unverified，不许当证据
    ④ 台账    claims.json + sources.json → r05 research ledger（覆盖率/悬空引用/类型白名单）
    ⑤ 成稿    交给唯一入口 report run-line → 同一套过账与渲染（v11 起）

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

from core import report_flow, runner

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _norm(s: str) -> str:
    s = html.unescape(str(s or ""))
    s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", "", s)


def _open(req: urllib.request.Request, timeout: int, insecure: bool = False):
    if insecure:
        import ssl
        ctx = ssl._create_unverified_context()
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return urllib.request.urlopen(req, timeout=timeout)


def _fetch(url: str, timeout: int = 25) -> Tuple[str, str]:
    import time
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "zh-CN,zh;q=0.9"})

    def _read_once(insecure: bool = False):
        with _open(req, timeout, insecure=insecure) as r:
            return (r.read(),
                    (r.headers.get("Content-Encoding") or "").lower(),
                    (r.headers.get_content_type() or "").lower())

    raw = enc = ctype = None
    last: Optional[Exception] = None
    for attempt in range(3):
        try:
            raw, enc, ctype = _read_once()
            break
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).upper()
            if "CERTIFICATE" in msg or "SSL" in msg:
                # 政府站点常见过期/链不全证书；只读核验允许降级为不校验证书。
                try:
                    raw, enc, ctype = _read_once(insecure=True)
                    break
                except Exception as exc2:  # noqa: BLE001
                    last = exc2
            elif any(code in msg for code in ("502", "503", "504")):
                last = exc
                time.sleep(1 + attempt)
            else:
                last = exc
                break
    if raw is None:
        raise last or RuntimeError("fetch failed")
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
    if ctype == "application/pdf" or url.lower().split("?")[0].endswith(".pdf"):
        try:
            import io
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            if text.strip():
                return text, ""
        except Exception:  # noqa: BLE001  解析失败退回字节解码
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


def verify(project: str, write_raw: bool = False,
           only_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """URL 可达性预检（P3-4）：**只回答「这个链接现在能不能打开」**。

    quote 是否命中原文，唯一判据在 `core.source_verify`（`quote_gate` 调用它）。
    本函数不再对 quote 下结论，避免两套判据给出不同答案。

    - only_ids：只检查被报告引用的来源，其余标 skipped；
    - 抓取失败：unreachable，绝不伪造 reachable。
    """
    base = Path(project)
    sources = load_sources(project)
    only = {str(x) for x in only_ids} if only_ids else None
    raw_dir = base / "raw"
    if write_raw:
        raw_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for s in sources:
        sid, url = s.get("id"), s.get("url", "")
        rec = {"id": sid, "url": url, "status": "unknown"}
        if only is not None and sid not in only:
            rec["status"] = "skipped"
            rec["detail"] = "未被本次报告引用"
            out.append(rec)
            continue
        if not url:
            rec["status"] = "unreachable"
            rec["detail"] = "缺 url"
            out.append(rec)
            continue
        try:
            cache = raw_dir / f"{sid}.txt"
            if cache.exists():
                text = cache.read_text(encoding="utf-8", errors="replace")
                via = "cache"
            else:
                text, _err = _fetch(url)
                via = "live"
                if write_raw:
                    cache.write_text(text[:400000], encoding="utf-8")
            rec["status"] = "reachable" if text else "unreachable"
            rec["chars"] = len(text or "")
            rec["via"] = via
        except Exception as exc:  # noqa: BLE001  抓取失败标 unreachable，不伪造
            rec["status"] = "unreachable"
            rec["detail"] = f"{type(exc).__name__}: {exc}"[:200]
        out.append(rec)
    summary = {
        "schema": "dsh.reachability/v1",
        "checked_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "total": len(out),
        "reachable": sum(1 for r in out if r["status"] == "reachable"),
        "unreachable": sum(1 for r in out if r["status"] == "unreachable"),
        "skipped": sum(1 for r in out if r["status"] == "skipped"),
        "items": out,
        "note": "只做可达性预检；quote 命中以 source_verify 为准",
    }
    (base / "data").mkdir(parents=True, exist_ok=True)
    (base / "data" / "reachability.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def collect_refs(draft: Optional[Dict[str, Any]],
                 pack: Optional[Dict[str, Any]] = None) -> List[str]:
    """从 draft 的 refs 里收来源编号。

    - 直接写 S01/S03 的，直接用；
    - 写派生量 D_* 的，用 evidence_pack 的 source_ref 回溯到 S*；
    - 没有 pack 时退化为只收 S*。
    """
    raw: set = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "refs":
                    for x in (v or []):
                        raw.add(str(x))
                else:
                    walk(v)
        elif isinstance(obj, list):
            for x in obj:
                walk(x)

    walk(draft or {})
    ids: set = set()
    for r in raw:
        ids.update(re.findall(r"\b(S\d+)\b", r))
    if pack:
        by_id = {str(n.get("id")): n for n in (pack.get("numbers") or [])}
        for r in raw:
            base = r.split("#", 1)[0]
            n = by_id.get(base) or by_id.get(r)
            if not n:
                continue
            src = str(n.get("source_ref") or "")
            ids.update(re.findall(r"\b(S\d+)\b", src))
            # 派生量的 formula/inputs 里若直接写了 S 编号，也收
            ids.update(re.findall(r"\b(S\d+)\b",
                                  f"{n.get('formula') or ''} {n.get('inputs') or ''}"))
    return sorted(ids)


def quote_gate(project: str, refs: Optional[List[str]] = None,
               mode: str = "warn", fetch=None) -> Dict[str, Any]:
    """数据 intake 门禁：被引用的来源必须 quote 命中。

    P3-4：quote 判据**只在** `core.source_verify` 一处（这里委托调用），
    `research_intake.verify` 只做 URL 可达性预检，不再给出第二套结论。

    mode:
        off    跳过
        warn   记录 verdict，不阻断（P3 默认，P4 收紧）
        strict 有未核验来源就抛 FlowError，不出报告
    """
    if mode == "off":
        return {"mode": "off", "ok": True, "verdict": "SKIP", "status": "skipped"}
    base = Path(project)
    sources = load_sources(project)
    if not sources:
        return {"mode": mode, "ok": True, "verdict": "SKIP", "status": "no_sources"}
    from core import source_verify
    norm = [{**s, "file": str(s.get("id") or s.get("file") or "")}
            for s in sources]
    # 优先用项目 raw/ 缓存（离线复跑/回归 fixture），否则走实时抓取
    cache_of = {str(s.get("url") or ""): base / "raw" / f"{s.get('id')}.txt"
                for s in sources}

    def _fetch_one(url: str) -> str:
        p = cache_of.get(str(url))
        if p is not None and p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")
        return (fetch or source_verify.default_fetch)(url)

    sv = source_verify.verify_sources(norm, fetch=_fetch_one)
    rows = sv.get("rows") or []
    by_id = {r["id"]: r for r in rows}
    used = sorted(set(refs or [s.get("id") for s in sources]))
    used_unverified = [i for i in used
                       if (by_id.get(i) or {}).get("status") != "verified"]
    counts = sv.get("counts") or {}
    ok = not used_unverified
    checked = (counts.get("verified", 0) + counts.get("quote_not_found", 0)
               + counts.get("fetch_failed", 0))
    summary = {
        "schema": "dsh.quote_check/v1",
        "checked_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "total": sv.get("total"),
        "checked": checked,
        "ok": sv.get("verified", 0),
        "mismatch": counts.get("quote_not_found", 0),
        "unreachable": counts.get("fetch_failed", 0),
        "unverified": counts.get("fields_missing", 0) + counts.get("unverified", 0),
        "skipped": counts.get("skipped", 0),
        "items": rows,
    }
    (base / "data").mkdir(parents=True, exist_ok=True)
    (base / "data" / "quote_check.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    res = {
        "mode": mode,
        "ok": ok,
        "verdict": "PASS" if ok else "FAIL",
        "total": summary["total"],
        "checked": summary["checked"],
        "ok_count": summary["ok"],
        "mismatch": summary["mismatch"],
        "unreachable": summary["unreachable"],
        "unverified": summary["unverified"],
        "skipped": summary["skipped"],
        "used": used,
        "used_unverified": used_unverified,
        "grades": {g: sum(1 for s in sources
                          if str(s.get("grade") or "").upper()[:1] == g)
                   for g in ("A", "B", "C", "D")},
        "items": rows,
    }
    if mode == "strict" and not ok:
        raise report_flow.FlowError(
            "quote 门禁未过：被引用的来源未核验 " + ", ".join(used_unverified) +
            "；先补 quote 或改引已核验来源")
    return res



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
    """[已下线] 旧「采集 → 校验 → 台账 → 成稿」入口。

    v11：成稿这一步不再由本模块调 report_compose（已删除），改为走唯一入口
    `report run-line --research`。采集/校验/台账三件事保留为独立子命令，
    供 P3 的采集型专家复用。
    """
    raise report_flow.FlowError(
        "research_intake.run 已下线（成稿阶段归唯一入口）。\n"
        "请用: python guagua.py report run-line --intent \"…\" --research --dir <项目> --out <目录>\n"
        "quote 校验/台账仍可单独跑: python -m core.research_intake verify|ledger")


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="research_intake",
                                 description="研究数据 intake：quote 回抓校验 + 门禁")
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify", help="回抓来源、核对 quote")
    v.add_argument("--project", required=True)
    v.add_argument("--refs", default="", help="逗号分隔的 S 编号；空=全部")
    v.add_argument("--raw", action="store_true", help="保存原始页面到 raw/")

    g = sub.add_parser("gate", help="数据 intake 门禁")
    g.add_argument("--project", required=True)
    g.add_argument("--refs", default="", help="逗号分隔的 S 编号；空=全部")
    g.add_argument("--mode", choices=("off", "warn", "strict"), default="warn")

    a = ap.parse_args(argv)
    refs = [x.strip() for x in (a.refs or "").split(",") if x.strip()] or None
    if a.cmd == "verify":
        out = verify(a.project, write_raw=a.raw, only_ids=refs)
    else:
        out = quote_gate(a.project, refs=refs, mode=a.mode)
    slim = {k: v for k, v in out.items() if k != "items"}
    print(json.dumps(slim, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
