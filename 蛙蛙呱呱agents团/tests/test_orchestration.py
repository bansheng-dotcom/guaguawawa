# -*- coding: utf-8 -*-
"""orchestration 域测试（合并自 7 个文件）。

源文件：
    test_clarify_dispatch.py —— 澄清 → 拆卡 → 发卡(nonce) → 收卡校验 的回归。
    test_dispatch.py —— v12.2：名册生成 + 发卡/收卡流水线。
    test_orchestrator.py —— P2：专家编排的硬规矩（意图绑定 / 数据齐备 / BLOCKED / 兜底）。
    test_run_router.py —— 统一入口路由器（D+）的选路测试。
    test_s4_relation_branch.py —— test_s4_relation_branch —— 验证 S4 在 report_flow 里的关系选型分支端到端生效。
    test_user_in_the_loop.py —— 2026-11-22：意图必须问用户、卡片必须给用户看；封面取 meta 不取首节。
    test_core_groups.py —— test_core_groups —— core 的逻辑分组入口（物理不动）。
"""
from __future__ import annotations
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent.parent
ROOT = TEAM
REPO = TEAM.parent
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))


import json
import tempfile
from core.cards import dispatch, report_dispatch, card_issue
from core.report import report_clarify
import shutil
from core.cards import dispatch
from core import roster
from core import orchestrator as O
from core.methods.spec import Caps
import guagua
from core.report.report_flow import build_sections_contract
from core.report import report_flow, report_editorial
import core

from core import intake, panel, dor, synthesis
from core.cards import card_plan



# ====================================================================
# 合并自 test_clarify_dispatch.py：澄清 → 拆卡 → 发卡(nonce) → 收卡校验 的回归。
# ====================================================================
# -*- coding: utf-8 -*-


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
    from core.report import report_exchange
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
    from core.report.report_flow import build_sections_contract
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
    from core.report.report_flow import build_sections_contract
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


# ====================================================================
# 合并自 test_dispatch.py：v12.2：名册生成 + 发卡/收卡流水线。
# ====================================================================
# -*- coding: utf-8 -*-


# 项目产物必须写在团外（core/base/paths.py 的边界守卫），测试也不例外
TMP_DISPATCH = Path(tempfile.mkdtemp(prefix="guagua-test-dispatch-"))


def setup_module(module):
    shutil.rmtree(TMP_DISPATCH, ignore_errors=True)


def teardown_module(module):
    shutil.rmtree(TMP_DISPATCH, ignore_errors=True)


def test_roster_is_generated_with_skills():
    r = roster.build()
    assert r["count"] == 20
    assert r["totals"]["actions"] > 150
    assert r["totals"]["skills"] > 100
    assert r["totals"]["report_roles"] == 16
    r05 = r["roles"]["r05"]
    assert r05["enters_report"] is True
    assert r05["actions"], "名册必须带动作，否则调不到技能"
    assert r05["skills"], "名册必须带技能包"


def test_roster_find_action_reverse_lookup():
    r = roster.build()
    hits = roster.find_action(r, "研究")
    assert hits, "反查「研究」应能找到角色"
    assert all(h["role"] for h in hits)


def test_brief_writes_one_card_per_report_role():
    res = dispatch.write_cards("测试用：某行业怎么做", str(TMP_DISPATCH))
    assert res["cards"] == 16
    r05 = TMP_DISPATCH / "cards" / "r05" / "TASK.md"
    assert r05.is_file()
    text = r05.read_text(encoding="utf-8")
    assert "你要判断什么（自己定" in text
    assert "claims.json" in text
    # 卡里不许出现预设题目
    assert "盘子多大" not in text


def test_collect_rejects_incomplete_card():
    dispatch.write_cards("测试用", str(TMP_DISPATCH))
    bad = TMP_DISPATCH / "cards" / "r05" / "claims.json"
    bad.write_text(json.dumps({"role": "r05", "numbers": [],
                               "sources": [], "sections": []},
                              ensure_ascii=False), encoding="utf-8")
    merged, problems = dispatch.collect(str(TMP_DISPATCH))
    assert problems, "空卡必须被拒"
    assert any("r05" in p for p in problems)


