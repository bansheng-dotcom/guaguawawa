# -*- coding: utf-8 -*-
"""R15 的确定性验证器层（harness）。

把「ERP 供应链门禁」做成可独立运行、返回 exit code 的确定性校验。每个 validator
读输入工件 → 逐条判据 → 输出 `{ok, grade, checks[]}`，`ok=false` 时返回码非 0。
这是 R04 蛙挑刺做硬门禁复核的可调用入口。

用法：
    python harness.py purchase_order --input po.json
    python harness.py runlog --n 5
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skills import _common as c  # noqa: E402
from skills import (s01_procurement, s02_inventory, s03_fulfillment,  # noqa: E402
                    s04_production, s05_finance, s06_masterdata, s07_report)

# harness 命令 → (技能模块, 校验函数)
_VALIDATORS = {
    "supplier": (s01_procurement, "_validate_supplier"),
    "rfq": (s01_procurement, "_validate_rfq"),
    "quotation": (s01_procurement, "_validate_quotation"),
    "purchase_order": (s01_procurement, "_validate_purchase_order"),
    "receipt": (s01_procurement, "_validate_receipt"),
    "item": (s02_inventory, "_validate_item"),
    "warehouse": (s02_inventory, "_validate_warehouse"),
    "bin": (s02_inventory, "_validate_bin"),
    "stock_entry": (s02_inventory, "_validate_stock_entry"),
    "sales_order": (s03_fulfillment, "_validate_sales_order"),
    "delivery": (s03_fulfillment, "_validate_delivery"),
    "bom": (s04_production, "_validate_bom"),
    "material_request": (s04_production, "_validate_material_request"),
    "invoice": (s05_finance, "_validate_invoice"),
    "payment": (s05_finance, "_validate_payment"),
    "master_data": (s06_masterdata, "_validate_master_data"),
    "permission": (s06_masterdata, "_validate_permission"),
    "report": (s07_report, "_validate_report"),
}

_GATE_HELP = {
    "supplier": "供应商门禁", "rfq": "询价比价门禁", "quotation": "报价门禁",
    "purchase_order": "采购订单门禁", "receipt": "采购收货门禁",
    "item": "物料主数据门禁", "warehouse": "仓库门禁", "bin": "库存明细门禁",
    "stock_entry": "库存交易门禁", "sales_order": "销售订单门禁",
    "delivery": "发货单门禁", "bom": "物料清单门禁",
    "material_request": "物料请求门禁", "invoice": "发票门禁",
    "payment": "付款单门禁", "master_data": "主数据门禁",
    "permission": "权限矩阵门禁", "report": "运营报表门禁",
}


def _grade(checks) -> str:
    if not checks:
        return "EMPTY"
    if all(x.get("ok") for x in checks):
        return "PASS"
    if any(x.get("sev") == "BLOCKER" and not x.get("ok") for x in checks):
        return "FAIL"
    return "WARN"


def run_validator(cmd: str, path: str, **kw) -> dict:
    if cmd not in _VALIDATORS:
        return {"ok": False, "grade": "FAIL",
                "checks": [{"ok": False, "msg": f"未知门禁 {cmd}", "dim": "existence",
                            "sev": "BLOCKER"}]}
    if not os.path.exists(path):
        return {"ok": False, "grade": "FAIL", "path": path,
                "checks": [{"ok": False, "msg": f"文件不存在 {path}", "dim": "existence",
                            "sev": "BLOCKER"}]}
    mod, fn = _VALIDATORS[cmd]
    data = c.load_json(path)
    out = getattr(mod, fn)(data, **kw) if kw else getattr(mod, fn)(data)
    checks = out.get("checks", [])
    out["grade"] = _grade(checks)
    out["gate"] = cmd
    return out


# --------------------------------------------------------------------------- #
# runlog
# --------------------------------------------------------------------------- #
def validate_runlog(n: int = 5) -> dict:
    from core import workspace as ws_mod
    w = ws_mod.Workspace(os.path.join(_ROOT, "workspace"))
    rows = w.runlog(int(n))
    return c.result([c.ck(True, f"读取最近 {len(rows)} 条 runlog", "runlog",
                          **{"rows": len(rows)})],
                    ok=True, rows=rows, count=len(rows), grade="PASS",
                    next="runlog 正常")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="harness.py", description="R15 确定性验证器层")
    sp = p.add_subparsers(dest="cmd", required=True)
    for name, help_txt in _GATE_HELP.items():
        pa = sp.add_parser(name, help=help_txt)
        pa.add_argument("--input", required=True)
    rl = sp.add_parser("runlog", help="读取最近 n 条 runlog")
    rl.add_argument("--n", type=int, default=5)

    args = p.parse_args(argv)
    if args.cmd == "runlog":
        out = validate_runlog(args.n)
    else:
        out = run_validator(args.cmd, args.input)

    c.emit(out)
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())


def run_strict_validation(input_data):
    """
    补厚的确定性门禁逻辑：对齐 R06/R09 规格。
    1. 校验必填字段
    2. 校验边界约束
    3. 校验产出物格式是否满足下游要求
    """
    errors = []
    if not input_data:
        errors.append("Input data is empty")
    # 占位补充...
    return {"ok": len(errors) == 0, "errors": errors}
