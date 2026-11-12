# -*- coding: utf-8 -*-
"""把 20 个 agent.py 里写死的 _INTENT_ROUTES 迁到 prompt_profile.json。

- 提取：AST 解析字面量；`os.path.join(_HERE, ...)` 这类调用存成 {"__path__": "a/b"}。
- 写入：profile["intent_routes"] = [{"when": [...], "skill": ..., "action": ..., "defaults": {...}}]
- 替换：agent.py 里的赋值改为从 profile 读取（_load_intent_routes）。
"""
from __future__ import annotations

import ast
import glob
import io
import json
import os
import sys

ROOT = r"D:\蛙蛙呱呱\蛙蛙呱呱agents团"

LOADER = '''def _load_intent_routes():
    """意图路由唯一出处：prompt_profile.json 的 intent_routes（勿在代码里再写一份）。"""
    import json as _json
    _p = os.path.join(_HERE, "prompt_profile.json")
    try:
        with open(_p, encoding="utf-8") as _f:
            _data = _json.load(_f)
    except (OSError, ValueError):
        return []
    def _defaults(d):
        out = {}
        for k, v in (d or {}).items():
            if isinstance(v, dict) and "__path__" in v:
                out[k] = os.path.join(_HERE, *str(v["__path__"]).split("/"))
            else:
                out[k] = v
        return out
    return [(tuple(r.get("when") or []), str(r.get("skill") or ""),
             str(r.get("action") or ""), _defaults(r.get("defaults")))
            for r in (_data.get("intent_routes") or [])]


_INTENT_ROUTES = _load_intent_routes()
'''


def ev(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        pass
    if isinstance(node, ast.Dict):
        return {ev(k): ev(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, (ast.Tuple, ast.List)):
        vals = [ev(x) for x in node.elts]
        return tuple(vals) if isinstance(node, ast.Tuple) else vals
    if isinstance(node, ast.Call):
        fn = node.func
        if isinstance(fn, ast.Attribute) and fn.attr == "join":
            parts = []
            for a in node.args[1:]:
                v = ev(a)
                parts.append(str(v))
            return {"__path__": "/".join(parts)}
    raise ValueError(f"无法求值的表达式: {ast.dump(node)[:80]}")


def find_node(tree):
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "_INTENT_ROUTES" for t in n.targets):
            return n
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) \
                and n.target.id == "_INTENT_ROUTES":
            return n
    return None


def migrate(dry: bool = True) -> int:
    ok, fail = 0, []
    for d in sorted(glob.glob(os.path.join(ROOT, "r*"))):
        ap = os.path.join(d, "agent.py")
        if not os.path.isfile(ap):
            continue
        role = os.path.basename(d)
        src = io.open(ap, encoding="utf-8").read()
        tree = ast.parse(src)
        node = find_node(tree)
        if node is None:
            fail.append((role, "_INTENT_ROUTES 未找到"))
            continue
        try:
            raw = ev(node.value)
        except ValueError as exc:
            fail.append((role, str(exc)))
            continue
        routes = []
        for item in raw:
            kws = list(item[0])
            skill = str(item[1])
            action = str(item[2])
            defaults = dict(item[3]) if len(item) > 3 and item[3] else {}
            routes.append({"when": kws, "skill": skill, "action": action,
                           "defaults": defaults})
        if dry:
            ok += 1
            continue

        pp = os.path.join(d, "prompt_profile.json")
        prof = json.load(io.open(pp, encoding="utf-8"))
        prof["intent_routes"] = routes
        with io.open(pp, "w", encoding="utf-8") as f:
            json.dump(prof, f, ensure_ascii=False, indent=2)
            f.write("\n")

        lines = src.splitlines(keepends=True)
        start = node.lineno - 1
        end = node.end_lineno
        src2 = "".join(lines[:start]) + LOADER + "".join(lines[end:])
        io.open(ap, "w", encoding="utf-8").write(src2)
        ok += 1

    print(f"{'DRY-RUN ' if dry else ''}迁移成功 {ok} 个")
    for role, err in fail:
        print(f"  [FAIL] {role}: {err}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(migrate(dry="--apply" not in sys.argv))