def test_collect_flags_missing_cards_when_strict():
    """覆盖门禁：发了 16 张卡只交 1 张，严格模式必须失败（2026-11-19 体检）。"""
    shutil.rmtree(TMP_DISPATCH, ignore_errors=True)
    dispatch.write_cards("测试用", str(TMP_DISPATCH))
    card = {
        "role": "r05",
        "numbers": [{"id": "N1", "name": "规模", "value": 100.0,
                     "unit": "亿元", "period": "2024", "source_file": "S1"}],
        "sources": [{"file": "S1", "title": "t", "org": "o",
                     "url": "https://example.com/s1", "date": "2026-11-19",
                     "grade": "A", "quote": "原文：规模 100.0 亿元，同比 12.0%。"}],
        "sections": [{"title": "规模 100.0 亿元", "refs": ["N1"],
                      "reading": [{"text": "观察：100.0 亿元", "refs": ["N1"]},
                                  {"text": "机理：判别方法是…", "refs": ["N1"]}],
                      "falsifier": "若偏离超过 10.0% 则作废"}],
        "boundaries": ["没有省级数据"],
    }
    (TMP_DISPATCH / "cards" / "r05" / "claims.json").write_text(
        json.dumps(card, ensure_ascii=False), encoding="utf-8")

    merged, problems = dispatch.collect(str(TMP_DISPATCH), require_all=True)
    assert merged["coverage"]["expected"] == 16
    assert merged["coverage"]["delivered"] == 1
    assert any("缺卡" in p for p in problems), problems
    assert "r16" in merged["coverage"]["missing"]

    # 2026-11-22：默认已改为硬门（没 issued.json 就拒收）。
    blocked, probs_blocked = dispatch.collect(str(TMP_DISPATCH))
    assert any("没有 issued.json" in p for p in probs_blocked), probs_blocked

    # 显式 legacy 才回到「只留痕」的老行为，并在产物上标降级。
    lenient, problems2 = dispatch.collect(str(TMP_DISPATCH), allow_legacy=True)
    assert not problems2, "显式 legacy 时只在 coverage 留痕"
    assert lenient["coverage"]["missing"]
    assert "legacy_no_issued" in lenient["degraded"]


def test_collect_namespaces_and_merges():
    shutil.rmtree(TMP_DISPATCH, ignore_errors=True)
    dispatch.write_cards("测试用", str(TMP_DISPATCH))
    card = {
        "role": "r05",
        "numbers": [{"id": "N1", "name": "规模", "value": 100.0,
                     "unit": "亿元", "period": "2024", "source_file": "S1"}],
        "derived": [{"id": "D1", "formula": "N1*2", "value": 200.0,
                     "unit": "亿元", "note": "翻倍"}],
        "sources": [{"file": "S1", "title": "t", "org": "o",
                     "url": "https://example.com/s1", "date": "2026-11-19",
                     "grade": "A", "quote": "原文：规模 100.0 亿元，同比 12.0%。"}],
        "sections": [{"title": "规模 100.0 亿元",
                      "refs": ["N1"],
                      "reading": [{"text": "观察：100.0 亿元", "refs": ["N1"]},
                                  {"text": "机理：判别方法是…", "refs": ["D1"]}],
                      "falsifier": "若偏离超过 10.0% 则作废"}],
        "boundaries": ["没有省级数据"],
        "missing": ["查不到 A"],
    }
    (TMP_DISPATCH / "cards" / "r05" / "claims.json").write_text(
        json.dumps(card, ensure_ascii=False), encoding="utf-8")
    merged, problems = dispatch.collect(str(TMP_DISPATCH), allow_legacy=True)
    assert not problems, problems
    assert merged["numbers"][0]["id"] == "r05:N1"
    assert merged["numbers"][0]["source_file"] == "r05:S1"
    assert merged["derived"][0]["formula"] == "r05:N1*2"
    assert merged["sections"][0]["refs"] == ["r05:N1"]
    assert merged["boundaries"], "卡里的边界必须带上来"
    assert merged["standfirst"].startswith("规模")


