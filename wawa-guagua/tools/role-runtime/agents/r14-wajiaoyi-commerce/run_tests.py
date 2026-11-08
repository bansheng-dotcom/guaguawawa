#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R14 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 8 技能 17 动作（含脏数据·越界·伪造结论必须 FAIL）/ 契约(T6) /
对抗评审(T7) / 案例库(T8) / 阈值外置(T9) / harness / demo / run_task /
verify_loop 闭环矩阵(T15)。

用法：
    python run_tests.py          # 全量
    python run_tests.py --verbose
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.dirname(HERE)
for p in (HERE, AGENTS):
    if p not in sys.path:
        sys.path.insert(0, p)

# Windows 中文控制台默认 GBK，直接 print 中文会乱码/抛错（R07 踩坑，全角色同款）。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from skills import (s01_catalog, s02_order, s03_billing, s04_payment,  # noqa: E402
                    s05_signature, s06_appointment, s07_workflow, s08_revenue)
from skills import SKILLS, _common as c  # noqa: E402
import contracts  # noqa: E402
import review  # noqa: E402
import cases  # noqa: E402
import harness  # noqa: E402
import verify_loop  # noqa: E402


class T:
    def __init__(self, verbose=False):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.verbose = verbose

    def check(self, name, cond, detail=""):
        if cond:
            self.passed += 1
            if self.verbose:
                print(f"  ok  {name}")
        else:
            self.failed += 1
            self.errors.append((name, detail))
            print(f"FAIL  {name}" + (f"  -> {detail}" if detail else ""))

    def section(self, title):
        print(f"\n== {title} ==")


