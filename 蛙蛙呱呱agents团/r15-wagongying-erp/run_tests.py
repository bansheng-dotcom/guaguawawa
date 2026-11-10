#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R15 端到端回归测试：把 SOP 的 T10 验收脚本化。

覆盖：manifest / 7 技能 18 动作（含脏数据·越界·伪造结论必须 FAIL）/ 契约(T6) /
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
REPO_ROOT = os.path.dirname(AGENTS)
for p in (HERE, AGENTS, REPO_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

# Windows 中文控制台默认 GBK，直接 print 中文会乱码/抛错（R07 踩坑，全角色同款）。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from skills import (s01_procurement, s02_inventory, s03_fulfillment,  # noqa: E402
                    s04_production, s05_finance, s06_masterdata, s07_report)
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
    t.check("7 个技能", len(m.get("skills", [])) == 7, str(len(m.get("skills", []))))
    t.check("角色 r15", m.get("role") == "r15", str(m.get("role")))
    t.check("输入端口 order/sop",
            m.get("inputs") == ["order", "sop"], str(m.get("inputs")))
    t.check("输出端口 purchase_order/inventory_ledger",
            m.get("outputs") == ["purchase_order", "inventory_ledger"],
            str(m.get("outputs")))
    t.check("7 个能力域", len(m.get("capabilities", [])) == 7,
            str(len(m.get("capabilities", []))))

    # ------------------------------------------------------------------ #
    t.section("S01 采购与供应商")
    r = s01_procurement._validate_supplier(c.load_json(_ex("supplier.json")))
    t.check("supplier 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("supplier_count=2", r["supplier_count"] == 2, str(r["supplier_count"]))
    r = s01_procurement._validate_supplier(c.load_json(_ex("supplier_dirty.json")))
    t.check("supplier 脏数据拦截", not r["ok"])
    t.check("supplier 拦截类型越界", any("类型" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("supplier 拦截超长账期", any("账期" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s01_procurement._validate_rfq(c.load_json(_ex("rfq.json")))
    t.check("rfq 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s01_procurement._validate_rfq(c.load_json(_ex("rfq_dirty.json")))
    t.check("rfq 脏数据拦截", not r["ok"])
    t.check("rfq 拦截比价家数不足", any("家数" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s01_procurement._validate_quotation(c.load_json(_ex("quotation.json")))
    t.check("quotation 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("quotation total 实算=700", r["total"] == 700.0, str(r["total"]))
    r = s01_procurement._validate_quotation(c.load_json(_ex("quotation_dirty.json")))
    t.check("quotation 脏数据拦截", not r["ok"])
    t.check("quotation 拦截恒等式不符", any("恒等式" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s01_procurement._validate_purchase_order(c.load_json(_ex("purchase_order.json")))
    t.check("purchase_order 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("po total 实算=700", r["total"] == 700.0, str(r["total"]))
    r = s01_procurement._validate_purchase_order(c.load_json(_ex("purchase_order_dirty.json")))
    t.check("purchase_order 脏数据拦截", not r["ok"])
    t.check("po 拦截时序倒退", any("交货日期" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s01_procurement._validate_receipt(c.load_json(_ex("receipt.json")))
    t.check("receipt 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s01_procurement._validate_receipt(c.load_json(_ex("receipt_dirty.json")))
    t.check("receipt 脏数据拦截", not r["ok"])
    t.check("receipt 拦截超收", any("超收" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S02 库存与仓库")
    r = s02_inventory._validate_item(c.load_json(_ex("item.json")))
    t.check("item 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("item_count=2", r["item_count"] == 2, str(r["item_count"]))
    r = s02_inventory._validate_item(c.load_json(_ex("item_dirty.json")))
    t.check("item 脏数据拦截", not r["ok"])
    t.check("item 拦截单位越界", any("单位" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s02_inventory._validate_warehouse(c.load_json(_ex("warehouse.json")))
    t.check("warehouse 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s02_inventory._validate_warehouse(c.load_json(_ex("warehouse_dirty.json")))
    t.check("warehouse 脏数据拦截", not r["ok"])
    t.check("warehouse 拦截缺名", any("仓库名" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s02_inventory._validate_bin(c.load_json(_ex("bin.json")))
    t.check("bin 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("bin stock_value=110", r["stock_value"] == 110.0, str(r["stock_value"]))
    r = s02_inventory._validate_bin(c.load_json(_ex("bin_dirty.json")))
    t.check("bin 脏数据拦截", not r["ok"])
    t.check("bin 拦截负库存", any("负库存" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    r = s02_inventory._validate_stock_entry(c.load_json(_ex("stock_entry.json")))
    t.check("stock_entry 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s02_inventory._validate_stock_entry(c.load_json(_ex("stock_entry_dirty.json")))
    t.check("stock_entry 脏数据拦截", not r["ok"])
    t.check("stock_entry 拦截用途越界", any("用途" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S03 销售与履约记录")
    r = s03_fulfillment._validate_sales_order(c.load_json(_ex("sales_order.json")))
    t.check("sales_order 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("so total 实算=880", r["total"] == 880.0, str(r["total"]))
    r = s03_fulfillment._validate_sales_order(c.load_json(_ex("sales_order_dirty.json")))
    t.check("sales_order 脏数据拦截", not r["ok"])
    t.check("so 拦截恒等式不符", any("恒等式" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s03_fulfillment._validate_delivery(c.load_json(_ex("delivery.json")))
    t.check("delivery 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s03_fulfillment._validate_delivery(c.load_json(_ex("delivery_dirty.json")))
    t.check("delivery 脏数据拦截", not r["ok"])
    t.check("delivery 拦截超发", any("超发" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S04 生产/服务资源")
    r = s04_production._validate_bom(c.load_json(_ex("bom.json")))
    t.check("bom 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("bom 2 行配方", r["line_item_count"] == 2, str(r["line_item_count"]))
    r = s04_production._validate_bom(c.load_json(_ex("bom_dirty.json")))
    t.check("bom 脏数据拦截", not r["ok"])
    t.check("bom 拦截零用量", any("用量" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s04_production._validate_material_request(c.load_json(_ex("material_request.json")))
    t.check("material_request 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s04_production._validate_material_request(c.load_json(_ex("material_request_dirty.json")))
    t.check("material_request 脏数据拦截", not r["ok"])
    t.check("mr 拦截用途越界", any("用途" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S05 ERP 财务业务接口")
    r = s05_finance._validate_invoice(c.load_json(_ex("invoice.json")))
    t.check("invoice 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("invoice total 实算=880", r["total"] == 880.0, str(r["total"]))
    r = s05_finance._validate_invoice(c.load_json(_ex("invoice_dirty.json")))
    t.check("invoice 脏数据拦截", not r["ok"])
    t.check("invoice 拦截恒等式不符", any("恒等式" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s05_finance._validate_payment(c.load_json(_ex("payment.json")))
    t.check("payment 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s05_finance._validate_payment(c.load_json(_ex("payment_dirty.json")))
    t.check("payment 脏数据拦截", not r["ok"])
    t.check("payment 拦截未授权", any("授权" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S06 主数据与权限")
    r = s06_masterdata._validate_master_data(c.load_json(_ex("master_data.json")))
    t.check("master_data 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("master_count=3", r["master_count"] == 3, str(r["master_count"]))
    r = s06_masterdata._validate_master_data(c.load_json(_ex("master_data_dirty.json")))
    t.check("master_data 脏数据拦截", not r["ok"])
    t.check("master_data 拦截编码不合规", any("编码" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    r = s06_masterdata._validate_permission(c.load_json(_ex("permission.json")))
    t.check("permission 干净通过", r["ok"], str(_fail_msgs(r)))
    r = s06_masterdata._validate_permission(c.load_json(_ex("permission_dirty.json")))
    t.check("permission 脏数据拦截", not r["ok"])
    t.check("permission 拦截 SoD 冲突", any("职责分离" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("S07 运营报表")
    r = s07_report._validate_report(c.load_json(_ex("report.json")))
    t.check("report 干净通过", r["ok"], str(_fail_msgs(r)))
    t.check("report kpi_count=1", r["kpi_count"] == 1, str(r["kpi_count"]))
    r = s07_report._validate_report(c.load_json(_ex("report_dirty.json")))
    t.check("report 脏数据拦截", not r["ok"])
    t.check("report 拦截周期口径", any("周期" in x for x in _fail_msgs(r)),
            str(_fail_msgs(r)))
    t.check("report 拦截 KPI 不可复算",
            any("可复算" in x for x in _fail_msgs(r)), str(_fail_msgs(r)))

    # ------------------------------------------------------------------ #
    t.section("T6 契约")
    t.check("18 动作契约登记", sum(len(contracts.actions(s))
                                    for s in contracts.skill_names()) == 18,
            str(sum(len(contracts.actions(s)) for s in contracts.skill_names())))
    v = contracts.validate_output("procurement", "purchase_order",
                                  c.load_json(_ex("purchase_order.json"))
                                  if False else
                                  s01_procurement._validate_purchase_order(
                                      c.load_json(_ex("purchase_order.json"))))
    t.check("采购订单产出契约合规", v["ok"], str(v["errors"]))
    v = contracts.validate_input("finance", "invoice",
                                 {"party": "A"})
    t.check("缺字段输入不合规", not v["ok"], str(v["errors"]))

    # ------------------------------------------------------------------ #
    t.section("T7 对抗评审")
    good = s01_procurement._validate_purchase_order(c.load_json(_ex("purchase_order.json")))
    rp = review.review_packet({"skill": "procurement", "action": "purchase_order",
                               "result": good})
    t.check("干净产出过评审", rp["ok"], str(rp.get("issues")))
    leaky = {"ok": True, "checks": [], "po_count": 1,
             "narrative": "已直接下单采购并向供应商发起付款",
             "purchase_order": {"id": "X"}}
    rp2 = review.review_packet({"skill": "procurement", "action": "purchase_order",
                                "result": leaky})
    t.check("越权执行拦截", not rp2["ok"]
            and rp2["failure_category"] == "unauthorized_exec", str(rp2))
    t.check("越权 route=writer", rp2["route"] == "writer", str(rp2["route"]))
    # 无任何可交付键/结论：契约缺 report_count/kpi_count，且无 concrete 键
    empty = {"ok": True, "checks": [], "next": "一切正常"}
    rp3 = review.review_packet({"skill": "report", "action": "report", "result": empty})
    t.check("无工件拦截", not rp3["ok"]
            and rp3["failure_category"] == "artifact_not_concrete", str(rp3))

    # ------------------------------------------------------------------ #
    t.section("T8 案例库")
    lst = cases.list_cases()
    t.check("案例列表 >= 2 个", len(lst) >= 2, str([x["case_id"] for x in lst]))
    for cid in ("purchase-over-receipt", "inventory-negative-stock"):
        vc = cases.validate_case(cid)
        t.check(f"{cid} 结构通过", vc["ok"],
                str([x["msg"] for x in vc["checks"] if not x["ok"]]))
    merged = cases.resolve_thresholds("purchase-over-receipt")
    t.check("案例阈值可覆盖全局",
            merged["procurement"].get("over_receipt_tolerance") == 0.02,
            str(merged["procurement"].get("over_receipt_tolerance")))
    t.check("案例覆盖不破坏全局键",
            merged["inventory"]["allow_negative_stock"] is False,
            str(merged["inventory"].get("allow_negative_stock")))

    # ------------------------------------------------------------------ #
    t.section("T9 阈值外置")
    th = c.load_thresholds()
    t.check("采购订单状态白名单 10 态外置", len(th["procurement"]["po_status"]) == 10)
    t.check("供应商类型外置", len(th["procurement"]["supplier_types"]) == 3)
    t.check("库存单位白名单外置", len(th["inventory"]["uom_whitelist"]) >= 9)
    t.check("计价方法外置", len(th["inventory"]["valuation_methods"]) == 4)
    t.check("库存交易用途外置", len(th["inventory"]["stock_entry_types"]) == 6)
    t.check("销售订单状态外置", len(th["fulfillment"]["so_status"]) == 9)
    t.check("物料请求状态外置", len(th["production"]["mr_status"]) == 11)
    t.check("发票状态外置", len(th["finance"]["invoice_status"]) == 9)
    t.check("主数据类型外置", len(th["masterdata"]["master_types"]) == 6)
    t.check("报表类型外置", len(th["report"]["report_types"]) == 4)
    t.check("review 红线词外置", bool(th["review"]["credential_words"])
            and bool(th["review"]["execution_words"])
            and bool(th["review"]["scope_terms"]))
    t.check("阈值文件存在", os.path.exists(c.thresholds_path()))

    # ------------------------------------------------------------------ #
    t.section("harness 确定性验证器")
    tmp = tempfile.mkdtemp(prefix="r15_harness_")
    good_path = os.path.join(tmp, "purchase_order.json")
    c.write_json(good_path, c.load_json(_ex("purchase_order.json")))
    h = harness.run_validator("purchase_order", good_path)
    t.check("harness purchase_order 门禁 PASS", h["ok"] and h["grade"] == "PASS",
            str(h.get("checks"))[:200])
    h = harness.run_validator("purchase_order", _ex("purchase_order_dirty.json"))
    t.check("harness 脏数据 FAIL", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("nope", good_path)
    t.check("harness 未知门禁拦截", not h["ok"] and h["grade"] == "FAIL")
    h = harness.run_validator("purchase_order", os.path.join(tmp, "missing.json"))
    t.check("harness 缺文件拦截", not h["ok"] and h["grade"] == "FAIL")
    t.check("18 个门禁全部登记", len(harness._VALIDATORS) == 18,
            str(len(harness._VALIDATORS)))
    code, rl = run_agent("harness", "runlog", "--n", "5")
    t.check("harness runlog 可读", code == 0 or "runlog" in rl, str(rl)[:120])

    # ------------------------------------------------------------------ #
    t.section("demo / CLI 端到端")
    code, demo = run_agent("demo")
    t.check("demo 生成示例工件", code == 0
            and len(demo.get("demo_artifacts", {})) == 5,
            str(demo.get("demo_artifacts", {}).keys()))
    code, _ = run_agent("case", "get", "--case", "purchase-over-receipt")
    t.check("CLI case get 正常", code == 0)
    code, ctr = run_agent("contract", "list")
    t.check("CLI contract list 正常", code == 0 and len(ctr.get("contracts", [])) == 7)

    # ------------------------------------------------------------------ #
    t.section("run_task 协作入口")
    from core import workspace, protocol
    ws = workspace.Workspace(os.path.join(AGENTS, "workspace"))
    inp = protocol.Port(_ex("purchase_order.json"), "data", note="")
    task = protocol.Task(title="补一张采购单",
                         owner="r15",
                         intent="这单货要补采购，帮我看这张采购订单合不合规、能不能下单",
                         inputs=[inp], acceptance=["purchase_order 门禁通过"])
    ws.create_task(task)
    code, res = run_agent("run", "--task", task.task_id)
    t.check("run_task 返回 ok", code == 0 and res.get("ok"), str(res.get("error")))
    t.check("run_task 路由到 procurement", res.get("skill") == "procurement",
            str(res.get("skill")))
    done = ws.read_task(task.task_id)
    t.check("任务状态 done", done.status == "done")
    t.check("任务写回产物", len(done.outputs) >= 2, str(len(done.outputs)))

    # 意图路由：库存→inventory/bin
    inp2 = protocol.Port(_ex("bin.json"), "data", note="")
    task2 = protocol.Task(title="库存台账核查", owner="r15",
                          intent="帮我看下当前库存明细，有没有负库存",
                          inputs=[inp2], acceptance=["bin 门禁通过"])
    ws.create_task(task2)
    code, res2 = run_agent("run", "--task", task2.task_id)
    t.check("意图路由 库存→inventory", res2.get("skill") == "inventory",
            str(res2.get("skill")))

    # ------------------------------------------------------------------ #
    t.section("T15 verify_loop 闭环矩阵")
    matrix = verify_loop.run_all()
    bad_rows = [r["skill"] + ":" + ",".join(r.get("notes", []))
                for r in matrix["matrix"] if not r["ok"]]
    t.check("闭环 36 行全绿", matrix["ok"],
            f"passed={matrix['passed']}/{matrix['total']} bad={bad_rows[:3]}")
    t.check("闭环 verdict=PASS", matrix["verdict"] == "PASS")
    n_clean = sum(1 for r in matrix["matrix"] if r["expect_ok"])
    n_dirty = sum(1 for r in matrix["matrix"] if not r["expect_ok"])
    t.check("闭环 18 干净 + 18 脏", n_clean == 18 and n_dirty == 18,
            f"clean={n_clean} dirty={n_dirty}")

    print(f"\n{'=' * 60}")
    print(f"通过 {t.passed} / {t.passed + t.failed}")
    if t.failed:
        print("失败项：")
        for name, detail in t.errors:
            print(f"  - {name}: {detail}")
        return 1
    print("全绿 · R15 端到端验收通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