def _card(**over):
    card = {
        "role": "r05",
        "numbers": [{"id": "N1", "name": "规模", "value": 100.0,
                     "unit": "亿元", "period": "2024", "source_file": "S1"}],
        "sources": [{"file": "S1", "title": "t", "org": "o",
                     "url": "https://example.com/s1", "date": "2026-11-19",
                     "grade": "A", "quote": "原文：规模 100.0 亿元，同比 12.0%。"}],
        "sections": [{"title": "规模 100.0 亿元", "refs": ["N1"],
                      "reading": [{"text": "观察：100.0 亿元", "refs": ["N1"]},
                                  {"text": "机理：判别方法是…", "refs": ["N1"]}],
                      "falsifier": "若偏离超过 10.0% 则作废"}],
        "boundaries": ["没有省级数据"],
    }
    card.update(over)
    return card


def test_collect_rejects_source_without_quote():
    """缺 quote 的来源等于没查：整张卡拒收，且说明缺什么。"""
    shutil.rmtree(TMP_DISPATCH, ignore_errors=True)
    dispatch.write_cards("测试用", str(TMP_DISPATCH))
    card = _card()
    card["sources"][0]["quote"] = ""
    (TMP_DISPATCH / "cards" / "r05" / "claims.json").write_text(
        json.dumps(card, ensure_ascii=False), encoding="utf-8")
    merged, problems = dispatch.collect(str(TMP_DISPATCH))
    assert any("quote" in p for p in problems), problems
    assert any(r["role"] == "r05" for r in merged["coverage"]["rejected"])
    assert not merged["sources"], "被拒的卡不能把来源合进来"


def test_min_sources_gate():
    """50 源门槛：不到就失败；--min-sources 0 关闭。"""
    shutil.rmtree(TMP_DISPATCH, ignore_errors=True)
    dispatch.write_cards("测试用", str(TMP_DISPATCH))
    (TMP_DISPATCH / "cards" / "r05" / "claims.json").write_text(
        json.dumps(_card(), ensure_ascii=False), encoding="utf-8")
    merged, problems = dispatch.collect(str(TMP_DISPATCH), min_sources=50, allow_legacy=True)
    assert any("低于门槛 50" in p for p in problems), problems
    assert merged["gaps"] == {} or merged["gaps"]["source_shortfall"] == 49
    merged2, problems2 = dispatch.collect(str(TMP_DISPATCH), min_sources=0, allow_legacy=True)
    assert not problems2, problems2
    assert merged2["evidence"]["sources"] == 1


# ====================================================================
# 合并自 test_orchestrator.py：P2：专家编排的硬规矩（意图绑定 / 数据齐备 / BLOCKED / 兜底）。
# ====================================================================
# -*- coding: utf-8 -*-


def _method_plan(mounted=(), skipped=()):
    return {"mounted": [{"key": k} for k in mounted],
            "skipped": [{"key": k, "missing": list(m)} for k, m in skipped]}


def test_experts_file_exists_and_has_twenty_roles():
    ex = O.load_experts()
    roles = ex.get("roles") or {}
    assert len(roles) == 20
    for rid in ("r06", "r15", "r16"):
        assert roles[rid]["methods"], f"{rid} 没有声明可答方法"


def test_hiring_intent_with_price_data_is_unbound():
    """问招聘 + 只有价格数据 → 必须 unbound，且说出缺 table.headcount。"""
    plan = _method_plan(mounted=["structure", "trajectory", "economics"],
                        skipped=[("headcount", ["table.headcount"])])
    d = O.plan("招聘编制与组织设计", method_plan=plan)
    assert d["mode"] == "unbound"
    assert "headcount" in d["reason"]
    blocked = {r["role"] for r in d["blocked"]}
    assert "r16" in blocked


