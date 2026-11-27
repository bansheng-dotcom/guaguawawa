#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R14 交易机制：订单状态机 + 幂等 + 对账（T12）。

升级方案 §15 对 R14 的要求是「状态机、幂等、对账」，验收「3 条交易链」。
本模块不接真实支付，只用确定性账本把三件事跑通：

    1. 状态机：created → paid → fulfilled → refunded / closed，非法迁移拒绝；
    2. 幂等：同一幂等键重复请求只生效一次，绝不重复扣款；
    3. 对账：订单与支付流水比对，差异分类（缺失/孤儿/重复/金额/状态）。

门禁（确定性）：
    T01_ILLEGAL_TRANSITION      不允许的状态迁移（如未支付就发货）
    T02_MISSING_IDEMPOTENCY_KEY 资金动作缺幂等键
    T03_DUPLICATE_CHARGE        同一幂等键换了金额/订单地重放（疑似重复扣款）
    T04_AMOUNT_MISMATCH         金额与订单不符 / 超退

对账差异分类：
    R01_MISSING_PAYMENT / R02_ORPHAN_PAYMENT / R03_DUPLICATE_PAYMENT /
    R04_AMOUNT_MISMATCH / R05_STATUS_MISMATCH

用法：
    python commerce_fsm.py run    --input examples/chain.json
    python commerce_fsm.py recon  --input examples/recon.json
    python commerce_fsm.py check  --case misuse/illegal-transition.json
    python commerce_fsm.py goldens
