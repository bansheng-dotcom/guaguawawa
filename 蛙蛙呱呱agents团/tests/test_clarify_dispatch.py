# -*- coding: utf-8 -*-
"""澄清 → 拆卡 → 发卡(nonce) → 收卡校验 的回归。

对应 2026-11-20 复盘的两条：
1. 卡里不写问句 → 每个角色自己猜 → R01 一把抓；
2. 没有 nonce / 执行者 → R01 自己写 claims，再自称"4 个角色都交了"。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import dispatch, report_clarify, report_dispatch, card_issue  # noqa: E402

INTENT = ("我想了解个护这个方向下面有哪些品类，品类下的品牌是有哪些？"
          "在内蒙区域哪些品牌销售会比较好？产地的货是怎么调拨的？"
          "各个品牌的价格都是怎样定的？新品试销的周期和营销方式？")

SEM_YAML = """schema: dsh.semantic/v3
generated: false
entities:
- id: region
  type: spatial
  levels: [全区, 呼和浩特, 包头, 鄂尔多斯, 赤峰]
- id: category
  type: hierarchy
  levels: [大类, 子类]
- id: brand
  type: party
- id: channel
  type: structural
- id: period
  type: time
  grain: year
grain_declarations:
- id: G_region_year
  dims: [region, year]
measures:
- id: retail_sales
  type: simple
  agg: sum
  expr: retail_sales
  unit: 亿元
  grain: G_region_year
- id: share
  type: ratio
  numerator: retail_sales
  denominator: retail_sales@total
  unit: '%'
  grain: G_region_year
  non_additive_dimension: [year]
- id: yoy
  type: ratio
  numerator: retail_sales
  denominator: retail_sales@t-1
  unit: '%'
  grain: G_region_year
boundaries:
- id: B1
  text: 测试口径
  affects: [retail_sales]
fingerprint:
  key: [measure_id, entity_scope, period]
