# -*- coding: utf-8 -*-
"""S05 客户反馈与 VOC —— 能力域 5。

整合自 formbricks__formbricks：`Survey`（type link/app、status draft/inProgress/
paused/completed）、`Response`（finished/data/contact）、`TSurveyElementTypeEnum`
（openText/nps/rating/csat/ces/matrix/ranking 等 17 种题型）。把「问卷与 VOC」
转成确定性实算：问卷要素齐全、题型白名单、NPS 三桶实算（推荐者-贬损者）、
响应率门槛、开放文本主题提炼（≥3 次提及才成主题）。

NPS 口径（真源）：NPS = (promoter% − detractor%)×100，promoter ≥9、detractor ≤6
（0-10 分制），这是 formbricks NPS 题型的标准三桶切分，非本角色自创。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from . import _common as c

NAME = "voc"
DESC = "客户反馈与 VOC：survey/voc"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("survey", help="校验问卷结构与题型")
    a.add_argument("--input", required=True)
    b = act.add_parser("voc", help="校验 VOC 数据与 NPS 实算")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "survey":
        return _validate_survey(data)
    if args.action == "voc":
        return _validate_voc(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


# --------------------------------------------------------------------------- #
def _validate_survey(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    vth = c.load_thresholds()["voc"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", element_count=0)

    ok_type = data.get("type") in vth["survey_types"]
    checks.append(_ck(ok_type, f"问卷类型={data.get('type')!r} 在白名单", "survey.type"))

    ok_status = data.get("status") in vth["survey_status"]
    checks.append(_ck(ok_status, f"问卷状态={data.get('status')!r} 在白名单", "survey.status"))

    ok_name = bool(str(data.get("name", "")).strip())
    checks.append(_ck(ok_name, "问卷名称非空", "survey.name"))

    questions = data.get("questions")
    ok_q = isinstance(questions, list) and len(questions) > 0
    checks.append(_ck(ok_q,
                      f"题目 ≥1（实际 {len(questions) if isinstance(questions, list) else 0}）",
                      "survey.questions"))
    bad_type: List[Any] = []
    bad_title: List[int] = []
    if isinstance(questions, list):
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                bad_type.append(i)
                continue
            if q.get("type") not in vth["element_types"]:
                bad_type.append(q.get("type"))
            if not str(q.get("title", "")).strip():
                bad_title.append(i)
    checks.append(_ck(not bad_type, f"题型全部在白名单（越界 {bad_type or '无'}）",
                      "survey.question_type"))
    checks.append(_ck(not bad_title, f"题目均有标题（缺 {bad_title or '无'}）",
                      "survey.question_title"))

    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    element_count=len(questions) if isinstance(questions, list) else 0,
                    survey_type=data.get("type"),
                    narrative=(f"问卷「{data.get('name', '?')}」（{data.get('type')}·"
                               f"{data.get('status')}）题目 "
                               f"{len(questions) if isinstance(questions, list) else 0} 题"))


# --------------------------------------------------------------------------- #
def _validate_voc(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    vth = c.load_thresholds()["voc"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", response_count=0)

    responses = data.get("responses")
    ok_resp = isinstance(responses, list) and len(responses) > 0
    checks.append(_ck(ok_resp,
                      f"响应 ≥1（实际 {len(responses) if isinstance(responses, list) else 0}）",
                      "voc.responses"))
    if not ok_resp:
        return c.result(checks, ok=False, verdict="FAIL", response_count=0,
                        nps_score=None, theme_count=0)

    n = len(responses)

    # NPS 实算
    scores = [_num(r.get("nps_score")) for r in responses if isinstance(r, dict)
              and r.get("nps_score") is not None]
    invalid = [s for s in scores if not (0 <= s <= 10)]
    checks.append(_ck(not invalid, f"NPS 分数均在 0-10（异常 {invalid or '无'}）",
                      "voc.nps_range"))
    promoters = sum(1 for s in scores if s >= vth["nps_promoter_min"])
    detractors = sum(1 for s in scores if s <= vth["nps_detractor_max"])
    nps = round((promoters - detractors) / len(scores) * 100, 1) if scores else None
    checks.append(_ck(True,
                      f"NPS={nps}（推荐者 {promoters} / 贬损者 {detractors} / 共 {len(scores)}）",
                      "voc.nps"))

    # 样本量门槛（做结论才需要；<min_responses 不判 NPS 好坏，只报告）
    enough = len(scores) >= vth["min_responses"]
    if scores and not enough:
        checks.append(_ck(True, f"样本量 {len(scores)} < {vth['min_responses']}，"
                                f"NPS 仅报告不作结论", "voc.sample"))
    else:
        checks.append(_ck(True, f"样本量 {len(scores)} ≥ {vth['min_responses']}", "voc.sample"))

    # 响应率门槛（发出数 vs 回收数）
    sent = _num(data.get("sent_count"))
    if sent > 0:
        rate = c.safe_div(n, sent)
        checks.append(_ck(rate >= vth["response_rate_min"],
                          f"响应率={rate} ≥ {vth['response_rate_min']}", "voc.response_rate"))
    else:
        checks.append(_ck(True, "未提供发出数，跳过响应率", "voc.response_rate"))

    # 主题提炼：开放文本词频 ≥ theme_min_mentions
    texts = [str(r.get("open_text", "")).strip() for r in responses if isinstance(r, dict)]
    themes = _extract_themes(texts, vth["theme_min_mentions"])
    checks.append(_ck(True, f"VOC 主题 {len(themes)} 个（≥{vth['theme_min_mentions']} 次提及）",
                      "voc.themes"))

    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        response_count=n, nps_score=nps, promoter_count=promoters,
        detractor_count=detractors, theme_count=len(themes),
        themes=themes,
        narrative=(f"响应 {n} 条、NPS={nps}（P{promoters}/D{detractors}）、"
                   f"主题 {len(themes)} 个"))


def _extract_themes(texts: List[str], min_mentions: int) -> List[Dict[str, Any]]:
    """从开放文本中提取高频主题（确定性词频，纯标准库中文分词近似）。"""
    from collections import Counter
    tokens: List[str] = []
    for t in texts:
        tokens += _tokens(t)
    counts = Counter(tokens)
    out = []
    for word, n in counts.most_common():
        if n >= min_mentions:
            out.append({"theme": word, "mentions": n})
    return out[:10]


def _tokens(text: str) -> List[str]:
    """轻量中文/英文分词：连续 CJK 字符按 2 字滑窗 + 英文单词。"""
    parts: List[str] = []
    for seg in re.findall(r"[A-Za-z0-9_]+|[一-鿿]+", text):
        if re.match(r"^[一-鿿]+$", seg):
            parts += [seg[i:i + 2] for i in range(len(seg) - 1)] or [seg]
        else:
            parts.append(seg.lower())
    # 去停用词（最小停用词表）
    stop = {"一个", "我们", "他们", "这个", "那个", "什么", "客户", "就是",
            "还是", "但是", "因为", "所以", "这个产品"}
    return [p for p in parts if p not in stop and len(p) >= 2]
