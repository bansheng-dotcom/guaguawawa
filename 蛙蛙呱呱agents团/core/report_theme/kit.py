# -*- coding: utf-8 -*-
"""core.report_theme.kit —— flow 版页构造器（自包含，不依赖 workspace 样例）。

由 workspace/sample_fruit 的 build.CSS 与 seasoning_v3 的 kit.py 固化而来：
- CSS / 基础组件（header/table/split_blocks/notes_html/to_pdf）
- 页构造器（cover/summary/toc/section/action/appendix/back）
- LOGO 运行时从 avatars/team.png 缩放后内联（不把 500KB base64 写进源码）

用法：
    from core.report_theme import kit
    html = kit.cover(meta, kpi) + kit.section_page(s, ...)
"""
from __future__ import annotations

import base64
import html
import io
import re
import subprocess
import sys
from pathlib import Path

from core.report_marks import FIGURE_SRC_CLASSES

# 页构造器沿用 v3 kit 的写法（内部以 build.xxx 调基础组件）；固化后指回本模块
build = sys.modules[__name__]

ROOT = Path(__file__).resolve().parents[2]
LOGO_SRC = ROOT / "avatars" / "team.png"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ORG = "蛙蛙呱呱专家团"


def logo_data_uri() -> str:
    try:
        from PIL import Image
        im = Image.open(LOGO_SRC).convert("RGBA")
        im.thumbnail((300, 300), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:  # noqa: BLE001
        return ""


LOGO = logo_data_uri()

CSS = r"""
:root{
  --ink:#1F2A37; --ink2:#33424F; --muted:#66737F; --faint:#98A2AC;
  --line:#E3E5E8; --line2:#C9D0D6;
  --accent:#C0392B; --accent2:#E74C3C; --accent-soft:#F8ECE9;
  --blue:#2E6F9E; --blue-soft:#EAF2F8;
  --gray:#7C8792; --paper:#FFFFFF; --surface:#F7F6F2;
  --serif:"Noto Serif SC","Source Han Serif SC","Songti SC",SimSun,serif;
  --sans:"Noto Sans SC","Source Han Sans SC","Microsoft YaHei","PingFang SC",sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:#E7E5E0; color:var(--ink);
  font-family:var(--sans); font-size:10pt; line-height:1.78;
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
  font-feature-settings:"tnum" 1,"pnum" 1;
}
a{color:inherit;text-decoration:none;border-bottom:1px solid var(--line2)}
a:hover{color:var(--accent);border-bottom-color:var(--accent)}
.page{
  width:210mm; height:297mm; background:var(--paper); position:relative;
  margin:0 auto 10mm; padding:14mm 18mm 12mm; overflow:hidden;
  box-shadow:0 12px 34px rgba(20,31,42,.10);
  page-break-after:always; break-after:page;
}
.page:last-child{page-break-after:auto;break-after:auto}
@media screen and (max-width:900px){
  .page{width:100%;height:auto;min-height:297mm;padding:22px 18px 40px;margin:0 0 14px}
}
.rh{
  position:absolute;top:8.5mm;left:18mm;right:18mm;height:6mm;
  display:flex;align-items:flex-end;justify-content:space-between;
  font-size:7.2pt;letter-spacing:.10em;color:var(--faint);
  border-bottom:.4pt solid var(--line);padding-bottom:2mm;
}
.rh b{font-weight:600;color:var(--muted);letter-spacing:.10em}
.rf{
  position:absolute;bottom:7mm;left:18mm;right:18mm;
  display:flex;align-items:center;justify-content:space-between;
  font-size:7pt;color:var(--faint);letter-spacing:.08em;
}
.rf .pn{font-size:8pt;color:var(--muted);font-weight:600;letter-spacing:0}
.rf .pn i{font-style:normal;color:var(--faint);font-weight:400}

/* cover */
.cover{padding:0}
.cover .inner{position:absolute;inset:0;padding:16mm 18mm 14mm;display:flex;flex-direction:column}
.cover .top{display:flex;align-items:center;justify-content:space-between}
.brand{display:flex;align-items:center;gap:3.2mm}
.brand img{width:15mm;height:15mm;object-fit:contain;filter:saturate(.92)}
.brand .bw{font-size:9.4pt;font-weight:700;letter-spacing:.16em}
.brand .bs{font-size:6.8pt;color:var(--faint);letter-spacing:.20em;margin-top:.8mm}
.chip{font-size:7pt;letter-spacing:.18em;color:var(--muted);border:.5pt solid var(--line2);
  padding:1.6mm 3.2mm;border-radius:20mm}
.cover .mid{margin-top:26mm}
.ck{font-size:8pt;letter-spacing:.20em;color:var(--accent);font-weight:700}
h1.cover-t{
  font-family:var(--serif);font-weight:600;font-size:30pt;line-height:1.28;
  margin:5mm 0 0;letter-spacing:-.02em;color:var(--ink);white-space:normal;
  max-width:172mm;text-wrap:balance;
}
h1.cover-t .l2{display:block;color:var(--ink)}
.cover .rule{width:22mm;height:1.2mm;background:var(--accent);margin:8mm 0 6mm}
.cover .sub{font-size:14.5pt;line-height:1.65;color:var(--ink2);font-weight:500;max-width:150mm}
.cover .stand{font-size:10pt;line-height:1.95;color:var(--muted);max-width:138mm;margin-top:6mm}
.cover .logic{display:flex;align-items:stretch;gap:5mm;margin-top:11mm;border-top:.5pt solid var(--line2);
  border-bottom:.5pt solid var(--line2);padding:4.2mm 0}
.cover .logic>div{flex:1;display:flex;flex-direction:column;gap:.8mm}
.cover .logic span{font-size:7pt;letter-spacing:.16em;color:var(--faint)}
.cover .logic b{font-family:var(--serif);font-size:19pt;font-weight:600;line-height:1.1;color:var(--ink)}
.cover .logic b u{text-decoration:none;font-family:var(--sans);font-size:8pt;color:var(--muted);margin-left:1mm}
.cover .logic i{font-style:normal;font-size:7.8pt;color:var(--muted)}
.cover .logic em{font-style:normal;color:var(--line2);font-size:13pt;align-self:center}
.cover-q{margin-top:11mm;border-left:1.8pt solid var(--accent);padding-left:4.6mm;max-width:132mm}
.cover-q .h{font-size:6.8pt;letter-spacing:.18em;color:var(--faint);margin-bottom:1.4mm}
.cover-q div{font-size:9.2pt;line-height:1.9;color:var(--ink2)}
.cover-q b{color:var(--accent);font-weight:700;margin-right:2.4mm;font-family:var(--serif)}
.cover .kpis{
  margin-top:auto;display:grid;grid-template-columns:repeat(4,1fr);
  border-top:1pt solid var(--ink);padding-top:5mm;gap:6mm;
}
.kpi .v{font-family:var(--serif);font-size:24pt;line-height:1.05;font-weight:600;letter-spacing:-.02em}
.kpi .v em{font-style:normal;font-size:13pt;margin-left:1mm;color:var(--muted)}
.kpi .l{font-size:8.2pt;color:var(--ink2);margin-top:2.2mm;font-weight:600}
.kpi .s{font-size:7.2pt;color:var(--faint);margin-top:.8mm}
.cover .foot{display:flex;justify-content:space-between;align-items:flex-end;
  margin-top:7mm;font-size:7.4pt;color:var(--faint);letter-spacing:.06em}

/* generic section head */
.sec .head{margin-top:7mm;position:relative;padding-left:0}
.sec .num{
  font-family:var(--serif);font-size:13pt;color:var(--accent);font-weight:600;letter-spacing:.02em;
}
.sec .kick{font-size:7.4pt;letter-spacing:.22em;color:var(--faint);font-weight:600;margin-left:2mm}
h2.action{
  font-size:21.5pt;line-height:1.36;font-weight:600;letter-spacing:-.012em;
  margin:2.6mm 0 1.8mm;color:var(--ink);text-wrap:balance;
}
.sec .q{font-size:10.4pt;color:var(--muted);margin:0 0 3.2mm}
.verdict{
  display:flex;gap:3mm;align-items:baseline;background:var(--surface);
  border-left:2.4pt solid var(--accent);padding:2.6mm 3.4mm;margin:0 0 3.4mm;
  font-size:9.6pt;color:var(--ink2);line-height:1.65;
}
.verdict b{color:var(--accent);font-size:7.6pt;letter-spacing:.14em;white-space:nowrap}

/* exhibit */
.ex{margin:0 0 4mm}
.ex-head{display:flex;align-items:baseline;gap:3mm;border-top:1pt solid var(--ink);padding-top:2.4mm}
.ex-no{font-size:7.3pt;letter-spacing:.16em;color:var(--accent);font-weight:700;white-space:nowrap}
.ex-title{font-size:9.6pt;font-weight:700;color:var(--ink);line-height:1.45;flex:1}
.ex-unit{font-size:7.4pt;color:var(--faint);white-space:nowrap}
.chart{display:block;width:100%;height:auto;margin:2mm 0 0}
.ex-src{font-size:7pt;line-height:1.5;color:var(--faint);margin-top:1.6mm;
  border-top:.4pt dashed var(--line);padding-top:1.4mm}

/* body */
.prose{font-size:10pt;line-height:1.82;color:var(--ink2);text-align:justify}
.pblocks{display:flex;flex-direction:column;gap:2.4mm}
.pblock{display:grid;grid-template-columns:13mm 1fr;gap:4mm}
.plabel{font-size:6.6pt;letter-spacing:.14em;color:var(--accent);font-weight:700;padding-top:1.4mm}
.pblock p{margin:0;font-size:9.7pt;line-height:1.76;color:var(--ink2);text-align:justify;text-indent:2em}
.ptext{min-width:0}
.ptext p{margin:0;font-size:9.7pt;line-height:1.76;color:var(--ink2);text-align:justify;text-indent:2em}
.ptext p+p{margin-top:2.2mm}
.prose p{margin:0 0 2.6mm}
.prose b,.prose strong{color:var(--ink);font-weight:600}
.prose .so{color:var(--ink);font-weight:600}
sup{font-size:6.2pt;color:var(--accent);vertical-align:super;line-height:0;margin-left:.4mm;font-weight:700}
.boundary{
  margin-top:2.8mm;padding:2.4mm 3mm;border-left:1.6pt solid var(--line2);
  background:#FBFAF8;font-size:8.4pt;line-height:1.65;color:var(--muted);
}
.boundary b{color:var(--ink2);letter-spacing:.06em;font-size:7.6pt;margin-right:1.6mm}
.notes{
  position:absolute;left:18mm;right:18mm;bottom:13mm;
  border-top:.5pt solid var(--line);padding-top:1.8mm;
  font-size:6.9pt;line-height:1.55;color:var(--faint);
}
.notes .n{display:flex;gap:1.6mm;margin-bottom:.6mm}
.notes .n b{color:var(--accent);font-weight:700;min-width:3mm}
.notes .n span{flex:1}

/* summary */
.sum-head{margin-top:9mm}
.sum-head .kick{font-size:7.6pt;letter-spacing:.22em;color:var(--accent);font-weight:700}
.sum-head h2{font-size:26pt;line-height:1.3;font-weight:600;margin:2mm 0 0;letter-spacing:-.015em}
.sum-grid{display:grid;grid-template-columns:1.62fr 1fr;gap:9mm;margin-top:7mm}
.sum-list{display:flex;flex-direction:column}
.sum-item{display:grid;grid-template-columns:9mm 1fr;gap:2.5mm;padding:3.4mm 0;border-top:.5pt solid var(--line)}
.sum-item:first-child{border-top:1pt solid var(--ink)}
.sum-item .no{font-family:var(--serif);font-size:11pt;color:var(--accent);font-weight:600}
.sum-item .t{font-size:10.4pt;font-weight:700;line-height:1.5;color:var(--ink)}
.sum-item .e{font-size:8.5pt;color:var(--muted);line-height:1.65;margin-top:.8mm}
.one{background:var(--ink);color:#fff;padding:6mm 6mm 5.4mm;margin-top:1pt}
.one .k{font-size:7.2pt;letter-spacing:.20em;color:#D9C9A8;font-weight:700}
.one .x{font-family:var(--serif);font-size:15pt;line-height:1.6;margin-top:3mm;color:#fff}
.one .y{font-size:8.4pt;line-height:1.75;color:#C9D2DA;margin-top:3mm}
.scope{margin-top:6mm;font-size:8.4pt;color:var(--muted);line-height:1.8}
.scope b{color:var(--ink2)}
.acts{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin-top:7mm}
.act{border-top:1.6pt solid var(--accent);padding-top:2.6mm}
.act .t{font-size:9.4pt;font-weight:700}
.act .d{font-size:8.2pt;color:var(--muted);margin-top:1.2mm;line-height:1.7}
.sum-foot{margin-top:7mm;border-top:.5pt solid var(--line);padding-top:3mm;font-size:8.2pt;
  color:var(--muted);line-height:1.75}
.sum-foot b{color:var(--accent);letter-spacing:.08em;margin-right:2mm}
.evi{display:grid;grid-template-columns:repeat(4,1fr);gap:4mm;margin-top:8mm;
  border-top:.5pt solid var(--line);padding-top:4mm}
.evi .v{font-family:var(--serif);font-size:17pt;font-weight:600;line-height:1.1}
.evi .l{font-size:7.6pt;color:var(--muted);margin-top:1.2mm}
.scope2{display:grid;grid-template-columns:1fr 1fr;gap:4mm;margin-top:5mm}
.scope2 .box{background:var(--surface);padding:3.2mm 3.8mm;font-size:8.1pt;line-height:1.7;color:var(--muted)}
.scope2 .box b{display:block;color:var(--accent);font-size:7pt;letter-spacing:.14em;margin-bottom:1mm}
.must{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin-top:6mm;
  border-top:.5pt solid var(--line);padding-top:3mm;font-size:8.1pt;color:var(--muted);line-height:1.6}
.must b{display:block;color:var(--accent);font-size:6.9pt;letter-spacing:.12em;margin-bottom:.8mm}

/* toc */
.toc-head{margin-top:9mm}
.toc-head .kick{font-size:7.6pt;letter-spacing:.22em;color:var(--accent);font-weight:700}
.toc-head h2{font-size:25pt;font-weight:600;margin:2mm 0 0}
.toc-cols{display:grid;grid-template-columns:1fr 1fr;gap:0 10mm;margin-top:7mm}
.toc-row{display:flex;align-items:baseline;gap:2.4mm;padding:2.6mm 0;border-bottom:.5pt solid var(--line)}
a.toc-row{color:inherit}
a.toc-row:hover{color:inherit;border-bottom-color:var(--accent)}
.toc-row .no{font-family:var(--serif);font-size:9pt;color:var(--accent);min-width:6mm}
.toc-row .ti{font-size:9.4pt;font-weight:600;white-space:nowrap}
.toc-row .de{font-size:8pt;color:var(--muted);overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.toc-row .dots{flex:1;border-bottom:.5pt dotted var(--line2);transform:translateY(-1mm)}
.toc-row .pg{font-size:8.6pt;color:var(--ink2);font-weight:600}
.toc-note{margin-top:8mm;display:grid;grid-template-columns:1fr 1fr;gap:6mm}
.note-box{background:var(--surface);padding:4mm 4.4mm}
.note-box h4{margin:0 0 2mm;font-size:8pt;letter-spacing:.16em;color:var(--accent);font-weight:700}
.note-box p,.note-box li{font-size:8.2pt;line-height:1.75;color:var(--muted);margin:0}
.note-box ul{margin:0;padding-left:3.4mm}
.map3{display:grid;grid-template-columns:repeat(3,1fr);gap:3mm;margin-top:8mm}
.map3 .m{border-top:1pt solid var(--ink);padding-top:2mm}
.map3 .m .n{font-size:7.2pt;letter-spacing:.16em;color:var(--faint)}
.map3 .m .t{font-size:9pt;font-weight:700;margin-top:1mm}
.map3 .m .d{font-size:7.8pt;color:var(--muted);line-height:1.6;margin-top:.8mm}
.fig-index{margin-top:6mm;border-top:.5pt solid var(--line);padding-top:3mm}
.fig-index h4{margin:0 0 1.6mm;font-size:7.4pt;letter-spacing:.16em;color:var(--accent)}
.fig-cols{display:grid;grid-template-columns:1fr 1fr;gap:0 8mm}
.fig-row{display:flex;gap:2mm;font-size:7.6pt;padding:1mm 0;border-bottom:.4pt dotted var(--line)}
.fig-row .n{color:var(--accent);font-weight:700;min-width:8mm}
.fig-row .t{flex:1;color:var(--ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fig-row .p{color:var(--muted)}

/* tables */
table{width:100%;border-collapse:collapse;font-size:8.4pt;line-height:1.55}
th{text-align:left;font-weight:700;color:var(--muted);font-size:7.4pt;letter-spacing:.08em;
  border-bottom:1pt solid var(--ink);padding:2mm 2mm}
td{padding:2mm 2mm;border-bottom:.5pt solid var(--line);vertical-align:top;color:var(--ink2)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:1pt solid var(--ink)}
.tbl-cap{font-size:7.4pt;letter-spacing:.14em;color:var(--accent);font-weight:700;margin:0 0 1.8mm}
.tbl-title{font-size:9.4pt;font-weight:700;margin:0 0 2mm}

/* action page */
.act-head{margin-top:9mm}
.act-head .kick{font-size:7.6pt;letter-spacing:.22em;color:var(--accent);font-weight:700}
.act-head h2{font-size:25pt;font-weight:600;margin:2mm 0 1mm}
.act-head .q{font-size:10pt;color:var(--muted)}
.act-wrap{margin-top:5mm}
.act-wrap h3{font-size:9.6pt;letter-spacing:.10em;margin:5mm 0 2mm;color:var(--ink)}
.stop{margin-top:4mm;background:var(--accent-soft);border-left:2.4pt solid var(--accent);
  padding:3mm 3.4mm;font-size:8.6pt;color:var(--ink2)}
.stop b{color:var(--accent)}

/* appendix */
.ap-head{margin-top:9mm}
.ap-head .kick{font-size:7.6pt;letter-spacing:.22em;color:var(--accent);font-weight:700}
.ap-head h2{font-size:24pt;font-weight:600;margin:2mm 0 1mm}
.ap-head .q{font-size:9.6pt;color:var(--muted)}
.src-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 8mm;margin-top:4mm}
.src{display:grid;grid-template-columns:10mm 1fr 15mm;gap:1.4mm;align-items:baseline;
  padding:1.35mm 0;border-bottom:.4pt solid var(--line);font-size:7.5pt;line-height:1.4}
.src .id{color:var(--accent);font-weight:700;font-size:7pt}
.src .nm{color:var(--ink2);overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.src .dt{color:var(--faint);text-align:right;font-size:6.9pt}
.files{margin-top:5mm}
.files table{font-size:7.2pt}
.files td,.files th{padding:1.3mm 1.6mm}
.meta-list{margin-top:4mm}
.meta-row{display:grid;grid-template-columns:22mm 1fr;gap:2mm;padding:2.2mm 0;border-bottom:.4pt solid var(--line);font-size:8.4pt}
.meta-row .k{color:var(--accent);font-weight:700;font-size:7.4pt;letter-spacing:.08em}
.meta-row .v{color:var(--ink2);line-height:1.7}
.bullets{margin:0;padding-left:4mm;font-size:8.4pt;line-height:1.8;color:var(--ink2)}
.bullets li{margin-bottom:1mm}
.bullets li::marker{color:var(--accent)}
.back{background:var(--ink);color:#fff}
.back .inner{position:absolute;inset:0;padding:18mm;display:flex;flex-direction:column}
.back img{width:17mm;height:17mm;object-fit:contain;filter:grayscale(1) brightness(1.6)}
.back h2{font-family:var(--serif);font-size:30pt;font-weight:500;margin:12mm 0 0;color:#fff}
.back .back-sub{font-size:10pt;color:#C9D2DA;letter-spacing:.08em;margin-top:3mm}
.back p{font-size:9pt;line-height:1.9;color:#C9D2DA;max-width:145mm}
.back .foot{margin-top:auto;font-size:7.4pt;color:#8E9AA6;letter-spacing:.08em;line-height:1.9}
.back-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:4mm;margin-top:14mm;
  border-top:.5pt solid rgba(255,255,255,.16);padding-top:5mm}
.back-stats div{font-size:6.8pt;color:#8E9AA6;letter-spacing:.14em}
.back-stats b{display:block;font-family:var(--serif);font-size:21pt;color:#fff;font-weight:500;letter-spacing:0;margin-bottom:1mm}
.logo-card{width:28mm;height:28mm;background:#fff;border-radius:3mm;display:flex;
  align-items:center;justify-content:center;padding:3mm}
.logo-card img{width:22mm;height:22mm;object-fit:contain;filter:none}

/* retained action cards */
.keep{display:grid;grid-template-columns:repeat(4,1fr);gap:4mm;margin-top:5mm}
.keep .k{border-top:1.6pt solid var(--accent);padding-top:2.2mm}
.keep .v{font-family:var(--serif);font-size:18pt;font-weight:600;line-height:1.1}
.keep .t{font-size:8.4pt;font-weight:700;margin-top:1.2mm}
.keep .d{font-size:7.6pt;color:var(--muted);line-height:1.55;margin-top:.6mm}
.keep-line{margin-top:4mm;background:var(--surface);border-left:2.4pt solid var(--accent);
  padding:2.6mm 3.4mm;font-size:8.8pt;color:var(--ink2);line-height:1.7}
.keep-line b{letter-spacing:.06em;color:var(--accent);font-size:7.8pt;margin-right:2mm}
.keep-line b.hl{color:var(--accent);font-size:9.4pt;margin:0}

/* gantt */
.gantt{margin-top:2mm}
.g-row{display:grid;grid-template-columns:34mm 1fr;align-items:center;gap:3mm;
  border-bottom:.4pt solid var(--line);padding:1.8mm 0}
.g-l{font-size:8.2pt;color:var(--ink2)}
.g-track{position:relative;height:5.4mm;background:
  repeating-linear-gradient(to right,transparent 0,transparent calc(16.666% - .4pt),var(--line) calc(16.666% - .4pt),var(--line) 16.666%)}
.g-bar{position:absolute;top:1.2mm;height:3mm;background:var(--accent);opacity:.85;border-radius:1mm}
.g-head{display:grid;grid-template-columns:34mm 1fr;gap:3mm;font-size:6.8pt;letter-spacing:.12em;color:var(--faint)}
.g-head div:last-child{display:grid;grid-template-columns:repeat(6,1fr);text-align:center}

/* quality */
.q-table{font-size:8.2pt}
.q-table td:last-child{color:var(--accent);font-weight:700}


/* ---------- hybrid: research-note rail (data pages) ---------- */
.sec.rail-layout .head{margin-top:5mm}
.sec.rail-layout h2.action{font-size:20pt;line-height:1.32;margin:2mm 0 1.2mm}
.sec.rail-layout .q{margin-bottom:2.4mm}
.sec.rail-layout .verdict{margin-bottom:3mm}
.sec.rail-layout .chart{width:156mm}
.rail-float{float:right;width:43mm;margin:0 0 4mm 7mm;background:var(--surface);
  border-top:1.6pt solid var(--accent);padding:3.2mm 3.4mm 2.6mm}
.rail-h{font-size:6.6pt;letter-spacing:.16em;color:var(--accent);font-weight:700;margin-bottom:2mm}
.rail-k{padding:1.35mm 0;border-bottom:.4pt solid var(--line);position:relative}
.rail-k b{font-family:var(--serif);font-size:14pt;font-weight:600;line-height:1.05;display:block}
.rail-k span{font-size:7pt;color:var(--muted);display:block;margin-top:.4mm}
.rail-k i{position:absolute;right:0;top:1.8mm;font-style:normal;font-size:6.2pt;color:var(--faint)}
.rail-one{margin-top:2.4mm;background:var(--ink);color:#fff;padding:2.6mm 3mm;font-size:7.4pt;line-height:1.65}
.rail-one em{display:block;font-style:normal;color:#D9C9A8;font-size:6pt;letter-spacing:.14em;margin-bottom:1.1mm}
.rail-main .rp{margin:0 0 2.6mm}
.rail-main .rl{display:block;font-size:6.4pt;letter-spacing:.14em;color:var(--accent);
  font-weight:700;margin-bottom:1mm}
.rail-main p{margin:0;font-size:9.4pt;line-height:1.7;color:var(--ink2);text-align:justify}
.rail-clear{clear:both;height:0}

/* tooltip */
#tip{position:fixed;z-index:99;pointer-events:none;opacity:0;transition:opacity .12s;
  background:rgba(24,33,42,.94);color:#fff;font-size:8pt;line-height:1.5;
  padding:2mm 2.6mm;border-radius:2pt;max-width:60mm;transform:translate(10px,10px)}
@media print{
  body{background:#fff}
  .page{margin:0;box-shadow:none}
  #tip{display:none}
  .page{break-after:page}
}

@page{size:A4;margin:0}
@media print{
  html,body{width:210mm}
  .page{width:210mm;height:297mm}
  *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
"""

# kit 增补（与 v3 一致）
CSS += r""""""


def to_pdf(html_path: Path, pdf_path: Path) -> dict:
    if not Path(CHROME).exists():
        return {"ok": False, "error": "chrome not found"}
    uri = html_path.resolve().as_uri()
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
           "--virtual-time-budget=3000",
           f"--print-to-pdf={Path(pdf_path).resolve()}", uri]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=180)
    return {"ok": pdf_path.exists() and proc.returncode == 0,
            "returncode": proc.returncode,
            "stderr": (proc.stderr or "")[-800:]}