"""
from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))

ERRORS = {
    "T01_ILLEGAL_TRANSITION": "非法状态迁移（前置状态不成立）",
    "T02_MISSING_IDEMPOTENCY_KEY": "资金动作缺幂等键，重放会重复扣款",
    "T03_DUPLICATE_CHARGE": "同一幂等键换了金额/订单重放，疑似重复扣款",
    "T04_AMOUNT_MISMATCH": "金额与订单不符或超过可退金额",
}

STATES = ("created", "paid", "fulfilled", "refunded", "closed", "cancelled")
TRANSITIONS = {
    "created": {"pay": "paid", "cancel": "cancelled"},
    "paid": {"fulfill": "fulfilled", "refund": "refunded"},
    "fulfilled": {"refund": "refunded", "close": "closed"},
    "refunded": {"close": "closed"},
    "closed": {},
    "cancelled": {},
}


def _money(value: Any) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"非法金额：{value!r}")
    if not d.is_finite() or d < 0:
        raise ValueError(f"非法金额：{value!r}")
    return d.quantize(Decimal("0.01"))


class OrderBook:
    """确定性订单账本：状态机 + 幂等键 + 资金流水。"""

    def __init__(self) -> None:
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.ledger: Dict[str, Dict[str, Any]] = {}
        self.violations: List[Dict[str, str]] = []

    # ------------------------------------------------------------------ #
    def _viol(self, code: str, detail: str) -> None:
        self.violations.append({"code": code, "msg": ERRORS[code], "detail": detail})

    def _seen(self, key: str) -> Optional[Dict[str, Any]]:
        return self.ledger.get(key)

    def _ok(self, order_id: str, dedup: bool = False, **extra) -> Dict[str, Any]:
        order = self.orders.get(order_id) or {}
        out = {"ok": True, "order_id": order_id, "status": order.get("status"),
               "deduplicated": dedup}
        out.update(extra)
        return out

    def _fail(self, order_id: str, code: str, detail: str) -> Dict[str, Any]:
        self._viol(code, detail)
        return {"ok": False, "order_id": order_id,
                "status": (self.orders.get(order_id) or {}).get("status"),
                "deduplicated": False,
                "violations": [{"code": code}]}

    # ------------------------------------------------------------------ #
    def create(self, order_id: str, amount: Any) -> Dict[str, Any]:
        if order_id in self.orders:
            return self._ok(order_id, dedup=True)
        amt = _money(amount)
        self.orders[order_id] = {"order_id": order_id, "amount": amt,
                                 "refunded": Decimal("0.00"), "status": "created",
                                 "history": [{"event": "create", "to": "created"}]}
        return self._ok(order_id, amount=str(amt))

    def _move(self, order_id: str, event: str, key: str) -> Dict[str, Any]:
        order = self.orders.get(order_id)
        if not order:
            return self._fail(order_id, "T01_ILLEGAL_TRANSITION", f"{order_id} 不存在")
        nxt = TRANSITIONS.get(order["status"], {}).get(event)
        if not nxt:
            return self._fail(order_id, "T01_ILLEGAL_TRANSITION",
                              f"{order['status']} 不允许 {event}")
        if not str(key or "").strip():
            return self._fail(order_id, "T02_MISSING_IDEMPOTENCY_KEY", f"{event} 缺 key")
        seen = self._seen(key)
        if seen is not None:
            return self._ok(order_id, dedup=True, replayed=seen.get("event"))
        order["status"] = nxt
        order["history"].append({"event": event, "to": nxt, "key": key})
        self.ledger[key] = {"order_id": order_id, "event": event,
                            "amount": str(order["amount"])}
        return self._ok(order_id, event=event, to=nxt)

    # ------------------------------------------------------------------ #
    def charge(self, order_id: str, amount: Any, key: str) -> Dict[str, Any]:
        order = self.orders.get(order_id)
        if not order:
            return self._fail(order_id, "T01_ILLEGAL_TRANSITION", f"{order_id} 不存在")
        if not str(key or "").strip():
            return self._fail(order_id, "T02_MISSING_IDEMPOTENCY_KEY", "charge 缺 key")
        seen = self._seen(key)
        if seen is not None:
            try:
                same_amount = _money(amount) == _money(seen.get("amount"))
            except ValueError:
                same_amount = False
            if seen.get("order_id") == order_id and same_amount:
                return self._ok(order_id, dedup=True, charged="0.00")
            return self._fail(order_id, "T03_DUPLICATE_CHARGE",
                              f"{key} 已用于 {seen.get('order_id')}/{seen.get('amount')}")
        if order["status"] != "created":
            return self._fail(order_id, "T01_ILLEGAL_TRANSITION",
                              f"{order['status']} 不允许 charge")
        amt = _money(amount)
        if amt != order["amount"]:
            return self._fail(order_id, "T04_AMOUNT_MISMATCH",
                              f"支付 {amt} != 订单 {order['amount']}")
        order["status"] = "paid"
        order["history"].append({"event": "pay", "to": "paid", "key": key})
        self.ledger[key] = {"order_id": order_id, "event": "pay", "amount": str(amt)}
        return self._ok(order_id, event="pay", to="paid", charged=str(amt))

    def refund(self, order_id: str, amount: Any, key: str) -> Dict[str, Any]:
        order = self.orders.get(order_id)
        if not order:
            return self._fail(order_id, "T01_ILLEGAL_TRANSITION", f"{order_id} 不存在")
        if not str(key or "").strip():
            return self._fail(order_id, "T02_MISSING_IDEMPOTENCY_KEY", "refund 缺 key")
        seen = self._seen(key)
        if seen is not None:
            return self._ok(order_id, dedup=True, refunded="0.00")
        if order["status"] not in ("paid", "fulfilled"):
            return self._fail(order_id, "T01_ILLEGAL_TRANSITION",
                              f"{order['status']} 不允许 refund")
        amt = _money(amount)
        remain = order["amount"] - order["refunded"]
        if amt > remain:
            return self._fail(order_id, "T04_AMOUNT_MISMATCH",
                              f"退款 {amt} > 可退 {remain}")
        order["refunded"] += amt
        order["status"] = "refunded" if order["refunded"] == order["amount"] else "paid"
        if order["status"] == "refunded":
            order["history"].append({"event": "refund", "to": "refunded", "key": key})
        else:
            order["history"].append({"event": "partial_refund", "to": "paid", "key": key})
        self.ledger[key] = {"order_id": order_id, "event": "refund", "amount": str(amt)}
        return self._ok(order_id, event="refund", refunded=str(amt),
                        total_refunded=str(order["refunded"]))

    def fulfill(self, order_id: str, key: str) -> Dict[str, Any]:
        return self._move(order_id, "fulfill", key)

    def close(self, order_id: str, key: str) -> Dict[str, Any]:
        return self._move(order_id, "close", key)

    def cancel(self, order_id: str, key: str) -> Dict[str, Any]:
        return self._move(order_id, "cancel", key)


# --------------------------------------------------------------------------- #
# 对账
# --------------------------------------------------------------------------- #
RECON_ERRORS = {
    "R01_MISSING_PAYMENT": "订单已支付/履约但没有成功支付流水",
    "R02_ORPHAN_PAYMENT": "支付流水找不到对应订单",
    "R03_DUPLICATE_PAYMENT": "同一订单有多笔成功支付（疑似重复扣款）",
    "R04_AMOUNT_MISMATCH": "订单金额与成功支付合计不一致",
    "R05_STATUS_MISMATCH": "订单状态与支付状态矛盾（未支付却有成功流水等）",
}


def reconcile(orders: List[Dict[str, Any]],
              payments: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_id = {str(o.get("order_id")): o for o in orders}
    paid: Dict[str, List[Dict[str, Any]]] = {}
    classes: Dict[str, List[Dict[str, Any]]] = {k: [] for k in RECON_ERRORS}

    for p in payments:
        oid = str(p.get("order_id"))
        if oid not in by_id:
            classes["R02_ORPHAN_PAYMENT"].append({"payment_id": p.get("payment_id"),
                                                  "order_id": oid,
                                                  "amount": str(p.get("amount"))})
            continue
        if str(p.get("status")) == "success":
            paid.setdefault(oid, []).append(p)

    for oid, o in by_id.items():
        status = str(o.get("status"))
        rows = paid.get(oid, [])
        if status in ("paid", "fulfilled", "refunded") and not rows:
            classes["R01_MISSING_PAYMENT"].append({"order_id": oid, "status": status})
        if status == "created" and rows:
            classes["R05_STATUS_MISMATCH"].append({"order_id": oid, "status": status,
                                                   "payments": len(rows)})
        if len(rows) > 1:
            classes["R03_DUPLICATE_PAYMENT"].append({"order_id": oid,
                                                     "payments": len(rows)})
        if rows:
            total = sum((_money(p.get("amount")) for p in rows), Decimal("0.00"))
            if total != _money(o.get("amount")):
                classes["R04_AMOUNT_MISMATCH"].append(
                    {"order_id": oid, "order_amount": str(_money(o.get("amount"))),
                     "paid_total": str(total)})

    counts = {k: len(v) for k, v in classes.items()}
    total = sum(counts.values())
    return {"ok": total == 0, "classes": classes, "counts": counts,
            "diff_total": total, "orders": len(orders), "payments": len(payments)}


# --------------------------------------------------------------------------- #
# 三条交易链（黄金成品与测试共用）
# --------------------------------------------------------------------------- #
def demo_chains() -> List[Dict[str, Any]]:
    chains: List[Dict[str, Any]] = []

    # 链 1：正常下单 → 支付 → 履约 → 关闭
    b1 = OrderBook()
    steps1 = [b1.create("SO-2001", "99.00"),
              b1.charge("SO-2001", "99.00", "pay-2001"),
              b1.fulfill("SO-2001", "ful-2001"),
              b1.close("SO-2001", "cls-2001")]
    chains.append({"chain": "正常成交", "order_id": "SO-2001", "steps": steps1,
                   "ok": all(s["ok"] for s in steps1)
                         and b1.orders["SO-2001"]["status"] == "closed",
                   "status": b1.orders["SO-2001"]["status"],
                   "violations": b1.violations})

    # 链 2：支付 → 部分退款 → 再退 → 关闭
    b2 = OrderBook()
    steps2 = [b2.create("SO-2002", "199.00"),
              b2.charge("SO-2002", "199.00", "pay-2002"),
              b2.refund("SO-2002", "30.00", "ref-2002-a"),
              b2.refund("SO-2002", "169.00", "ref-2002-b"),
              b2.close("SO-2002", "cls-2002")]
    chains.append({"chain": "全额退款", "order_id": "SO-2002", "steps": steps2,
                   "ok": all(s["ok"] for s in steps2)
                         and b2.orders["SO-2002"]["status"] == "closed",
                   "status": b2.orders["SO-2002"]["status"],
                   "violations": b2.violations})

    # 链 3：网络超时重放（幂等） + 非法迁移 + 重复扣款企图
    b3 = OrderBook()
    steps3 = [
        b3.create("SO-2003", "129.00"),
        b3.fulfill("SO-2003", "ful-early"),          # T01：未支付就发货
        b3.charge("SO-2003", "129.00", "pay-2003"),
        b3.charge("SO-2003", "129.00", "pay-2003"),  # 幂等：不重复扣款
        b3.charge("SO-2003", "88.00", "pay-2003"),   # T03：同键不同金额
        b3.fulfill("SO-2003", "ful-2003"),
        b3.close("SO-2003", "cls-2003"),
    ]
    codes = [v["code"] for v in b3.violations]
    chains.append({"chain": "超时重放 + 非法企图", "order_id": "SO-2003", "steps": steps3,
                   "ok": b3.orders["SO-2003"]["status"] == "closed"
                         and steps3[3]["deduplicated"] is True
                         and "T01_ILLEGAL_TRANSITION" in codes
                         and "T03_DUPLICATE_CHARGE" in codes,
                   "status": b3.orders["SO-2003"]["status"],
                   "violations": b3.violations})
    return chains


RECON_ORDERS = [
    {"order_id": "SO-1001", "amount": "99.00", "status": "paid"},
    {"order_id": "SO-1002", "amount": "199.00", "status": "fulfilled"},
    {"order_id": "SO-1003", "amount": "59.00", "status": "paid"},
    {"order_id": "SO-1004", "amount": "29.00", "status": "created"},
    {"order_id": "SO-1005", "amount": "258.00", "status": "fulfilled"},
]
RECON_PAYMENTS = [
    {"payment_id": "P-01", "order_id": "SO-1001", "amount": "99.00", "status": "success"},
    {"payment_id": "P-02", "order_id": "SO-1002", "amount": "189.00", "status": "success"},
    {"payment_id": "P-03", "order_id": "SO-1004", "amount": "29.00", "status": "success"},
    {"payment_id": "P-04", "order_id": "SO-1005", "amount": "129.00", "status": "success"},
    {"payment_id": "P-05", "order_id": "SO-1005", "amount": "129.00", "status": "success"},
    {"payment_id": "P-06", "order_id": "SO-9999", "amount": "50.00", "status": "success"},
]


# --------------------------------------------------------------------------- #
# 误用样本
# --------------------------------------------------------------------------- #
def apply_ops(ops: List[Dict[str, Any]]) -> Dict[str, Any]:
    book = OrderBook()
    results = []
    for op in ops:
        name = op.get("op")
        oid = op.get("order_id")
        if name == "create":
            results.append(book.create(oid, op.get("amount")))
        elif name == "charge":
            results.append(book.charge(oid, op.get("amount"), op.get("key")))
        elif name == "refund":
            results.append(book.refund(oid, op.get("amount"), op.get("key")))
        elif name == "fulfill":
            results.append(book.fulfill(oid, op.get("key")))
        elif name == "close":
            results.append(book.close(oid, op.get("key")))
        elif name == "cancel":
            results.append(book.cancel(oid, op.get("key")))
    return {"ops": results, "violations": book.violations,
            "orders": {k: {"status": v["status"], "amount": str(v["amount"]),
                           "refunded": str(v["refunded"])}
                       for k, v in book.orders.items()}}


def check_case(path: str) -> Dict[str, Any]:
    spec = json.load(open(path, encoding="utf-8-sig"))
    out = apply_ops(spec.get("ops") or [])
    got = {v["code"] for v in out["violations"]}
    expect = set(spec.get("expect") or [])
    return {"case_id": spec.get("case_id"), "expect": sorted(expect),
            "hit": sorted(expect & got), "rejected": bool(out["violations"]),
            "as_expected": bool(expect) and expect <= got,
            "violations": out["violations"]}


# --------------------------------------------------------------------------- #
# 页面渲染
# --------------------------------------------------------------------------- #
STYLE = """
@page { size: A4; margin: 18mm; }
:root { --paper:#ffffff; --ink:#111827; --muted:#4b5563; --faint:#6b7280; --line:#d1d5db; --accent:#be123c; --accent-soft:#fff1f2; }
* { box-sizing: border-box; }
body { margin:0; padding:32px 20px; background:var(--paper); color:var(--ink);
  font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; line-height:1.65; font-size:15px; }
.sheet { max-width:920px; margin:0 auto; }
h1 { font-size:28px; line-height:1.35; margin:0 0 6px; }
h2 { font-size:20px; line-height:1.4; margin:28px 0 10px; padding-bottom:6px; border-bottom:2px solid var(--accent); }
h3 { font-size:16px; line-height:1.45; margin:18px 0 8px; color:var(--accent); }
p, li, td, th { font-size:14px; }
.meta { font-size:12px; color:var(--muted); margin:0 0 18px; }
.tag { display:inline-block; font-size:12px; padding:1px 8px; border-radius:4px; background:var(--accent-soft); color:var(--accent); }
table { width:100%; border-collapse:collapse; margin:10px 0 16px; }
thead th { background:var(--accent-soft); color:var(--ink); text-align:left; font-size:12.5px; }
th, td { border:1px solid var(--line); padding:6px 8px; vertical-align:top; }
code { font-size:12px; color:var(--muted); word-break:break-all; }
.block { background:#f9fafb; border-left:4px solid var(--accent); padding:10px 14px; margin:12px 0; border-radius:4px; }
figure, .block, section, tr { break-inside: avoid; }
.fig-card { border:1px solid var(--line); border-radius:6px; padding:12px 14px; margin:12px 0; }
.fig-sub { font-size:13px; color:var(--ink); margin:0 0 4px; }
.fig-src, .fig-unit { font-size:12px; color:var(--muted); }
"""


def _page(title: str, body: str) -> str:
    return ("<!doctype html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{title}</title>\n<style>{STYLE}</style>\n</head>\n"
            f"<body data-theme=\"light\">\n<main class=\"sheet\">\n{body}\n</main>\n</body>\n</html>\n")


def render_state_machine_html(chains: List[Dict[str, Any]]) -> str:
    trans = "".join(f"<tr><td>{src}</td><td>{ev}</td><td>{dst}</td></tr>"
                    for src, evs in TRANSITIONS.items() for ev, dst in evs.items())
    chain_rows = "".join(
        f"<tr><td>{c['chain']}</td><td>{c['order_id']}</td><td>{c['status']}</td>"
        f"<td>{len(c['steps'])}</td>"
        f"<td>{'、'.join(sorted({v['code'] for v in c['violations']})) or '—'}</td>"
        f"<td>{'通过' if c['ok'] else '不通过'}</td></tr>" for c in chains)
    detail = "".join(
        "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>".format(
            c["chain"], i + 1, s.get("event") or s.get("to") or "—",
            "幂等跳过" if s.get("deduplicated") else ("成功" if s["ok"] else "拒绝"))
        for c in chains for i, s in enumerate(c["steps"]))
    body = f"""
<h1>订单状态机报告 · 三条交易链</h1>
<p class="meta">出具 R14 蛙交易 ｜ 复核 R04 ｜ 状态机 6 态 ｜ 门禁 T01–T04 ｜
三链结果 {'全通过' if all(c['ok'] for c in chains) else '有失败'}</p>
<h2>1. 结论先行</h2>
<div class="block">三条链分别覆盖正常成交、全额退款（含部分退款）、超时重放；
未支付就发货被 T01 拒绝，同键换金额的重复扣款企图被 T03 拒绝，超时重放被幂等吸收，最终三单均可关闭。</div>
<h2>2. 状态迁移表</h2>
<table>
<thead><tr><th>前置状态</th><th>事件</th><th>目标状态</th></tr></thead>
<tbody>{trans}</tbody>
</table>
<p>未列出的迁移一律拒绝（T01）；资金动作必须有幂等键（T02）。</p>
<h2>3. 三条交易链</h2>
<table>
<thead><tr><th>链</th><th>订单</th><th>终态</th><th>步数</th><th>触发门禁</th><th>结果</th></tr></thead>
<tbody>{chain_rows}</tbody>
</table>
<h2>4. 逐步明细</h2>
<table>
<thead><tr><th>链</th><th>步</th><th>事件/目标</th><th>结果</th></tr></thead>
<tbody>{detail}</tbody>
</table>
<figure class="fig-card">
  <figcaption class="fig-sub">图 1：三条链的步数与门禁触发数（T01×1、T03×1，其余 0）</figcaption>
  <table>
    <thead><tr><th>链</th><th>步数</th></tr></thead>
    <tbody>{''.join(f"<tr><td>{c['chain']}</td><td>{len(c['steps'])}</td></tr>" for c in chains)}</tbody>
  </table>
  <div class="fig-src">来源：commerce_fsm.demo_chains（确定性账本）</div>
  <div class="fig-unit">单位：步；参考线为三条链步数均值（{sum(len(c['steps']) for c in chains) / len(chains):.2f} 步）</div>
</figure>
<h2>5. 幂等与防重复扣款</h2>
<p>同一幂等键重复请求只返回既有结果（<code>deduplicated=true</code>），账本不新增流水；
同键换金额直接判 T03，杜绝“同一次付款被扣两次”。</p>
<h3>5.1 边界</h3>
<p>本报告只覆盖单订单内状态与幂等，不涉及跨订单合并支付与分账。</p>
"""
    return _page("订单状态机报告", body)


def render_reconciliation_html(recon: Dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{code}</td><td>{RECON_ERRORS[code]}</td><td>{len(items)}</td>"
        f"<td>{'、'.join(str(i.get('order_id') or i.get('payment_id')) for i in items) or '—'}</td></tr>"
        for code, items in recon["classes"].items())
    detail = "".join(
        f"<tr><td>{code}</td><td><code>{json.dumps(i, ensure_ascii=False)}</code></td></tr>"
        for code, items in recon["classes"].items() for i in items)
    body = f"""
<h1>交易对账报告 · 订单 vs 支付流水</h1>
<p class="meta">出具 R14 ｜ 订单 {recon['orders']} 笔 ｜ 流水 {recon['payments']} 笔 ｜
差异 {recon['diff_total']} 项 ｜ 对账结论 {'一致' if recon['ok'] else '需处理'}</p>
<h2>1. 结论先行</h2>
<div class="block">本次对账共 {recon['diff_total']} 项差异，覆盖缺失流水、孤儿流水、重复支付、
金额不符、状态矛盾五类；每类都定位到具体订单，可直接派单处理。</div>
<h2>2. 差异分类汇总</h2>
<table>
<thead><tr><th>差异码</th><th>含义</th><th>数量</th><th>对象</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<figure class="fig-card">
  <figcaption class="fig-sub">图 1：五类差异的数量分布（合计 {recon['diff_total']} 项）</figcaption>
  <table>
    <thead><tr><th>差异码</th><th>数量</th></tr></thead>
    <tbody>{''.join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in recon['counts'].items())}</tbody>
  </table>
  <div class="fig-src">来源：commerce_fsm.reconcile（确定性夹具）</div>
  <div class="fig-unit">单位：项；参考线为零差异（均值 0）</div>
</figure>
<h2>3. 差异明细</h2>
<table>
<thead><tr><th>差异码</th><th>对象</th></tr></thead>
<tbody>{detail}</tbody>
</table>
<h2>4. 处置建议</h2>
<table>
<thead><tr><th>差异码</th><th>动作</th><th>负责人</th></tr></thead>
<tbody>
<tr><td>R01_MISSING_PAYMENT</td><td>补拉支付流水或改订单状态</td><td>r14</td></tr>
<tr><td>R02_ORPHAN_PAYMENT</td><td>查下单链路，补单或退款</td><td>r14 + r03</td></tr>
<tr><td>R03_DUPLICATE_PAYMENT</td><td>确认重复扣款后退一笔</td><td>r03</td></tr>
<tr><td>R04_AMOUNT_MISMATCH</td><td>核对优惠/运费后调账</td><td>r03</td></tr>
<tr><td>R05_STATUS_MISMATCH</td><td>回写支付成功状态</td><td>r14</td></tr>
</tbody>
</table>
<h3>4.1 边界</h3>
<p>对账基于本地夹具，不含退款流水与渠道手续费；真实对账需接入渠道账单与时间窗。</p>
"""
    return _page("交易对账报告", body)


def build_goldens(base: Optional[str] = None) -> Dict[str, Any]:
    out_dir = base or os.path.join(HERE, "golden")
    os.makedirs(out_dir, exist_ok=True)
    chains = demo_chains()
    recon = reconcile(RECON_ORDERS, RECON_PAYMENTS)
    with open(os.path.join(out_dir, "commerce-run.json"), "w", encoding="utf-8") as f:
        json.dump({"chains": chains, "reconciliation": recon}, f,
                  ensure_ascii=False, indent=2)
        f.write("\n")
    for name, html in (("commerce-state-machine.html", render_state_machine_html(chains)),
                       ("commerce-reconciliation.html", render_reconciliation_html(recon))):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
    return {"ok": all(c["ok"] for c in chains) and recon["diff_total"] == 5,
            "chains": chains, "reconciliation": recon, "dir": out_dir}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="commerce_fsm.py", description="R14 交易机制")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--input", required=True)
    rc = sub.add_parser("recon")
    rc.add_argument("--input", required=True)
    c = sub.add_parser("check")
    c.add_argument("--case", required=True)
    sub.add_parser("goldens")
    a = ap.parse_args(argv)

    if a.cmd == "goldens":
        out = build_goldens()
        print(json.dumps({"ok": out["ok"],
                          "chains": [{"chain": c["chain"], "ok": c["ok"],
                                      "status": c["status"]} for c in out["chains"]],
                          "diff_total": out["reconciliation"]["diff_total"],
                          "dir": out["dir"]}, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    if a.cmd == "run":
        spec = json.load(open(a.input, encoding="utf-8-sig"))
        out = apply_ops(spec.get("ops") or [])
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if not out["violations"] else 1
    if a.cmd == "recon":
        spec = json.load(open(a.input, encoding="utf-8-sig"))
        out = reconcile(spec.get("orders") or [], spec.get("payments") or [])
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out["ok"] else 1
    out = check_case(a.case)
    out["ok"] = out["as_expected"]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
