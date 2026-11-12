#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2.0 语义字段映射：给 374 个动作标注“执行前必须明确的语义字段”。

规则：
    1. 角色已有 prompt_profile.json 且动作在清单里 → 直接采用 requires（curated）；
    2. 不在路由清单里的动作，读取 profile.semantic_fields 的显式声明（declared）；
    3. 显式声明为空列表 = 明确判定无需业务口径（no_spec_needed）；
    4. 只有 profile 未声明时才退回启发式（heuristic），P3 后应恒为 0。

用法：
    python scripts/build_semantic_field_map.py
输出：
    docs/semantic_field_map.json
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "docs", "actions_catalog.json")
OUT = os.path.join(ROOT, "docs", "semantic_field_map.json")

TIERS = {
    "r01": "C", "r02": "C", "r03": "B", "r04": "C", "r05": "A",
    "r06": "B", "r07": "A", "r08": "A", "r09": "A", "r10": "A",
    "r11": "A", "r12": "A", "r13": "A", "r14": "B", "r15": "B",
    "r16": "B", "r17": "C", "r18": "B", "r19": "A", "r20": "B",
}

FIELDS = {
    "dataset": "数据来源（文件/表/任务卡端口）",
    "metric": "衡量指标（成交额/收入/转化率…）",
    "dimension": "拆分维度（渠道/城市/品类…）",
    "time_window": "时间窗（近7天/近30天/本季度…）",
    "comparison": "对比口径（同比/环比/对照组）",
    "stage": "漏斗或流程阶段字段",
    "topic": "主题或命题",
    "platform": "发布平台",
    "voice": "语气与人格",
    "audience": "目标受众",
    "objective": "本次编排要达成的目标",
    "scope": "范围与不做什么",
    "evidence": "评审所需证据来源",
    "artifact": "被评审的成品路径",
    "owner": "任务归属角色",
    "deadline": "交付时间",
    "output_contract": "产物格式与必含段落",
}

COMPUTE_RULES = [
    (("probe", "health", "manifest", "ping", "doctor", "smoke", "selftest",
      "self_test", "watchdog"), "no_spec_needed"),
    (("quality", "audit", "clean", "dedupe", "validate"), ["dataset", "output_contract"]),
    (("trend", "series", "forecast", "growth"), ["dataset", "metric", "time_window"]),
    (("groupby", "segment", "rank", "breakdown", "cohort"), ["dataset", "metric", "dimension"]),
    (("funnel", "conversion"), ["dataset", "stage", "time_window"]),
    (("rootcause", "drill", "attribut", "contrib"), ["dataset", "metric", "dimension", "time_window"]),
    (("abtest", "ttest", "chi2", "anova", "regress", "correlate"), ["dataset", "metric", "dimension"]),
]

GEN_RULES = [
    (("probe", "health", "manifest", "ping", "doctor", "smoke", "selftest",
      "self_test", "watchdog"), "no_spec_needed"),
    (("hook", "title", "headline", "angle"), ["topic", "platform", "output_contract"]),
    (("article", "copy", "script", "draft", "write"), ["topic", "voice", "output_contract"]),
    (("adapt", "localize", "translate", "rewrite"), ["topic", "platform", "output_contract"]),
    (("outline", "plan", "proposal"), ["topic", "output_contract"]),
]

ORCH_RULES = [
    (("probe", "health", "manifest", "ping", "doctor", "smoke", "selftest",
      "self_test", "watchdog"), "no_spec_needed"),
    (("review", "criteria", "critique", "gate", "verify"), ["artifact", "evidence", "output_contract"]),
    (("task", "decompose", "dispatch", "assign", "schedule"), ["objective", "owner", "deadline", "output_contract"]),
]


def _match(name: str, rules):
    low = name.lower()
    for keys, fields in rules:
        if any(k in low for k in keys):
            return fields
    return None


def heuristic(tier: str, skill: str, action: str):
    name = "%s %s" % (skill, action)
    if tier == "A":
        return _match(name, GEN_RULES) or ["topic", "output_contract"]
    if tier == "C":
        return _match(name, ORCH_RULES) or ["objective", "scope", "output_contract"]
    return _match(name, COMPUTE_RULES) or ["dataset", "output_contract"]


def main() -> int:
    catalog = json.load(open(CATALOG, encoding="utf-8"))
    roles_out, summary = [], {"actions": 0, "profile_defined": 0, "declared": 0,
                             "heuristic": 0, "no_spec_needed": 0}

    for role in catalog["roles"]:
        rid, tier = role["role"], TIERS.get(role["role"], "B")
        profile_path = os.path.join(ROOT, role["dir"], "prompt_profile.json")
        curated, declared = {}, {}
        if os.path.exists(profile_path):
            profile = json.load(open(profile_path, encoding="utf-8"))
            for act in profile.get("actions", []):
                curated[(act["skill"], act["action"])] = act.get("requires", [])
            declared = profile.get("semantic_fields", {})

        actions_out = []
        for skill in role["skills"]:
            for act in skill["actions"]:
                pair = (skill["name"], act["name"])
                key = "%s.%s" % pair
                if pair in curated:
                    fields, status, source = curated[pair], "profile", profile_path
                    summary["profile_defined"] += 1
                elif key in declared:
                    fields = declared[key]
                    source = profile_path
                    if fields:
                        status = "declared"
                        summary["declared"] += 1
                    else:
                        status = "no_spec_needed"
                        summary["no_spec_needed"] += 1
                else:
                    fields = heuristic(tier, skill["name"], act["name"])
                    source = "scripts/build_semantic_field_map.py"
                    if fields == "no_spec_needed":
                        fields, status = [], "no_spec_needed"
                        summary["no_spec_needed"] += 1
                    else:
                        status = "heuristic"
                        summary["heuristic"] += 1
                actions_out.append({
                    "skill": skill["name"], "action": act["name"],
                    "cli_required": act.get("required", []),
                    "semantic_required": fields, "status": status,
                    "source": os.path.relpath(source, ROOT).replace("\\", "/")
                    if os.path.isabs(source) else source,
                })
                summary["actions"] += 1
        roles_out.append({"role": rid, "tier": tier, "actions": actions_out})

    payload = {
        "generated_by": "scripts/build_semantic_field_map.py",
        "note": "profile=路由清单已定义；declared=profile.semantic_fields 显式声明；no_spec_needed=显式判定无需业务口径；heuristic=未声明时的兜底推断（P3 后应为 0）",
        "fields": FIELDS,
        "summary": summary,
        "roles": roles_out,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))
    print("written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