# --------------------------------------------------------------------------- #
# 基础组件
# --------------------------------------------------------------------------- #
def header(left: str, right: str) -> str:
    return f'<div class="rh"><span><b>{html.escape(left)}</b></span><span>{html.escape(right)}</span></div>'
def table(headers: list[str], rows: list[tuple], num_cols: set[int] | None = None,
          cls: str = "") -> str:
    num_cols = num_cols or set()
    th = "".join(
        f'<th class="{"num" if i in num_cols else ""}">{html.escape(h)}</th>'
        for i, h in enumerate(headers)
    )
    trs = []
    for row in rows:
        tds = "".join(
            f'<td class="{"num" if i in num_cols else ""}">{c}</td>'
            for i, c in enumerate(row)
        )
        trs.append(f"<tr>{tds}</tr>")
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table>'
def split_blocks(body: str, n: int = 3) -> list[str]:
    sents = [x for x in re.split(r"(?<=。)", body) if x.strip()]
    total = sum(len(x) for x in sents) or 1
    target = total / n
    groups: list[str] = []
    cur = ""
    acc = 0
    for s in sents:
        cur += s
        acc += len(s)
        if len(groups) < n - 1 and acc >= target * (len(groups) + 1):
            groups.append(cur)
            cur = ""
    if cur:
        groups.append(cur)
    while len(groups) < n:
        groups.append("")
    return groups
