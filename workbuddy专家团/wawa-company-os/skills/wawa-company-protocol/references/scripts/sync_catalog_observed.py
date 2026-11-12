# -*- coding: utf-8 -*-
"""一次性：修复「目录与实际调用脱节」（Track A）。

做三件事：
    1. 把调用量 ≥ 阈值且**目录未登记**的 (role, skill, action) 写进 catalog 的
       `observed_actions`（不是塞进 capabilities——它们还没有能力卡，
       混进去会让"能力数"虚增、均值失真）；
    2. 为每条观测记录给出 `suggested_pack`：该角色已有包里最可能吸收它的一张；
    3. 记录 `entry_mismatch`：已登记能力的 entry 与实际调用名不一致的情况。

只改 `shared/capabilities/catalog.json`，不动任何能力卡文件。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import capability_usage as cu  # noqa: E402

CATALOG = os.path.join(ROOT, "shared", "capabilities", "catalog.json")
THRESHOLD = 10  # 调用量 ≥ 10 才值得登记（低于此视为一次性试跑）


def main() -> int:
    events, bad = cu.read_events()
    with io.open(CATALOG, encoding="utf-8") as fh:
        data = json.load(fh)
    caps = data["capabilities"]
    index = cu.build_index(caps)
    agg = cu.aggregate(events, index, {c["id"]: c for c in caps})

    # 角色 → 该角色已有 skill 包（用于给建议）
    packs_by_role = {}
    for c in caps:
        if c.get("status") == "pack":
            packs_by_role.setdefault(c["owner"], []).append(c["id"])

    observed = []
    skipped = 0
    for (role, skill, action), n in agg["unmapped"].most_common():
        if n < THRESHOLD:
            skipped += 1
            continue
        suggested = packs_by_role.get(role, [])
        observed.append({
            "role": role,
            "skill": skill,
            "action": action,
            "calls": n,
            "ok": agg["pair_ok"][(role, skill, action)],
            "fail": agg["pair_fail"][(role, skill, action)],
            "last_seen": agg["pair_last"].get((role, skill, action), ""),
            "suggested_pack": suggested[0] if suggested else None,
            "note": "已在日志中观测到，但目录尚无对应能力卡；先登记以便后续按真实使用率排序",
        })

    # entry 名与实际调用名的错配（已登记但 action 名对不上）
    mismatch = []
    for c in caps:
        ent = c.get("entry") or {}
        sk = str(ent.get("skill") or "").strip()
        if not sk:
            continue
        role = str(c.get("owner") or "").lower()
        seen_actions = {a for (r, s, a) in agg["pairs"] if r == role and s == sk}
        declared = {str(x).strip() for x in (ent.get("actions") or [])}
        extra = sorted(seen_actions - declared)
        if extra:
            mismatch.append({"capability": c["id"], "role": role, "skill": sk,
                             "declared_actions": sorted(declared),
                             "observed_extra_actions": extra,
                             "note": "实际调用出现过未声明的 action；建议补进 entry.actions 或解释差异"})

    data["observed_actions"] = observed
    data["entry_mismatch"] = mismatch
    data["audit"] = {
        "generated_by": "scripts/capability_usage.py",
        "log_events": len(events),
        "bad_lines": bad,
        "threshold": THRESHOLD,
        "skipped_below_threshold": skipped,
        "observed_count": len(observed),
        "entry_mismatch_count": len(mismatch),
    }
    data["version"] = int(data.get("version", 0)) + 1

    with io.open(CATALOG, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"日志 {len(events)} 条｜坏行 {bad}｜阈值 {THRESHOLD}")
    print(f"登记 observed_actions: {len(observed)} 条（低于阈值跳过 {skipped} 条）")
    for o in observed:
        print("  %-4s %-14s %-12s calls=%-4d → 建议并入 %s"
              % (o["role"], o["skill"], o["action"], o["calls"], o["suggested_pack"] or "（无）"))
    print(f"entry 错配: {len(mismatch)} 条")
    for m in mismatch:
        print("  %-24s %s 未声明 action: %s" % (m["capability"], m["skill"], m["observed_extra_actions"]))
    print("catalog version =", data["version"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
