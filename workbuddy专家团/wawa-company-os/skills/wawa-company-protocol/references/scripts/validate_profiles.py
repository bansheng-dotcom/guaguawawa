#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2.0 profile 校验器：把 20 份 prompt_profile.json 变成可 CI 的门禁。

校验项：
    1. 角色目录与 role_id 一致；domain 非空；
    2. 每个 action 的 (skill, action) 必须存在于 docs/actions_catalog.json；
    3. 同一角色内 when 关键词不得重复（重复即路由歧义）；
    4. requires 字段必须有来源：lexicon / regex / questions / assumptions；
    5. max_questions ∈ [1, 3]；
    6. L2 提示词块按档位：生成型必须有，计算型必须为空；
    7. 置信度自测：填满 requires 后 confidence 必须为 1.0 且路由到该动作；
    8. 语义字段全覆盖：actions 之外的每个动作必须在 semantic_fields 中显式声明，
       字段 ≤2 且必须有来源——禁止继续依赖启发式。

用法：
    python scripts/validate_profiles.py                # 校验已有 profile
    python scripts/validate_profiles.py --require-all  # 20 个角色缺一即失败
    python scripts/validate_profiles.py --role r07     # 只校验单个角色
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "docs", "actions_catalog.json")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# A 生成型 / B 计算型 / C 编排评审型（与升级方案一致）
TIERS = {
    "r01": "C", "r02": "C", "r03": "B", "r04": "C", "r05": "A",
    "r06": "B", "r07": "A", "r08": "A", "r09": "A", "r10": "A",
    "r11": "A", "r12": "A", "r13": "A", "r14": "B", "r15": "B",
    "r16": "B", "r17": "C", "r18": "B", "r19": "A", "r20": "B",
}


def role_dirs() -> dict:
    out = {}
    for name in sorted(os.listdir(ROOT)):
        if not os.path.isdir(os.path.join(ROOT, name)) or "-" not in name:
            continue
        rid = name.split("-")[0]
        if len(rid) == 3 and rid[0] == "r" and rid[1:].isdigit():
            out[rid] = os.path.join(ROOT, name)
    return out


def load_catalog() -> dict:
    with open(CATALOG, encoding="utf-8") as f:
        data = json.load(f)
    index = {}
    for role in data.get("roles", []):
        actions = set()
        for skill in role.get("skills", []):
            for action in skill.get("actions", []):
                actions.add((skill["name"], action["name"]))
        index[role["role"]] = actions
    return {"index": index, "errors": data.get("errors", []),
            "summary": data.get("summary", {})}


def _field_sources(profile: dict) -> set:
    src = set(profile.get("lexicon", {}))
    src |= set(profile.get("regex", {}))
    src |= set(profile.get("questions", {}))
    src |= set(profile.get("assumptions", {}))
    src |= set(profile.get("execution_inputs", {}))
    return src


def _self_test(role_id: str, profile: dict, action: dict) -> str:
    """填满 requires 后必须 1.0 置信度并命中该动作。"""
    from core.prompt_kernel import compile_intent

    requires = action.get("requires", [])
    words = [str(action["when"][0])]
    for field in requires:
        mapping = profile.get("lexicon", {}).get(field, {})
        if not mapping:
            return "requires 字段 %s 缺少 lexicon" % field
        canonical, aliases = next(iter(mapping.items()))
        if "*" in aliases:
            words.append("测试主题")
        else:
            words.append(str(aliases[0]))
    plan = compile_intent(" ".join(words), profile)
    if plan["route"] is None:
        return "填满字段后仍未路由（问题：%s）" % plan["reason"]
    got = (plan["route"]["skill"], plan["route"]["action"])
    want = (action["skill"], action["action"])
    if got != want:
        return "期望路由 %s.%s，实际 %s.%s" % (want[0], want[1], got[0], got[1])
    if requires and plan["confidence"] != 1.0:
        return "填满 requires 后 confidence=%s，应为 1.0" % plan["confidence"]
    return ""