def notes_html(notes: list[str]) -> str:
    rows = "".join(
        f'<div class="n"><b>{i}</b><span>{html.escape(n)}</span></div>'
        for i, n in enumerate(notes, 1)
    )
    return f'<div class="notes">{rows}</div>'

# --------------------------------------------------------------------------- #
# 页构造器
# --------------------------------------------------------------------------- #
def _meta_html(meta: dict) -> str:
    rows = meta.get("sum_meta") or []
    if not rows:
        return ""
    return '<div class="sum-meta">' + "".join(
        f'<div><b>{k}</b>{v}</div>' for k, v in rows) + "</div>"


def footer(pn: int, total: int) -> str:
    return (f'<div class="rf"><span>{ORG} · 内部研究</span>'
            f'<span class="pn">{pn:02d} <i>/ {total:02d}</i></span></div>')
def page(inner: str, cls: str, pn: int, total: int,
         head: tuple[str, str] | None = None, sid: str = "") -> str:
    h = build.header(*head) if head else ""
    return f'<section class="page {cls}" id="{sid}">{h}{inner}{footer(pn, total)}</section>'
def cover(meta: dict, kpi: list[tuple[str, str, str]]) -> str:
    chips = "".join(
        f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div><div class="s">{s}</div></div>'
        for v, l, s in kpi
    )
    lg = meta.get("logic") or []
    logic = ""
    if lg:
        cells = []
        for i, (lab, val, note) in enumerate(lg):
            cells.append(f'<div><span>{lab}</span><b>{val}</b><i>{note}</i></div>')
            if i < len(lg) - 1:
                cells.append("<em>→</em>")
        logic = '<div class="logic">' + "".join(cells) + "</div>"
    qs = meta.get("questions") or []
    qhtml = ""
    if qs:
        qhtml = '<div class="cover-q"><div class="h">这份报告回答三个问题</div>' + "".join(
            f'<div><b>{no}</b>{q}</div>' for no, q in qs) + "</div>"
    cas = meta.get("cover_actions") or []
    cahtml = ""
    if cas:
        cahtml = '<div class="cover-a">' + "".join(
            f'<div><b>{k}</b><div class="t">{t}</div><div class="d">{d}</div></div>'
            for k, t, d in cas) + "</div>"
    return f"""
<div class="page cover"><div class="inner">
  <div class="top">
    <div class="brand"><img src="{build.LOGO}" alt="{ORG}"><div><div class="bw">{ORG}</div></div></div>
    <div class="chip">内部研究 · 2026.11</div>
  </div>
  <div class="mid">
    <div class="ck">{meta["kicker"]}</div>
    <h1 class="cover-t">{meta["title"]}</h1>
    <div class="rule"></div>
    <div class="sub">{meta["subtitle"]}</div>
    <div class="stand">{meta["standfirst"]}</div>
    {logic}
    {qhtml}
    {cahtml}
  </div>
  <div class="kpis">{chips}</div>
  <div class="foot"><span>{ORG} · 2026 年 11 月</span><span>{meta.get("asof", "")}</span></div>
</div></div>
"""
def summary_page(meta: dict, findings: list[tuple[str, str, str]],
                 one: str, actions: list[tuple[str, str]],
                 pn: int, total: int) -> str:
    items = "".join(
        f'<div class="sum-item"><div class="no">{no}</div><div>'
        f'<div class="t">{t}</div><div class="e">{e}</div></div></div>'
        for no, t, e in findings
    )
    acts = "".join(f'<div class="act"><div class="t">{t}</div><div class="d">{d}</div></div>'
                   for t, d in actions)
    inner = f"""
<div class="sum-head"><div class="kick">结论摘要 / EXECUTIVE SUMMARY</div><h2>{meta["sum_title"]}</h2></div>
<div class="sum-grid">
  <div class="sum-list">{items}</div>
  <div><div class="one"><div class="k">如果只做一件事</div><div class="x">{meta["one_x"]}</div>
  <div class="y">{one}</div></div>
  <div class="scope"><b>读法</b>：每节先给判断，再给数字、机理与边界；数字在页脚可回溯。</div></div>
</div>
<div class="acts">{acts}</div>
{_meta_html(meta)}
<div class="sum-foot"><b>边界</b>{meta.get("scope", "")}</div>
"""
    return page(inner, "summary", pn, total, ("结论摘要", meta["short"]), "summary")
