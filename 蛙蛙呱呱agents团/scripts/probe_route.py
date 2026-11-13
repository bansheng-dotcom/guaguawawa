# -*- coding: utf-8 -*-
"""单角色路由探针：输出当前 _route() 的行为，用于 P1.0 基线测量。

用法：
    python scripts/probe_route.py --role-dir r06-wadeqing-analyst --intent "看看这数据"
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role-dir", required=True)
    ap.add_argument("--intent", required=True)
    args = ap.parse_args()

    role_dir = os.path.abspath(args.role_dir)
    root = os.path.dirname(os.path.dirname(role_dir))
    sys.path.insert(0, root)
    sys.path.insert(0, role_dir)
    os.chdir(role_dir)

    import agent  # noqa: E402

    # 20 个角色存在四种历史路由形态，探针统一归一化为 (skill, action, defaults)。
    if hasattr(agent, "_route"):
        routed = agent._route(args.intent)
    elif hasattr(agent, "route_intent"):
        routed = agent.route_intent(args.intent)
    elif hasattr(agent, "route"):
        routed = agent.route(args.intent)
    else:
        routed = ("", "", {})

    if isinstance(routed, str):
        skill, action, defaults = routed, "", {}
    elif isinstance(routed, (tuple, list)) and len(routed) >= 2:
        skill, action = routed[0], routed[1]
        defaults = routed[2] if len(routed) > 2 else {}
    else:
        skill, action, defaults = "", "", {}

    table = getattr(agent, "_INTENT_ROUTES", [])
    low = args.intent.lower()
    if table:
        matched = any(any(k.lower() in low for k in kws) for kws, *_ in table)
    else:
        # r03 这类角色用 INTENTS 字典（关键词 → 技能）声明路由。
        intents = getattr(agent, "INTENTS", {})
        matched = any(str(k).lower() in low for k in intents) if intents else None

    out = {
        "role": os.path.basename(role_dir).split("-")[0],
        "intent": args.intent,
        "route": {"skill": skill, "action": action,
                  "params": sorted((defaults or {}).keys()) if isinstance(defaults, dict) else []},
        "keyword_matched": matched,
        "silent_default": matched is False,
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
