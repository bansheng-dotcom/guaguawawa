# -*- coding: utf-8 -*-
"""S11 小红书发布包（xhs-content-skills / rednote-post 的确定性落地）。

把「内容评分卡」「合规审查官」「笔记构成规则」从提示词规范变成可执行门禁：
  note       校验一篇小红书笔记（标题 / 正文 / 标签 / CTA / 封面文案 / AI 标注）
  score      8 项质量快检（≥7 项通过才可发）+ CES 参考区间 + 关键词覆盖 + 发布时间
  compliance CTA 黑名单、四类诱导互动、绝对化用语、收入数字、联系方式、AI 标注

规则出处（已拷入本角色 references/external/）：
  xhs-content-scorer / xhs-compliance-check / xhs-title-analyzer / rednote-post
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import _common as c

NAME = "xhs"
DESC = "小红书发布包：note/score/compliance"

TITLE_MAX = 20          # 标题 ≤20 字（emoji 计 1 字）
BODY_MIN, BODY_MAX = 550, 650
TAGS_MIN, TAGS_MAX = 3, 8

FORMAT_CES = {
    "story": ("案例故事", "30-60"),
    "pain_solution": ("痛点+方法", "15-35"),
    "opinion": ("互动观点", "10-20"),
    "list": ("清单/教程（上游判定为低效格式）", "5-12"),
    "overview": ("行业概览（上游判定为最低效）", "5-6"),
}

CTA_BLACKLIST = {
    "免费利益": ["免费", "白嫖", "0元", "不花钱", "送你", "送你一份"],
    "利益交换": ["帮你免费", "评论送", "评论抽", "评论领", "扣1领取", "私信送"],
    "惊喜悬念": ["有惊喜", "解锁", "彩蛋", "秘密", "隐藏福利", "不看后悔"],
    "玄学诱导": ["接好运", "去霉运", "祈福", "许愿", "保佑", "转发有好运"],
    "指令互动": ["评论区发", "评论区扣", "评论区告诉我", "私信我"],
    "利益承诺": ["帮你诊断", "帮你分析账号", "帮你免费看", "帮你评估", "帮你优化", "帮你做"],
}

SAFE_CTA = ("你怎么看", "评论区聊聊", "你有什么经验", "一起交流", "收藏备用",
            "欢迎在评论区分享", "这个问题你怎么解决", "哪个方法更适合你")

# 绝对化用语按"短语"匹配，避免把「最后」「最近」误判为违规
ABSOLUTE_PHRASES = ["最便宜", "最好用", "最强", "最低价", "全网第一", "第一名", "绝对", "100%",
                    "保证有效", "保证瘦", "保证赚", "唯一", "顶级", "国家级", "永久"]

CONTACT_RE = re.compile(r"(微信|vx|VX|Vx|二维码|加我|私信我|https?://|www\.|\.com\b)")
INCOME_RE = re.compile(r"((月|日|年)入\s*\d+|\d+\s*万\s*(收入|利润|GMV)|赚\s*\d+\s*万|暴富|躺赚)")
NUM_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?\s*(%|％|元|块|个|天|周|月|年|万|单|人|次|倍|小时)")
TIME_WORD_RE = re.compile(r"(今天|昨天|上周|上个月|三个月|半年|去年|今年|第一天|当时|\d+\s*(天|周|月|年)前)")


def _ck(ok: bool, msg: str, dim: str = "", warn: bool = False) -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim,
            "sev": "OK" if ok else ("WARN" if warn else "BLOCKER")}


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    for name, hlp in (("note", "校验笔记四要素"), ("score", "8 项质量快检 + CES/关键词"),
                      ("compliance", "发布前合规扫描")):
        a = act.add_parser(name, help=hlp)
        a.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "note":
        return _note(data)
    if args.action == "score":
        return _score(data)
    if args.action == "compliance":
        return _compliance(data)
    return {"error": f"未知动作: {args.action}"}


# --------------------------------------------------------------------------- #
def _text(data: Dict[str, Any]) -> str:
    return "\n".join(str(data.get(k, "")) for k in ("title", "body", "cta", "cover_text"))


def _note(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    checks: List[Dict[str, Any]] = []
    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()
    tags = data.get("tags") or []
    kws = [str(k) for k in (data.get("core_keywords") or []) if str(k).strip()]
    cta = str(data.get("cta", "")).strip()

    checks.append(_ck(0 < len(title) <= TITLE_MAX,
                      f"标题 1–{TITLE_MAX} 字（实际 {len(title)}）", "xhs.title.length"))
    head = title[:10]
    checks.append(_ck(bool(kws) and any(k in head for k in kws),
                      f"前 10 字含核心词（核心词 {kws or '未提供'}）", "xhs.title.keyword"))
    checks.append(_ck(BODY_MIN <= len(body) <= BODY_MAX,
                      f"正文 {BODY_MIN}–{BODY_MAX} 字（实际 {len(body)}）", "xhs.body.length"))
    checks.append(_ck(isinstance(tags, list) and TAGS_MIN <= len(tags) <= TAGS_MAX,
                      f"标签 {TAGS_MIN}–{TAGS_MAX} 个（实际 {len(tags) if isinstance(tags, list) else 0}）",
                      "xhs.tags.count"))
    text_all = title + body
    closed = sum(1 for t in (tags or [])
                 if str(t) in text_all or any(k in str(t) for k in kws))
    checks.append(_ck(closed >= 2, f"埋词闭环：≥2 个标签复用核心词（实际 {closed}）",
                      "xhs.tags.loop"))
    checks.append(_ck(bool(cta), "CTA 非空", "xhs.cta"))
    n = _check_cta(cta)
    checks.append(_ck(n["ok"], n["msg"], "xhs.cta.blacklist"))
    if data.get("ai_assisted"):
        checks.append(_ck("#AI辅助创作" in (title + body + " ".join(map(str, tags))),
                          "AI 辅助内容需带 #AI辅助创作", "xhs.ai_tag"))
    return c.result(checks, title_len=len(title), body_len=len(body),
                    tag_count=len(tags) if isinstance(tags, list) else 0,
                    next="四要素齐全，可进 score 快检")


def _check_cta(cta: str) -> Dict[str, Any]:
    hits = [w for words in CTA_BLACKLIST.values() for w in words if w in cta]
    if re.search(r"帮你(看|诊断|分析|评估|优化|做)", cta):
        hits.append("帮你+服务动词（致命模式）")
    if hits:
        return {"ok": False, "msg": f"CTA 命中黑名单：{hits[:4]}"}
    return {"ok": True, "msg": "CTA 未命中黑名单"}


def _score(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    title = str(data.get("title", ""))
    body = str(data.get("body", ""))
    cta = str(data.get("cta", ""))
    tags = [str(t) for t in (data.get("tags") or [])]
    kws = [str(k) for k in (data.get("core_keywords") or []) if str(k).strip()]
    fmt = str(data.get("format_type", "")).strip()
    text = _text(data)
    head40 = body[:40]

    items = [
        ("前 40 字是具体场景（时间+人物+困境）",
         bool(TIME_WORD_RE.search(head40)) and "我" in head40),
        ("第一人称叙事", "我" in body),
        ("有出乎意料的数据或踩坑", bool(NUM_TOKEN_RE.search(body)) and
         bool(re.search(r"(没想到|反过来|结果|踩坑|坑|意外|居然)", body))),
        (f"全文 {BODY_MIN}–{BODY_MAX} 字", BODY_MIN <= len(body) <= BODY_MAX),
        ("≥3 个硬信息点（带数字）", len(NUM_TOKEN_RE.findall(body)) >= 3),
        ("段落可拆解（≥3 段且每段≥30 字）",
         len([p for p in re.split(r"\n\s*\n", body) if len(p.strip()) >= 30]) >= 3),
        ("CTA 是二选一提问", ("?" in cta or "？" in cta) and bool(re.search(r"(还是|哪个|A 还是 B)", cta))),
        ("去掉 CTA 后正文仍≥400 字", len(body) >= 400),
    ]
    passed = [name for name, ok in items if ok]
    checks = [_ck(ok, ("✓ " if ok else "✗ ") + name, f"xhs.check.{i}")
              for i, (name, ok) in enumerate(items)]

    checks.append(_ck(fmt in FORMAT_CES, f"format_type ∈ {list(FORMAT_CES)}（实际 {fmt or '空'}）",
                      "xhs.format"))
    checks.append(_ck(len(passed) >= 7, f"质量快检 ≥7 项通过（实际 {len(passed)}/8）",
                      "xhs.gate"))

    # 关键词覆盖（上游：小红书 ≥3 为品牌词建议，核心业务词 ≥2 为硬要求）
    keyword_counts = {"小红书": text.count("小红书")}
    for k in kws:
        keyword_counts[k] = text.count(k)
    checks.append(_ck(keyword_counts["小红书"] >= 3,
                      f"品牌词「小红书」≥3 次（实际 {keyword_counts['小红书']}）",
                      "xhs.keywords.brand", warn=True))
    kw_ok = (not kws) or all(text.count(k) >= 2 for k in kws)
    checks.append(_ck(kw_ok, f"核心业务词每个 ≥2 次（{keyword_counts}）", "xhs.keywords.core"))

    publish = _publish_hint(data.get("publish_at"))
    checks.append(_ck(publish["ok"], publish["msg"], "xhs.publish_time"))

    fmt_name, ces = FORMAT_CES.get(fmt, ("未指定", "—"))
    total_ok = all(x["ok"] for x in checks if x["sev"] != "WARN")
    return c.result(checks, ok=total_ok, verdict="PASS" if total_ok else "FAIL",
                    format=fmt_name, ces_reference=ces,
                    passed=len(passed), total=8,
                    keyword_counts=keyword_counts,
                    publish_time=publish["best"],
                    next="可发布；发布后按 CES 复盘" if total_ok else "按未通过项修补后再发")


def _publish_hint(value: Any) -> Dict[str, Any]:
    best = "周四 20:00（上游数据最佳）"
    if not value:
        return {"ok": True, "best": best, "msg": f"建议发布时间：{best}"}
    text = str(value)
    if re.match(r"^周一", text) or "星期一" in text:
        return {"ok": False, "best": best, "msg": "周一发布划走率高，建议改到周四 20:00"}
    return {"ok": True, "best": best, "msg": f"发布时间 {text} 可接受（最佳为{best}）"}


def _compliance(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")], verdict="FAIL")
    text = _text(data)
    checks: List[Dict[str, Any]] = []

    hits = [w for words in CTA_BLACKLIST.values() for w in words if w in text]
    checks.append(_ck(not hits, f"CTA 黑名单 0 命中（命中 {hits[:5] or '无'}）", "xhs.cta.blacklist"))
    checks.append(_ck(not re.search(r"帮你(看|诊断|分析|评估|优化|做)", text),
                      "无「帮你+服务动词」致命模式", "xhs.cta.assist"))
    checks.append(_ck(not [p for p in ABSOLUTE_PHRASES if p in text],
                      f"绝对化用语 0 命中（命中 {[p for p in ABSOLUTE_PHRASES if p in text] or '无'}）",
                      "xhs.absolute"))
    checks.append(_ck(not INCOME_RE.search(text),
                      f"收入/暴富表述 0 命中（命中 {INCOME_RE.findall(text)[:2] or '无'}）", "xhs.income"))
    checks.append(_ck(not CONTACT_RE.search(text),
                      f"无微信/二维码/外链（命中 {CONTACT_RE.findall(text)[:2] or '无'}）", "xhs.contact"))
    if data.get("ai_assisted"):
        checks.append(_ck("#AI辅助创作" in text, "AI 辅助内容已带 #AI辅助创作", "xhs.ai_tag"))
    return c.result(checks, verdict="PASS" if all(x["ok"] for x in checks) else "FAIL",
                    next="合规通过，可进入发布" if all(x["ok"] for x in checks)
                    else "命中红线：替换后重扫")