def toc_page(meta: dict, entries: list[tuple[str, str, int]], pn: int, total: int) -> str:
    rows = "".join(
        f'<a class="toc-row" href="#{sid}"><span class="no">{no}</span>'
        f'<span class="ti">{lab}</span><span class="de">{desc}</span>'
        f'<span class="dots"></span><span class="pg">{pg}</span></a>'
        for no, sid, lab, desc, pg in entries
    )
    half = (len(entries) + 1) // 2
    parts = rows.split("</a>")
    parts = [x + "</a>" for x in parts if x]
    left, right = "".join(parts[:half]), "".join(parts[half:])
    ps = meta.get("parts") or []
    parts_html = ""
    if ps:
        parts_html = '<div class="toc-parts">' + "".join(
            f'<div><div class="p">{p}</div><div class="t">{t}</div><div class="d">{d}</div></div>'
            for p, t, d in ps) + "</div>"
    inner = f"""
<div class="toc-head"><div class="kick">目录 / CONTENTS</div><h2>{meta["toc_title"]}</h2></div>
{parts_html}
<div class="toc-cols"><div>{left}</div><div>{right}</div></div>
<div class="note-box" style="margin-top:8mm">
  <h4>阅读说明</h4>
  <p>单位与口径见图下；来源等级 A 政府/官方、B 行业报告、C 平台/媒体。上标对应页脚 S/D 编号；图和表的来源、样本、口径都写在图下。</p>
</div>
"""
    return page(inner, "toc", pn, total, ("目录", meta["short"]), "toc")
