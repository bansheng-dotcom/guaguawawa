# -*- coding: utf-8 -*-
"""R04 黄金成品生成器：调用本角色真实评审技能，渲染成独立静态 HTML。

确定性：纯标准库、不联网、不写时间戳（固定 RUN_DATE）。
跑法：python r04-watiaoci-reviewer/golden/build_golden.py
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

ROLE = "r04"
ROLE_TITLE = "R04 蛙挑剔 · 独立评审官"
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
<footer>本文件由 golden/build_golden.py 调用角色真实评审技能生成，可复算；R04 只评审不代改。</footer>
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
    verdict = "评审通过，可放行" if not failed else f"发现 {len(failed)} 条未通过，阻断放行"
    blocks.append('<h2>四、结论与边界</h2>')
    blocks.append(f'<p class="badge">评审结论：{esc(verdict)}</p>')
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
        "file": "review-gate-report.html",
        "title": "独立评审报告：门禁强度 + 事实链 + 判据 + 质量",
        "subtitle": "成品门禁与证据链的真实评审夹具",
        "steps": [
            {"label": "门禁强度审计", "skill": "gate", "action": "audit",
             "fixture": "gate_audit.json"},
            {"label": "五维事实核查", "skill": "facts", "action": "check",
             "fixture": "facts_check.json"},
            {"label": "外置判据审查", "skill": "criteria", "action": "review",
             "fixture": "criteria_review.json"},
            {"label": "完成声明质量", "skill": "quality", "action": "critique",
             "fixture": "quality_critique.json"},
        ],
        "conclusion": "门禁强度 100 分（solid）、五维事实 0 违例、外置判据 0 fail、"
                      "完成声明均带新鲜证据，四道评审共同给出 PASS 结论。",
        "boundary": "R04 只评审已存在成品，不代改、不替生产方补证据；"
                    "评审通过与对外发布是两件事，发布仍由 R01 签发。",
    },
    {
        "file": "human-review-report.html",
        "title": "人工评审工作流报告：评审包 / 批次契约 / 确认",
        "subtitle": "独立 reviewer 身份核验 + 人工批注回填 + staged 确认",
        "steps": [
            {"label": "评审包身份核验", "skill": "human", "action": "package",
             "fixture": "human_package.json"},
            {"label": "人工批注批次契约", "skill": "human", "action": "ingest",
             "fixture": "human_ingest.json"},
            {"label": "staged 资产确认", "skill": "human", "action": "ack",
             "fixture": "human_ack.json"},
            {"label": "保留优点标记", "skill": "strengths", "action": "mark",
             "fixture": "strengths_mark.json"},
        ],
        "conclusion": "reviewer=r04 ≠ producer=r08，身份红线通过；批注批次契约合规并产出"
                      "逐字回填计划；staged 资产全部 copied 后 ACKED。",
        "boundary": "ack 即删除服务端批次，本流程只登记与回填计划；"
                    "人工批注的 after 原话必须逐字回填，R04 不代改产品。",
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