def run_agent(*args):
    """运行 agent.py 并解析 __AGENT_RESULT__。返回 (exit_code, dict)。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([sys.executable, os.path.join(HERE, "agent.py"), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)
    for line in (proc.stdout or "").splitlines():
        if line.startswith("__AGENT_RESULT__ "):
            return proc.returncode, json.loads(line[len("__AGENT_RESULT__ "):])
    return proc.returncode, {"_raw_stdout": (proc.stdout or "")[-4000:],
                             "_stderr": (proc.stderr or "")[-2000:]}


def _ex(name):
    return os.path.join(HERE, "examples", name)


def _fail_msgs(r):
    return [x["msg"] for x in r.get("checks", []) if not x["ok"]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    t = T(args.verbose)

    # ------------------------------------------------------------------ #
    t.section("manifest / 技能清单")
    code, m = run_agent("manifest")
    t.check("manifest 返回正常", code == 0 and "skills" in m)
    t.check("8 个技能", len(m.get("skills", [])) == 8, str(len(m.get("skills", []))))
    t.check("角色 r14", m.get("role") == "r14", str(m.get("role")))
    t.check("输入端口 package/quotation",
            m.get("inputs") == ["package", "quotation"], str(m.get("inputs")))
    t.check("输出端口 order/payment_status",
            m.get("outputs") == ["order", "payment_status"], str(m.get("outputs")))
    t.check("8 个能力域", len(m.get("capabilities", [])) == 8,
            str(len(m.get("capabilities", []))))

    # ------------------------------------------------------------------ #
    t.section("S01 商品电商后端")
    r = s01_catalog._validate_product(c.load_json(_ex("product.json")))
    t.check("product 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("product_count=3", r["product_count"] == 3, str(r["product_count"]))
    t.check("sellable_count=2（draft 不可售）", r["sellable_count"] == 2,
            str(r["sellable_count"]))
    r = s01_catalog._validate_product(c.load_json(_ex("product_dirty.json")))
    t.check("product 脏数据拦截", not r["ok"])
    t.check("product 拦截空标题", any("必填" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("product 拦截状态越界", any("状态" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("product 拦截非正价格", any("价格" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s01_catalog._validate_price(c.load_json(_ex("price.json")))
    t.check("price 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s01_catalog._validate_price({"title": "免费包", "status": "published",
                                     "price": 0})
    t.check("price=0 被拦截（> 0 口径）", not r["ok"], str(_fail_msgs(r)))
    r = s01_catalog._validate_price(c.load_json(_ex("price_dirty.json")))
    t.check("price 脏数据拦截", not r["ok"])

    # ------------------------------------------------------------------ #
    t.section("S02 购物车与订单")
    r = s02_order._validate_cart(c.load_json(_ex("cart.json")))
    t.check("cart 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("line_item_count=2", r["line_item_count"] == 2, str(r["line_item_count"]))
    t.check("cart_total=1046.0", abs(r["cart_total"] - 1046.0) < 0.01,
            str(r["cart_total"]))
    r = s02_order._validate_cart(c.load_json(_ex("cart_dirty.json")))
    t.check("cart 脏数据拦截", not r["ok"])
    t.check("cart 拦截负单价", any("单价" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("cart 拦截零数量", any("数量" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("cart 拦截小计不恒等", any("小计" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s02_order._validate_order(c.load_json(_ex("order.json")))
    t.check("order 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("order 三态回显", r["status"] == "completed"
            and r["payment_status"] == "captured"
            and r["fulfillment_status"] == "delivered")
    r = s02_order._validate_order(c.load_json(_ex("order_dirty.json")))
    t.check("order 脏数据拦截", not r["ok"])
    t.check("order 拦截空订单号", any("订单号" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("order 拦截退款却已完成",
            any("自相矛盾" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    # 三轴各自合法但组合矛盾 —— 分轴校验的样例
    r = s02_order._validate_order({"id": "o1", "status": "completed",
                                   "payment_status": "refunded",
                                   "fulfillment_status": "delivered",
                                   "total": 1000})
    t.check("order 三轴单看合法、组合矛盾被拦截", not r["ok"],
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S03 订阅计量计费")
    r = s03_billing._validate_plan(c.load_json(_ex("plan.json")))
    t.check("plan 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("charge_count=2", r["charge_count"] == 2, str(r["charge_count"]))
    t.check("interval=monthly", r["interval"] == "monthly", str(r["interval"]))
    r = s03_billing._validate_plan(c.load_json(_ex("plan_dirty.json")))
    t.check("plan 脏数据拦截", not r["ok"])
    t.check("plan 拦截自定义聚合缺表达式",
            any("custom_agg" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s03_billing._validate_usage(c.load_json(_ex("usage.json")))
    t.check("usage 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("usage_count=2", r["usage_count"] == 2, str(r["usage_count"]))
    t.check("total_quantity=351200", abs(r["total_quantity"] - 351200.0) < 0.01,
            str(r["total_quantity"]))
    r = s03_billing._validate_usage(c.load_json(_ex("usage_dirty.json")))
    t.check("usage 脏数据拦截", not r["ok"])
    t.check("usage 拦截零/负用量", any("用量均为正" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s03_billing._validate_invoice(c.load_json(_ex("invoice.json")))
    t.check("invoice 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("invoice 恒等式 897+149=1046",
            abs(r["total"] - 1046.0) < 0.01, str(r["total"]))
    r = s03_billing._validate_invoice({"id": "i1", "status": "finalized",
                                       "total": 1046.0,
                                       "line_items": [{"description": "a",
                                                       "amount": 946.0}]})
    t.check("invoice 恒等式不成立被拦截", not r["ok"], str(_fail_msgs(r)))
    r = s03_billing._validate_invoice(c.load_json(_ex("invoice_dirty.json")))
    t.check("invoice 脏数据拦截", not r["ok"])
    t.check("invoice 拦截空明细", any("明细" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S04 支付集成")
    r = s04_payment._validate_payment_intent(c.load_json(_ex("payment_intent.json")))
    t.check("payment_intent 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("pi status=succeeded", r["status"] == "succeeded", str(r["status"]))
    t.check("pi amount=104600", abs(r["amount"] - 104600.0) < 0.01, str(r["amount"]))
    r = s04_payment._validate_payment_intent(
        c.load_json(_ex("payment_intent_dirty.json")))
    t.check("payment_intent 脏数据拦截", not r["ok"])
    t.check("pi 拦截状态越界", any("状态" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("pi 拦截金额低于下限（元分混淆）",
            any("最低" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    # succeeded 但缺幂等键 —— 重复入账风险
    r = s04_payment._validate_payment_intent(
        {"id": "pi_x", "status": "succeeded", "amount": 100000,
         "intent_type": "payment_intent"})
    t.check("pi succeeded 缺幂等键被拦截", not r["ok"], str(_fail_msgs(r)))
    r = s04_payment._validate_refund(c.load_json(_ex("refund.json")))
    t.check("refund 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("refund_ratio=0.2859", abs(r["refund_ratio"] - 0.2859) < 0.001,
            str(r["refund_ratio"]))
    r = s04_payment._validate_refund(c.load_json(_ex("refund_dirty.json")))
    t.check("refund 脏数据拦截", not r["ok"])
    t.check("refund 拦截超额（ratio>1.0）",
            any("退款比例" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("refund 拦截不可退前置状态",
            any("前置状态" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("refund 拦截缺 payment_intent",
            any("必填" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S05 电子签与签署审计")
    r = s05_signature._validate_document(c.load_json(_ex("document.json")))
    t.check("document 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("recipient_count=3", r["recipient_count"] == 3, str(r["recipient_count"]))
    r = s05_signature._validate_document(c.load_json(_ex("document_dirty.json")))
    t.check("document 脏数据拦截", not r["ok"])
    t.check("document 拦截 SIGNED 误用为文件状态",
            any("状态" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    t.check("document 拦截角色越界", any("角色" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s05_signature._validate_signing(c.load_json(_ex("signing.json")))
    t.check("signing 干净通过（全签）", r["ok"], str(_fail_msgs(r)))
    t.check("signed_count=2 / must_sign=2",
            r["signed_count"] == 2 and r["must_sign_count"] == 2,
            f"{r['signed_count']}/{r['must_sign_count']}")
    r = s05_signature._validate_signing(c.load_json(_ex("signing_dirty.json")))
    t.check("signing 脏数据拦截（伪造完成信号）", not r["ok"])
    t.check("signing 拦截未签却 COMPLETED",
            any("全签" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    # CC 不签不影响完成
    r = s05_signature._validate_signing({
        "status": "COMPLETED",
        "recipients": [{"email": "a@e.com", "role": "SIGNER",
                        "signing_status": "SIGNED"},
                       {"email": "c@e.com", "role": "CC",
                        "signing_status": "NOT_SIGNED"}]})
    t.check("signing CC 未签不阻塞完成", r["ok"], str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S06 服务预约")
    r = s06_appointment._validate_appointment(c.load_json(_ex("appointment.json")))
    t.check("appointment 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("appointment 状态归一化为 booked", r["status"] == "booked",
            str(r["status"]))
    r = s06_appointment._validate_appointment(
        c.load_json(_ex("appointment_dirty.json")))
    t.check("appointment 脏数据拦截", not r["ok"])
    t.check("appointment 拦截时序倒挂",
            any("顺序" in x or "时长" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s06_appointment._validate_appointment(
        {"customer_id": 1, "provider_id": 1, "service_id": 1,
         "start_datetime": "2026-11-10 09:00",
         "end_datetime": "2026-11-10 14:00", "status": "booked"})
    t.check("appointment 拦截超长时段（5h>240min）", not r["ok"],
            str(_fail_msgs(r)))
    r = s06_appointment._validate_calendar(c.load_json(_ex("calendar.json")))
    t.check("calendar 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("calendar overlap_count=0", r["overlap_count"] == 0,
            str(r["overlap_count"]))
    r = s06_appointment._validate_calendar(c.load_json(_ex("calendar_dirty.json")))
    t.check("calendar 脏数据拦截（双重预订）", not r["ok"])
    t.check("calendar overlap_count=1", r["overlap_count"] == 1,
            str(r["overlap_count"]))
    # 缓冲边界：10:00 结束、10:05 开始恰好通过
    r = s06_appointment._validate_calendar({"events": [
        {"id": 1, "start": "2026-11-10 09:00", "end": "2026-11-10 10:00"},
        {"id": 2, "start": "2026-11-10 10:05", "end": "2026-11-10 11:00"}]})
    t.check("calendar 缓冲边界 5min 恰好通过", r["ok"], str(_fail_msgs(r)))
    r = s06_appointment._validate_calendar({"events": [
        {"id": 1, "start": "2026-11-10 09:00", "end": "2026-11-10 10:00"},
        {"id": 2, "start": "2026-11-10 10:04", "end": "2026-11-10 11:00"}]})
    t.check("calendar 缓冲内 4min 被拦截", not r["ok"], str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S07 交易状态编排")
    r = s07_workflow._validate_state(c.load_json(_ex("state.json")))
    t.check("state 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("state event_count=4", r["event_count"] == 4, str(r["event_count"]))
    r = s07_workflow._validate_state(c.load_json(_ex("state_dirty.json")))
    t.check("state 脏数据拦截（终态挂后续动作）", not r["ok"])
    t.check("state 拦截 completed+ship 与 refunded+recapture",
            any("终态" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    r = s07_workflow._validate_transition(c.load_json(_ex("transition.json")))
    t.check("transition 干净通过（processing→succeeded）", r["ok"],
            str(_fail_msgs(r)))
    r = s07_workflow._validate_transition(c.load_json(_ex("transition_dirty.json")))
    t.check("transition 脏数据拦截（refunded→captured）", not r["ok"])
    t.check("transition 拦截终态迁移",
            any("终态" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))
    # 合法边：captured 族不在表内，succeeded→partially_refunded 合法
    r = s07_workflow._validate_transition({"kind": "payment",
                                           "from_status": "succeeded",
                                           "to_status": "partially_refunded"})
    t.check("transition succeeded→partially_refunded 合法", r["ok"],
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S08 收入数据接口")
    r = s08_revenue._validate_events(c.load_json(_ex("events.json")))
    t.check("events 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("events event_count=3", r["event_count"] == 3, str(r["event_count"]))
    t.check("events total_amount=313800",
            abs(r["total_amount"] - 313800.0) < 0.01, str(r["total_amount"]))
    r = s08_revenue._validate_events(c.load_json(_ex("events_dirty.json")))
    t.check("events 脏数据拦截", not r["ok"])
    t.check("events 拦截类型越界", any("类型" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("events 拦截负金额", any("金额非负" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("events 拦截时序倒退", any("时序" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s08_revenue._validate_webhook(c.load_json(_ex("webhook.json")))
    t.check("webhook 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s08_revenue._validate_webhook(c.load_json(_ex("webhook_dirty.json")))
    t.check("webhook 脏数据拦截", not r["ok"])
    t.check("webhook 拦截重试越界", any("重试" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("webhook 拦截高危回调无审批",
            any("审批" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("T6 契约")
    t.check("8 技能登记", len(contracts.skill_names()) == 8,
            str(contracts.skill_names()))
    total_actions = sum(len(contracts.actions(s)) for s in contracts.skill_names())
    t.check("17 动作登记", total_actions == 17, str(total_actions))
    for s in contracts.skill_names():
        ent = contracts.get(s)
        for a in contracts.actions(s):
            vi = contracts.validate_input(s, a, {})
            t.check(f"{s}/{a} 输入契约拒绝空对象", not vi["ok"], str(vi["errors"]))
    vo = contracts.validate_output("order", "order",
                                   s02_order._validate_order(
                                       c.load_json(_ex("order.json"))))
    t.check("输出契约校验干净产出通过", vo["ok"], str(vo["errors"]))
    vo = contracts.validate_output("order", "order", {"ok": True})
    t.check("输出契约拒绝缺 checks", not vo["ok"], str(vo["errors"]))

    # ------------------------------------------------------------------ #
    t.section("T7 对抗评审")
    good_packet = {"skill": "payment", "action": "refund",
                   "result": s04_payment._validate_refund(
                       c.load_json(_ex("refund.json")))}
    rev = review.review_packet(good_packet)
    t.check("评审通过有效产出", rev["verdict"] == "PASS", str(rev.get("issues")))

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"ok": True, "checks": [],
                                           "summary": "用 api_key sk_live_x 调网关"}})
    t.check("评审拦截凭据外泄", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "credential_leak",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"refund_count": 1, "checks": [],
                                           "summary": "我直接退款给客户"}})
    t.check("评审拦截越权执行扣款/退款", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "unauthorized_exec",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"invoice_count": 1, "checks": [],
                                           "summary": "这笔要计入财务报表"}})
    t.check("评审拦截越界到财务报表", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "scope_overlap",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"summary": "稍后补充"}})
    t.check("评审拦截无具体工件", rev["verdict"] == "FAIL"
            and rev["failure_category"] == "artifact_not_concrete",
            f"category={rev['failure_category']}")

    rev = review.review_packet({"skill": "", "action": "",
                                "result": {"refund_count": 1, "checks": [],
                                           "summary": "退款需人工授权后执行",
                                           "handoff": "业务负责人"}})
    t.check("已声明 handoff 的执行类产出通过", rev["verdict"] == "PASS",
            str(rev.get("issues")))

    # ------------------------------------------------------------------ #
    t.section("T8 案例库")
    lst = cases.list_cases()
    t.check("案例列表 2 个", len(lst) == 2, str([x["case_id"] for x in lst]))
    for cid in ("order-refund-dispute", "subscription-usage-dispute"):
        vc = cases.validate_case(cid)
        t.check(f"{cid} 结构通过", vc["ok"],
                str([x["msg"] for x in vc["checks"] if not x["ok"]]))
    merged = cases.resolve_thresholds("order-refund-dispute")
    t.check("案例阈值可覆盖全局",
            merged["order"].get("refund_requires_authorization_ratio") == 0.2,
            str(merged["order"].get("refund_requires_authorization_ratio")))
    t.check("案例覆盖不破坏全局键",
            merged["payment"]["amount_min"] == 50,
            str(merged["payment"].get("amount_min")))

    # ------------------------------------------------------------------ #
    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("catalog 状态白名单外置", len(th["catalog"]["product_status"]) == 4)
    t.check("order 支付状态白名单外置", len(th["order"]["payment_status"]) == 10)
    t.check("billing 计费模型外置", len(th["billing"]["charge_models"]) == 6)
    t.check("billing 聚合类型外置", len(th["billing"]["aggregation_types"]) == 7)
    t.check("payment 状态白名单外置", len(th["payment"]["pi_status"]) == 7)
    t.check("payment 退款比例上限外置", th["payment"]["refund_ratio_max"] == 1.0)
    t.check("signature 添加角色外置", len(th["signature"]["recipient_roles"]) == 5)
    t.check("appointment 时长上限外置", th["appointment"]["max_duration_min"] == 240)
    t.check("appointment 缓冲外置", th["appointment"]["overlap_buffer_min"] == 5)
    t.check("event 类型外置", len(th["event"]["event_types"]) == 9)
    t.check("review 红线词外置", bool(th["review"]["credential_words"])
            and bool(th["review"]["execution_words"])
            and bool(th["review"]["scope_terms"]))
    t.check("阈值文件存在", os.path.exists(c.thresholds_path()))

    # ------------------------------------------------------------------ #
    t.section("harness 确定性验证器")
    tmp = tempfile.mkdtemp(prefix="r14_harness_")
    good_path = os.path.join(tmp, "refund.json")
    c.write_json(good_path, c.load_json(_ex("refund.json")))
    h = harness.run_validator("refund", good_path)
    t.check("harness refund 门禁 PASS", h["ok"] and h["grade"] == "PASS",
            str(h.get("checks"))[:200])
    h = harness.run_validator("refund", _ex("refund_dirty.json"))
    t.check("harness refund 脏数据 FAIL", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("nope", good_path)
    t.check("harness 未知门禁拦截", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("refund", os.path.join(tmp, "missing.json"))
    t.check("harness 缺文件拦截", not h["ok"] and h["grade"] == "FAIL")
    t.check("17 个门禁全部登记", len(harness._VALIDATORS) == 17,
            str(len(harness._VALIDATORS)))
    code, rl = run_agent("harness", "runlog", "--n", "5")
    t.check("harness runlog 可读", code == 0 or "runlog" in rl, str(rl)[:120])

    # ------------------------------------------------------------------ #
    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0
            and len(demo.get("demo_artifacts", {})) == 5,
            str(demo.get("demo_artifacts", {}).keys()))
    code, _ = run_agent("case", "get", "--case", "order-refund-dispute")
    t.check("CLI case get 正常", code == 0)
    code, ctr = run_agent("contract", "list")
    t.check("CLI contract list 正常", code == 0 and len(ctr.get("contracts", [])) == 8)

    # ------------------------------------------------------------------ #
    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(_ex("refund.json"), "data", note="")
    task = protocol.Task(title="这单客户要退款",
                         owner="r14",
                         intent="客户申请退款，帮我看这笔退款合不合规、能不能直接退",
                         inputs=[inp], acceptance=["refund 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    t.check("run_task 路由到 payment", res.get("skill") == "payment",
            str(res.get("skill")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 2, str(len(done.outputs)))

    # 意图路由：签署→signature
    inp2 = protocol.Port(_ex("signing.json"), "data", note="")
    task2 = protocol.Task(title="合同签署审计", owner="r14",
                          intent="帮我看看这份电子签合同签完了没，有没有人没签",
                          inputs=[inp2], acceptance=["signature 门禁通过"])
    ws.create_task(task2)
    code, res2 = run_agent("run", "--task", task2.task_id)
    t.check("意图路由 签署→signature", res2.get("skill") == "signature",
            str(res2.get("skill")))

    # ------------------------------------------------------------------ #
    t.section("T15 verify_loop 闭环矩阵")
    matrix = verify_loop.run_all()
    bad_rows = [r["skill"] + ":" + ",".join(r.get("notes", []))
                for r in matrix["matrix"] if not r["ok"]]
    t.check("闭环 34 行全绿", matrix["ok"],
            f"passed={matrix['passed']}/{matrix['total']} bad={bad_rows[:3]}")
    t.check("闭环 verdict=PASS", matrix["verdict"] == "PASS")
    n_clean = sum(1 for r in matrix["matrix"] if r["expect_ok"])
    n_dirty = sum(1 for r in matrix["matrix"] if not r["expect_ok"])
    t.check("闭环 17 干净 + 17 脏", n_clean == 17 and n_dirty == 17,
            f"clean={n_clean} dirty={n_dirty}")

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R14 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
