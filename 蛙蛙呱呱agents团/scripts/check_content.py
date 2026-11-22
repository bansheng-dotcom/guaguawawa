# -*- coding: utf-8 -*-
"""scripts/check_content.py —— 内容哈希（变更台账的底层工具）。

对「去掉图表负载的合同」取 SHA256，得到 content_hash：
  - 保留：标题 / 正文 / 表格 / 图题 / 图来源 / 图 refs / 顺序 / 证据
  - 丢弃：chart.type 与图负载（items/points/bars/vbars/unit_meta/...）

这样"换图型"不会触发 diff，而"数字/正文被意外改坏"会触发。
本工具只读，不修改任何产物。

用法：
    python scripts/check_content.py <contract.json | report.md | 目录>
    python scripts/check_content.py --ledger <目录>   # 追加一条台账记录
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict

_TIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?")


def _clean(v: Any) -> Any:
    """去掉空值 + 时间戳，保证序列化稳定（时间戳不是内容）。"""
    if isinstance(v, str):
        v = _TIME_RE.sub("TIME", v)
        if v.startswith("生成时间："):
            v = "生成时间：TIME"
        return v
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()
                if x not in (None, "", [], {})}
    if isinstance(v, list):
        out = [_clean(x) for x in v]
        return [x for x in out if x not in (None, "", [], {})]
    return v


CONTENT_TOP = ("doc_type", "title_lines", "standfirst", "metric_strip",
               "summary", "decision", "notes", "footer", "sources",
               "one_x", "summary_title")
CONTENT_SEC = ("index", "title", "full_title", "question", "reading",
               "headline", "headline_ref", "action", "relation", "refs",
               "falsifier", "table")
CHART_KEEP = ("title", "source", "refs")


def normalize_contract(data: Dict[str, Any]) -> Dict[str, Any]:
    top = {k: _clean(data[k]) for k in CONTENT_TOP if k in data}
    secs = []
    for s in data.get("sections") or []:
        sec = {k: _clean(s[k]) for k in CONTENT_SEC if k in s}
        ch = s.get("chart")
        if isinstance(ch, dict):
            sec["chart"] = {k: _clean(ch[k]) for k in CHART_KEEP
                            if k in ch and ch[k] not in (None, "", [], {})}
        secs.append(sec)
    top["sections"] = secs
    return top


def hash_bytes(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_contract(data: Dict[str, Any]) -> str:
    norm = normalize_contract(data)
    s = json.dumps(norm, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":"))
    return hash_bytes(s)


def hash_md(text: str) -> str:
    return hash_bytes(text)


def hash_path(path: Path) -> Dict[str, Any]:
    path = path.resolve()
    if path.is_dir():
        c = path / "contract.json"
        if c.exists():
            return hash_path(c)
        m = path / "report.md"
        if m.exists():
            return hash_path(m)
        raise FileNotFoundError(f"{path} 里没有 contract.json / report.md")
    name = path.name.lower()
    if name == "contract.json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return {"kind": "contract", "path": str(path),
                "content_hash": hash_contract(data),
                "sections": len(data.get("sections") or [])}
    if name.endswith(".md"):
        text = path.read_text(encoding="utf-8-sig")
        return {"kind": "md", "path": str(path),
                "content_hash": hash_md(text),
                "chars": len(text)}
    raise ValueError(f"不支持的文件类型：{name}（要 contract.json 或 report.md）")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="内容哈希（变更台账工具）")
    ap.add_argument("target", help="contract.json / report.md / 目录")
    ap.add_argument("--ledger", help="追加到台账文件（jsonl）")
    args = ap.parse_args(argv)
    try:
        res = hash_path(Path(args.target))
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    res["ok"] = True
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if args.ledger:
        lp = Path(args.ledger)
        lp.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
               **res}
        with lp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
