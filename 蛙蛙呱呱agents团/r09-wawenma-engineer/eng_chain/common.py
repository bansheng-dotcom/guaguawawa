# -*- coding: utf-8 -*-
"""R09 工程链（T7）公共层：工件读写、确定性门禁结构、指纹与 brief 合并。

设计约束（对齐升级方案 §12 / §17.2）：
  - 每段只做一件事，产出一个可独立审计的 JSON 工件；
  - 门禁返回 `{ok, grade, checks, errors, blockers}`，只有 CRITICAL 失败才阻断；
  - 阶段内容不写时间戳，保证同一 brief 重复运行得到相同工件（manifest 才留痕）；
  - 只依赖 Python 标准库，不联网、不新增依赖。
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


STAGE_ORDER = (
    "adr", "api", "feature", "testing", "debug",
    "release", "security", "performance", "incident", "review",
)

FILE_BY_STAGE = {stage: f"{stage}.json" for stage in STAGE_ORDER}


def now_iso() -> str:
    """UTC 时间，仅用于 manifest 留痕。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: str) -> Any:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: str, data: Any) -> str:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def write_text(path: str, text: str) -> str:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ck(ok: bool, msg: str, dim: str, sev: str = "OK", **evidence: Any) -> Dict[str, Any]:
    """统一检查项结构；dim 即门禁 ID（如 api:migration_reversible）。"""
    d: Dict[str, Any] = {"ok": bool(ok), "msg": msg, "dim": dim, "sev": sev}
    d.update(evidence)
    return d


def grade(checks: List[Dict[str, Any]]) -> str:
    if not checks:
        return "EMPTY"
    if all(x["ok"] for x in checks):
        return "PASS"
    if any(x["sev"] == "CRITICAL" and not x["ok"] for x in checks):
        return "FAIL"
    return "WARN"


def gate(checks: List[Dict[str, Any]], stage: str = "") -> Dict[str, Any]:
    """压成统一门禁：CRITICAL 失败阻断；HIGH/WARN 记录但不阻断。"""
    failed = [x for x in checks if not x["ok"]]
    blockers = [x for x in failed if x.get("sev") == "CRITICAL"]
    return {
        "ok": not blockers,
        "grade": grade(checks),
        "stage": stage,
        "checks": checks,
        "errors": [f"{x['dim']}: {x['msg']}" for x in failed],
        "blockers": [f"{x['dim']}: {x['msg']}" for x in blockers],
        "warnings": [f"{x['dim']}: {x['msg']}" for x in failed if x.get("sev") != "CRITICAL"],
    }


def fail(msg: str, stage: str = "") -> Dict[str, Any]:
    g = gate([ck(False, msg, "existence", "CRITICAL")], stage)
    return {"artifact": stage or "eng_chain", "gate": g,
            "errors": g["errors"], "ok": False, "grade": "FAIL"}


def _deep_merge(base: Any, override: Any) -> Any:
    """dict 递归合并；list/标量整体替换（便于误用夹具精确覆盖）。"""
    if isinstance(base, dict) and isinstance(override, dict):
        out = dict(base)
        for k, v in override.items():
            out[k] = _deep_merge(out.get(k), v) if k in out else copy.deepcopy(v)
        return out
    return copy.deepcopy(override)


def load_brief(path: str) -> Dict[str, Any]:
    """读入 brief；支持 `extends` 相对路径继承，便于误用夹具只写差异。"""
    data = read_json(path)
    ext = data.pop("extends", None) if isinstance(data, dict) else None
    if not ext:
        return data
    base_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(path)), ext))
    base = load_brief(base_path)
    return _deep_merge(base, data)


def nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def nonempty_list(v: Any) -> bool:
    return isinstance(v, list) and len(v) > 0


def md_table(headers: List[str], rows: List[List[Any]]) -> str:
    """生成 Markdown 表格；空行自动跳过 None。"""
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)


def md_list(items: List[Any], prefix: str = "-") -> str:
    return "\n".join(f"{prefix} {x}" for x in items)


def gate_badge(art: Dict[str, Any]) -> str:
    g = art.get("gate") or {}
    return f"**门禁：{g.get('grade', '?')}**（ok={bool(g.get('ok'))}）"


def render_stage(art: Dict[str, Any], summary: str, tables: List[str]) -> str:
    """统一段级 Markdown：标题 + 门禁 + 摘要 + 各表 + 失败项。"""
    g = art.get("gate") or {}
    lines = [f"# {art.get('artifact', 'artifact')} · {art.get('stage', '')}",
             "", f"> 项目：{art.get('project', '-')}", f"> {gate_badge(art)}",
             "", summary, ""]
    lines.extend(tables)
    if g.get("errors"):
        lines += ["", "## 未通过检查", ""]
        lines += [f"- {e}" for e in g["errors"]]
    return "\n".join(lines).rstrip() + "\n"