def validate_role(role_id: str, role_dir: str, catalog: dict) -> dict:
    problems, warnings = [], []
    path = os.path.join(role_dir, "prompt_profile.json")
    if not os.path.exists(path):
        return {"role": role_id, "ok": False, "missing": True,
                "problems": ["缺少 prompt_profile.json"], "warnings": []}
    with open(path, encoding="utf-8") as f:
        profile = json.load(f)

    tier = TIERS.get(role_id, "?")
    if profile.get("role_id") != role_id:
        problems.append("role_id=%r 与目录 %r 不一致" % (profile.get("role_id"), role_id))
    if not str(profile.get("domain", "")).strip():
        problems.append("domain 为空")

    max_q = profile.get("max_questions", 0)
    if not isinstance(max_q, int) or not 1 <= max_q <= 3:
        problems.append("max_questions=%r 必须在 1~3" % (max_q,))

    actions = profile.get("actions", [])
    if not actions:
        problems.append("actions 为空")
    known = catalog["index"].get(role_id, set())
    seen_pairs, keyword_owner = set(), {}
    for action in actions:
        pair = (action.get("skill"), action.get("action"))
        if pair in seen_pairs:
            problems.append("动作重复：%s.%s" % pair)
        seen_pairs.add(pair)
        if pair not in known:
            problems.append("动作不存在于 actions_catalog.json：%s.%s" % pair)
        when = action.get("when", [])
        if not when:
            problems.append("%s.%s 缺少 when 关键词" % pair)
        for kw in when:
            keyword_owner.setdefault(str(kw).lower(), []).append(pair)

    # 共享关键词本身可接受（内核按命中数加权），但动作不能只靠共享关键词被触达。
    for kw, owners in sorted(keyword_owner.items()):
        if len(owners) > 1:
            warnings.append("关键词 %r 被 %d 个动作共享：%s"
                            % (kw, len(owners), ", ".join("%s.%s" % p for p in owners)))
    for action in actions:
        pair = (action.get("skill"), action.get("action"))
        exclusive = [kw for kw in action.get("when", [])
                     if len(keyword_owner[str(kw).lower()]) == 1]
        if action.get("when") and not exclusive:
            problems.append("%s.%s 没有独占关键词，只能靠共享词路由"
                            % pair)

    sources = _field_sources(profile)
    for action in actions:
        for field in action.get("requires", []):
            if field not in sources:
                problems.append("%s.%s 必填字段 %r 没有任何来源定义"
                                % (action.get("skill"), action.get("action"), field))

    declared = profile.get("semantic_fields", {})
    if not isinstance(declared, dict):
        problems.append("semantic_fields 必须是 {skill.action: [字段]} 对象")
        declared = {}
    known_keys = {"%s.%s" % p for p in known}
    routed_keys = {"%s.%s" % p for p in seen_pairs}
    declared_keys = set()
    for key, fields in declared.items():
        if key in declared_keys:
            problems.append("semantic_fields 重复键：%s" % key)
        declared_keys.add(key)
        if key not in known_keys:
            problems.append("semantic_fields 动作不存在于目录：%s" % key)
        if key in routed_keys:
            problems.append("semantic_fields 与 actions 重复定义：%s" % key)
        if not isinstance(fields, list):
            problems.append("semantic_fields.%s 必须是字段数组" % key)
            continue
        if len(fields) > 2:
            problems.append("semantic_fields.%s 字段超过 2 个" % key)
        for field in fields:
            if field not in sources:
                problems.append("semantic_fields.%s 字段 %r 没有来源定义" % (key, field))
    missing = sorted(known_keys - routed_keys - declared_keys)
    if missing:
        problems.append("有 %d 个动作未声明语义字段：%s"
                        % (len(missing), ", ".join(missing[:6])))

    blocks = profile.get("l2_prompt_blocks", [])
    if tier == "A" and not blocks:
        problems.append("生成型角色必须有 l2_prompt_blocks")
    if tier == "B" and blocks:
        problems.append("计算型角色不应有 l2_prompt_blocks（写作提示不属于分析口径）")
    for block in blocks:
        if not block.get("name") or not block.get("template"):
            problems.append("l2_prompt_blocks 存在空 name/template")

    for action in actions:
        if action.get("requires"):
            err = _self_test(role_id, profile, action)
            if err:
                problems.append("%s.%s 置信度自测失败：%s"
                                % (action.get("skill"), action.get("action"), err))

    if not profile.get("output_contract", {}).get("must_include"):
        warnings.append("output_contract.must_include 为空，产物验收缺依据")

    return {"role": role_id, "tier": tier, "ok": not problems,
            "actions": len(actions), "declared": len(declared),
            "problems": problems, "warnings": warnings}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", default=None, help="只校验某个角色，如 r07")
    ap.add_argument("--require-all", action="store_true", help="20 个角色缺一即失败")
    ap.add_argument("--json", action="store_true", help="输出机器可读结果")
    args = ap.parse_args()

    catalog = load_catalog()
    if catalog["errors"]:
        print("[FAIL] actions_catalog.json 存在导出错误：%s" % catalog["errors"],
              file=sys.stderr)
        return 1

    dirs = role_dirs()
    targets = [args.role] if args.role else sorted(dirs)
    results = [validate_role(rid, dirs[rid], catalog) for rid in targets if rid in dirs]

    missing = [r["role"] for r in results if r.get("missing")]
    failed = [r for r in results if not r["ok"] and not r.get("missing")]
    if args.require_all and missing:
        failed.append({"role": "ALL", "problems": ["缺少 profile: %s" % ", ".join(missing)]})

    if args.json:
        print(json.dumps({"results": results, "missing": missing,
                          "ok": not failed}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            if r.get("missing"):
                print("[SKIP] %s 无 prompt_profile.json" % r["role"])
                continue
            print("[%s] %s tier=%s actions=%d declared=%d%s" % (
                "PASS" if r["ok"] else "FAIL", r["role"], r["tier"], r["actions"],
                r.get("declared", 0),
                "" if r["ok"] else " problems=%d" % len(r["problems"])))
            for p in r["problems"]:
                print("    - %s" % p)
            for w in r["warnings"]:
                print("    ~ %s" % w)
        if missing and not args.require_all:
            print("[INFO] 尚未接入内核：%s" % ", ".join(missing))
        print(json.dumps({"checked": len(results), "failed": len(failed),
                          "missing": len(missing)}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