"""


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="guagua_dispatch_"))


def _claims(role: str, qids, nonce: str = "", by: str = "",
            answers=None) -> dict:
    return {
        "schema": "dsh.agent.claims/v1",
        "role": role,
        "dispatch": ({"nonce": nonce, "role": role, "by": by,
                      "questions": list(qids)} if nonce or by else {}),
        "meta": {"title": "测试", "intent": "测试", "profile": "research"},
        "numbers": [{"id": "N1", "name": "规模", "value": 12, "unit": "亿元",
                     "source_file": "S1"}],
        "sources": [{"file": "S1", "kind": "web", "url": "https://example.com/a",
                     "date": "2026-01-01",
                     "quote": "这是一条足够长的原文引文用于字段校验"}],
        "sections": [{"title": f"{qids[0]} 12 亿元", "refs": ["N1"],
                      "answers": list(answers if answers is not None else qids),
                      "reading": [{"text": "一"}, {"text": "二"}],
                      "falsifier": "若跌破 10 亿元则作废"}],
    }


def _setup() -> Path:
    base = _tmp()
    assert report_clarify.write(INTENT, str(base))["ok"]
    assert report_clarify.confirm(str(base), user_said="用户确认：按这个意图做")["ok"]
    # v1.5：发卡前必须先过拆卡 SOP 门禁，所以测试项目也要有真实语义层 + 五轴
    (base / "semantic_layer.yaml").write_text(SEM_YAML, encoding="utf-8")
    spec = card_issue.prepare(base)
    assert spec["ok"], spec
    plan = report_dispatch.write_plan(str(base), confirm=True)
    assert plan["ok"], plan
    issued = report_dispatch.issue(str(base))
    assert issued["ok"], issued
    return base


# --------------------------------------------------------------------------- #
def test_clarify_extracts_questions():
    c = report_clarify.draft(INTENT)
    assert len(c["asks"]) >= 4
    assert sum(1 for a in c["asks"] if a["must"]) >= 3
    assert all(a["type"] for a in c["asks"])
    # 问句里"什么/哪些"要被拆出来，而不是整段当一句
    assert any("调拨" in a["text"] for a in c["asks"])


def test_plan_covers_every_question():
    base = _tmp()
    report_clarify.write(INTENT, str(base))
    report_clarify.confirm(str(base), user_said="用户确认：按这个意图做")
    plan = report_dispatch.write_plan(str(base))
    qids = {m["qid"] for m in plan["mapping"]}
    assert qids == {a["id"] for a in report_clarify.load(str(base))["asks"]}
    assert all(m["primary"] not in ("r01", "r04") for m in plan["mapping"])
    assert len(plan["cards"]) >= 2  # 不能又变成一个人全干


def test_plan_routes_by_keyword():
    base = _tmp()
    report_clarify.write(INTENT, str(base))
    report_clarify.confirm(str(base), user_said="用户确认：按这个意图做")
    plan = report_dispatch.write_plan(str(base))
    m = {x["question"]: x["primary"] for x in plan["mapping"]}
    assert any("调拨" in q and p == "r15" for q, p in m.items())
    assert any("价格" in q and p == "r14" for q, p in m.items())


def test_plan_requires_confirmed_clarify():
    base = _tmp()
    report_clarify.write(INTENT, str(base))
    res = report_dispatch.write_plan(str(base))
    assert res["ok"] is False and "确认" in res["error"]


def test_issue_writes_nonce_and_assignment():
    base = _setup()
    issued = json.loads((base / "coverage" / "issued.json").read_text(encoding="utf-8"))
    assert issued["cards"]
    assert issued.get("card_spec", {}).get("passed") == issued["card_spec"]["total"]
    for rid, rec in issued["cards"].items():
        task = (base / "cards" / rid / "TASK.md").read_text(encoding="utf-8")
        assert rec["nonce"] in task
        # v1.5：卡里带格子 + R02 契约，不再让角色"自己定"
        assert "你负责的" in task and "格子" in task
        assert "R02 任务契约" in task
        assert "你自己定" not in task


def test_collect_rejects_card_without_dispatch():
    base = _setup()
    for rid, rec in json.loads(
            (base / "coverage" / "issued.json").read_text(encoding="utf-8"))["cards"].items():
        (base / "cards" / rid / "claims.json").write_text(
            json.dumps(_claims(rid, rec["questions"]), ensure_ascii=False),
            encoding="utf-8")
    _, problems = dispatch.collect(str(base), min_sources=0)
    assert any("缺 dispatch 块" in p for p in problems)


def test_collect_rejects_self_authored_card():
    base = _setup()
    issued = json.loads(
        (base / "coverage" / "issued.json").read_text(encoding="utf-8"))["cards"]
    for rid, rec in issued.items():
        (base / "cards" / rid / "claims.json").write_text(
            json.dumps(_claims(rid, rec["questions"], nonce=rec["nonce"], by="r01"),
                       ensure_ascii=False), encoding="utf-8")
    _, problems = dispatch.collect(str(base), min_sources=0)
    assert any("代写" in p for p in problems)


def test_collect_accepts_signed_card():
    base = _setup()
    issued = json.loads(
        (base / "coverage" / "issued.json").read_text(encoding="utf-8"))["cards"]
    for rid, rec in issued.items():
        (base / "cards" / rid / "claims.json").write_text(
            json.dumps(_claims(rid, rec["questions"], nonce=rec["nonce"], by=rid),
                       ensure_ascii=False), encoding="utf-8")
    merged, problems = dispatch.collect(str(base), min_sources=0)
    assert not [p for p in problems if "dispatch" in p or "代写" in p]
    assert merged["dispatch"]["mode"] == "nonce"
    assert merged["dispatch"]["verified"] == len(issued)


def test_clarify_reports_coverage_gaps():
    # 只管"有什么/多少"，没问"在什么条件下不成立"→ 边界维必须报缺
    c = report_clarify.draft("内蒙个护有哪些品类，规模多少，哪些品牌卖得好")
    assert "边界" in (c.get("coverage") or {}).get("missing", [])
    assert c["coverage"]["covered"]


def test_card_is_a_workorder_not_a_format_sheet():
    base = _setup()
    issued = json.loads(
        (base / "coverage" / "issued.json").read_text(encoding="utf-8"))["cards"]
    rid = next(iter(issued))
    task = (base / "cards" / rid / "TASK.md").read_text(encoding="utf-8")
    for need in ("事实", "机理", "反例", "什么算答好", "发散槽",
                 "needs.json", "unanswered"):
        assert need in task, f"工单缺「{need}」"
    # 每张卡都带协商脚手架
    assert (base / "cards" / rid / "needs.json").is_file()
    assert (base / "cards" / rid / "answers.json").is_file()


def test_question_accounting_flags_unanswered():
    base = _setup()
    issued = json.loads(
        (base / "coverage" / "issued.json").read_text(encoding="utf-8"))["cards"]
    for rid, rec in issued.items():
        # 只认领第一问：其余 must 应当进 unanswered
        (base / "cards" / rid / "claims.json").write_text(
            json.dumps(_claims(rid, rec["questions"], nonce=rec["nonce"], by=rid,
                               answers=[rec["questions"][0]]),
                       ensure_ascii=False), encoding="utf-8")
    merged, _ = dispatch.collect(str(base), min_sources=0)
    q = merged["questions"]
    assert q["must"], "should have must questions"
    assert q["unanswered"], "没被认领的必答问必须暴露出来"
    assert q["coverage"] is not None and q["coverage"] < 1.0


def test_exchange_blocks_until_answered():
    from core import report_exchange
    base = _setup()
    issued = json.loads(
        (base / "coverage" / "issued.json").read_text(encoding="utf-8"))["cards"]
    rid = next(iter(issued))
    other = next(r for r in issued if r != rid)
    # 我向别的角色要数据，没说清楚就不能闭环
    (base / "cards" / rid / "needs.json").write_text(json.dumps(
        {"needs": [{"id": "N1", "to": other, "what": "四城社零",
                    "why": "要判断节点城市", "status": "open"}]},
        ensure_ascii=False), encoding="utf-8")
    routed = report_exchange.route(str(base))
    assert routed["routed"][other] == 1
    assert (base / "cards" / other / "INBOX.md").is_file()

    for r, rec in issued.items():
        (base / "cards" / r / "claims.json").write_text(
            json.dumps(_claims(r, rec["questions"], nonce=rec["nonce"], by=r),
                       ensure_ascii=False), encoding="utf-8")

    _, problems = dispatch.collect(str(base), min_sources=0)
    assert any("未闭环" in p for p in problems)

    # 对方回一条（带来源），才闭环
    (base / "cards" / other / "answers.json").write_text(json.dumps(
        {"answers": [{"need": f"{rid}:N1", "to": rid, "what": "四城社零",
                      "value": "3538.2", "source_file": "S1",
                      "quote": "四城合计 3538.2 亿元"}]}, ensure_ascii=False),
        encoding="utf-8")
    merged, problems = dispatch.collect(str(base), min_sources=0)
    assert not [p for p in problems if "未闭环" in p]
    assert merged["exchange"]["counts"]["answered"] == 1


def test_coverage_panel_on_caliber_page():
    """口径页要有「问题覆盖」面板，且正文不再重复那句对账。"""
    from core.report_flow import build_sections_contract
    from core.report_theme import pages
    draft = {
        "schema": "dsh.agent.draft/v1", "standfirst": "x 12 亿元",
        "profile": "research",
        "sections": [{"title": "a 12 亿元", "question": "q",
                      "refs": ["r05:N1"],
                      "reading": [{"text": "事实 12 亿元", "refs": ["r05:N1"]}],
                      "boundary": "只覆盖测试口径"}],
        "questions": {"must": ["Q1", "Q2", "Q3"], "unanswered": ["Q2", "Q3"],
                      "asks": {"Q2": "品牌有哪些", "Q3": "哪些卖得好"},
                      "unanswered_detail": [
                          {"qid": "Q2", "why": "无公开品牌级数据"},
                          {"qid": "Q3", "why": "无区域动销"}],
                      "explore": 2},
    }
    pack = {"counts": {"files": 1, "numbers": 1},
            "sources": [{"file": "r05:S1", "url": "https://e.com/a"}],
            "numbers": [{"id": "r05:N1", "name": "n", "value": 12, "unit": "亿元"}]}
    c = build_sections_contract(draft, pack)
    cal = [s for s in c["sections"] if "口径" in s["title"]][0]
    assert cal["coverage"]["must"] == 3
    assert len(cal["coverage"]["items"]) == 2
    html = pages._section(cal, 1, 1, "图 1", "blocks")
    assert 'class="qcov"' in html
    assert "未答 2 问" in html
    assert "无公开品牌级数据" in html
    assert "问题对账" not in html  # 面板已说明，不再重复一行


def test_explore_becomes_a_real_section():
    """发散槽收上来的东西必须成节，不能只统计条数。"""
    from core.report_flow import build_sections_contract
    draft = {
        "schema": "dsh.agent.draft/v1", "standfirst": "x 12 亿元",
        "profile": "research",
        "sections": [{"title": "a 12 亿元", "question": "q", "refs": ["r05:N1"],
                      "reading": [{"text": "事实 12 亿元", "refs": ["r05:N1"]}],
                      "boundary": "只覆盖测试口径"}],
        "explore": [
            {"text": "包头是唯一正号，可能与装备制造用工有关", "value": 9.1,
             "unit": "%", "why_important": "若成立，选品要按城市分", "role": "r06"},
            {"text": "洗衣皂人均购买件数高于香皂", "value": 4.2, "unit": "件",
             "why_important": "家庭装可能比旅行装好卖", "role": "r12"},
        ],
    }
    pack = {"counts": {"files": 1, "numbers": 1},
            "sources": [{"file": "r05:S1", "url": "https://e.com/a"}],
            "numbers": [{"id": "r05:N1", "name": "n", "value": 12, "unit": "亿元"}]}
    c = build_sections_contract(draft, pack)
    titles = [s["title"] for s in c["sections"]]
    ext = [t for t in titles if "延伸发现" in t]
    assert ext, titles
    assert "2 条" in ext[0]
    sec = next(s for s in c["sections"] if "延伸发现" in s["title"])
    assert "9.1%" in " ".join(r["text"] for r in sec["reading"])
    # 末节仍是口径，延伸发现排在它前面
    assert titles[-1] == "口径与分数"


def test_support_merges_into_same_owner():
    """同一个角色的支撑问句，要提示并进它服务的必答节，不要单开一节。"""
    from core import roster
    clarify = {"intent": "x", "asks": [
        {"id": "Q1", "text": "个护品牌有哪些", "type": "清单型",
         "must": True, "default_owner": "r05"},
        {"id": "Q2", "text": "全国对照是怎么样的", "type": "判断型",
         "must": False, "default_owner": "r05"},
    ]}
    plan = report_dispatch.build_plan(clarify, roster.build())
    row = next(m for m in plan["mapping"] if m["qid"] == "Q2")
    assert row["tier"] == "support"
    if row["primary"] == "r05":
        assert row["merge_into"] == "Q1"


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    raise SystemExit(1 if failed else 0)
