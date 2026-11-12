# -*- coding: utf-8 -*-
"""MCP 体检/登记 CLI（零依赖）。

    python scripts/mcp_doctor.py list
    python scripts/mcp_doctor.py doctor            # 只体检 enabled=true 的
    python scripts/mcp_doctor.py doctor --all      # 连预留槽位一起报
    python scripts/mcp_doctor.py template search   # 打印该槽位的接入模板
    python scripts/mcp_doctor.py add search --command "uvx mcp-server-brave" --args ...

接入流程：填 registry.json → enabled=true → doctor 通过 → 在角色方法包里登记工具。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.mcp.client import MCPError, doctor, load_registry  # noqa: E402


def cmd_list(reg: dict) -> int:
    rows = reg["servers"]
    print(f"{'槽位':<16}{'状态':<10}{'负责人':<8}{'传输':<8}{'消费者'}")
    print("-" * 78)
    for name, s in rows.items():
        state = "已启用" if s.get("enabled") else "预留"
        print(f"{name:<16}{state:<10}{s.get('owner_role',''):<8}{s['transport']:<8}{','.join(s.get('consumers', []))}")
    on = sum(1 for s in rows.values() if s.get("enabled"))
    print(f"\n共 {len(rows)} 个槽位，已启用 {on} 个。")
    return 0


def cmd_doctor(reg: dict, all_slots: bool) -> int:
    results = []
    for name, s in reg["servers"].items():
        if not s.get("enabled") and not all_slots:
            continue
        results.append(doctor(s, name))
    bad = 0
    for r in results:
        if r["status"] == "ok":
            print(f"[OK]   {r['name']:<16} tools={r['count']} {r['tools'][:6]}")
        elif r["status"] == "reserved":
            print(f"[--]   {r['name']:<16} {r['detail']}")
        else:
            bad += 1
            print(f"[FAIL] {r['name']:<16} {r['detail']}")
    print(f"\n体检 {len(results)} 个，失败 {bad} 个。")
    return 1 if bad else 0


def cmd_template(reg: dict, name: str) -> int:
    s = reg["servers"].get(name)
    if not s:
        print(f"没有槽位 {name}；可选：{', '.join(reg['servers'])}")
        return 1
    print(json.dumps({name: s}, ensure_ascii=False, indent=2))
    return 0


def cmd_add(reg: dict, name: str, command: str, args: list[str], url: str) -> int:
    s = reg["servers"].get(name)
    if not s:
        print(f"没有槽位 {name}；先在 registry.json 里加槽位，再接入")
        return 1
    if s["transport"] == "stdio":
        if not command:
            print("stdio 槽位需要 --command")
            return 1
        s["command"], s["args"] = command, args
    else:
        if not url:
            print("http 槽位需要 --url")
            return 1
        s["url"] = url
    s["enabled"] = True
    p = ROOT / "shared" / "mcp" / "registry.json"
    p.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已登记 {name} 并启用；下一步：python scripts/mcp_doctor.py doctor")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    d = sub.add_parser("doctor")
    d.add_argument("--all", action="store_true")
    t = sub.add_parser("template")
    t.add_argument("name")
    a = sub.add_parser("add")
    a.add_argument("name")
    a.add_argument("--command", default="")
    a.add_argument("--args", nargs="*", default=[])
    a.add_argument("--url", default="")
    ns = ap.parse_args()

    try:
        reg = load_registry()
    except MCPError as exc:
        print(f"registry 校验失败：{exc}")
        return 2

    if ns.cmd == "list":
        return cmd_list(reg)
    if ns.cmd == "doctor":
        return cmd_doctor(reg, ns.all)
    if ns.cmd == "template":
        return cmd_template(reg, ns.name)
    if ns.cmd == "add":
        return cmd_add(reg, ns.name, ns.command, ns.args, ns.url)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
