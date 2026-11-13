#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全员 LLM 网关自检：接入点覆盖、默认关闭、开启后可接管、脏输入不接管。

用法：python scripts/check_prompt_wiring.py
退出码：0 全过 / 1 有问题
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared import prompt_gateway as gw  # noqa: E402
from shared import prompt_pack as pp  # noqa: E402

ROLES = [f"r{i:02d}" for i in range(1, 21)]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    fails = []

    # 1) 19 个角色走同一个接入点（r10 自带 imagegen 路径，不强求）
    covered = []
    for rid in ROLES:
        d = pp.role_dir(rid)
        agent = os.path.join(d, "agent.py") if d else ""
        if agent and os.path.isfile(agent):
            src = open(agent, encoding="utf-8", errors="replace").read()
            if "handle_meta_command" in src:
                covered.append(rid)
    if len(covered) < 19:
        fails.append(f"接入点覆盖不足：{len(covered)}/20 -> {covered}")

    # 2) 默认关闭：不设 flag 时一律不接管
    argv = ["prd", "prd", "--input", "x.json"]
    if gw.maybe("r07", argv) is not None:
        fails.append("默认状态不应接管")

    # 3) 开了 flag 但没 Key：不接管
    os.environ["PROMPT_PACK_LLM"] = "1"
    for k in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
        os.environ.pop(k, None)
    if gw.maybe("r07", argv) is not None:
        fails.append("无 Key 时不应接管")

    # 4) 有 Key + 未设 flag：默认就走模型优先，接管并标 llm=True
    os.environ.pop("PROMPT_PACK_LLM", None)
    os.environ["DEEPSEEK_API_KEY"] = "test-key"
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"topic": "礼盒"}, f, ensure_ascii=False)

    pack = pp.build("r07", "prd.prd", {"topic": "礼盒"})
    good = {k: "x" for k in pack["schema"]["must_include"]}
    orig = pp.generate
    try:
        pp.generate = lambda *a, **k: {"ok": True, "payload": good, "attempts": 1}
        res = gw.maybe("r07", ["prd", "prd", "--input", path])
    finally:
        pp.generate = orig
    if not res or not res.get("llm"):
        fails.append(f"有 Key 默认应接管：{res}")

    # 4.1) 显式关掉：PROMPT_PACK_LLM=0 + Key → 不接管
    os.environ["PROMPT_PACK_LLM"] = "0"
    if gw.maybe("r07", ["prd", "prd", "--input", path]) is not None:
        fails.append("PROMPT_PACK_LLM=0 时不应接管")
    os.environ.pop("PROMPT_PACK_LLM", None)

    # 5) 未登记动作：不接管
    try:
        pp.generate = lambda *a, **k: {"ok": True, "payload": {}, "attempts": 1}
        res2 = gw.maybe("r07", ["not-a-skill", "nope", "--input", path])
    finally:
        pp.generate = orig
    if res2 is not None:
        fails.append("未登记动作不应接管")

    # 6) 模型输出不合法：回退（不接管）
    try:
        pp.generate = lambda *a, **k: {"ok": False, "errors": ["x"]}
        res3 = gw.maybe("r07", ["prd", "prd", "--input", path])
    finally:
        pp.generate = orig
    if res3 is not None:
        fails.append("校验失败时不应接管（应回退规则实现）")

    for k in ("PROMPT_PACK_LLM", "DEEPSEEK_API_KEY"):
        os.environ.pop(k, None)
    try:
        os.unlink(path)
    except OSError:
        pass

    print("全员 LLM 网关自检")
    print("=" * 62)
    print(f"接入点覆盖 {len(covered)}/20｜问题 {len(fails)}")
    for f in fails:
        print("  [FAIL] " + f)
    if fails:
        return 1
    print("\n[OK] 19 角色同点接入；有 Key 默认接管；PROMPT_PACK_LLM=0 可关；脏输出回退")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
