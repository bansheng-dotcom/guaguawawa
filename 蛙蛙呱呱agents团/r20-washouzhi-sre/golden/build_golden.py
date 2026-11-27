# -*- coding: utf-8 -*-
"""R20 黄金成品生成器：调用本角色真实 SRE 技能，渲染成独立静态 HTML。

确定性：纯标准库、不联网、不写时间戳（固定 RUN_DATE）。
跑法：python r20-washouzhi-sre/golden/build_golden.py
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

ROLE = "r20"
ROLE_TITLE = "R20 蛙值守 · SRE 与可靠性官"
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
<footer>本文件由 golden/build_golden.py 调用角色真实技能生成，可复算；R20 不擅自灾难切换/恢复生产。</footer>
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
    verdict = "SLO/演练/复盘门禁全绿" if not failed else f"发现 {len(failed)} 条未通过，冻结发版"
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
        "file": "slo-and-drill.html",
        "title": "SLO 与演练报告：错误预算 / 恢复演练 / RPO-RTO",
        "subtitle": "30 天窗口 99.9% SLO + 恢复 150 文件校验和一致 + 依赖无环回滚计划",
        "steps": [
            {"label": "SLO 错误预算", "skill": "slo",
             "args": {"slo": 99.9, "window_days": 30, "requests": 1000000,
                      "downtime_min": 10.0}},
            {"label": "恢复演练证据", "skill": "restore", "action": "drill",
             "fixture": "drill.json"},
            {"label": "RPO/RTO 与回滚", "skill": "dr", "action": "rpo_rto",
             "fixture": "rpo_rto.json"},
        ],
        "conclusion": "30 天 99.9% SLO 允许停机 43.2 分钟，已用 10 分钟，剩余预算 33.2 分钟、"
                      "燃尽率 0.231；恢复演练 150 文件校验和一致；RPO/RTO 在限值内，"
                      "依赖图无环且回滚计划非空。",
        "boundary": "灾难恢复是预案不是已发生切换；R20 只校验结构与证据，"
                    "不擅自执行灾难切换/恢复生产。",
    },
    {
        "file": "backup-and-postmortem.html",
        "title": "备份与复盘报告：加密备份仓 / 恢复请求 / 复盘闭环",
        "subtitle": "备份存在 ≠ 恢复成功；复盘四要素 + 改进项闭环",
        "steps": [
            {"label": "加密备份仓", "skill": "backup", "action": "backup",
             "fixture": "backup.json"},
            {"label": "恢复请求", "skill": "restore", "action": "restore",
             "fixture": "restore.json"},
            {"label": "故障复盘", "skill": "postmortem", "action": "postmortem",
             "fixture": "postmortem.json"},
            {"label": "改进项闭环", "skill": "postmortem", "action": "improvement",
             "fixture": "improvement.json"},
        ],
        "conclusion": "备份仓已声明加密且排除规则合法；恢复请求指向真实快照并带授权；"
                      "复盘四要素齐备、严重度合法，改进项均有 owner/due/status 且全部闭环。",
        "boundary": "R20 不持有仓库密码、不实际执行 restic；复盘是学习不是追责，"
                    "根因描述不等于责任认定。",
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