def section_page(s: dict, pn: int, total: int, fig_no: str,
                 chart_fn, meta: dict) -> str:
    fig = ""
    if s.get("chart"):
        fig = f"""
<figure class="ex">
  <div class="ex-head"><span class="ex-no">{fig_no}</span>
    <span class="ex-title">{s["fig_title"]}</span><span class="ex-unit">{s.get("fig_unit", "")}</span></div>
  {chart_fn()}
  <div class="{FIGURE_SRC_CLASSES}">{s["fig_src"]}</div>
</figure>"""
    else:
        rows = s["table"][1:]
        fig = f"""
<div class="ex">
  <div class="ex-head"><span class="ex-no">{fig_no}</span>
    <span class="ex-title">{s["table_title"]}</span><span class="ex-unit"></span></div>
  <div style="margin-top:3mm">{build.table(list(s["table"][0]), rows)}</div>
</div>"""
    blocks = build.split_blocks(s["body"], 3)
    labels = ("事实", "解释", "所以")
    head = f"""
<div class="head"><span class="num">{s["no"]}</span><span class="kick">{s["kicker"]}</span>
  <h2 class="action">{s["title"]}</h2><div class="q">{s["question"]}</div>
  <div class="verdict"><b>结论</b><span>{s["verdict"]}</span></div></div>"""
    rail = s.get("rail")
    if rail:
        items = "".join(
            f'<div class="rail-k"><b>{v}</b><span>{lab}</span><i>{u}</i></div>'
            for v, lab, u in rail["items"]
        )
        rail_html = (f'<aside class="rail-float"><div class="rail-h">关键数字 / KEY NUMBERS</div>'
                     f'{items}<div class="rail-one"><em>一句话</em>{rail["line"]}</div></aside>')
        main = "".join(
            f'<div class="rp"><span class="rl">{lab}</span><p>{txt}</p></div>'
            for lab, txt in zip(labels, blocks)
        )
        inner = (head + fig
                 + f'<div class="rail-main">{rail_html}{main}</div><div class="rail-clear"></div>'
                 + f'<div class="boundary"><b>边界</b>{s["boundary"]}</div>'
                 + build.notes_html(s["notes"]))
        return page(inner, "sec rail-layout", pn, total,
                    (f'{s["no"]} / {s["kicker"]}', meta["short"]), s["id"])
    pb = "".join(
        f'<div class="pblock"><span class="plabel">{lab}</span><p>{txt}</p></div>'
        for lab, txt in zip(labels, blocks) if txt.strip()
    )
    inner = f"""
<div class="sec-lead">{head}
{fig}</div>
<div class="pblocks">{pb}</div>
<div class="boundary"><b>边界</b>{s["boundary"]}</div>
{build.notes_html(s["notes"])}
"""
    return page(inner, "sec", pn, total,
                (f'{s["no"]} / {s["kicker"]}', meta["short"]), s["id"])
