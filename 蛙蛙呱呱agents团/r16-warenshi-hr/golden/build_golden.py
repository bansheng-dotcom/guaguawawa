# -*- coding: utf-8 -*-
"""R16 黄金成品生成器：调用本角色真实人事技能，渲染成独立静态 HTML。

确定性：纯标准库、不联网、不写时间戳（固定 RUN_DATE）。
跑法：python r16-warenshi-hr/golden/build_golden.py
"""
from __future__ import annotations

import hashlib
import html
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

ROLE = "r16"
ROLE_TITLE = "R16 蛙人师 · 人事与组织官"
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
<footer>本文件由 golden/build_golden.py 调用角色真实技能生成，可复算；R16 不擅自录用/发薪。</footer>
</main>
</body>
</html>
"""


def _module(name):
    return next(m for m in SKILLS if m.NAME == name)


def _run_step(step):
    mod = _module(step["skill"])
    path = os.path.join(ROLE_DIR, "examples", step["fixture"])
    with open(path, "rb") as f:
        raw = f.read()
    out = mod.run(Namespace(action=step["action"], input=path))
    return {"label": step["label"], "skill": step["skill"],
            "action": step["action"], "source": "examples/" + step["fixture"],
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
    verdict = "招聘/绩效门禁全绿" if not failed else f"发现 {len(failed)} 条未通过，暂缓推进"
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
        "file": "hiring-performance-pack.html",
        "title": "招聘与绩效包：职位 / 候选人 / 录用 / 评估",
        "subtitle": "招聘管道前置条件 + 绩效评分区间与 KRA 完整性",
        "steps": [
            {"label": "职位空缺", "skill": "recruit", "action": "opening",
             "fixture": "opening.json"},
            {"label": "候选人记录", "skill": "recruit", "action": "applicant",
             "fixture": "applicant.json"},
            {"label": "录用前置", "skill": "recruit", "action": "offer",
             "fixture": "offer.json"},
            {"label": "绩效评估", "skill": "performance", "action": "appraisal",
             "fixture": "appraisal.json"},
        ],
        "conclusion": "职位/候选人/录用三级状态与必填字段齐备；Accepted 来自 Shortlisted，"
                      "未跳过筛选；绩效总分与 KRA 单项分均在 0–5 区间且打分完整。",
        "boundary": "R16 只产招聘与绩效工件，不擅自发 Offer/入职/定档；"
                    "薪酬与劳动关系结论须 R03/外部专业复核。",
    },
    {
        "file": "payroll-compliance-pack.html",
        "title": "薪酬准备包：输入来源 / 毛净恒等 / 制度字段溯源",
        "subtitle": "薪酬是「准备」不是「发放」——净额恒等与制度性幻觉防护",
        "steps": [
            {"label": "薪酬输入表", "skill": "payroll", "action": "input",
             "fixture": "payroll_input.json"},
            {"label": "薪酬核算记录", "skill": "payroll", "action": "calc",
             "fixture": "payroll_calc.json"},
        ],
        "conclusion": "薪酬输入频率与组成项类型合法，每个组成项都有 source；核算记录"
                      "毛额=ΣEarning、净额=毛额−ΣDeduction，制度性字段均可溯源。",
        "boundary": "本包仅为薪酬输入与核算草稿，交 R03（税务/合规）与外部专业人士复核，"
                    "绝不直接发薪/代发/打款。",
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
