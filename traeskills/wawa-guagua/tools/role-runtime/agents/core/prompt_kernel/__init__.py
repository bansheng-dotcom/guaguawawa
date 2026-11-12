# -*- coding: utf-8 -*-
"""共享 L02 提示词编译内核（P1 试点版）。

职责：把模糊意图编译成可解释的 PromptPlan：
    intent -> spec -> 缺失字段 -> 澄清问题 / 动作路由 -> 提示词块

设计约束：
    1. 纯标准库，不依赖 LLM、不依赖 yaml；
    2. 角色差异全部放在各自的 prompt_profile.json；
    3. 置信度必须可复算，禁止常量；
    4. 未命中必须返回 needs_clarification，禁止静默落到默认动作。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_role_dir(role_id: str) -> str:
    """按 rXX- 前缀定位角色目录，避免硬编码 20 个目录名。"""
    for name in sorted(os.listdir(ROOT)):
        if name.startswith(role_id + "-") and os.path.isdir(os.path.join(ROOT, name)):
            return os.path.join(ROOT, name)
    raise FileNotFoundError(f"找不到角色目录: {role_id}")


def load_profile(role_id_or_dir: str) -> Dict[str, Any]:
    path = role_id_or_dir
    if not os.path.isdir(path):
        path = find_role_dir(role_id_or_dir)
    profile_path = os.path.join(path, "prompt_profile.json")
    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)
    profile.setdefault("_dir", os.path.basename(path))
    return profile


def _match_alias(text: str, aliases: List[str]) -> Optional[str]:
    low = text.lower()
    for alias in aliases:
        if alias == "*":
            continue
        if alias.lower() in low:
            return alias
    return None


def _extract_spec(text: str, profile: Dict[str, Any]):
    spec, evidence, topic_meta = {}, [], None
    for field, mapping in profile.get("lexicon", {}).items():
        for canonical, aliases in mapping.items():
            if "*" in aliases:
                clean, meta = refine_topic(text, profile)
                spec[field] = clean
                if field == "topic":
                    topic_meta = meta
                evidence.append({"field": field, "value": clean, "matched": "*"})
                break
            hit = _match_alias(text, aliases)
            if hit:
                spec[field] = canonical
                evidence.append({"field": field, "value": canonical, "matched": hit})
                break
        if field in spec:
            continue
        rule = profile.get("regex", {}).get(field)
        if rule:
            m = re.search(rule, text)
            if m:
                spec[field] = m.group(0)
                evidence.append({"field": field, "value": m.group(0), "matched": "regex"})
    return spec, evidence, topic_meta


# 主题抽取：去掉对话性前后缀、截断到可读长度，不做语义改写（无 NLP 依赖）。
TOPIC_PREFIX = (
    "帮我", "帮忙", "请你", "麻烦你", "麻烦", "请", "我想要", "我想", "我要", "想",
    "能不能", "可以", "能否", "麻烦帮我", "帮我看看", "看一下", "看看", "看下",
    "写一篇", "写一个", "写篇", "写个", "做一篇", "做一份", "做一版",
    "生成一篇", "生成一个", "出一篇", "关于", "针对",
)
TOPIC_SUFFIX = ("怎么样", "怎么", "如何", "一下吧", "一点", "一些",
                "一下", "呗", "吧", "吗", "呢", "啊", "呀")
TOPIC_TAIL_CHARS = "的了。，、！？；;,.!? \t\r\n"


def refine_topic(text: str, profile: Dict[str, Any]) -> tuple:
    """把整句意图收敛成短主题：去对话前缀/语气后缀 + 按标点断句 + 长度上限。"""
    cfg = profile.get("topic_extraction", {})
    max_chars = int(cfg.get("max_chars", 40))
    prefix = tuple(cfg.get("prefix", TOPIC_PREFIX))
    suffix = tuple(cfg.get("suffix", TOPIC_SUFFIX))

    raw = (text or "").strip()
    clean, removed = raw, []
    changed = True
    while changed:
        changed = False
        for s in prefix:
            if clean.startswith(s) and len(clean) > len(s) + 1:
                clean, changed = clean[len(s):].lstrip(), True
                removed.append("prefix:" + s)
        for s in suffix:
            if clean.endswith(s) and len(clean) > len(s) + 1:
                clean, changed = clean[: -len(s)].rstrip(), True
                removed.append("suffix:" + s)
        stripped = clean.rstrip(TOPIC_TAIL_CHARS)
        if stripped != clean and stripped:
            clean, changed = stripped, True

    clean = re.sub(r"\s+", " ", clean).strip()
    truncated = False
    if len(clean) > max_chars:
        cut = clean[:max_chars]
        idx = max(cut.rfind(ch) for ch in "，。；、,; ")
        if idx >= max_chars // 3:
            cut = cut[:idx]
        clean, truncated = cut.rstrip("，。；、,; "), True
    if not clean:
        clean = raw[:max_chars]
    return clean, {"raw": raw, "clean": clean, "truncated": truncated, "removed": removed}


def compile_intent(intent: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    text = (intent or "").strip()
    low = text.lower()
    spec, evidence, topic_meta = _extract_spec(text, profile)

    best, best_score, best_hits = None, 0, []
    for action in profile.get("actions", []):
        hits = [k for k in action.get("when", []) if k.lower() in low]
        if not hits:
            continue
        score = len(hits) * 10 + sum(3 for f in action.get("requires", []) if f in spec)
        if score > best_score:
            best, best_score, best_hits = action, score, hits

    assumptions: List[Dict[str, str]] = []
    if best:
        for field in best.get("requires", []):
            if field not in spec and field in profile.get("assumptions", {}):
                value = profile["assumptions"][field]
                spec[field] = value
                assumptions.append({
                    "field": field,
                    "value": value,
                    "reason": profile.get("assumption_reason", {}).get(field, "角色清单默认口径"),
                })

    questions: List[Dict[str, Any]] = []
    if best:
        for field in best.get("requires", []):
            if field not in spec:
                q = profile.get("questions", {}).get(field, {})
                questions.append({
                    "field": field,
                    "question": q.get("question", f"请补充 {field}"),
                    "options": q.get("options", []),
                })
    else:
        q = profile.get("questions", {}).get("action", {})
        questions.append({
            "field": "action",
            "question": q.get("question", "你想做什么？"),
            "options": q.get("options", []),
        })
    questions = questions[: int(profile.get("max_questions", 3))]

    needs_clarification = best is None or bool(questions)
    route = None
    if not needs_clarification:
        params = {}
        for arg, tpl in best.get("params", {}).items():
            params[arg] = spec.get(tpl[1:], "") if tpl.startswith("$") else tpl
        route = {
            "skill": best["skill"],
            "action": best["action"],
            "params": params,
            "label": best.get("label", ""),
        }

    required = best.get("requires", []) if best else []
    if required:
        confidence = round(sum(1 for f in required if f in spec) / len(required), 2)
    else:
        confidence = 1.0 if best else 0.0

    blocks = []
    if route:
        for block in best.get("prompt_blocks") or profile.get("l2_prompt_blocks", []):
            blocks.append({
                "name": block.get("name", ""),
                "text": block.get("template", "").format_map(_SafeDict(spec)),
            })

    if best is None:
        reason = "没有任何动作关键词命中，需要确认意图"
    elif questions:
        reason = "意图已识别为「%s」，但缺少必要字段：%s" % (
            best.get("label") or best.get("action"), "、".join(q["field"] for q in questions))
    else:
        reason = "字段齐备，可直接执行"

    return {
        "role": profile.get("role_id", ""),
        "domain": profile.get("domain", ""),
        "intent": text,
        "topic": spec.get("topic"),
        "topic_meta": topic_meta,
        "spec": spec,
        "matched_action": None if best is None else {
            "skill": best["skill"], "action": best["action"],
            "label": best.get("label", ""), "hits": best_hits,
        },
        "missing": [q["field"] for q in questions],
        "questions": questions,
        "assumptions": assumptions,
        "route": route,
        "prompt_blocks": blocks,
        "confidence": confidence,
        "needs_clarification": needs_clarification,
        "reason": reason,
        "evidence": evidence,
        "execution_inputs": profile.get("execution_inputs", {}),
        "output_contract": profile.get("output_contract", {}),
    }


class _SafeDict(dict):
    def __missing__(self, key):  # noqa: D105
        return ""


# --------------------------------------------------------------------------- #
# 角色接入辅助：18 个角色共用同一段接入代码，避免复制粘贴漂移。
# --------------------------------------------------------------------------- #
CLARIFY_SKILL = "__clarify__"


def fallback_route(role_id: str, intent: str):
    """旧关键词未命中时调用：返回与各角色 _route 一致的 (skill, action, defaults)。

    未命中即澄清；内核自身异常也必须显式暴露，禁止静默落到默认动作。
    """
    try:
        plan = compile_intent(intent, load_profile(role_id))
    except Exception as exc:  # noqa: BLE001
        return CLARIFY_SKILL, "clarify", {"error": str(exc), "questions": [],
                                          "assumptions": []}
    if plan["needs_clarification"]:
        return CLARIFY_SKILL, "clarify", {
            "plan": plan, "questions": plan["questions"], "assumptions": plan["assumptions"]}
    route = plan["route"]
    return route["skill"], route["action"], route["params"]


def add_clarify_parser(subparsers):
    """给角色 CLI 注册统一的 `clarify --intent` 子命令。"""
    parser = subparsers.add_parser("clarify", help="L02: 模糊意图编译（澄清/路由）")
    parser.add_argument("--intent", required=True)
    return parser


def clarify_cli(role_id: str, intent: str) -> int:
    """`clarify` 子命令实现：打印 PromptPlan JSON；无法路由时退出码 2。"""
    plan = compile_intent(intent, load_profile(role_id))
    print(json.dumps(plan, ensure_ascii=False))
    return 0 if plan["route"] else 2


def render_markdown(plan: Dict[str, Any]) -> str:
    """把 PromptPlan 渲染成人工可读的 prompt_plan 片段。"""
    lines = ["# Prompt Plan · %s" % plan.get("role", ""), "",
             "- 原始意图：%s" % plan.get("intent", "")]
    if plan.get("topic"):
        meta = plan.get("topic_meta") or {}
        note = "（已截断）" if meta.get("truncated") else ""
        lines.append("- 主题：%s%s" % (plan["topic"], note))
    lines += ["- 置信度：%s" % plan.get("confidence", 0),
              "- 结论：%s" % plan.get("reason", ""), ""]
    if plan.get("route"):
        r = plan["route"]
        lines += ["## 路由", "`%s.%s` %s" % (r["skill"], r["action"], json.dumps(r["params"], ensure_ascii=False)), ""]
    if plan.get("questions"):
        lines.append("## 待确认")
        for q in plan["questions"]:
            opts = " / ".join(str(o.get("label", o)) if isinstance(o, dict) else str(o)
                              for o in q.get("options", []))
            lines.append("- %s（%s）" % (q["question"], opts))
        lines.append("")
    if plan.get("assumptions"):
        lines.append("## 显式假设")
        for a in plan["assumptions"]:
            lines.append("- %s = %s（%s）" % (a["field"], a["value"], a["reason"]))
        lines.append("")
    if plan.get("prompt_blocks"):
        lines.append("## 提示词块")
        for b in plan["prompt_blocks"]:
            lines.append("### %s\n%s\n" % (b["name"], b["text"]))
    return "\n".join(lines)
