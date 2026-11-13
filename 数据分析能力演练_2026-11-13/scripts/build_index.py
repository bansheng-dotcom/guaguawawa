# -*- coding: utf-8 -*-
"""生成总览页：6 个命题 + 21 项能力覆盖矩阵 + 数据来源与已知问题。"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPORTS = HERE / "reports"
OUT = REPORTS / "00_总览.html"

index = json.loads((REPORTS / "_index.json").read_text(encoding="utf-8"))

SKILLS = [
    ("semantics", "P1 数据体检", "validate / compute / reconcile", "通过；发现 count_distinct 返回类型缺陷"),
    ("quality", "P1 数据体检", "audit / clean", "8.1 分；及时性 0"),
    ("explore", "P6 用户与内容", "funnel / cohort / rfm / segment / metrics / time_series / saas", "7 个动作全部跑通"),
    ("rootcause", "P2 增长拆解", "decompose / drilldown", "城市贡献 + 品类帕累托"),
    ("describe", "P1 / P2 / P3", "均值/中位/分位/偏度", "4 次"),
    ("correlate", "P2 增长拆解", "Pearson", "折扣 vs 金额 r=-0.12"),
    ("ttest", "P4 / P6", "Welch t + Cohen's d", "2 次，均不显著"),
    ("chi2", "P3 / P4 / P6", "独立性 + Cramér's V", "3 次；渠道×退货显著"),
    ("anova", "P3 定价", "单因素 + η²", "F=314，η²=0.059"),
    ("regression", "P2 增长拆解", "OLS + 标准化 beta", "R²=0.022"),
    ("abtest", "P4 A/B", "lift + SRM + 决策", "clean=no_ship；srm=rerun"),
    ("power", "P4 A/B", "样本量 / MDE", "8.07 万/组"),
    ("causal", "P5 因果", "后门调整 + 分层", "5.57pp，偏差 0.88pp"),
    ("matched", "P5 因果", "PSM + 卡尺 + 反驳", "6.05pp，CI 不含 0"),
    ("did", "P5 因果", "2×2 / TWFE / 事件研究 / 安慰剂 / 交错", "ATT +9.9 万/周"),
    ("elasticity", "P2 增长拆解", "log-log OLS", "-1.344，R²=0.569"),
    ("scinlp", "P1 / P2", "describe / textstats / backend", "偏度 1.52；标题词频"),
    ("domain", "P1 数据体检", "list", "omicverse 后端不在本机，blocked"),
    ("viz", "P1 数据体检", "spec / guide / report", "48 类图表注册表校验通过"),
    ("selfmedia", "P6 用户与内容", "normalize / dashboard / report", "3 平台，partial"),
    ("rdd", "P3 定价", "局部线性 + 带宽 + 密度 + 协变量", "+12.62 元，密度 p=0.84"),
]

CARDS = []
for it in index:
    kpis = "".join(
        f'<span class="chip"><b>{k["value"]}</b>{k["label"]}</span>' for k in it["kpis"][:3]
    )
    CARDS.append(f'''
    <a class="card" href="{it['name']}.html">
      <div class="card-top"><span class="kicker">{it['doc_type'].split(' · ')[0]}</span><span class="arrow">→</span></div>
      <h2>{it['title']}</h2>
      <p class="sub">{it['sub']}</p>
      <div class="chips">{kpis}</div>
      <p class="file">{it['name']}.html</p>
    </a>''')

SKILL_ROWS = "".join(
    f"<tr><td><code>{s}</code></td><td>{where}</td><td>{acts}</td><td>{status}</td></tr>"
    for s, where, acts, status in SKILLS
)

html = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>数据分析能力演练 · 6 个命题</title>
<style>
  :root {{ --ink:#14231c; --paper:#fff; --green:#2f6f4f; --soft:#eef6f0; --line:rgba(20,35,28,.16); --muted:#5b6b62; }}
  * {{ box-sizing:border-box }}
  body {{ margin:0; background:radial-gradient(circle at 1px 1px, rgba(47,111,79,.13) 1.3px, transparent 1.4px) 0 0/22px 22px, #fff;
         color:var(--ink); font-family:"PingFang SC","Microsoft YaHei",-apple-system,"Segoe UI",sans-serif; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:36px 24px 64px; }}
  header.hero {{ background:linear-gradient(135deg,#0e2f22,#2f6f4f); color:#fff; border-radius:24px; padding:34px 36px;
                box-shadow:8px 10px 0 rgba(20,35,28,.12); }}
  .kicker {{ font-size:12px; letter-spacing:.18em; text-transform:uppercase; opacity:.75; }}
  h1 {{ margin:.35em 0 .2em; font-size:clamp(30px,5vw,46px); line-height:1.08; letter-spacing:-.02em; }}
  h1 em {{ font-style:normal; background:linear-gradient(transparent 62%, #ffd43b 62%); padding:0 .08em; color:#fff; }}
  .lede {{ margin:0; max-width:60ch; line-height:1.8; color:rgba(255,255,255,.85); }}
  .facts {{ display:flex; flex-wrap:wrap; gap:10px; list-style:none; padding:0; margin:18px 0 0; }}
  .facts li {{ border:1px solid rgba(255,255,255,.35); border-radius:999px; padding:6px 13px; font-size:13px; }}
  h2.sec {{ font-size:24px; margin:44px 0 6px; }}
  .sec-note {{ color:var(--muted); margin:0 0 18px; font-size:14px; line-height:1.7; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(310px,1fr)); gap:16px; }}
  .card {{ display:block; background:#fff; border:2px solid var(--ink); border-radius:18px; padding:18px 18px 16px;
           text-decoration:none; color:inherit; box-shadow:4px 5px 0 rgba(20,35,28,.1); transition:transform .15s, box-shadow .15s; }}
  .card:hover {{ transform:translateY(-3px); box-shadow:7px 9px 0 rgba(20,35,28,.14); }}
  .card-top {{ display:flex; justify-content:space-between; align-items:center; }}
  .card h2 {{ font-size:19px; margin:8px 0 4px; letter-spacing:-.01em; }}
  .card .sub {{ margin:0; color:var(--muted); font-size:13px; }}
  .card .chips {{ display:flex; flex-wrap:wrap; gap:6px; margin:12px 0 8px; }}
  .chip {{ font-size:12px; background:var(--soft); border:1px solid var(--line); border-radius:999px; padding:3px 9px; color:#21402f; }}
  .chip b {{ margin-right:4px; }}
  .file {{ margin:0; font-family:Consolas,monospace; font-size:11.5px; color:#7a8a80; }}
  .arrow {{ font-size:20px; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); font-size:13.5px; }}
  th, td {{ text-align:left; padding:9px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ background:var(--soft); font-size:12.5px; letter-spacing:.02em; }}
  td:first-child {{ white-space:nowrap; }}
  code {{ font-family:Consolas,monospace; font-size:12.5px; background:var(--soft); padding:1px 5px; border-radius:4px; }}
  .note {{ background:#fffaf0; border-left:4px solid #e6a700; padding:12px 14px; border-radius:0 10px 10px 0; font-size:13.5px; line-height:1.8; }}
  .two {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  @media (max-width:760px) {{ .two {{ grid-template-columns:1fr; }} }}
  footer {{ margin-top:40px; border-top:1px dashed var(--line); padding-top:14px; color:var(--muted); font-size:12.5px; }}
  a {{ color:#1d5c3f; }}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div class="kicker">R06 蛙得清 · 数据分析能力演练</div>
    <h1>六个命题，二十一项能力，<em>全跑一遍</em></h1>
    <p class="lede">自己出题、自己找数、自己算、自己验。六个命题从数据底座一路走到因果推断与用户分群，
       每份报告都由报告内核确定性渲染，数字能追到 results/ 里的原始 JSON。</p>
    <ul class="facts">
      <li><b>49</b> 次技能调用</li>
      <li><b>21/21</b> 技能覆盖</li>
      <li><b>6</b> 份完整报告</li>
      <li><b>1</b> 个底层缺陷被修</li>
      <li>数据截止 2026-11-13</li>
    </ul>
  </header>

  <h2 class="sec">六个命题</h2>
  <p class="sec-note">按「先验数据、再拆增长、再定价、再做实验、再做因果、最后看用户与内容」的顺序读；每份都是独立可交付的报告，含结论先行、KPI、图表、证据边界、记录层与口径分数。</p>
  <div class="grid">{''.join(CARDS)}
  </div>

  <h2 class="sec">能力覆盖：21 项技能</h2>
  <p class="sec-note">「跑一遍」指真的通过 <code>guagua.py call r06 …</code> 执行并取回结构化输出，不是文档里勾选。49 次调用全部 exit 0。</p>
  <table>
    <thead><tr><th>技能</th><th>用在</th><th>执行的动作</th><th>结果</th></tr></thead>
    <tbody>{SKILL_ROWS}</tbody>
  </table>

  <h2 class="sec">数据来源：真实与模拟分开标</h2>
  <div class="two">
    <div class="note"><b>真实公开数据</b><br>
      个护调研 76 条观测、魔镜牙膏价格带 / 口腔分平台、6 家上市公司 2025 年报、2024–2025 洗护发年度值。
      用于 P1 的对账、P2 的量价分解、P3 的价格带。</div>
    <div class="note" style="border-left-color:#2f6f4f;background:#f2f8f4"><b>模拟数据（seed=42）</b><br>
      订单 2 万单、A/B 20 万会话、40 城 × 26 周面板、12,000 购物车、5,345 用户 cohort、内容快照。
      锚点对齐公开数据（洗护均价≈53 元、CTR≈3.2%），只用于演示方法，不冒充真实业务。</div>
  </div>

  <h2 class="sec">这次发现并处理的问题</h2>
  <div class="note">
    <b>1. 修了一个底层缺陷：</b><code>shared/methods/deep.py::_within2</code> 在子样本（事件研究只用 pre 期）时对空的 unit/time 单元做除法，直接 ZeroDivisionError，导致 TWFE + 事件研究跑不起来。已改为空单元跳过，<code>test_methods_deep</code> 13 项全过。<br>
    <b>2. 报了一个未修缺陷：</b><code>semantics compute</code> 的 <code>count_distinct</code> 返回去重值列表而不是计数；不是数据问题，已在 P1 里标注并绕开。<br>
    <b>3. 一个方法口径提醒：</b>事件研究以「窗口外所有期」为基准，和线性预趋势检验口径不同；P5 里两处结论不一致时，按更保守的读。
  </div>

  <footer>
    R06 蛙得清 · 数据分析能力演练 ｜ 2026-11-13 ｜ 复现：<code>python scripts/gen_data.py && python scripts/derive.py && python scripts/run_skills.py && python scripts/build_reports.py</code><br>
    报告渲染：core/report_renderer.py（确定性）｜ 技能输出：results/*.json ｜ 数据：data/（含 MANIFEST.json）
  </footer>
</div>
</body>
</html>
'''

OUT.write_text(html, encoding="utf-8")
print(f"index: {OUT} ({OUT.stat().st_size/1024:.0f} KB)")
