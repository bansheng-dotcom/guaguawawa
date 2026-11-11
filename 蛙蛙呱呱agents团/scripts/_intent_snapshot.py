# -*- coding: utf-8 -*-
"""单角色意图路由快照：导入 agent.py，对所有关键词跑 _route，输出 JSON。

用法：python scripts/_intent_snapshot.py <role_dir>
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys


def main() -> int:
    role_dir = os.path.abspath(sys.argv[1])
    sys.path.insert(0, role_dir)
    sys.path.insert(0, os.path.dirname(role_dir))
    spec = importlib.util.spec_from_file_location("agent_under_test",
                                                  os.path.join(role_dir, "agent.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    prof = json.load(open(os.path.join(role_dir, "prompt_profile.json"), encoding="utf-8"))
    routes = prof.get("intent_routes") or []
    routes = routes or [(list(r[0]), r[1], r[2]) for r in mod._INTENT_ROUTES]
    route_fn = getattr(mod, "_route", None) or getattr(mod, "route", None)
    if route_fn is None:
        print(json.dumps({"error": "no _route/route"}))
        return 0
    out = {}
    for r in routes:
        kws = r["when"] if isinstance(r, dict) else list(r[0])
        skill = r["skill"] if isinstance(r, dict) else r[1]
        action = r["action"] if isinstance(r, dict) else r[2]
        for kw in kws:
            got = route_fn(kw)
            out[kw] = [got[0], got[1]] if got else None
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
