# -*- coding: utf-8 -*-
"""契约测试：20 角色 × 3 fixture。

两种闸门：
  --mode preserve  旧路径（generic_contract）仍合法且哈希稳定 —— 证明重构未破坏行为
  --mode spec      新内核（report_kernel）产出满足 spec —— 证明迁移达标

用法：
  python scripts/contract_test.py --all --mode spec
  python scripts/contract_test.py --role r06 --mode preserve
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import report_bridge  # noqa: E402
from core import report_renderer  # noqa: E402
from core.report_kernel import layers as klayers  # noqa: E402
from core.report_kernel import spec as kspec  # noqa: E402
from scripts.report_spec import ROLE_MAP  # noqa: E402

FIXTURES = {
    "normal": {
        "ok": True,
        "conclusion": "本次执行完成，门禁全部通过。",
        "checks": [
            {"ok": True, "dim": "contract", "msg": "字段齐备"},
            {"ok": True, "dim": "gate", "msg": "门禁通过"},
            {"ok": True, "dim": "evidence", "msg": "证据链完整"},
        ],
        "items": [{"name": "A", "value": 1.0}, {"name": "B", "value": 2.0}],
        "notes": ["样本数据，用于契约测试"],
    },
    "empty": {},
    "failure": {
        "ok": False,
        "checks": [{"ok": False, "dim": "gate", "msg": "门禁未通过：缺证据"}],
        "next": "回补证据后重跑",
    },
}

DATASET = [
    {"date": "2026-10-01", "item": "牛肉", "value": 37.0, "unit": "元/斤", "source": "test"},
    {"date": "2026-10-02", "item": "牛肉", "value": 37.2, "unit": "元/斤", "source": "test"},
    {"date": "2026-10-01", "item": "鸡蛋", "value": 5.4, "unit": "元/斤", "source": "test"},
    {"date": "2026-10-02", "item": "鸡蛋", "value": 5.2, "unit": "元/斤", "source": "test"},
]


def h(contract) -> str:
    return hashlib.sha256(json.dumps(contract, ensure_ascii=False, sort_keys=True, default=str)
                          .encode()).hexdigest()[:12]


def run_preserve(role: str) -> dict:
    rows = []
    for fname, res in FIXTURES.items():
        c1 = report_bridge.generic_contract(res, role, "测试", "契约测试", "skill", "action", "intent")
        c2 = report_bridge.generic_contract(res, role, "测试", "契约测试", "skill", "action", "intent")
        errs = report_renderer.validate_contract(c1)
        rows.append({"fixture": fname, "valid": not errs, "stable": h(c1) == h(c2), "errors": errs})
    return {"role": role, "rows": rows}


def _layout_errors(contract) -> list:
    """底层版式规则：分数在末尾 / 记录层折叠 / 不允许结论清单复述。"""
    errs = []
    secs = contract.get("sections") or []
    if not secs:
        return ["无章节"]
    last = secs[-1]
    if last.get("title") != "口径与分数":
        errs.append(f"末节不是「口径与分数」: {last.get('title')}")
    if not any(s.get("appendix") for s in secs):
        errs.append("记录层未标 appendix（应折叠）")
    for s in secs:
        if "结论清单" in s.get("title", "") or "摘要复述" in s.get("title", ""):
            errs.append(f"出现重复章节: {s.get('title')}")
    strip = contract.get("metric_strip") or []
    for m in strip:
        if m.get("label") in ("保留率", "溯源率", "弃置率"):
            errs.append(f"首页指标带仍含自检分数: {m.get('label')}")
    return errs


def run_spec(role: str) -> dict:
    s = kspec.load(role)
    rows = []
    for fname, res in FIXTURES.items():
        ds = DATASET if s["tier"] == "A" else None
        c, fid = klayers.build_contract(role, "测试", "契约测试", res, s, "skill", "action",
                                        "intent", dataset=ds)
        errs = report_renderer.validate_contract(c)
        spec_errs = klayers.spec_compliance(c, s) + _layout_errors(c)
        rows.append({"fixture": fname, "valid": not errs, "spec_ok": not spec_errs,
                     "spec_errors": spec_errs, "fid": fid})
    return {"role": role, "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--mode", choices=["preserve", "spec"], default="spec")
    args = ap.parse_args(argv)

    roles = sorted(ROLE_MAP) if args.all else [args.role]
    fail = 0
    print(f"mode={args.mode} roles={len(roles)}")
    for r in roles:
        out = run_preserve(r) if args.mode == "preserve" else run_spec(r)
        for row in out["rows"]:
            if args.mode == "preserve":
                ok = row["valid"] and row["stable"]
                flag = "PASS" if ok else "FAIL"
                if not ok:
                    fail += 1
                print(f'  {flag} {r} {row["fixture"]:<8} valid={row["valid"]} stable={row["stable"]}')
            else:
                # spec 模式：normal 必须过；empty/failure 允许 spec 不达标，但 contract 必须合法
                ok = row["valid"] and (row["spec_ok"] or row["fixture"] != "normal")
                flag = "PASS" if ok else "FAIL"
                if not ok:
                    fail += 1
                extra = "" if row["spec_ok"] else f' spec_errs={len(row["spec_errors"])}'
                print(f'  {flag} {r} {row["fixture"]:<8} valid={row["valid"]}{extra}')
    print(f"\n失败 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
