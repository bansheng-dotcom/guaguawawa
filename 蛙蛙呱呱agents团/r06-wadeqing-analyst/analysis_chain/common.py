# -*- coding: utf-8 -*-
"""R06 分析链（T8a）的公共层：工件读写、确定性门禁结构、指纹与时间。

设计约束（对齐方案 §13 / §17）：
  - 每个阶段只做一件事，产出一个可独立审计的 JSON 工件；
  - 门禁返回 `{ok, grade, checks, errors}`，`ok=false` 时 CLI 退出码非 0；
  - 时间只用于留痕（generated_at），不参与任何判断，保证复算稳定。
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List


STAGE_ORDER = ("frame", "plan", "profile", "explore", "explain", "test")


def now_iso() -> str:
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


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ck(ok: bool, msg: str, dim: str, sev: str = "OK", **evidence: Any) -> Dict[str, Any]:
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
    """把检查清单压成统一门禁结构。

    只有 CRITICAL 失败才阻断（ok=False）；HIGH/WARN 记录但不阻断，
    避免把“值得注意”误判成“不能交付”。
    """
    failed = [x for x in checks if not x["ok"]]
    blockers = [x for x in failed if x.get("sev") == "CRITICAL"]
    out = {
        "ok": not blockers,
        "grade": grade(checks),
        "stage": stage,
        "checks": checks,
        "errors": [f"{x['dim']}: {x['msg']}" for x in failed],
        "blockers": [f"{x['dim']}: {x['msg']}" for x in blockers],
        "warnings": [f"{x['dim']}: {x['msg']}" for x in failed if x.get("sev") != "CRITICAL"],
    }
    return out


def fail(msg: str, stage: str = "") -> Dict[str, Any]:
    return {"ok": False, "grade": "FAIL", "stage": stage,
            "checks": [ck(False, msg, "existence", "CRITICAL")],
            "errors": [msg]}


def load_gate_artifact(path: str, stage: str) -> Dict[str, Any]:
    """读入上一阶段工件；不存在或坏 JSON 时返回带错误的空对象。"""
    if not os.path.exists(path):
        return {"_error": f"文件不存在 {path}"}
    try:
        return read_json(path)
    except (OSError, ValueError) as exc:
        return {"_error": f"无法解析 {path}: {exc}"}


def require_ok(artifact: Dict[str, Any], stage: str) -> List[Dict[str, Any]]:
    """把上游工件自身的门禁结果转成当前阶段的检查项（防止带病流转）。"""
    g = artifact.get("gate") or {}
    if not g:
        return [ck(False, f"上游 {stage} 缺少 gate 结果", "upstream", "CRITICAL")]
    return [ck(bool(g.get("ok")), f"上游 {stage} 门禁={g.get('grade')}",
               "upstream", "CRITICAL" if not g.get("ok") else "OK")]
