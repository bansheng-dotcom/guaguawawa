# -*- coding: utf-8 -*-
"""第 7 段 Security：STRIDE 威胁建模 + OWASP ASVS 检查 + 依赖/密钥扫描。

硬门槛：
  - S/T/R/I/D/E 六类威胁都必须过一遍，并写缓解措施；
  - ASVS 至少 6 项且全部 pass，等级不低于 L2；
  - 依赖扫描无 high，密钥扫描 0 泄漏；
  - API 错误码必须与安全清单一致（不允许“接口有码、安全不认”）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .common import (ck, gate, md_table, nonempty_str, render_stage)

_STRIDE = ("S", "T", "R", "I", "D", "E")
_STRIDE_NAMES = {"S": "Spoofing", "T": "Tampering", "R": "Repudiation",
                 "I": "Information disclosure", "D": "Denial of service",
                 "E": "Elevation of privilege"}


def _norm_cat(v: str) -> str:
    v = str(v or "").strip()
    if not v:
        return ""
    if v[0].upper() in _STRIDE:
        return v[0].upper()
    for k, name in _STRIDE_NAMES.items():
        if name.lower() in v.lower():
            return k
    return ""


def build(brief: Dict[str, Any]) -> Dict[str, Any]:
    sec = brief.get("security") or {}
    api_codes = [e.get("code") for e in (brief.get("api") or {}).get("error_codes") or []]
    threats = [{"category": _norm_cat(t.get("category")),
                "asset": t.get("asset", ""), "threat": t.get("threat", ""),
                "mitigation": t.get("mitigation", ""),
                "severity": t.get("severity", "medium")}
               for t in sec.get("threats") or []]
    asvs = [{"id": a.get("id", ""), "requirement": a.get("requirement", ""),
             "status": a.get("status", "")} for a in sec.get("asvs") or []]
    art: Dict[str, Any] = {
        "artifact": "security",
        "stage": "security",
        "project": brief.get("project", ""),
        "stride": {k: [t for t in threats if t["category"] == k] for k in _STRIDE},
        "threats": threats,
        "asvs": asvs,
        "asvs_level": sec.get("asvs_level", ""),
        "dependency_scan": sec.get("dependency_scan") or {},
        "secret_scan": sec.get("secret_scan") or {},
        "api_error_codes": sorted(c for c in api_codes if c),
        "handled_error_codes": sorted(set(sec.get("handled_error_codes") or [])),
    }
    art["gate"] = check(art)
    return art


def check(art: Dict[str, Any]) -> Dict[str, Any]:
    """安全门禁：STRIDE 全覆盖、ASVS≥6 全 pass、无 high、无泄漏、错误码对齐。"""
    threats = art.get("threats") or []
    cats = {t.get("category") for t in threats}
    asvs = art.get("asvs") or []
    dep = art.get("dependency_scan") or {}
    secret = art.get("secret_scan") or {}
    checks = [
        ck(set(_STRIDE) <= cats and
           all(nonempty_str(t.get("threat")) and nonempty_str(t.get("mitigation"))
               for t in threats),
           "STRIDE 六类威胁均有缓解措施", "security:stride", "CRITICAL"),
        ck(len(asvs) >= 6 and all(a.get("status") == "pass" for a in asvs) and
           str(art.get("asvs_level", "")).upper() in ("L2", "L3"),
           "OWASP ASVS ≥6 项全 pass 且等级≥L2", "security:asvs", "CRITICAL"),
        ck(int(dep.get("high", 0)) == 0 and nonempty_str(dep.get("tool")),
           "依赖扫描无 high 漏洞", "security:no_high", "CRITICAL"),
        ck(int(secret.get("leaked", 0)) == 0 and nonempty_str(secret.get("tool")),
           "密钥扫描 0 泄漏", "security:no_leaked_secrets", "CRITICAL"),
        ck(bool(art.get("api_error_codes")) and
           set(art.get("api_error_codes")) == set(art.get("handled_error_codes")),
           "安全清单覆盖全部 API 错误码", "security:error_codes", "CRITICAL"),
    ]
    return gate(checks, "security")


def render(art: Dict[str, Any]) -> str:
    rows = [[f"{t.get('category')} · {_STRIDE_NAMES.get(t.get('category'), '')}",
             t.get("asset"), t.get("threat"), t.get("mitigation"), t.get("severity")]
            for t in art.get("threats") or []]
    asvs_rows = [[a.get("id"), a.get("requirement"), a.get("status")]
                 for a in art.get("asvs") or []]
    dep = art.get("dependency_scan") or {}
    sec = art.get("secret_scan") or {}
    summary = (f"依赖扫描（{dep.get('tool')}）：{dep.get('findings')} 项，"
               f"high={dep.get('high')}；密钥扫描（{sec.get('tool')}）："
               f"泄漏 {sec.get('leaked')} 项；ASVS 等级 {art.get('asvs_level')}。")
    tables = [
        "## STRIDE 威胁", "", md_table(["类别", "资产", "威胁", "缓解", "级别"], rows),
        "", "## OWASP ASVS", "", md_table(["条目", "要求", "状态"], asvs_rows),
        "", "## 错误码对齐", "",
        f"- API：{'、'.join(art.get('api_error_codes') or [])}",
        f"- 安全清单：{'、'.join(art.get('handled_error_codes') or [])}",
    ]
    return render_stage(art, summary, tables)
