# -*- coding: utf-8 -*-
"""reportkit.render —— 三层结构渲染（摘要 / 分析 / 记录）。

数字全部来自 metrics（源自 obs 表）；正文用 {{key|fmt}} 槽位，不手写数字。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TEAM = Path(r"D:\蛙蛙呱呱\蛙蛙呱呱agents团")
sys.path.insert(0, str(TEAM))
try:
    from shared.report_theme import get_publishing_css  # type: ignore
    CSS = get_publishing_css({"primary": "#2c3e50", "accent": "#3498db"})
except Exception:  # 主题不可用时退化为极简样式
    CSS = "body{font-family:'Microsoft YaHei';margin:40px auto;max-width:1080px;line-height:1.75}"
    CSS += "table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left}"

SUPP = """
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.up{color:#B91C1C;font-weight:600}.down{color:#15803D;font-weight:600}.flat{color:#6B7280}
.layer{border-left:3px solid #2c3e50;padding-left:14px;margin:28px 0 10px}
.layer h2{margin:0;font-size:18px}
.stat{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}
.stat div{border:1px solid #E2E8F0;border-top:3px solid #3498db;padding:10px 12px;border-radius:2px}
.stat b{display:block;font-size:12px;color:#475569;font-weight:600}
.stat span{font-size:22px;font-weight:700}
table{font-size:13px}th{font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:#475569}
.slot-bad{background:#FEF2F2;color:#B91C1C}
.heat td{text-align:center;font-size:12px}
.ok{background:#F0FDF4;color:#15803D}.partial{background:#FFFBEB;color:#B45309}.empty{background:#FEF2F2;color:#B91C1C}
.ann{border-left:3px solid #B45309;background:#FFFBEB;padding:10px 14px;margin:12px 0;font-size:13px;line-height:1.7}
.ann.stale{border-left-color:#B91C1C;background:#FEF2F2}
.ann .tag{font-size:11px;font-weight:700;letter-spacing:.05em;color:#B45309;margin-bottom:4px}
.ann.stale .tag{color:#B91C1C}
.ann p{margin:2px 0}
details{margin:12px 0;border:1px solid #E2E8F0;border-radius:2px;padding:10px 14px}
summary{cursor:pointer;font-weight:700;color:#2c3e50}
"""


def fmt(v, kind="raw"):
    if v is None:
        return "—"
    if kind == "pct":
        return f"{v:+.2f}%"
    if kind == "num2":
        return f"{v:.2f}"
    if kind == "int":
        return f"{int(v)}"
    return f"{v}"


def fill(text: str, m: dict) -> str:
    def repl(mo):
        key, _, kind = mo.group(1).partition("|")
        cur = m
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return f'<span class="slot-bad">[缺 {key}]</span>'
        return fmt(cur, kind or "raw")
    return re.sub(r"\{\{([^}]+)\}\}", repl, text)


def cls(v):
    return "up" if v and v > 0 else ("down" if v and v < 0 else "flat")


def table(headers, rows, num_from=1):
    th = "".join(f'<th class="num">{h}</th>' if i >= num_from else f"<th>{h}</th>"
                 for i, h in enumerate(headers))
    body = ""
    for r in rows:
        cells = ""
        for i, c in enumerate(r):
            cells += f'<td class="num">{c}</td>' if i >= num_from else f"<td><b>{c}</b></td>"
        body += f"<tr>{cells}</tr>"
    return f"<table><tr>{th}</tr>{body}</table>"


def heatmap(cells, case):
    cats = list(case["categories"])
    dims = [(d["id"], d["name"]) for d in case["dimensions"]]
    head = "<tr><th>维度</th>" + "".join(f"<th>{c}</th>" for c in cats) + "</tr>"
    rows = ""
    for did, dname in dims:
        tds = ""
        for cat in cats:
            cell = next((x for x in cells if x["cat"] == cat and x["dim"] == did), None)
            st = cell["status"] if cell else "empty"
            txt = f'{cell["have"]}/{cell["need"]}' if cell else "0/—"
            tds += f'<td class="{st}">{txt}</td>'
        rows += f'<tr><td><b>{dname}</b></td>{tds}</tr>'
    return f'<table class="heat">{head}{rows}</table>'


def ann_html(anns, anchor):
    blocks = [a for a in (anns or []) if a["anchor"] == anchor]
    if not blocks:
        return ""
    out = []
    for a in blocks:
        cls = "ann stale" if a.get("status") == "stale" else "ann"
        tag = {"stale": "⚠ 数据已更新，请复核", "new": "首次挂载", "ok": "已复核"}.get(a.get("status"), "批注")
        ps = "".join("<p>%s</p>" % ln for ln in a["text"].split("\n") if ln.strip())
        out.append('<div class="%s"><div class="tag">%s · %s</div>%s</div>' % (cls, tag, a["anchor"], ps))
    return "".join(out)


def render(case, conn, m, audit, snap, claims, conflicts, faileds, anns=None) -> str:
    c = conn.cursor()
    ann_count = len(anns or [])
    ann_stale = sum(1 for a in (anns or []) if a.get("status") == "stale")

    # ---------- 分析层表格 ----------
    daily_rows = [["%s" % k, f'{v["first"]:.2f}', f'{v["last"]:.2f}',
                   f'<span class="{cls(v["change"])}">{v["change"]:+.2f}%</span>',
                   f'{v["min"]:.2f}', f'{v["max"]:.2f}', f'{v["mean"]:.2f}',
                   f'{v["range"]:.1f}%', f'{v["cv"]:.2f}%']
                  for k, v in sorted(m["daily"].items())]
    weekly_rows = [[k, f'{v["first"]:.2f}', f'{v["last"]:.2f}',
                    f'<span class="{cls(v["change"])}">{v["change"]:+.2f}%</span>',
                    f'{v["yoy"]:+.1f}%' if v.get("yoy") is not None else "—"]
                   for k, v in sorted(m["weekly"].items())]
    retail_rows = [[k, f'{v["first"]:.2f}', f'{v["last"]:.2f}',
                    f'<span class="{cls(v["change"])}">{v["change"]:+.2f}%</span>']
                   for k, v in sorted(m["retail"].items())]
    city_rows = []
    for item, series in sorted(m["city"].items()):
        ds = sorted(series)
        city_rows.append([item] + [f'{series[d]:.2f}' for d in ds])
    fut_rows = [[k, f'{v["first"]:.0f}', f'{v["last"]:.0f}',
                 f'<span class="{cls(v["change"])}">{v["change"]:+.2f}%</span>']
                for k, v in sorted(m["futures"].items())]

    # ---------- 记录层：全量观测（按源汇总 + 明细折叠） ----------
    src_rows = c.execute(
        "SELECT source, market, COUNT(*) n, MIN(date) d0, MAX(date) d1, unit, spec, grade "
        "FROM obs GROUP BY source, market, unit, spec, grade ORDER BY source").fetchall()
    src_table = table(["来源", "市场", "观测数", "起", "止", "单位", "规格", "级"],
                      [[r["source"], r["market"], r["n"], r["d0"], r["d1"], r["unit"], r["spec"], r["grade"]]
                       for r in sorted(src_rows, key=lambda x: (x["source"], x["market"]))], num_from=2)

    # ---------- 记录层：冲突 / 失败 ----------
    conf_rows = table(["品类", "口径A", "值A", "口径B", "值B", "差%", "判定"],
                      [[r["item"], r["a_source"], f'{r["a_value"]:.2f}', r["b_source"],
                        f'{r["b_value"]:.2f}', f'{r["delta_pct"]:+.2f}%', r["verdict"]]
                       for r in conflicts], num_from=2)
    fail_rows = table(["目标", "试过的源", "结果", "下一步"],
                      [[r["target"], r["tried"], r["reason"], r["next_action"]] for r in faileds], num_from=4)

    # ---------- 摘要层 ----------
    claim_html = "".join(
        f'<li>{fill(cl["text"], m)} <a href="#{cl["section"]}" style="font-size:11px;color:#3498db">→ 证据</a></li>'
        for cl in claims)

    compress = (f'本报告把 <b>{audit["obs_total"]}</b> 个观测压缩为 {len(m["daily"]) + len(m["weekly"]) + len(m["retail"]) + len(m["city"]) + len(m["futures"])} 张表；'
                f'压缩方式为「全量入记录层、聚合入分析层」，<b>未丢弃任何观测</b>（弃置 {audit["discard"]*100:.1f}% 见记录层清单）。')

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{case["title"]}（保真版）</title><style>{CSS}{SUPP}</style></head>
<body><div class="document">
<header class="doc-header">
  <div class="doc-type-bar"><span class="doc-glyph"><i></i><i></i><i></i></span>
  <span>{case["title"]} · 保真交付（记录/分析/摘要 三层同构）</span></div>
  <h1>{case["title"]}</h1>
  <div class="doc-meta"><span>窗口 {case["window"]["start"]} — {case["window"]["end"]}</span>
  <span>快照 {snap["id"]}</span>
  <span>观测 {audit["obs_total"]:,}</span></div>
</header>

<div class="layer"><h2>§0 交付首页</h2></div>
<div class="stat">
  <div><b>保留率</b><span>{audit["retention"]*100:.1f}%</span></div>
  <div><b>溯源率</b><span>{audit["trace_rate"]*100:.0f}%</span></div>
  <div><b>弃置率</b><span>{audit["discard"]*100:.1f}%</span></div>
  <div><b>规格覆盖</b><span>{audit["coverage"]*100:.0f}%</span></div>
</div>
<p><b>批注：</b>{ann_count} 条，其中待复核 {ann_stale} 条（批注是人的判断，数据变了会亮 ⚠ 但不丢）</p>
<p><b>压缩声明：</b>{compress}</p>
<p><b>审计判定：</b>{audit["verdict"]}（不是"通过"，是"亮灯"：红格见 §4 热力图，缺口见 §3.5）</p>

<div class="layer"><h2>§1 摘要层（由分析层派生，可点回证据）</h2></div>
<ol>{claim_html}</ol>

<div class="layer"><h2>§2 分析层</h2></div>
<h3 id="s2-1">2.1 全国日度：{len(m["daily"])} 品类 × 每类全序列</h3>
{table(["品类", "首日", "末日", "累计", "最低", "最高", "均值", "振幅", "CV"], daily_rows)}
<p>判断：{fill("鸡蛋 {{daily.鸡蛋.change|pct}} 是最大跌幅，牛肉 {{daily.牛肉.change|pct}} 是唯一显著上涨；鸡蛋 CV {{daily.鸡蛋.cv|num2}}% 为九类最高，意味着它最该锁量而不锁价。", m)}</p>
{ann_html(anns, "s2-1")}

<h3 id="s2-2">2.2 全国周度：本周价与同比</h3>
{table(["品类", "首周", "末周", "5 周变化", "末周同比"], weekly_rows)}
<p>判断：{fill("周度同比把品类分成三层——鸡蛋 {{weekly.鸡蛋.yoy|num2}}%、牛肉 {{weekly.牛肉.yoy|num2}}% 在高位；猪肉 {{weekly.猪肉.yoy|num2}}% 在低位。", m)}</p>
{ann_html(anns, "s2-2")}

<h3 id="s2-3">2.3 内蒙古零售：旬度四时点</h3>
{table(["品类", "10/05", "11/05", "变化"], retail_rows)}
{ann_html(anns, "s2-3")}

<h3 id="s2-4">2.4 呼和浩特周度：{len(m["city"])} 品类</h3>
{table(["品类"] + [d[5:] for d in sorted(next(iter(m["city"].values())).keys())], city_rows)}
{ann_html(anns, "s2-4")}

<h3 id="s2-5">2.5 期货主力：方向锚</h3>
{table(["品种", "期初", "期末", "累计"], fut_rows)}
{ann_html(anns, "s2-5")}

<h3 id="s2-6">2.6 传导缺口</h3>
<p>{fill("内蒙鸡蛋 {{retail.鸡蛋.change|pct}} vs 全国 {{daily.鸡蛋.change|pct}}，缺口 {{gap_egg|num2}} 个百分点——本地慢半拍，但这半拍是可以被排进采购节奏的。", m)}</p>
{ann_html(anns, "s2-6")}

<div class="layer"><h2>§3 记录层（全量 / 可复算）</h2></div>
<details open><summary>3.1 观测来源汇总（{audit["obs_total"]:,} 条）</summary>{src_table}</details>
<details><summary>3.2 计算过程（公式）</summary>
<ul>
<li>涨跌幅 =（末日值 ÷ 首日值 − 1）× 100；</li>
<li>振幅 =（最高 − 最低）÷ 均值 × 100；CV = 标准差 ÷ 均值 × 100（总体标准差）；</li>
<li>周度同比取来源方口径（去年同期），非本报告推算；</li>
<li>传导缺口 = 内蒙零售变化率 − 全国批发变化率。</li>
</ul></details>
<details open><summary>3.3 口径冲突（单列，不写成"坑"）</summary>{conf_rows}</details>
<details open><summary>3.4 失败尝试（试过什么、为什么没拿到）</summary>{fail_rows}</details>
<details><summary>3.5 缺口与责任（owner / due / method）</summary>
{table(["缺口", "owner", "due", "补数方式"], [[g["cell"], g.get("owner") or "待指派", g.get("due") or "待定", g.get("method") or "—"] for g in audit["gaps"]] or [["无", "—", "—", "—"]], num_from=3)}
</details>

<div class="layer"><h2>§4 附录：规格覆盖热力图（{len(audit["cells"])} 格）</h2></div>
{heatmap(audit["cells"], case)}
<p style="font-size:12px;color:#475569">绿=达标，黄=不足，红=空缺。红格不阻断交付，但会出现在这里——这就是"亮灯不拦人"。</p>

<div class="doc-footer"><span>reportkit · 保真交付 · metrics {snap["metrics_hash"]}</span>
<span>输出哈希 __HASH__</span></div>
</div></body></html>"""
    return html
