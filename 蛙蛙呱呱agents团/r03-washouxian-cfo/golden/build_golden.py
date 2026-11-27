# -*- coding: utf-8 -*-
"""R03 黄金成品生成器：调用本角色真实技能，把结果渲染成独立静态 HTML。

确定性：纯标准库、不联网、不写时间戳（固定 RUN_DATE）。
跑法：python r03-washouxian-cfo/golden/build_golden.py
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
if ROLE_DIR not in sys.path:
    sys.path.insert(0, ROLE_DIR)

from skills import SKILLS  # noqa: E402

ROLE = "r03"
ROLE_TITLE = "R03 蛙守线 · CFO / 财务合规官"
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
<footer>本文件由 golden/build_golden.py 调用角色真实技能生成，可复算；R03 不出具持牌意见。</footer>
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
    verdict = "门禁全部通过" if not failed else f"发现 {len(failed)} 条未通过，已阻断放行"
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
        "file": "month-end-close.html",
        "title": "月度关账包：roll-forward / 对账 / 差异注解",
        "subtitle": "财务月结真实夹具 → 三道确定性门禁",
        "steps": [
            {"label": "期末余额滚动平衡", "skill": "financial", "action": "rollforward",
             "fixture": "financial_rollforward.json"},
            {"label": "GL↔子账对账", "skill": "financial", "action": "recon",
             "fixture": "financial_recon.json"},
            {"label": "预算差异注解", "skill": "financial", "action": "variance",
             "fixture": "financial_variance.json"},
        ],
        "conclusion": "月结包把「账户滚动平衡 → 总账/子账对账 → 重大差异注解」串成一条链；"
                      "本包检出未平账户（cash 差 500）与未归因差异，输出 break 清单与 next 动作，"
                      "供当日调平后再进 controller sign-off。",
        "boundary": "R03 只做确定性校验与归因，不代签、不调账、不出具正式审计意见；"
                    "调平与签署由财务负责人完成。",
    },
    {
        "file": "contract-review.html",
        "title": "合同审查包：红线扫描 / 整改跟踪 / 政策字段",
        "subtitle": "合同真实夹具 → 12 条规则扫描 + redline 闭环 + 政策门禁",
        "steps": [
            {"label": "合同红线扫描", "skill": "contract", "action": "scan",
             "fixture": "contract_scan.json"},
            {"label": "整改状态跟踪", "skill": "contract", "action": "redline",
             "fixture": "contract_redline.json"},
            {"label": "内部政策字段", "skill": "contract", "action": "policy",
             "fixture": "contract_policy.json"},
        ],
        "conclusion": "扫描命中自动续约、单方调价、无上限责任等 CRITICAL 条款，sign_gate 判定"
                      "不允许送签；redline 列出未闭合整改项，政策字段门禁确认政策本身可执行。",
        "boundary": "R03 输出的是红线清单与整改建议，不构成正式法律意见；"
                    "签署决策与对外承诺须创始人签字。",
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