def test_price_intent_selects_price_experts():
    """水果经营诊断 + 价格数据 → 命中 r06（且不被 r16 抢走）。"""
    plan = _method_plan(mounted=["structure", "trajectory", "momentum",
                                 "contribution", "economics", "transmission",
                                 "arbitrage", "breakeven"])
    d = O.plan("内蒙古三城水果经营诊断", method_plan=plan)
    assert d["mode"] == "intent"
    assert [r["role"] for r in d["roster"]] == ["r06"]


def test_procurement_intent_pulls_supply_expert():
    """停采换源/提价 → r15 必须出场，且相关度高于「只命中水果」的 r06。"""
    plan = _method_plan(mounted=["structure", "economics", "transmission",
                                 "arbitrage", "breakeven"])
    d = O.plan("内蒙古三城水果：停采换源还是提价", method_plan=plan)
    roles = [r["role"] for r in d["roster"]]
    assert "r15" in roles
    by_role = {r["role"]: r for r in d["rows"]}
    assert by_role["r15"]["relevance"] > by_role["r06"]["relevance"]
    assert {"停采", "换源", "提价"} & set(by_role["r15"]["hits"])


def test_refuses_are_excluded_even_if_keywords_match():
    """r16 声明不答「价格行情」→ 提到价格也不能让它出场。"""
    plan = _method_plan(mounted=["headcount", "structure"])
    d = O.plan("价格行情分析", method_plan=plan)
    assert "r16" not in [r["role"] for r in d["roster"]]


def test_unrelated_intent_falls_back_to_data_mode():
    """完全不相关的一句话 → data 兜底（auto），而不是硬塞专家。"""
    d = O.plan("帮我写一首关于秋天的诗", method_plan=_method_plan(mounted=["structure"]))
    assert d["mode"] == "data"
    assert d["roster"] == []


def test_readiness_uses_method_plan():
    ex = O.load_experts()["roles"]["r06"]
    full = O.readiness(ex, _method_plan(mounted=ex["methods"]))
    none = O.readiness(ex, _method_plan(skipped=[(k, ["price.series2"]) for k in ex["methods"]]))
    assert full["readiness"] == 1.0
    assert none["readiness"] == 0.0
    assert "price.series2" in none["missing"]


def test_role_without_methods_is_review_only_not_selected():
    """无方法的角色不许进数据 roster（2026-11-19 体检：它会被选中却答不了）。

    旧病：r11/r19/r03 readiness=1.0 → 选中 → 出题 0 个 → 静默回退数据题库。
    新规矩：标 review_only + blocked；命中的专家全答不了 → 整份 unbound。
    """
    ex = O.load_experts()["roles"]["r11"]
    assert not ex["methods"], "r11 若新增了方法，这条用例要改成换一个无方法角色"
    d = O.plan("小红书笔记怎么写才能带货",
               method_plan=_method_plan(mounted=["structure", "trajectory"]))
    rows = {r["role"]: r for r in d["rows"]}
    assert rows["r11"]["status"] == "blocked"
    assert rows["r11"].get("review_only") is True
    assert rows["r11"]["why"].startswith("该角色没有可进报告的方法")
    assert d["mode"] == "unbound"
    assert "r11" in d["reason"]


# ====================================================================
# 合并自 test_run_router.py：统一入口路由器（D+）的选路测试。
# ====================================================================
# -*- coding: utf-8 -*-


def _run(argv, capsys):
    code = guagua.main(argv)
    return code, json.loads(capsys.readouterr().out)


def test_role_routes_to_single(capsys):
    code, data = _run(["run", "--role", "r06", "--", "--help"], capsys)
    assert code == 0
    assert data["mode"] == "single"
    assert data["argv"][0] == "call"


