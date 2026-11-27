# -*- coding: utf-8 -*-
"""R15 黄金成品生成器：调用本角色真实供应链技能，渲染成独立静态 HTML。

确定性：纯标准库、不联网、不写时间戳（固定 RUN_DATE）。
跑法：python r15-wagongying-erp/golden/build_golden.py
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import sys
from argparse import Namespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROLE_DIR = os.path.dirname(HERE)
AGENTS = os.path.dirname(ROLE_DIR)
REPO_ROOT = os.path.dirname(AGENTS)
for _p in (ROLE_DIR, AGENTS, REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skills import SKILLS  # noqa: E402

ROLE = "r15"
ROLE_TITLE = "R15 蛙供应 · 供应链与 ERP 运营官"
RUN_DATE = "2026-11-27"

_TEMPLATE = """<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@TITLE@ · @ROLE@</title>
<style>
@page { size: A4; margin: 18mm; }
:root { --ink:#1b2430; --muted:#5b6675; --line:#d8dee7; --bg:#f7f8fa;
        --ok:#1a7f4b; --bad:#b3261e; }
* { box-sizing: border-box; }
body { margin:0; padding:28px; background:var(--bg); color:var(--ink);
       font:15px/1.65 "Microsoft YaHei","PingFang SC",sans-serif; }
main { max-width:900px; margin:0 auto; background:#fff; border:1px solid var(--line);
       border-radius:8px; padding:34px 40px; }
h1 { font-size:25px; margin:0 0 6px; }
h2 { font-size:19px; margin:28px 0 10px; padding-bottom:6px;
     border-bottom:2px solid var(--line); }
h3 { font-size:16px; margin:18px 0 8px; }
.meta { color:var(--muted); font-size:13px; }
table { width:100%; border-collapse:collapse; margin:10px 0 6px; font-size:14px; }
thead th { background:#eef1f5; text-align:left; padding:8px 10px;
           border:1px solid var(--line); }
tbody td { padding:7px 10px; border:1px solid var(--line); vertical-align:top; }
.pass { color:var(--ok); font-weight:600; }
.fail { color:var(--bad); font-weight:600; }
.badge { display:inline-block; padding:2px 10px; border-radius:12px; font-size:13px;
         background:#eef1f5; }
.note { background:#fbfbfc; border-left:3px solid var(--line); padding:10px 14px;
        color:var(--muted); }
footer { margin-top:30px; color:var(--muted); font-size:12px; }
</style>
</head>
<body data-theme="light">
<main>
<h1>@TITLE@</h1>
<p class="meta">@ROLE@ · @SUBTITLE@ · 运行日 @DATE@</p>
@BODY@
<footer>本文件由 golden/build_golden.py 调用角色真实技能生成，可复算；R15 不擅自下单/付款。</footer>
</main>
</body>
</html>
"""


def _module(name):
    return next(m for m in SKILLS if m.NAME == name)


def _run_step(step):
    mod = _module(step["skill"])
    if "args" in step:
        out = mod.run(Namespace(**step["args"]))
        src = "args " + json.dumps(step["args"], ensure_ascii=False, sort_keys=True)
        raw = src.encode("utf-8")
    else:
        path = os.path.join(ROLE_DIR, "examples", step["fixture"])
        with open(path, "rb") as f:
            raw = f.read()
        out = mod.run(Namespace(action=step["action"], input=path))
        src = "examples/" + step["fixture"]
    return {"label": step["label"], "skill": step["skill"],
            "action": step.get("action", "args"), "source": src,
            "sha256": hashlib.sha256(raw).hexdigest()[:16],
            "bytes": len(raw), "out": out}


def _fmt(v):
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _fields(out):
    rows = []
    for k, v in out.items():
        if k in ("checks", "next"):
            continue
        if isinstance(v, (bool, int, float, str)):
            text = _fmt(v)
            if len(text) > 160:
                text = text[:160] + "…"
            rows.append((k, text))
        elif isinstance(v, list):
            rows.append((k, f"list · {len(v)} 项"))
        elif isinstance(v, dict):
            rows.append((k, f"object · {len(v)} 键"))
    return rows


def _render(spec, runs):
    esc = html.escape
    blocks = ['<h2>一、输入摘要</h2>',
              '<table><thead><tr><th>步骤</th><th>技能/动作</th><th>夹具</th>'
              '<th>sha256</th><th>字节</th></tr></thead><tbody>']
    for r in runs:
        blocks.append(f'<tr><td>{esc(r["label"])}</td>'
                      f'<td>{esc(r["skill"])}.{esc(r["action"])}</td>'
                      f'<td>{esc(r["source"])}</td><td>{r["sha256"]}</td>'
                      f'<td>{r["bytes"]}</td></tr>')
    blocks.append('</tbody></table>')

    blocks.append('<h2>二、关键输出字段</h2>')
    for r in runs:
        blocks.append(f'<h3>{esc(r["label"])} · {esc(r["skill"])}.{esc(r["action"])}</h3>')
        blocks.append('<table><thead><tr><th>字段</th><th>值</th></tr></thead><tbody>')
        for k, v in _fields(r["out"]):
            blocks.append(f'<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>')
        blocks.append('</tbody></table>')

    blocks.append('<h2>三、门禁结果</h2>')
    blocks.append('<table><thead><tr><th>步骤</th><th>维度</th><th>级别</th>'
                  '<th>结果</th><th>说明</th></tr></thead><tbody>')
    gates = []
    for r in runs:
        for c in r["out"].get("checks", []) or []:
            gates.append((r["label"], str(c.get("dim", "")), str(c.get("sev", "")),
                          "PASS" if c.get("ok") else "FAIL", str(c.get("msg", ""))))
    for g in gates:
        cls = "pass" if g[3] == "PASS" else "fail"
        blocks.append(f'<tr><td>{esc(g[0])}</td><td>{esc(g[1])}</td><td>{esc(g[2])}</td>'
                      f'<td class="{cls}">{g[3]}</td><td>{esc(g[4])}</td></tr>')
    blocks.append('</tbody></table>')

    failed = [g for g in gates if g[3] == "FAIL"]
    verdict = "补货/履约门禁全绿" if not failed else f"发现 {len(failed)} 条未通过，暂缓下单"
    blocks.append('<h2>四、结论与边界</h2>')
    blocks.append(f'<p class="badge">综合结论：{esc(verdict)}</p>')
    blocks.append(f'<p>{esc(spec["conclusion"])}</p>')
    blocks.append(f'<p class="note">{esc(spec["boundary"])}</p>')
    doc = (_TEMPLATE.replace("@TITLE@", esc(spec["title"]))
           .replace("@ROLE@", esc(ROLE_TITLE))
           .replace("@SUBTITLE@", esc(spec["subtitle"]))
           .replace("@DATE@", RUN_DATE)
           .replace("@BODY@", "\n".join(blocks)))
    return doc, len(gates), len(failed)


SPECS = [
    {
        "file": "replenishment-advice.html",
        "title": "补货建议包：安全库存 / 库存守恒 / 采购单",
        "subtitle": "σ=12、LT=7、95% 服务水平 → SS 与 ROP；库存台账与采购单同链",
        "steps": [
            {"label": "安全库存计算", "skill": "safety-stock",
             "args": {"sigma": 12.0, "lead": 7.0, "z": 1.65}},
            {"label": "库存台账守恒", "skill": "inventory", "action": "bin",
             "fixture": "bin.json"},
            {"label": "采购订单合规", "skill": "procurement", "action": "purchase_order",
             "fixture": "purchase_order.json"},
        ],
        "conclusion": "按 SS = z×σ_d×√LT 实算安全库存与再订货点；库存台账 projected 守恒、"
                      "无负库存；采购单金额恒等与时序合规，三者共同构成补货建议。",
        "boundary": "安全库存是统计量，需结合供应商准时率与资金占用复核；"
                    "R15 只出建议与校验，不擅自下单/付款。",
    },
    {
        "file": "fulfillment-report.html",
        "title": "履约报告：销售订单 / 发货 / 到货验收",
        "subtitle": "订单双轴 + 超发门禁 + 采购到货数量核对",
        "steps": [
            {"label": "销售订单双轴", "skill": "fulfillment", "action": "sales_order",
             "fixture": "sales_order.json"},
            {"label": "发货单超发门禁", "skill": "fulfillment", "action": "delivery",
             "fixture": "delivery.json"},
            {"label": "采购到货验收", "skill": "procurement", "action": "receipt",
             "fixture": "receipt.json"},
        ],
        "conclusion": "销售订单状态/发货/开票三轴自洽且金额恒等；发货不超订单量；"
                      "采购到货满足到货数量约束，形成可交付的履约证据链。",
        "boundary": "履约报告只记录已发生与已校验事实，不替代仓库实盘；"
                    "超发与超收均须人工审批后调整。",
    },
]


def main():
    for spec in SPECS:
        runs = [_run_step(s) for s in spec["steps"]]
        doc, n, bad = _render(spec, runs)
        with open(os.path.join(HERE, spec["file"]), "w", encoding="utf-8") as f:
            f.write(doc)
        print(f"[golden] {spec['file']}: {n} 条门禁，未过 {bad}")


if __name__ == "__main__":
    main()
