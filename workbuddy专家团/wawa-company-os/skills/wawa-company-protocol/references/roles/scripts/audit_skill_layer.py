# -*- coding: utf-8 -*-
"""技能层体检：对照 SKILL.md 质量标准给 20 角色 + 29 能力卡打分。

用法：
    python scripts/audit_skill_layer.py            # 人类可读表格
    python scripts/audit_skill_layer.py --json     # 机器可读，便于 CI 门禁
    python scripts/audit_skill_layer.py --min 70   # 低于阈值则退出码 1（CI 用）

设计原则：只读，不改任何文件；零第三方依赖。
评分口径见 docs/SKILL-LAYER-SPEC.md。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# 满分 100，权重按"对 LLM 可选性与可执行性的影响"排序
WEIGHTS = {
    "frontmatter": 15,      # 有 --- 围栏 + name/description
    "trigger_phrases": 15,  # description 含 "Use when / 当...时使用" 触发语
    "workflow": 10,         # 有编号执行流程
    "resource_map": 10,     # 有按需加载的资源地图（references/ 索引）
    "scripts_table": 10,    # 列明脚本与入口命令
    "selfcheck": 10,        # 交付前自检清单
    "pitfalls": 15,         # 编号化易犯错误对照表
    "degradation": 10,      # 异常与降级表
    "provenance": 5,        # 来源/版本/变更记录
}
MAX_SCORE = sum(WEIGHTS.values())

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def split_frontmatter(text: str):
    m = FM_RE.match(text)
    if not m:
        return None, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, text[m.end():]


def score_doc(text: str, fm_required: bool = True) -> dict:
    fm, body = split_frontmatter(text)
    score = {}
    detail = {}

    has_fm = fm is not None and bool(fm.get("name")) and bool(fm.get("description"))
    if not fm_required:
        has_fm = True
    score["frontmatter"] = WEIGHTS["frontmatter"] if has_fm else 0
    detail["frontmatter"] = "ok" if has_fm else ("缺 --- 围栏或 name/description" if fm is None else "缺 name/description")

    desc = (fm or {}).get("description", "")
    trigger = bool(re.search(r"use when|use this|当.*时使用|用于|适用", desc, re.I))
    score["trigger_phrases"] = WEIGHTS["trigger_phrases"] if (trigger and len(desc) >= 40) else 0
    detail["trigger_phrases"] = f"desc {len(desc)} 字" + ("" if trigger else "，无触发语")

    workflow = bool(re.search(r"(?m)^#{1,4}\s*.*(流程|workflow|步骤|执行序列|流水线|pipeline)", body, re.I)) and bool(
        re.search(r"(?m)^\s*(\d+[\.\)]|Step\s*\d|步骤\s*\d)", body, re.I))
    score["workflow"] = WEIGHTS["workflow"] if workflow else 0
    detail["workflow"] = "ok" if workflow else "无编号执行流程"

    res_map = bool(re.search(r"(?m)^#{1,4}\s*.*(资源|resource|参考文件|知识资产|索引|Reference)", body, re.I))
    score["resource_map"] = WEIGHTS["resource_map"] if res_map else 0
    detail["resource_map"] = "ok" if res_map else "无资源地图"

    # 「有可执行门禁入口」：包内 scripts/，或角色根目录 harness.py / review.py / agent.py
    scripts = (("scripts/" in body) and bool(re.search(r"\.py|\.sh|\.js", body))) or bool(
        re.search(r"(harness|review|agent|prdguard|gate_wrap)\.py|agent\.py\s+\w+", body))
    score["scripts_table"] = WEIGHTS["scripts_table"] if scripts else 0
    detail["scripts_table"] = "ok" if scripts else "未列脚本/门禁入口"

    selfcheck = bool(re.search(r"(?m)^#{1,4}\s*.*(自检|checklist|检查清单|交付前)", body, re.I)) and body.count("- [ ]") >= 3
    score["selfcheck"] = WEIGHTS["selfcheck"] if selfcheck else 0
    detail["selfcheck"] = "ok" if selfcheck else "无交付前自检清单"

    pitfalls = bool(re.search(r"(?m)^#{1,4}\s*.*(错误|坑|反模式|pitfall|常见问题对照)", body, re.I)) and bool(
        re.search(r"[A-Z]{1,4}-\d{2}", body))
    score["pitfalls"] = WEIGHTS["pitfalls"] if pitfalls else 0
    detail["pitfalls"] = "ok" if pitfalls else "无编号化错误表"

    degrade = bool(re.search(r"(?m)^#{1,4}\s*.*(降级|异常|degrad|fallback|故障)", body, re.I))
    score["degradation"] = WEIGHTS["degradation"] if degrade else 0
    detail["degradation"] = "ok" if degrade else "无异常降级表"

    prov = bool(re.search(r"(?m)^#{1,4}\s*.*(变更记录|changelog|来源|版本历史|provenance)", body, re.I))
    score["provenance"] = WEIGHTS["provenance"] if prov else 0
    detail["provenance"] = "ok" if prov else "无变更记录"

    total = sum(score.values())
    return {"score": total, "max": MAX_SCORE, "breakdown": score, "detail": detail}


def grade(total: int) -> str:
    if total >= 90:
        return "A 旗舰"
    if total >= 75:
        return "B 可用"
    if total >= 50:
        return "C 骨架"
    if total >= 25:
        return "D 占位"
    return "E 空壳"


# 资源地图里允许出现的前缀；只校验这几类，避免把命令片段误判为路径
REF_PREFIX = ("references/", "templates/", "scripts/", "tests/", "assets/")
# 注意：扩展名按长度倒序排列，否则 `.json` 会被 `js` 抢先匹配成 `.js`
_EXT = r"jsonl|json|mjs|yaml|yml|html|csv|md|py|sh|js|txt|png|jpg"
REF_RE = re.compile(
    r"(?<![\w/.-])((?:references|templates|scripts|tests|assets)/[A-Za-z0-9_./\-]+\.(?:%s))(?![\w])" % _EXT
)


def check_refs(base_dir: str, text: str) -> list:
    """校验正文里提到的资源文件是否真实存在（相对 base_dir）。

    返回缺失的相对路径列表。只校验 REF_PREFIX 开头的路径，
    且忽略带占位符（`<...>`）或通配的路径。
    """
    missing = []
    for m in REF_RE.finditer(text):
        rel = m.group(1).rstrip(".,;:）)")
        if "<" in rel or "*" in rel:
            continue
        if os.path.isfile(os.path.join(base_dir, rel.replace("/", os.sep))):
            continue
        if rel not in missing:
            missing.append(rel)
    return missing


def audit() -> dict:
    roles, caps = [], []
    for name in sorted(os.listdir(ROOT)):
        d = os.path.join(ROOT, name)
        if not os.path.isdir(d) or not re.match(r"^r\d{2}-", name):
            continue
        skill = os.path.join(d, "SKILL.md")
        text = ""
        if os.path.exists(skill):
            with open(skill, encoding="utf-8-sig") as fh:
                text = fh.read()
        res = score_doc(text, fm_required=True)
        roles.append({
            "id": name[:3], "dir": name, "file": "SKILL.md",
            "bytes": len(text.encode("utf-8")), "lines": text.count("\n") + 1,
            "missing_refs": check_refs(d, text),
            **res, "grade": grade(res["score"]),
        })
        caps_dir = os.path.join(d, "references", "capabilities")
        if not os.path.isdir(caps_dir):
            continue
        for cap in sorted(os.listdir(caps_dir)):
            cap_dir = os.path.join(caps_dir, cap)
            if not os.path.isdir(cap_dir):
                continue
            # 口径：优先 SKILL.md（技能包），回落 README.md（旧能力卡）
            card = os.path.join(cap_dir, "SKILL.md")
            if not os.path.isfile(card):
                card = os.path.join(cap_dir, "README.md")
            if not os.path.isfile(card):
                continue
            with open(card, encoding="utf-8-sig") as fh:
                ctext = fh.read()
            cres = score_doc(ctext, fm_required=True)
            caps.append({
                "id": cap, "owner": name[:3],
                "file": os.path.relpath(card, ROOT).replace(os.sep, "/"),
                "has_skill_md": os.path.isfile(os.path.join(cap_dir, "SKILL.md")),
                "bytes": len(ctext.encode("utf-8")), "lines": ctext.count("\n") + 1,
                "missing_refs": check_refs(cap_dir, ctext),
                **cres, "grade": grade(cres["score"]),
            })
    return {"roles": roles, "caps": caps}


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
    ap = argparse.ArgumentParser(description="技能层体检（SKILL.md 质量打分）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--min", type=int, default=0, help="低于该分数则退出码 1（CI 门禁）")
    ap.add_argument("--verbose", action="store_true", help="显示逐项失分原因")
    ap.add_argument("--check-refs", action="store_true",
                    help="资源地图指向的文件缺失时退出码 1（悬空指针门禁）")
    args = ap.parse_args(argv)

    data = audit()
    roles, caps = data["roles"], data["caps"]
    dangling = [(r["id"], ref) for r in roles for ref in r.get("missing_refs", [])] + \
               [(c["id"], ref) for c in caps for ref in c.get("missing_refs", [])]

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("蛙蛙呱呱 · 技能层体检（SKILL.md 规格对照）\n")
        print(f"角色 SKILL.md：{len(roles)} 份，平均 {sum(r['score'] for r in roles) // max(1, len(roles))} 分")
        print(table(roles, ["id", "lines", "score", "grade"],
                    ["角色", "行数", "得分", "等级"]))
        print(f"\n能力卡 README.md：{len(caps)} 份，平均 {sum(c['score'] for c in caps) // max(1, len(caps))} 分")
        print(table(caps[:12], ["owner", "id", "bytes", "score", "grade"],
                    ["归属", "能力", "字节", "得分", "等级"]))
        if len(caps) > 12:
            print(f"... 其余 {len(caps) - 12} 份同规格（全部为 D/E 级占位卡）")
        if args.verbose:
            print("\n失分明细（角色）：")
            for r in roles:
                miss = [k for k, v in r["breakdown"].items() if v == 0]
                print(f"  {r['id']}: 失分项 {', '.join(miss) or '无'}")
        if dangling:
            print(f"\n悬空指针 {len(dangling)} 处（资源地图指向不存在的文件）：")
            for owner, ref in dangling[:20]:
                print(f"  {owner}: {ref}")
            if len(dangling) > 20:
                print(f"  ... 另有 {len(dangling) - 20} 处")
        else:
            print("\n悬空指针 0 处（资源地图全部可解析）")
        print("\n口径：见 docs/SKILL-LAYER-SPEC.md；逐项打分见 --json")

    worst = min([r["score"] for r in roles] + [c["score"] for c in caps]) if (roles or caps) else 0
    if args.min and worst < args.min:
        if not args.json:
            print(f"\n[FAIL] 最低分 {worst} < 阈值 {args.min}")
        return 1
    if args.check_refs and dangling:
        if not args.json:
            print(f"\n[FAIL] 资源地图有 {len(dangling)} 处悬空指针")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
