# -*- coding: utf-8 -*-
"""S04 全渠道客服 —— 能力域 4。

整合自 chatwoot__chatwoot：`conversation.rb`（status 枚举 open/resolved/pending/
snoozed、first_reply_created_at、waiting_since、assignee、team）、`inbox.rb`
（channel_type 白名单）、`message.rb`（message_type incoming/outgoing/activity/
template、private 内部备注）、`csat_survey_response.rb`（rating 1-5）、
`app/builders/v2/reports`（conversations_count/avg_first_response_time/
avg_resolution_time 指标口径）。把「客服收件箱」转成确定性校验：渠道白名单、
首响时长、解决时长、重开率、CSAT 均值、私有备注隔离。

动作：
  inbox   客服收件箱与 SLA 门禁（渠道 + 首响/解决/重开 + CSAT）
  ticket  单张工单/会话完整性（状态 + 渠道 + 消息方向 + 私有备注）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "support"
DESC = "全渠道客服：inbox/ticket"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("inbox", help="校验客服收件箱与 SLA")
    a.add_argument("--input", required=True)
    b = act.add_parser("ticket", help="校验单张工单")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "inbox":
        return _validate_inbox(data)
    if args.action == "ticket":
        return _validate_ticket(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


# --------------------------------------------------------------------------- #
def _validate_inbox(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    sth = c.load_thresholds()["support"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", ticket_count=0, channel_count=0)

    tickets = data.get("conversations")
    if not isinstance(tickets, list) or not tickets:
        return c.result([_ck(False, "conversations 必须是非空列表", "support.list")],
                        ok=False, verdict="FAIL", ticket_count=0, channel_count=0)

    channels = sth["channel_types"]
    bad_channel = [t.get("channel") for t in tickets
                   if not isinstance(t, dict) or t.get("channel") not in channels]
    checks.append(_ck(not bad_channel,
                      f"渠道全部在白名单（越界 {bad_channel or '无'}）",
                      "support.channel_enum"))

    bad_status = [t.get("status") for t in tickets
                  if not isinstance(t, dict) or t.get("status") not in sth["conversation_status"]]
    checks.append(_ck(not bad_status,
                      f"会话状态全部在白名单（越界 {bad_status or '无'}）",
                      "support.status_enum"))

    # 首响时长（分钟，仅对已分配且有首响记录的）
    fr_max = sth["first_response_minutes_max"]
    slow_fr = [t.get("id", "?") for t in tickets if isinstance(t, dict)
               and t.get("first_response_minutes") is not None
               and _num(t.get("first_response_minutes")) > fr_max]
    checks.append(_ck(not slow_fr,
                      f"首响 ≤ {fr_max} 分钟（超时 {slow_fr or '无'}）",
                      "support.first_response"))

    # 解决时长（小时，仅对 resolved 会话）
    res_max = sth["resolution_hours_max"]
    slow_res = [t.get("id", "?") for t in tickets if isinstance(t, dict)
                and t.get("status") == "resolved"
                and t.get("resolution_hours") is not None
                and _num(t.get("resolution_hours")) > res_max]
    checks.append(_ck(not slow_res,
                      f"解决 ≤ {res_max} 小时（超时 {slow_res or '无'}）",
                      "support.resolution"))

    # 重开率
    reopened = [t for t in tickets if isinstance(t, dict) and t.get("reopened")]
    reopen_ratio = c.safe_div(len(reopened), len(tickets))
    checks.append(_ck(reopen_ratio <= sth["reopen_ratio_max"],
                      f"重开率={reopen_ratio} ≤ {sth['reopen_ratio_max']}"
                      f"（重开 {len(reopened)}）", "support.reopen"))

    # CSAT 均值（有评分的会话）
    ratings = [_num(t.get("csat")) for t in tickets if isinstance(t, dict)
               and t.get("csat") is not None]
    bad_rating = [r for r in ratings if r not in sth["csat_scale"]]
    checks.append(_ck(not bad_rating, f"CSAT 评分均在 1-5（异常 {bad_rating or '无'}）",
                      "support.csat_scale"))
    avg_csat = round(sum(ratings) / len(ratings), 2) if ratings else None
    checks.append(_ck(avg_csat is None or avg_csat >= sth["csat_min"],
                      f"CSAT 均值={avg_csat} ≥ {sth['csat_min']}"
                      f"（{'无评分' if avg_csat is None else '达标' if avg_csat >= sth['csat_min'] else '不达标'}）",
                      "support.csat"))

    open_count = sum(1 for t in tickets if isinstance(t, dict)
                     and t.get("status") in ("open", "pending", "snoozed"))
    ok = all(x["ok"] for x in checks)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        ticket_count=len(tickets),
        channel_count=len({t.get("channel") for t in tickets if isinstance(t, dict)}),
        open_count=open_count, avg_csat=avg_csat,
        reopen_count=len(reopened),
        narrative=(f"会话 {len(tickets)} 条（开放 {open_count}）、"
                   f"CSAT 均值 {avg_csat if avg_csat is not None else '无评分'}、"
                   f"重开 {len(reopened)} 条"))


# --------------------------------------------------------------------------- #
def _validate_ticket(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    sth = c.load_thresholds()["support"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", ticket_count=0)

    ok_status = data.get("status") in sth["conversation_status"]
    checks.append(_ck(ok_status, f"状态={data.get('status')!r} 在白名单", "ticket.status"))

    ok_channel = data.get("channel") in sth["channel_types"]
    checks.append(_ck(ok_channel, f"渠道={data.get('channel')!r} 在白名单", "ticket.channel"))

    messages = data.get("messages")
    ok_msgs = isinstance(messages, list) and len(messages) > 0
    checks.append(_ck(ok_msgs,
                      f"消息 ≥1（实际 {len(messages) if isinstance(messages, list) else 0}）",
                      "ticket.messages"))
    bad_mt: List[Any] = []
    if isinstance(messages, list):
        for m in messages:
            if not isinstance(m, dict) or m.get("message_type") not in sth["message_types"]:
                bad_mt.append(m.get("message_type") if isinstance(m, dict) else m)
    checks.append(_ck(not bad_mt, f"消息方向在白名单（越界 {bad_mt or '无'}）",
                      "ticket.message_type"))

    # 私有备注必须 private=true 且内容非空
    private_leak = [i for i, m in enumerate(messages) if isinstance(m, dict)
                    and m.get("message_type") == "outgoing"
                    and m.get("private") is not True
                    and "内部" in str(m.get("content", ""))]
    checks.append(_ck(not private_leak, f"内部备注已隔离（泄漏下标 {private_leak or '无'}）",
                      "ticket.private"))

    has_incoming = any(isinstance(m, dict) and m.get("message_type") == "incoming"
                       for m in (messages or []))
    checks.append(_ck(has_incoming, "会话至少一条客户入站消息", "ticket.incoming"))

    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    ticket_count=1, status=data.get("status"),
                    message_count=len(messages) if isinstance(messages, list) else 0,
                    narrative=f"会话 {data.get('id', '?')}（{data.get('status')}·"
                              f"{data.get('channel')}）消息 {len(messages) if isinstance(messages, list) else 0} 条")
