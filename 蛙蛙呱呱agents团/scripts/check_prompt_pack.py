#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""20 角色提示词拼装自检：四层是否齐、schema 是否可校验、失败是否回退。

判定：
    1. 每个角色 build() 必须成功，且 L2 领域块 ≥1；
    2. system 必须含角色宪法与领域名，user 必须含输入与输出要求；
    3. schema.must_include 非空；
    4. 模型返回合法 JSON → ok；返回脏数据 → 触发回退且 fallback=True；
    5. 缺角色 → 失败而不是静默。

用法：python scripts/check_prompt_pack.py
退出码：0 全过 / 1 有问题
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared import prompt_pack as pp  # noqa: E402

ROLES = [f"r{i:02d}" for i in range(1, 21)]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    fails = []
    for rid in ROLES:
        pack = pp.build(rid, "check", {"topic": "自检样例"})
        if not pack.get("ok"):
            fails.append(f"{rid}: build 失败 {pack.get('error')}")
            continue
        if pack["l2_block_count"] < 1:
            fails.append(f"{rid}: L2 块为 0")
        system = pack["messages"][0]["content"]
        user = pack["messages"][1]["content"]
        if pack["domain"] and pack["domain"] not in system:
            fails.append(f"{rid}: system 未包含领域")
        if "绝不做的三件事" not in system:
            fails.append(f"{rid}: system 缺角色宪法")
        if "本次输入" not in user:
            fails.append(f"{rid}: user 缺输入契约")
        if not pack["schema"]["must_include"]:
            fails.append(f"{rid}: must_include 为空")

    # 合法输出 → 通过
    good = {"ok": True}
    pack = pp.build("r07", "prd", {"topic": "礼盒"})
    good = {k: "x" for k in pack["schema"]["must_include"]}
    res = pp.generate("r07", "prd", {"topic": "礼盒"},
                      client=lambda msgs: json.dumps(good, ensure_ascii=False))
    if not res.get("ok") or res.get("fallback"):
        fails.append(f"generate 合法输出未通过：{res.get('errors')}")

    # 脏输出 → 回退
    res2 = pp.generate("r07", "prd", {"topic": "礼盒"},
                       client=lambda msgs: json.dumps({"随手": "写点"}, ensure_ascii=False),
                       fallback=lambda: {"fallback": "skills"})
    if not res2.get("fallback"):
        fails.append("generate 脏输出未触发回退")

    # 缺角色 → 失败
    if pp.build("r99").get("ok"):
        fails.append("缺角色未报错")

    print("20 角色提示词拼装自检")
    print("=" * 66)
    print(f"角色 {len(ROLES)} 个｜问题 {len(fails)}")
    for f in fails:
        print("  [FAIL] " + f)
    if fails:
        return 1
    print("\n[OK] 20 角色四层齐备，schema 可校验，失败可回退")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