def action_page(title: str, question: str, rows: list[tuple],
                stop: str, pn: int, total: int, meta: dict) -> str:
    inner = f"""
<div class="act-head"><div class="kick">动作 / ACTION REGISTER</div>
  <h2>{title}</h2><div class="q">{question}</div></div>
<div class="act-wrap">
  {build.table(["#", "动作", "谁", "何时", "预算", "停止线", "验收"], rows)}
  <div class="stop"><b>统一停止线</b>　{stop}</div>
</div>
"""
    return page(inner, "actions", pn, total, ("动作清单", meta["short"]), "actions")
def appendix_page(title: str, subtitle: str, sources: list[tuple],
                  files: list[tuple], pn: int, total: int, meta: dict) -> str:
    src_rows = [(i, t, d) for i, t, d, *_ in sources]
    file_rows = [(f, k, n) for f, k, n in files]
    inner = f"""
<div class="ap-head"><div class="kick">附录 / EVIDENCE</div>
  <h2>{title}</h2><div class="q">{subtitle}</div></div>
<div class="files" style="margin-top:5mm">
  {build.table(["来源", "说明", "日期"], src_rows) if src_rows else ""}
  {('<div class="tbl-cap" style="margin-top:5mm">数据文件</div>' + build.table(["文件", "类型", "数字条数"], file_rows)) if file_rows else ""}
</div>
"""
    return page(inner, "appendix", pn, total, ("附录 · 证据", meta["short"]), "appendix")
def back_page(meta: dict) -> str:
    return f"""
<section class="page back" id="back"><div class="inner">
  <div class="logo-card"><img src="{build.LOGO}" alt="{ORG}"></div>
  <h2>{ORG}</h2>
  <p class="back-sub">内部研究 · 2026 年 11 月</p>
  <div class="foot">{meta.get("disclaimer", "")}</div>
</div></section>
"""
