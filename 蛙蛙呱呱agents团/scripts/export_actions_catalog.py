#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0 基线导出器：扫描 20 个角色的技能模块，导出动作目录与 CLI 必填字段。

用法：
    python scripts/export_actions_catalog.py --all
    python scripts/export_actions_catalog.py --role-dir <角色绝对路径>   # 内部子进程用

输出：
    docs/actions_catalog.json

说明：
    必填字段取 argparse 层 `required=True` 的选项；这是 P0 的确定性初稿，
    P1 再补语义字段（dataset / metric / time_window 等）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "actions_catalog.json")


def _type_name(tp):
    if tp is None:
        return "str"
    return getattr(tp, "__name__", str(tp))


def _extract_args(parser):
    required, optional, positional = [], [], []
    for act in parser._actions:
        if act.dest in ("help", "action"):
            continue
        if not act.option_strings:
            positional.append({"name": act.dest, "required": bool(act.required)})
            continue
        item = {
            "name": act.dest,
            "flags": list(act.option_strings),
            "type": _type_name(act.type),
            "default": act.default if isinstance(act.default, (str, int, float, bool, type(None))) else None,
            "help": (act.help or "").strip(),
        }
        (required if act.required else optional).append(item)
    return required, optional, positional


def scan_role(role_dir: str) -> dict:
    role_dir = os.path.abspath(role_dir)
    sys.path.insert(0, ROOT)
    sys.path.insert(0, role_dir)

    from core.registry import ROLES  # noqa: E402

    role_id = os.path.basename(role_dir).split("-")[0]
    meta = next((r for r in ROLES if r["id"] == role_id), {})

    import skills  # noqa: E402

    skills_out = []
    for mod in skills.SKILLS:
        name = getattr(mod, "NAME", None) or getattr(mod, "HEAP", None) or mod.__name__.split(".")[-1]
        desc = (getattr(mod, "DESC", "") or getattr(mod, "HEAP", "") or "").strip()
        actions, mode, error = [], "", ""
        if hasattr(mod, "add_parser"):
            parser = argparse.ArgumentParser(add_help=False)
            sub = parser.add_subparsers()
            try:
                mod.add_parser(sub)
                skill_parser = sub.choices.get(name)
                acts = [a for a in skill_parser._actions
                        if isinstance(a, argparse._SubParsersAction)] if skill_parser else []
                if acts:
                    helps = {c.dest: (c.help or "").strip() for c in acts[0]._choices_actions}
                    for aname, ap in acts[0].choices.items():
                        req, opt, pos = _extract_args(ap)
                        actions.append({"name": aname, "help": helps.get(aname, ""),
                                        "required": [x["name"] for x in req],
                                        "required_detail": req, "optional": opt,
                                        "positional": pos})
                    mode = "argparse"
                elif skill_parser is not None:
                    req, opt, pos = _extract_args(skill_parser)
                    actions.append({"name": "run", "help": "", "required": [x["name"] for x in req],
                                    "required_detail": req, "optional": opt, "positional": pos})
                    mode = "argparse_single"
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

        if not actions:
            # 兼容历史技能模块：用 ACTIONS 字典或模块内公开函数作为动作来源。
            declared = getattr(mod, "ACTIONS", None)
            if isinstance(declared, dict) and declared:
                # 这类模块没有 add_parser，CLI 由 agent.py 统一按 `--input` 构造。
                # 目录必须反映该真实约束，否则 P2 会误判为“无需输入”。
                actions = [{"name": k, "help": str(v), "required": ["input"],
                            "required_detail": [{"name": "input", "flags": ["--input"],
                                                 "type": "str", "default": None,
                                                 "help": "动作输入 JSON"}],
                            "optional": [], "positional": []}
                           for k, v in declared.items()]
                mode = "ACTIONS"
            else:
                funcs = [f for n, f in vars(mod).items()
                         if callable(f) and not n.startswith("_") and n not in ("add_parser", "run")
                         and getattr(f, "__module__", "") == mod.__name__]
                actions = [{"name": f.__name__, "help": (f.__doc__ or "").strip().splitlines()[0]
                            if f.__doc__ else "", "required": [], "required_detail": [],
                            "optional": [], "positional": []} for f in funcs]
                mode = "functions" if actions else "none"

        skills_out.append({"name": name, "desc": desc, "file": _rel(mod.__file__),
                           "extract_mode": mode, "error": error, "actions": actions})

    return {
        "role": role_id,
        "name": meta.get("name", ""),
        "title": meta.get("title", ""),
        "dir": os.path.basename(role_dir),
        "skill_count": len(skills_out),
        "action_count": sum(len(s["actions"]) for s in skills_out),
        "skills": skills_out,
    }


def _rel(path: str) -> str:
    try:
        return os.path.relpath(path, ROOT).replace("\\", "/")
    except ValueError:
        return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--role-dir")
    ap.add_argument("--out", default=None, help="输出路径（CI 自检时写入临时文件）")
    args = ap.parse_args()

    if args.role_dir:
        print(json.dumps(scan_role(args.role_dir), ensure_ascii=False))
        return 0

    roles = sorted(d for d in os.listdir(ROOT)
                   if d.startswith("r") and "-" in d and os.path.isdir(os.path.join(ROOT, d)))
    results, errors = [], []
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for d in roles:
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--role-dir",
                            os.path.join(ROOT, d)],
                           cwd=os.path.join(ROOT, d), capture_output=True, text=True,
                           encoding="utf-8", env=env)
        if p.returncode != 0 or not p.stdout.strip():
            errors.append({"dir": d, "rc": p.returncode, "stderr": p.stderr[-500:]})
            continue
        results.append(json.loads(p.stdout))

    payload = {
        "generated_by": "scripts/export_actions_catalog.py",
        "python": sys.version.split()[0],
        "summary": {
            "roles": len(results),
            "skills": sum(r["skill_count"] for r in results),
            "actions": sum(r["action_count"] for r in results),
        },
        "errors": errors,
        "roles": results,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out_path = args.out or OUT
    if os.path.dirname(out_path):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(json.dumps(payload["summary"], ensure_ascii=False))
    for e in errors:
        print(f"[ERROR] {e['dir']} rc={e['rc']} {e['stderr'][-200:]}", file=sys.stderr)
    print(f"written: {out_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
