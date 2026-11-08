# -*- coding: utf-8 -*-
"""s07 迁移 CI/CD 安全（ops）：migration / security 两动作。

- migration：迁移与回滚——步骤、回滚计划、可逆性校验（不可逆操作需授权）。
- security：依赖与密钥审计——CVE 严重度、泄露密钥、供应链。
阈值：thresholds.json → ops.*。
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "ops"
DESC = "迁移 CI/CD 安全：数据迁移、回滚、流水线、依赖与密钥审计"

ACTIONS = {
    "migration": "迁移与回滚计划",
    "security": "依赖与密钥安全审计",
}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for a, h in ACTIONS.items():
        ap = act.add_parser(a, help=h)
        ap.add_argument("--input", required=True)


# --------------------------------------------------------------------------- #
# migration
# --------------------------------------------------------------------------- #
def migration(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["ops"]
    irreversible_ops = th["irreversible_ops"]

    steps = data.get("steps") or []
    rollback = data.get("rollback_plan") or []
    authorized = bool(data.get("authorization", False))
    checks: List[Dict[str, Any]] = []

    if not steps:
        checks.append(c.ck(False, "steps 为空，无迁移可校验", "ops:migration_steps", "CRITICAL"))

    irreversible_found: List[str] = []
    for i, s in enumerate(steps):
        op = str(s.get("operation") or "").lower()
        if not op:
            checks.append(c.ck(False, f"steps[{i}] 缺 operation", "ops:migration_op", "HIGH", **{"index": i}))
        for kw in irreversible_ops:
            if kw in op:
                irreversible_found.append(op)

    if irreversible_found:
        if not authorized:
            checks.append(c.ck(False, f"含不可逆操作 {irreversible_found} 但未授权（不可逆线上操作需授权）", "ops:irreversible_auth", "CRITICAL", **{"operations": irreversible_found}))
        else:
            checks.append(c.ck(True, f"不可逆操作 {irreversible_found} 已授权", "ops:irreversible_auth", **{"operations": irreversible_found}))
    else:
        checks.append(c.ck(True, "迁移步骤均为可逆操作", "ops:irreversible"))

    if not rollback:
        checks.append(c.ck(False, "rollback_plan 为空（迁移必须有回滚计划）", "ops:rollback", "CRITICAL"))
    else:
        checks.append(c.ck(True, f"回滚计划 {len(rollback)} 步", "ops:rollback", **{"rollback_steps": len(rollback)}))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   step_count=len(steps),
                   irreversible_found=irreversible_found,
                   rollback_steps=len(rollback),
                   verdict=verdict,
                   next="迁移与回滚计划合规" if ok else "补齐授权/回滚计划后重新 migration",
                   )
    return out


# --------------------------------------------------------------------------- #
# security
# --------------------------------------------------------------------------- #
def security(data: Dict[str, Any]) -> Dict[str, Any]:
    th = c.load_thresholds()["ops"]
    cve_severities = th["cve_severities"]
    max_leaked_keys = th["max_leaked_keys"]

    dependencies = data.get("dependencies") or []
    leaked = data.get("leaked_keys") or []
    checks: List[Dict[str, Any]] = []

    if not dependencies:
        checks.append(c.ck(False, "dependencies 为空，无依赖可审计", "ops:dependencies", "CRITICAL"))

    cve_counts: Dict[str, int] = {}
    for i, d in enumerate(dependencies):
        name = str(d.get("name") or "")
        cves = d.get("cves") or []
        for cve in cves:
            sev = str(cve.get("severity") or "").lower()
            if sev not in cve_severities:
                checks.append(c.ck(False, f"依赖 {name!r} CVE {cve.get('id')!r} severity={sev!r} 不在枚举", "ops:cve_severity", "HIGH", **{"name": name}))
            else:
                cve_counts[sev] = cve_counts.get(sev, 0) + 1
                if sev in ("critical", "high"):
                    checks.append(c.ck(False, f"依赖 {name!r} 含 {sev} 级 CVE {cve.get('id')!r}", "ops:cve_high", "CRITICAL", **{"name": name, "cve": cve.get("id")}))
                else:
                    checks.append(c.ck(True, f"依赖 {name!r} CVE {cve.get('id')!r} 为 {sev} 级", "ops:cve", **{"name": name}))

    if leaked:
        if len(leaked) > max_leaked_keys:
            checks.append(c.ck(False, f"泄露密钥 {len(leaked)} 条 > 上限 {max_leaked_keys}", "ops:leaked_keys", "CRITICAL", **{"count": len(leaked)}))
        else:
            checks.append(c.ck(False, f"发现泄露密钥 {len(leaked)} 条", "ops:leaked_keys", "CRITICAL", **{"count": len(leaked)}))
    else:
        checks.append(c.ck(True, "无泄露密钥", "ops:leaked_keys"))

    ok = all(ch.get("ok", False) for ch in checks)
    verdict = "PASS" if ok else "FAIL"
    out = c.result(checks,
                   dependency_count=len(dependencies),
                   cve_counts=cve_counts,
                   leaked_key_count=len(leaked),
                   verdict=verdict,
                   next="依赖与密钥审计通过" if ok else "修复高危 CVE/泄露密钥后重新 security",
                   )
    return out


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "migration":
        result = migration(data)
    elif args.action == "security":
        result = security(data)
    else:
        raise SystemExit(f"未知动作：{args.action}")
    c.emit(result)
    return result
