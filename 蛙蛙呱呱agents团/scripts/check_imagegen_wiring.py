#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨角色生图接线一致性检查：**声明了转交 r10，就必须真的调**。

为什么需要它：
    「主图归 r10」这句话如果只写在技能卡里，而本角色没有任何调用路径，
    就是文档与代码的漂移——用户按文档以为会交接，实际没人发起请求。
    本脚本只认两种状态：要么没声称转交，要么有真实调用（`imagegen_client`）。

判定：
    1. 任一角色文档里出现「转/交给/调用 r10」这类强委托措辞 → 该角色 skills/ 必须
       出现 `imagegen_client`（真实调用），否则记冲突。
    2. 反向：角色代码调了 client，但文档没写入口 → 记警告（不失败）。
    3. 基础件：`shared/imagegen_client.py` 存在，且 R10 有 `compose` 动作。

用法：
    python scripts/check_imagegen_wiring.py
    python scripts/check_imagegen_wiring.py --json

退出码：0 一致 / 1 有冲突 / 2 环境问题
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLIENT = os.path.join(ROOT, "shared", "imagegen_client.py")
R10_AGENT = os.path.join(ROOT, "r10-wachengmei-design", "agent.py")

STRONG = re.compile(r"(转|交给|调用)\s*`?r10", re.IGNORECASE)
WIRING_HINT = ("platform visual", "catalog image", "imagegen_client", "imagegen_bridge")


def roles() -> list:
    return sorted(d for d in os.listdir(ROOT)
                  if d.startswith("r") and os.path.isdir(os.path.join(ROOT, d)))


def md_files(role_dir: str) -> list:
    out = []
    for base, _dirs, files in os.walk(role_dir):
        for f in files:
            if f.endswith(".md"):
                out.append(os.path.join(base, f))
    return sorted(out)


def py_files(role_dir: str) -> list:
    skills = os.path.join(role_dir, "skills")
    out = []
    for base, _dirs, files in os.walk(skills):
        for f in files:
            if f.endswith(".py"):
                out.append(os.path.join(base, f))
    return out


def check() -> dict:
    problems, warnings = [], []

    if not os.path.isfile(CLIENT):
        problems.append({"scope": "shared", "msg": "缺少 shared/imagegen_client.py"})
    if not os.path.isfile(R10_AGENT):
        problems.append({"scope": "r10", "msg": "缺少 r10-wachengmei-design/agent.py"})
    else:
        src = open(R10_AGENT, encoding="utf-8").read()
        if "imagegen" not in src:
            warnings.append({"scope": "r10", "msg": "agent.py 未见 imagegen 注册"})
        # 默认意图必须是 compose（提示词路线），不能默认 generate（要引擎）
        if ('"imagegen", "compose"' not in src) or ('"imagegen", "generate"' in src):
            problems.append({"scope": "r10", "msg": "默认意图未指向 imagegen compose"})

    for role in roles():
        role_dir = os.path.join(ROOT, role)
        claims = []
        for path in md_files(role_dir):
            text = open(path, encoding="utf-8", errors="replace").read()
            for ln, line in enumerate(text.splitlines(), 1):
                if STRONG.search(line):
                    claims.append({"file": os.path.relpath(path, ROOT),
                                   "line": ln, "text": line.strip()[:90]})
        uses = False
        for path in py_files(role_dir):
            if any(k in open(path, encoding="utf-8", errors="replace").read()
                   for k in ("imagegen_client", "imagegen_bridge")):
                uses = True
                break
        if claims and not uses:
            for c in claims:
                problems.append({"scope": role, "msg": "声明转交但无调用实现",
                                 **c})
        if uses and not claims:
            warnings.append({"scope": role,
                             "msg": "已有调用实现但文档未写入口（建议补一行命令）"})

        docs = " ".join(open(p, encoding="utf-8", errors="replace").read()
                        for p in md_files(role_dir))
        if uses and not any(h in docs for h in WIRING_HINT):
            warnings.append({"scope": role, "msg": "调用实现已有，但文档没给命令示例"})

    return {"roles": len(roles()), "problems": problems, "warnings": warnings}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="跨角色生图接线一致性检查")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    res = check()
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 1 if res["problems"] else 0

    print("跨角色生图接线检查（声明转交 r10 就必须真有调用）")
    print("=" * 70)
    print(f"扫描角色 {res['roles']} 个｜冲突 {len(res['problems'])}｜提示 {len(res['warnings'])}")
    for p in res["problems"]:
        print(f"  [冲突] {p['scope']}  {p['msg']}")
        if p.get("file"):
            print(f"         {p['file']}:{p['line']}  {p['text']}")
    for w in res["warnings"]:
        print(f"  [提示] {w['scope']}  {w['msg']}")
    if res["problems"]:
        print("\n修复：要么补 `from shared.imagegen_client import compose` 的真实调用，"
              "要么把措辞改成「本卡不产出，由 r10 负责」。")
        return 1
    print("\n[OK] 无冲突：所有声称转交的角色都有调用实现")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