def test_intent_routes_to_card(capsys):
    code, data = _run(["run", "--intent", "本周库存怎么补"], capsys)
    assert code == 0
    assert data["mode"] == "card"
    assert data["argv"][0] == "plan"


def test_dir_out_routes_to_inline(capsys):
    code, data = _run(["run", "--intent", "分析", "--dir", "p", "--out", "o"], capsys)
    assert code == 0
    assert data["mode"] == "inline"
    assert data["argv"][:3] == ["report", "run-line", "--intent"]


def test_cards_source_needs_claims(capsys):
    code, data = _run(["run", "--intent", "分析", "--dir", "p", "--out", "o",
                       "--source", "cards"], capsys)
    assert code == 2
    assert data["stage"] == "route"


def test_no_input_returns_2(capsys):
    code, data = _run(["run"], capsys)
    assert code == 2
    assert data["stage"] == "route"


# ====================================================================
# 合并自 test_s4_relation_branch.py：test_s4_relation_branch —— 验证 S4 在 report_flow 里的关系选型分支端到端生效。
# ====================================================================
# -*- coding: utf-8 -*-


def _draft(chart_type, relation):
    return {
        "standfirst": "三地价差 1.5 倍",
        "sections": [{
            "title": "三地价差 1.5 倍",
            "question": "两地价差有多大",
            "relation": relation,
            "reading": [{"strong": "事实　", "text": "包头 2 元，呼市 3 元。",
                         "refs": ["N1", "N2"]}],
            "refs": ["N1", "N2", "N3"],
            "falsifier": "价差收敛到 1.2 倍以下即作废",
            "boundary": "同口径批发价",
            "chart": {
                "type": chart_type,
                "relation": relation,
                "intent": "排序",
                "why_this_chart": "哑铃图直接编码同一品类两地价差",
                # 2026-11-23：门槛提到 ≥3 点（1–2 点不出图），测试补第三个点
                "refs": ["N1", "N2", "N3"],
                "bars": [{"label": "包头", "value": 2.0},
                         {"label": "呼和浩特", "value": 3.0},
                         {"label": "鄂尔多斯", "value": 2.5}],
            },
        }],
    }


def _pack():
    return {"numbers": [
        {"id": "N1", "name": "包头批发价", "value": 2.0, "unit": "元/公斤",
         "entity": "包头", "period": ""},
        {"id": "N2", "name": "呼市批发价", "value": 3.0, "unit": "元/公斤",
         "entity": "呼和浩特", "period": ""},
        {"id": "N3", "name": "鄂尔多斯批发价", "value": 2.5, "unit": "元/公斤",
         "entity": "鄂尔多斯", "period": ""},
    ]}


def test_relation_branch_valid_dumbbell():
    secs = build_sections_contract(_draft("dumbbell", "ranking"), _pack())
    ch = secs["sections"][0]["chart"]
    assert ch.get("relation") == "ranking"
    assert ch.get("chart_validation", {}).get("ok") is True


def test_relation_branch_invalid_line():
    # line 不能表达 ranking → 应 ok=False 并给 suggest
    secs = build_sections_contract(_draft("line", "ranking"), _pack())
    ch = secs["sections"][0]["chart"]
    val = ch.get("chart_validation", {})
    assert val.get("ok") is False
    assert val.get("suggest")


# ====================================================================
# 合并自 test_user_in_the_loop.py：2026-11-22：意图必须问用户、卡片必须给用户看；封面取 meta 不取首节。
# ====================================================================
# -*- coding: utf-8 -*-


# 临时目录必须在团外：写团内会让"项目边界门禁"变红（且污染工具仓）
TMP_UITL = Path(tempfile.gettempdir()) / "guagua_test_user_in_the_loop"


