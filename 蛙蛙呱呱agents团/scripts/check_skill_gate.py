#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能层 CI 门禁：升级门槛 + 黄金快照回归。

解决两个不同的问题：
    1. **新升级必须达标** —— 任何存在 SKILL.md 的能力包，得分必须 ≥ 75（旗舰 ≥ 90）。
    2. **已达标不许退化** —— 与快照对比，任何已登记对象的分数下降即失败。
       （没有这一条，改一次技能就会悄悄降一次质量，且没人发现。）

用法：
    python scripts/check_skill_gate.py                    # 检查（CI 用）
    python scripts/check_skill_gate.py --update           # 重写快照（人工确认后）
    python scripts/check_skill_gate.py --snapshot x.json  # 指定快照路径
    python scripts/check_skill_gate.py --json             # 机器可读结果

退出码：
    0  通过
    1  有违规（新包不达标 / 已登记对象退化 / 快照缺失）
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AUDIT = os.path.join(HERE, "audit_skill_layer.py")
DEFAULT_SNAPSHOT = os.path.join(HERE, "skill_score_snapshot.json")

# 门槛口径（分三类，避免"一次性让 20 个角色卡全部达标"这种不可能任务）：
#   1. 能力技能包（references/capabilities/<id>/SKILL.md）→ 必须达标，默认 75
#   2. 角色技能卡（<role>/SKILL.md）→ 默认不做分数要求（尚有 13 份无 frontmatter），
#      但一旦 `--role-bar` 设了值就按该值要求；无论哪种都受快照回归约束
#   3. 未升级的旧能力卡（只有 README.md）→ 不设分数地板，只受快照回归约束
BAR_PACK = 75
ROLE_BAR = 0


def load_audit() -> dict:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, AUDIT, "--json"],
        cwd=ROOT, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode not in (0, 1):
        raise SystemExit(f"[gate] 体检脚本异常: {proc.stderr[:400]}")
    return json.loads(proc.stdout)


def collect(data: dict) -> dict:
    """展开成 {key: {...}}，key 形如 `role:r01` / `cap:decision-gate`。

    `has_pack` 表示"这是一个已升级的能力技能包"；
    角色卡只是 `is_role`，默认不纳入分数门槛（见文件头门槛口径）。
    """
    out = {}
    for r in data["roles"]:
        out[f"role:{r['id']}"] = {
            "score": r["score"], "has_pack": False, "is_role": True,
            "kind": "role", "lines": r["lines"],
            "missing_refs": r.get("missing_refs", []),
        }
    for c in data["caps"]:
        out[f"cap:{c['id']}"] = {
            "score": c["score"], "has_pack": bool(c.get("has_skill_md")),
            "is_role": False, "kind": c.get("kind", ""), "lines": c["lines"],
            "missing_refs": c.get("missing_refs", []),
        }
    return out


def check(current: dict, snapshot: dict, bar_pack: int = BAR_PACK, role_bar: int = ROLE_BAR) -> list:
    """返回违规列表 [(key, 类型, 说明)]。"""
    bad = []
    for key, cur in sorted(current.items()):
        # 1) 已升级的能力技能包必须达标
        if cur["has_pack"] and cur["score"] < bar_pack:
            bad.append((key, "BELOW_BAR",
                        f"已升级技能包得分 {cur['score']} < 门槛 {bar_pack}"))
        # 2) 角色卡：仅当显式设了 role_bar 时才要求
        if cur["is_role"] and role_bar and cur["score"] < role_bar:
            bad.append((key, "BELOW_BAR",
                        f"角色卡得分 {cur['score']} < 门槛 {role_bar}"))
        # 3) 悬空指针：已升级对象零容忍
        if cur["has_pack"] and cur["missing_refs"]:
            bad.append((key, "DANGLING",
                        f"资源地图悬空 {len(cur['missing_refs'])} 处：{', '.join(cur['missing_refs'][:3])}"))
        # 4) 黄金快照回归（对所有已登记对象生效）
        prev = snapshot.get(key)
        if prev is None:
            continue
        if cur["score"] < prev["score"]:
            bad.append((key, "REGRESSION",
                        f"得分从 {prev['score']} 降到 {cur['score']}（少了 {prev['score'] - cur['score']}）"))
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="技能层 CI 门禁（升级门槛 + 黄金快照）")
    ap.add_argument("--update", action="store_true", help="用当前得分重写快照")
    ap.add_argument("--snapshot", default=DEFAULT_SNAPSHOT, help="快照文件路径")
    ap.add_argument("--json", action="store_true", help="输出机器可读结果")
    ap.add_argument("--bar", type=int, default=BAR_PACK, help=f"已升级技能包的门槛分（默认 {BAR_PACK}）")
    ap.add_argument("--role-bar", type=int, default=0,
                    help="角色技能卡门槛分（默认 0=不要求；建议在角色卡批量升级后再设为 75）")
    args = ap.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    bar_pack = args.bar
    role_bar = args.role_bar

    cur = collect(load_audit())
    packs = {k: v for k, v in cur.items() if v["has_pack"]}

    if args.update:
        payload = {
            "_note": "技能层得分黄金快照。由 scripts/check_skill_gate.py --update 生成；CI 对比此文件检测退化。",
            "_generated_by": "scripts/check_skill_gate.py",
            "scores": {k: {"score": v["score"], "kind": v["kind"]} for k, v in sorted(cur.items())},
        }
        with open(args.snapshot, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print(f"[gate] 快照已更新：{os.path.relpath(args.snapshot, ROOT)}（{len(cur)} 个对象）")
        return 0

    if not os.path.isfile(args.snapshot):
        msg = (f"[gate] 找不到快照 {args.snapshot}；首次使用请先执行 "
               f"`python scripts/check_skill_gate.py --update` 建立基线")
        print(msg, file=sys.stderr)
        return 1
    with open(args.snapshot, encoding="utf-8") as fh:
        snapshot = json.load(fh).get("scores", {})

    bad = check(cur, snapshot, bar_pack=bar_pack, role_bar=role_bar)

    if args.json:
        print(json.dumps({
            "ok": not bad, "violations": [{"key": k, "type": t, "detail": d} for k, t, d in bad],
            "counts": {"total": len(cur), "packs": len(packs),
                       "snapshot": len(snapshot), "violations": len(bad)},
        }, ensure_ascii=False, indent=2))
    else:
        print("蛙蛙呱呱 · 技能层 CI 门禁")
        print("=" * 64)
        print(f"对象 {len(cur)} 个｜已升级技能包 {len(packs)} 个｜快照 {len(snapshot)} 条")
        print(f"门槛：技能包 ≥ {bar_pack}｜角色卡 "
              + (f"≥ {role_bar}" if role_bar else "不设分（待批量升级后启用 --role-bar 75）"))
        if bad:
            print(f"\n违规 {len(bad)} 条：")
            for key, typ, detail in bad:
                print(f"  [{typ:<10}] {key:<28} {detail}")
        else:
            print("\n无违规：已升级包全部达标且无悬空指针，已登记对象无退化。")
            if packs:
                print("\n旗舰包：")
                for score, key in sorted(((v["score"], k) for k, v in packs.items()), reverse=True):
                    print(f"  {score:>3}  {key}")

    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
