# -*- coding: utf-8 -*-
"""S01 客户与联系人管理 —— 能力域 1。

整合自 twentyhq__twenty 的 workspace 标准对象：
`person.workspace-entity.ts`（人员/联系方式/时间线）、`company.workspace-entity.ts`
（公司/域名/年收入/people 与 opportunities 关系）、`note/timeline` 的互动记录。
把「客户档案」从 Excel 式堆字段转成确定性校验：人员必填、生命周期枚举、
联系方式渠道白名单、时间线时序单调、公司↔人员↔商机引用完整性。

动作：
  person   人员档案与联系人时间线
  company  公司档案与关系完整性
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "crm"
DESC = "客户与联系人管理：person/company"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("person", help="校验人员档案与时间线")
    a.add_argument("--input", required=True)
    b = act.add_parser("company", help="校验公司档案与关系完整性")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "person":
        return _validate_person(data)
    if args.action == "company":
        return _validate_company(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


# --------------------------------------------------------------------------- #
def _validate_person(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["crm"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", record_count=0)

    person = data.get("person")
    if not isinstance(person, dict):
        return c.result([_ck(False, "缺少 person 对象", "crm.person")],
                        ok=False, verdict="FAIL", record_count=0)

    missing = [k for k in th["person_required"] if not str(person.get(k, "")).strip()]
    checks.append(_ck(not missing, f"人员必填齐备（缺 {missing or '无'}）",
                      "crm.person_required"))

    lifecycle = person.get("lifecycle")
    ok_life = lifecycle in th["lifecycle_stages"]
    checks.append(_ck(ok_life, f"生命周期={lifecycle!r} 在白名单", "crm.lifecycle"))

    channels = person.get("channels") or []
    ok_chan_list = isinstance(channels, list) and len(channels) > 0
    checks.append(_ck(ok_chan_list,
                      f"联系方式 ≥1（实际 {len(channels) if isinstance(channels, list) else 0}）",
                      "crm.channels"))
    bad_chan: List[Any] = []
    empty_chan: List[str] = []
    if isinstance(channels, list):
        for ch in channels:
            if not isinstance(ch, dict):
                bad_chan.append(ch)
                continue
            if ch.get("type") not in th["contact_channels"]:
                bad_chan.append(ch.get("type"))
            if not str(ch.get("value", "")).strip():
                empty_chan.append(str(ch.get("type")))
    checks.append(_ck(not bad_chan, f"渠道在白名单（越界 {bad_chan or '无'}）",
                      "crm.channel_enum"))
    checks.append(_ck(not empty_chan, f"渠道值非空（空值 {empty_chan or '无'}）",
                      "crm.channel_value"))

    timeline = person.get("timeline") or []
    ok_tl = isinstance(timeline, list)
    ts_list = [str(x.get("ts", "")) for x in timeline if isinstance(x, dict)] \
        if ok_tl else []
    ok_mono = ts_list == sorted(ts_list) and all(ts_list)
    checks.append(_ck(ok_tl, "时间线为列表", "crm.timeline"))
    checks.append(_ck(ok_mono, f"时间线时序单调（{len(ts_list)} 条）", "crm.timeline_order"))

    ok = (not missing and ok_life and ok_chan_list and not bad_chan
          and not empty_chan and ok_tl and ok_mono)
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        record_count=1,
        channel_count=len(channels) if isinstance(channels, list) else 0,
        timeline_count=len(ts_list),
        summary=(f"{person.get('name', '?')}（{lifecycle}）"
                 f"渠道 {len(channels) if isinstance(channels, list) else 0} 个、"
                 f"时间线 {len(ts_list)} 条"))

# --------------------------------------------------------------------------- #
def _validate_company(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    th = c.load_thresholds()["crm"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", record_count=0)

    company = data.get("company")
    if not isinstance(company, dict):
        return c.result([_ck(False, "缺少 company 对象", "crm.company")],
                        ok=False, verdict="FAIL", record_count=0)

    missing = [k for k in th["company_required"] if not str(company.get(k, "")).strip()]
    checks.append(_ck(not missing, f"公司必填齐备（缺 {missing or '无'}）",
                      "crm.company_required"))

    people = company.get("people") or []
    ok_people = isinstance(people, list) and len(people) > 0
    checks.append(_ck(ok_people,
                      f"关联人员 ≥1（实际 {len(people) if isinstance(people, list) else 0}）",
                      "crm.company_people"))
    nameless = [i for i, p in enumerate(people)
                if not isinstance(p, dict) or not str(p.get("name", "")).strip()] \
        if isinstance(people, list) else []
    checks.append(_ck(not nameless, f"关联人员均有姓名（缺名下标 {nameless or '无'}）",
                      "crm.company_people_name"))

    opps = company.get("opportunities") or []
    ok_opps = isinstance(opps, list)
    checks.append(_ck(ok_opps, "商机关联为列表", "crm.company_opps"))
    bad_opp = [o.get("name") for o in opps
               if isinstance(o, dict) and not str(o.get("name", "")).strip()] \
        if ok_opps else []
    checks.append(_ck(not bad_opp, f"关联商机均有名称（缺名 {bad_opp or '无'}）",
                      "crm.company_opps_name"))

    ok = not missing and ok_people and not nameless and ok_opps and not bad_opp
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        record_count=1,
        person_count=len(people) if isinstance(people, list) else 0,
        opp_count=len(opps) if isinstance(opps, list) else 0,
        summary=(f"{company.get('name', '?')}：人员 "
                 f"{len(people) if isinstance(people, list) else 0} 名、商机 "
                 f"{len(opps) if isinstance(opps, list) else 0} 个"))