def _setup_uitl(by: str = "agent", ack: bool = False):
    shutil.rmtree(TMP_UITL, ignore_errors=True)
    TMP_UITL.mkdir(parents=True)
    (TMP_UITL / "clarify.json").write_text(json.dumps({
        "status": "confirmed", "confirmed_by": by,
        "user_said": "用户说：按这个做" if by == "user" else "",
        "asks": [{"id": f"Q{i}", "text": "问句", "must": True} for i in range(1, 11)],
    }, ensure_ascii=False), encoding="utf-8")
    (TMP_UITL / "intake.json").write_text(json.dumps({
        "answers": {f"I{i}": "答案" for i in range(1, 13)},
        "answered_by": {f"I{i}": by for i in range(1, 13)},
        "user_answers": 12 if by == "user" else 0,
        "status": "complete",
    }, ensure_ascii=False), encoding="utf-8")
    plan = {"status": "confirmed",
            "cards": [{"role": "r06", "questions": ["Q1"]}]}
    if ack:
        plan["acknowledged_at"] = "2026-11-22T10:00:00"
    (TMP_UITL / "plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    (TMP_UITL / "semantic_layer.yaml").write_text("measures:\n- id: m\n", encoding="utf-8")
    return TMP_UITL


def test_preflight_blocks_agent_confirmed_intent():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pf", Path("scripts/preflight.py").resolve())
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    r = mod.run(str(_setup_uitl(by="agent")), 0)
    fails = {c["id"] for c in r["checks"] if not c["ok"]}
    assert "P8" in fails, r
    r2 = mod.run(str(_setup_uitl(by="user", ack=True)), 0)
    assert not {c["id"] for c in r2["checks"] if not c["ok"]} & {"P8", "P9"}, r2


def test_cover_title_comes_from_meta_not_first_section():
    secs = [{"index": 1, "title": "首节结论 42%",
             "reading": [{"strong": "事实　", "text": "42%"},
                         {"strong": "所以　", "text": "所以先做 A"}],
             "refs": ["N1"], "headline": "42%", "falsifier": "跌破 30% 作废"}]
    pack = {"meta": {"title": "小码女装市场研究",
                     "subtitle": "人群 · 竞争 · 价盘",
                     "metrics": [{"label": "女装大盘", "value": "12311亿元"}]},
            "numbers": [{"id": "N1", "value": 42, "unit": "%", "name": "占比"}]}
    dec = report_flow._build_decision(secs, pack)
    assert dec["title"] == "小码女装市场研究", dec
    assert dec["subtitle"] == "人群 · 竞争 · 价盘"
    strip = report_editorial._metrics({"decision": dec}, pack)
    assert strip and strip[0]["value"] == "12311亿元", strip


def test_evidence_pack_carries_meta():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "car", Path("scripts/compile_agent_report.py").resolve())
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pack = mod.build_pack({"meta": {"title": "T", "subtitle": "S"},
                           "sources": [], "numbers": []})
    assert pack["meta"]["title"] == "T"
    assert pack["meta"]["subtitle"] == "S"


# ====================================================================
# 合并自 test_core_groups.py：test_core_groups —— core 的逻辑分组入口（物理不动）。
# ====================================================================
# -*- coding: utf-8 -*-


def test_group_attributes_exist():
    for g in ("pipeline", "intent", "experts", "data", "cards",
              "semantic", "narrative", "render", "gates", "coordination"):
        assert hasattr(core, g), g
        assert len(dir(getattr(core, g))) > 0, g


def test_group_resolves_to_same_module():
    assert core.gates.quality_gate is core.quality_gate
    assert core.pipeline.report_flow is core.report.report_flow
    assert core.semantic.report_ir is core.report.report_ir
    assert core.cards.card_issue is core.cards.card_issue
    assert core.narrative.claims_v4 is core.claims.claims_v4


def test_group_member_is_lazy_then_cached():
    # 访问前不在 sys.modules 里（可能已被别的测试导入，所以只验证访问后能拿到）
    m1 = core.experts.roster
    m2 = core.experts.roster
    assert m1 is m2


