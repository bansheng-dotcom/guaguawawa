#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""能力调用频次盘点：从各角色运行日志反推"哪些能力真的被用过"。

为什么需要它：
    能力目录（catalog.json）记录的是"我们声称有什么"，不是"实际用了什么"。
    决定一张旧卡该不该优先升级时，"有没有被调用"比"看起来重不重要"更有依据。

数据来源（只读，不改任何文件）：
    */workspace/logs/*.jsonl
    workspace/logs/*.jsonl
       每行一个 JSON：{"ts","role","level","event","payload":{"skill","action","ok",...}}

局限（如实说明，不掩盖）：
    1. 只有 `kind: skill` 且有 `entry` 的能力能被观测；
       `kind: knowledge` 的规范卡没有命令入口 → **天然零记录**，不代表没价值。
    2. 日志只覆盖本机跑过的调用，不含线上真实流量。
    3. 旧日志的 ts 可能跨月，`--since` 可限定时间窗。

用法：
    python scripts/capability_usage.py                 # 人读报告
    python scripts/capability_usage.py --json          # 机器可读
    python scripts/capability_usage.py --since 2026-11-01
    python scripts/capability_usage.py --top 30

退出码：0 正常 / 2 找不到日志
"""
from __future__ import annotations

import argparse
import collections
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CATALOG = os.path.join(ROOT, "shared", "capabilities", "catalog.json")


def log_files() -> list:
    pats = [
        os.path.join(ROOT, "*", "workspace", "logs", "*.jsonl"),
        os.path.join(ROOT, "workspace", "logs", "*.jsonl"),
        os.path.join(ROOT, "agents", "workspace", "logs", "*.jsonl"),
    ]
    out = []
    for p in pats:
        out.extend(glob.glob(p))
    return sorted(set(out))


def read_events(since: str = "") -> tuple:
    """返回 (events, 坏行数)。事件含 ts/role/skill/action/ok。"""
    events, bad = [], 0
    for path in log_files():
        with io.open(path, encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    bad += 1
                    continue
                pl = rec.get("payload") or {}
                skill = str(pl.get("skill") or "").strip()
                action = str(pl.get("action") or "").strip()
                if not skill and not action:
                    continue
                ts = str(rec.get("ts") or "")
                if since and ts < since:
                    continue
                events.append({
                    "ts": ts,
                    "role": str(rec.get("role") or ""),
                    "skill": skill,
                    "action": action,
                    "ok": pl.get("ok"),
                    "event": str(rec.get("event") or ""),
                })
    return events, bad


def load_caps() -> list:
    with io.open(CATALOG, encoding="utf-8") as fh:
        return list(json.load(fh).get("capabilities", []))


def build_index(caps: list) -> dict:
    """按「角色 + skill（+ action）」建索引。

    **必须带角色**：不同角色会重名同一个 skill（r06 与 r18 都有 `quality`），
    不带角色会把 r18 的调用错记到 r06 的能力上——这是本工具第一版的真实 bug。
    """
    by_pair, by_skill = collections.defaultdict(list), collections.defaultdict(list)
    for c in caps:
        ent = c.get("entry") or {}
        sk = str(ent.get("skill") or "").strip()
        if not sk:
            continue
        role = str(c.get("owner") or "").strip().lower()
        by_skill[(role, sk)].append(c["id"])
        for act in ent.get("actions") or []:
            by_pair[(role, sk, str(act).strip())].append(c["id"])
        # 一个能力可跨多个 skill（entry.skills），逐条登记
        for extra in ent.get("skills") or []:
            sk2 = str((extra or {}).get("skill") or "").strip()
            if not sk2:
                continue
            for act in (extra or {}).get("actions") or []:
                by_pair[(role, sk2, str(act).strip())].append(c["id"])
    return {"pair": by_pair, "skill": by_skill}


def aggregate(events: list, index: dict, caps_by_id: dict) -> dict:
    pair_cnt = collections.Counter()
    pair_ok = collections.Counter()
    pair_fail = collections.Counter()
    pair_last = {}
    pair_roles = collections.defaultdict(set)

    for e in events:
        key = (e["role"].lower(), e["skill"], e["action"])
        pair_cnt[key] += 1
        if e["ok"] is True:
            pair_ok[key] += 1
        elif e["ok"] is False:
            pair_fail[key] += 1
        ts = e["ts"]
        if ts and (key not in pair_last or ts > pair_last[key]):
            pair_last[key] = ts
        if e["role"]:
            pair_roles[key].add(e["role"])

    cap_usage = collections.defaultdict(lambda: {"calls": 0, "ok": 0, "fail": 0,
                                                 "last": "", "roles": set(), "pairs": []})
    unmapped = collections.Counter()
    for key, n in pair_cnt.items():
        role_k, sk, act = key
        # 只认精确 (role, skill, action) 匹配。
        # 曾经的 skill 级兜底会把同一 skill 下未声明的 action 也算进来，属虚增。
        ids = index["pair"].get(key) or []
        if not ids:
            unmapped[(role_k, sk, act)] = n
            continue
        for cid in ids:
            u = cap_usage[cid]
            u["calls"] += n
            u["ok"] += pair_ok[key]
            u["fail"] += pair_fail[key]
            u["roles"] |= pair_roles[key]
            u["pairs"].append(f"{role_k}:{sk}.{act}")
            if pair_last.get(key, "") > u["last"]:
                u["last"] = pair_last[key]

    return {"pairs": pair_cnt, "pair_ok": pair_ok, "pair_fail": pair_fail,
            "pair_last": pair_last, "pair_roles": pair_roles,
            "caps": cap_usage, "unmapped": unmapped}


def table(rows, cols, headers):
    widths = [len(h) for h in headers]
    for r in rows:
        for i, c in enumerate(cols):
            widths[i] = max(widths[i], len(str(r.get(c, ""))))
    out = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)),
           "  ".join("-" * widths[i] for i in range(len(headers)))]
    for r in rows:
        out.append("  ".join(str(r.get(c, "")).ljust(widths[i]) for i, c in enumerate(cols)))
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="能力调用频次盘点（只读日志）")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    ap.add_argument("--since", default="", help="只统计 ts >= 该值的事件（如 2026-11-01）")
    ap.add_argument("--top", type=int, default=20, help="明细表显示前 N 条（默认 20）")
    ap.add_argument("--check", action="store_true",
                    help="目录漂移门禁：有调用量 ≥ 阈值却未登记的 action 时退出码 1（CI 用）")
    ap.add_argument("--threshold", type=int, default=10,
                    help="--check 的调用量阈值（默认 10）")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    files = log_files()
    if not files:
        print("[usage] 找不到任何 workspace/logs/*.jsonl", file=sys.stderr)
        return 2

    events, bad = read_events(args.since)
    with io.open(CATALOG, encoding="utf-8") as fh:
        catalog_doc = json.load(fh)
    caps = list(catalog_doc.get("capabilities", []))
    observed_declared = {(o.get("role"), o.get("skill"), o.get("action"))
                         for o in (catalog_doc.get("observed_actions") or [])}
    caps_by_id = {c["id"]: c for c in caps}
    index = build_index(caps)
    agg = aggregate(events, index, caps_by_id)

    ts_all = sorted(e["ts"] for e in events if e["ts"])
    span = (ts_all[0], ts_all[-1]) if ts_all else ("", "")

    # 每张卡一行
    rows = []
    for c in caps:
        cid = c["id"]
        st = c.get("status", "active")
        u = agg["caps"].get(cid)
        rows.append({
            "id": cid,
            "owner": c["owner"],
            "status": st,
            "kind": c["kind"],
            "entry": "有" if (c.get("entry") or {}).get("skill") else "—",
            "calls": u["calls"] if u else 0,
            "ok": u["ok"] if u else 0,
            "fail": u["fail"] if u else 0,
            "last": (u["last"] if u else "") or "—",
        })

    # 升级优先级（仅针对 active 卡）
    def priority(r):
        if r["status"] != "active":
            return None
        if r["calls"] > 0:
            return "P1 有实测调用"
        if r["entry"] == "有":
            return "P2 有入口但零调用"
        return "P3 无入口（规范卡，不可测）"

    for r in rows:
        r["priority"] = priority(r) or ""

    # 目录漂移：调用量达标却既没登记能力、也没登记 observed 的 action
    drift = [(k, v) for k, v in agg["unmapped"].most_common()
             if v >= args.threshold and k not in observed_declared]
    declared_hit = sum(1 for k, v in agg["unmapped"].items() if k in observed_declared)

    if args.check:
        print("能力目录漂移检查（--check）")
        print("=" * 70)
        print(f"日志事件 {len(events)}｜未登记 action {len(agg['unmapped'])} 组"
              f"｜其中已在 observed_actions 备案 {declared_hit} 组")
        if drift:
            print(f"\n[FAIL] {len(drift)} 组调用量 ≥ {args.threshold} 却未备案：")
            for (role, sk, act), n in drift[:20]:
                print(f"  {role} {sk}.{act}  calls={n}")
            print("\n修复：python scripts/sync_catalog_observed.py（或把它加进 catalog.observed_actions）")
            return 1
        print(f"\n[OK] 无未备案的高频调用（阈值 {args.threshold}）")
        return 0

    if args.json:
        print(json.dumps({
            "log_files": [os.path.relpath(f, ROOT).replace(os.sep, "/") for f in files],
            "events": len(events), "bad_lines": bad,
            "span": span, "since": args.since,
            "rows": rows,
            "top_pairs": [{"role": k[0], "skill": k[1], "action": k[2], "calls": v,
                           "ok": agg["pair_ok"][k], "fail": agg["pair_fail"][k],
                           "last": agg["pair_last"].get(k, ""),
                           "roles": sorted(agg["pair_roles"][k])}
                          for k, v in agg["pairs"].most_common()],
            "unmapped": [{"role": k[0], "skill": k[1], "action": k[2], "calls": v}
                         for k, v in agg["unmapped"].most_common()],
        }, ensure_ascii=False, indent=2))
        return 0

    print("蛙蛙呱呱 · 能力调用频次盘点")
    print("=" * 78)
    print(f"日志文件 {len(files)} 个｜事件 {len(events)} 条｜坏行 {bad}｜"
          f"时间跨度 {span[0][:10]} → {span[1][:10]}" if events else "无事件")
    if args.since:
        print(f"过滤：ts >= {args.since}")

    calls = [r for r in rows if r["calls"] > 0]
    print(f"\n有调用记录的能力：{len(calls)} / {len(rows)}")
    if calls:
        print(table(sorted(calls, key=lambda r: -r["calls"])[:args.top],
                    ["id", "owner", "calls", "ok", "fail", "last"],
                    ["能力", "负责", "调用", "通过", "失败", "最近"][:6]))

    print(f"\nTop {args.top} 被调用的 skill.action")
    print(table([{"role": k[0], "skill": k[1], "action": k[2], "calls": v,
                  "ok": agg["pair_ok"][k], "fail": agg["pair_fail"][k],
                  "last": agg["pair_last"].get(k, "")[:10],
                  "roles": ",".join(sorted(agg["pair_roles"][k]))}
                 for k, v in agg["pairs"].most_common(args.top)],
                ["role", "skill", "action", "calls", "ok", "fail", "last", "roles"],
                ["角色", "skill", "action", "调用", "通过", "失败", "最近", "角色数"]))

    if agg["unmapped"]:
        print(f"\n日志里出现但**无能力卡**的调用（{len(agg['unmapped'])} 组；"
              f"其中已在 observed_actions 备案 {declared_hit} 组，未备案 {len(drift)} 组）")
        print(table([{"role": k[0], "skill": k[1], "action": k[2], "calls": v}
                     for k, v in agg["unmapped"].most_common(15)],
                    ["role", "skill", "action", "calls"], ["角色", "skill", "action", "调用"]))

    # active 卡分级
    act = [r for r in rows if r["status"] == "active"]
    print(f"\n22 张 active 旧卡的升级优先级（按实测调用排序）")
    print(table(sorted(act, key=lambda r: (-r["calls"], r["id"])),
                ["priority", "id", "owner", "kind", "entry", "calls", "last"],
                ["优先级", "能力", "负责", "类型", "入口", "调用", "最近"]))
    tier = collections.Counter(r["priority"] for r in act)
    print("\n分级汇总：" + "｜".join(f"{k} {v} 张" for k, v in sorted(tier.items())))

    print("\n口径说明：")
    print("  · 只有 kind=skill 且有 entry 的能力可被观测；knowledge 卡天然零记录，不代表无价值。")
    print("  · 日志仅覆盖本机跑过的调用，不含线上真实流量。")
    print("  · 结论：优先升级 P1（有实测调用），P2 次之，P3 需先用真实业务问题验证是否值得。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
