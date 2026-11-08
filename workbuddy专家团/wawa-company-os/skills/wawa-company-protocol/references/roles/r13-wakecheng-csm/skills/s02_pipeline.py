# -*- coding: utf-8 -*-
"""S02 销售管道 —— 能力域 2。

整合自 twentyhq__twenty 的 `opportunity.workspace-entity.ts`（name/amount/closeDate/
stage/pointOfContact/company/owner）+ 标准阶段常量（NEW/SCREENING/MEETING/PROPOSAL/
NEGOTIATION/WON/LOST，见 dev-seeder 与 prefill 数据）+ `compute-standard-opportunity-
view-groups` 的分组视图口径。把「管道视图」从截图转成确定性实算：阶段枚举、
加权管道值 Σ(amount×stage_probability)、停滞商机识别、单一客户集中度 HHI。

关键立场：**stage 只是一个人填的字符串，加权值才是决定资源投放的口径**；
封闭阶段（WON/LOST）不进加权池，避免把已赢的单重复计入预测。

动作：
  pipeline  管道视图与加权预测（阶段分布 + 加权值 + 停滞识别 + 集中度）
  opp       单条商机完整性（阶段/金额/下一步/负责人/停滞原因）
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import _common as c

NAME = "pipeline"
DESC = "销售管道：pipeline/opp"


def add_parser(sp) -> None:
    p = sp.add_parser(NAME, help=DESC)
    act = p.add_subparsers(dest="action", required=True)
    a = act.add_parser("pipeline", help="校验管道视图与加权预测")
    a.add_argument("--input", required=True)
    b = act.add_parser("opp", help="校验单条商机完整性")
    b.add_argument("--input", required=True)


def run(args) -> Dict[str, Any]:
    data = c.load_json(args.input)
    if args.action == "pipeline":
        return _validate_pipeline(data)
    if args.action == "opp":
        return _validate_opp(data)
    return {"error": f"未知动作: {args.action}"}


def _ck(ok: bool, msg: str, dim: str = "") -> Dict[str, Any]:
    return {"ok": ok, "msg": msg, "dim": dim, "sev": "OK" if ok else "BLOCKER"}


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


# --------------------------------------------------------------------------- #
def _validate_pipeline(data: Any) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    pth = c.load_thresholds()["pipeline"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", opp_count=0, stage_count=0)

    opps = data.get("opportunities")
    if not isinstance(opps, list) or not opps:
        return c.result([_ck(False, "opportunities 必须是非空列表", "pipeline.list")],
                        ok=False, verdict="FAIL", opp_count=0, stage_count=0,
                        weighted_value=0.0, stale_count=0, concentration_hhi=0.0)

    stages = pth["stages"]
    open_stages = set(pth["open_stages"])
    prob = pth["stage_probability"]
    stall_days = pth["stall_days_max"]

    bad_stage = [o.get("stage") for o in opps
                 if not isinstance(o, dict) or o.get("stage") not in stages]
    checks.append(_ck(not bad_stage, f"阶段全部在白名单（越界 {bad_stage or '无'}）",
                      "pipeline.stage_enum"))

    bad_amount = [o.get("name") for o in opps
                  if not isinstance(o, dict) or _num(o.get("amount")) <= 0]
    checks.append(_ck(not bad_amount, f"金额均为正数（异常 {bad_amount or '无'}）",
                      "pipeline.amount"))

    open_opps = [o for o in opps
                 if isinstance(o, dict) and o.get("stage") in open_stages]
    weighted = round(sum(_num(o.get("amount")) * prob.get(o.get("stage"), 0.0)
                         for o in open_opps), 2)
    checks.append(_ck(True, f"加权管道值={weighted}（开放阶段 {len(open_opps)} 条）",
                      "pipeline.weighted"))

    # 停滞：open 阶段且 days_in_stage > 阈值
    stale = [o.get("name") for o in open_opps
             if _num(o.get("days_in_stage")) > stall_days]
    stale_ratio = c.safe_div(len(stale), len(open_opps))
    checks.append(_ck(stale_ratio <= pth["stale_ratio_max"],
                      f"停滞商机占比={stale_ratio} ≤ {pth['stale_ratio_max']}"
                      f"（停滞 {stale or '无'}）", "pipeline.stall"))

    # 停滞必须有原因
    stale_no_reason = [o.get("name") for o in open_opps
                       if _num(o.get("days_in_stage")) > stall_days
                       and not str(o.get("stall_reason", "")).strip()]
    checks.append(_ck(not stale_no_reason,
                      f"停滞商机均写原因（缺 {stale_no_reason or '无'}）",
                      "pipeline.stall_reason"))

    # 下一步与负责人
    no_next = [o.get("name") for o in open_opps
               if not str(o.get("next_step", "")).strip()]
    checks.append(_ck(not no_next, f"开放商机均有下一步（缺 {no_next or '无'}）",
                      "pipeline.next_step"))
    no_owner = [o.get("name") for o in open_opps
                if not str(o.get("owner", "")).strip()]
    checks.append(_ck(not no_owner, f"开放商机均有负责人（缺 {no_owner or '无'}）",
                      "pipeline.owner"))

    # 集中度：按客户（company）占开放管道金额的 HHI
    by_company: Dict[str, float] = {}
    for o in open_opps:
        key = str(o.get("company", "") or "未归属")
        by_company[key] = by_company.get(key, 0.0) + _num(o.get("amount"))
    total = sum(by_company.values())
    hhi = round(sum((v / total) ** 2 for v in by_company.values()), 4) if total else 0.0
    checks.append(_ck(hhi <= pth["concentration_hhi_max"],
                      f"客户集中度 HHI={hhi} ≤ {pth['concentration_hhi_max']}"
                      f"（{len(by_company)} 个客户）", "pipeline.concentration"))

    stage_counts: Dict[str, int] = {s: 0 for s in stages}
    for o in opps:
        if isinstance(o, dict) and o.get("stage") in stage_counts:
            stage_counts[o["stage"]] += 1
    # stage_count = 实际被使用的阶段数（阶段分布覆盖度），不是商机条数
    used_stages = sum(1 for n in stage_counts.values() if n)

    ok = all(x["ok"] for x in checks)
    top = sorted(by_company.items(), key=lambda kv: -kv[1])[:3]
    return c.result(
        checks, ok=ok, verdict="PASS" if ok else "FAIL",
        opp_count=len(opps), stage_count=used_stages,
        open_count=len(open_opps), weighted_value=weighted,
        stale_count=len(stale), concentration_hhi=hhi,
        stage_distribution=stage_counts,
        top_accounts=[{"company": k, "amount": v} for k, v in top],
        narrative=(f"开放商机 {len(open_opps)} 条、加权管道值 {weighted}、"
                   f"停滞 {len(stale)} 条、客户集中度 HHI={hhi}"))


# --------------------------------------------------------------------------- #
def _validate_opp(data: Any) -> Dict[str, Any]:
    """单条商机完整性：阶段/金额/下一步/负责人/停滞原因（对应 twenty 的 5 个必填语义）。"""
    checks: List[Dict[str, Any]] = []
    pth = c.load_thresholds()["pipeline"]
    if not isinstance(data, dict):
        return c.result([_ck(False, "必须是 JSON 对象", "structure")],
                        ok=False, verdict="FAIL", opp_count=0)

    name = str(data.get("name", "")).strip()
    checks.append(_ck(bool(name), "商机名称非空", "opp.name"))

    stage = data.get("stage")
    ok_stage = stage in pth["stages"]
    checks.append(_ck(ok_stage, f"阶段={stage!r} 在白名单", "opp.stage"))

    amount = _num(data.get("amount"))
    checks.append(_ck(amount > 0, f"金额={amount} 为正", "opp.amount"))

    close_date = str(data.get("close_date", "")).strip()
    checks.append(_ck(bool(close_date), "预计成交日非空", "opp.close_date"))

    owner = str(data.get("owner", "")).strip()
    checks.append(_ck(bool(owner), "负责人非空", "opp.owner"))

    is_open = stage in set(pth["open_stages"])
    if is_open:
        next_step = str(data.get("next_step", "")).strip()
        checks.append(_ck(bool(next_step), "开放阶段必须有下一步", "opp.next_step"))
        stalled = _num(data.get("days_in_stage")) > pth["stall_days_max"]
        if stalled:
            reason = str(data.get("stall_reason", "")).strip()
            checks.append(_ck(bool(reason), "停滞商机必须写停滞原因", "opp.stall_reason"))
        else:
            checks.append(_ck(True, "未停滞，无需原因", "opp.stall_reason"))
    else:
        checks.append(_ck(True, f"{stage} 为封闭阶段，不要求下一步", "opp.next_step"))
        checks.append(_ck(True, f"{stage} 为封闭阶段，不要求停滞原因", "opp.stall_reason"))

    ok = all(x["ok"] for x in checks)
    return c.result(checks, ok=ok, verdict="PASS" if ok else "FAIL",
                    opp_count=1, stage=stage, amount=amount,
                    weighted_value=round(amount * pth["stage_probability"].get(stage, 0.0), 2),
                    narrative=f"{name or '?'}（{stage}）金额 {amount}")