def test_unknown_member_raises():
    try:
        core.gates.not_a_module  # noqa: B018
    except AttributeError as exc:
        assert "not_a_module" in str(exc)
    else:
        raise AssertionError("应当抛 AttributeError")


def test_charts_package_aggregates_chart_modules():
    from core.charts import chart_grammar, chart_lib
    assert chart_grammar is core.charts.chart_grammar
    assert chart_lib is __import__("core.charts.chart_lib", fromlist=["x"])


def test_render_group_points_at_report_theme():
    assert core.render.report_theme is core.report_theme


def test_group_repr():
    assert "modules" in repr(core.gates)


# ====================================================================
# 合并自 test_v5_wiring.py（原为无 pytest 的脚本式自测，2026-11-25 转正）
# ====================================================================
def test_v5_intake_sign_flow(tmp_path):
    r = intake.start(tmp_path, "北京宠物用品市场机会")
    assert r["questions"] == 12 and r["min_answers"] == 10
    assert intake.sign_brief(tmp_path)["ok"] is False
    a = intake.answer(tmp_path, [f"I{i}=答案{i}" for i in range(1, 11)])
    assert a["ok"] is True and a["answered"] == 10
    # 2026-11-22：签 brief 必须带用户原话，否则拒签
    assert intake.sign_brief(tmp_path)["ok"] is False
    sg = intake.sign_brief(tmp_path, user_said="用户确认：就按这个目标做")
    assert sg["ok"] is True and sg["signed"]["sha"]
    assert intake.signed(tmp_path) is not None


def test_v5_panel_dor_synthesis():
    panels = panel.build("北京宠物用品市场机会", {"asks": []})
    assert len(panels) == 3 and all(p["target_rows"] > 0 for p in panels)
    rows = []
    for i, city in enumerate(("朝阳", "海淀", "丰台"), 1):
        rows.append({"metric_name": f"北京{city}零售额", "entity": city, "period": "2025",
                     "value": 10 * i, "unit": "亿元", "row_id": f"R{i}",
                     "number_id": f"r05:N{i}", "metric_id": "retail.sales",
                     "value_base": 10 * i * 1e8})
    cov = panel.coverage(rows, panels)
    assert cov["panels"][0]["filled"] >= 1

    card = {"question": "北京各品类零售额差距", "primary": "r05", "cells": rows,
            "tier": "must", "metrics": ["retail.sales"], "panel": "P1",
            "acceptance": ["G1"], "deliverable": "rows.json", "depends_on": [],
            "why": "面板切片"}
    d = dor.check(card)
    assert d["ok"] is True
    assert dor.score(card) >= 16
    empty = dor.check({"question": ""})
    assert empty["ok"] is False and empty["missing"]

    th = synthesis.theses(rows, panels)
    assert len(th) >= 1
    secs = synthesis.sections(th, rows)
    assert secs and secs[0]["chart"] and secs[0]["prose_spec"]["signal"]
    assert secs[0]["refs"] and secs[0]["refs"][0].startswith("r05:")


def test_v5_card_plan_cluster_and_load_cap():
    cells = []
    for q in ("Q1", "Q2", "Q3"):
        for i in range(16):
            cells.append({"cell_id": f"{q}.c{i}", "qid": q, "dim": "空间",
                          "measure": "retail_sales"})
    cl = card_plan.cluster(cells)
    assert len(cl) == 3
    big = [{"cell_id": f"Q9.c{i}", "qid": "Q9", "dim": "空间", "measure": "retail_sales"}
           for i in range(30)]
    cl2 = card_plan.cluster(big)
    assert len(cl2) == 2 and all(len(c["cells"]) <= 24 for c in cl2)
    cl3, _ = card_plan.assign(cl, {r: {"role": r, "capabilities": ["数据"],
                                       "skills": [], "entitlements": {}}
                                   for r in ("r05", "r06")}, load_cap=2)
    assert sum(1 for c in cl3 if c.get("owner") == "r05") <= 2
