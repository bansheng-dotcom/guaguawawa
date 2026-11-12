# -*- coding: utf-8 -*-
"""report_spec 工具：new（从原型生成 role 差异）/ check（全量校验）。

用法：
  python scripts/report_spec.py new --role r12 --archetype decision --prefix 增长
  python scripts/report_spec.py new-all            # 按内置映射批量生成
  python scripts/report_spec.py check
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.report_kernel import spec as kspec  # noqa: E402

# 角色 → (原型, 标题前缀)
ROLE_MAP = {
    "r01": ("decision", "全局"),
    "r02": ("decision", "排布"),
    "r03": ("analyst", "财务"),
    "r04": ("review", "评审"),
    "r05": ("analyst", "调研"),
    "r06": ("analyst", "数据"),
    "r07": ("decision", "产品"),
    "r08": ("decision", "MVP"),
    "r09": ("delivery", "工程"),
    "r10": ("design", "设计"),
    "r11": ("delivery", "文案"),
    "r12": ("decision", "增长"),
    "r13": ("delivery", "客户"),
    "r14": ("decision", "电商"),
    "r15": ("delivery", "供应"),
    "r16": ("delivery", "人力"),
    "r17": ("delivery", "集成"),
    "r18": ("analyst", "数仓"),
    "r19": ("analyst", "模型"),
    "r20": ("delivery", "SRE"),
}


def write_role(role: str, arche: str, prefix: str) -> Path:
    body = (
        f"extends: {arche}\n"
        f"role: {role}\n"
        f"title_prefix: {prefix}\n"
    )
    p = kspec.SPEC_DIR / "roles" / f"{role}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def cmd_new(args) -> int:
    p = write_role(args.role, args.archetype, args.prefix or "")
    print(f"written {p}")
    return 0


def cmd_new_all(_args) -> int:
    for role, (arche, prefix) in ROLE_MAP.items():
        write_role(role, arche, prefix)
    print(f"written {len(ROLE_MAP)} role specs")
    return 0


def cmd_check(_args) -> int:
    roles = kspec.all_roles()
    bad = 0
    for r in roles:
        errs = kspec.validate(r)
        if errs:
            bad += 1
            print(f"[FAIL] {r}: {errs}")
        else:
            s = kspec.load(r)
            print(f"[ OK ] {r} -> {s['extends']} tier {s['tier']} sections {len(s['sections'])}")
    missing = [r for r in ROLE_MAP if r not in roles]
    if missing:
        bad += 1
        print(f"[FAIL] 缺 spec: {missing}")
    print(f"\n总计 {len(roles)} 份，失败 {bad}")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("new"); a.add_argument("--role", required=True)
    a.add_argument("--archetype", required=True); a.add_argument("--prefix", default="")
    a.set_defaults(func=cmd_new)
    b = sub.add_parser("new-all"); b.set_defaults(func=cmd_new_all)
    c = sub.add_parser("check"); c.set_defaults(func=cmd_check)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
