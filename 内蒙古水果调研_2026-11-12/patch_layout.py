# -*- coding: utf-8 -*-
"""按反馈调整水果主报告：
1) KPI 指标带从开头移到最末尾（第 11 节「口径与分数」）
2) 删掉「结论清单」整节（与正文重复）
3) 删掉「附录 C · 复现命令」
"""
from pathlib import Path

p = Path(r"D:\蛙蛙呱呱\内蒙古水果调研_2026-11-12\render_r1.py")
t = p.read_text(encoding="utf-8")

# ---- 1) 顶部 KPI 带移除
top_strip = '''    body = []
    body.append(K.metric_strip([
        ("有效观测", f"{VALID_OBS:,}", f"L1+L2+L4+L5+L6；另弃用 B 级 {DISCARD} 条", "accent"),
        ("结论条数", str(len(L["claims"])), "每条挂来源与层号", ""),
        ("来源", str(len(L["sources"])), "部委 / 政府 / 交易所 / 研究机构", ""),
        ("保留率", f"{RETAIN:.0f}%", f"{VALID_OBS:,}/{VALID_OBS:,} 可回指", "healthy"),
        ("溯源率", "100%", f"0 条无源结论", "healthy"),
    ]))'''
assert top_strip in t
t = t.replace(top_strip, "    body = []")

# ---- 2) 结论清单整节 → 换成末尾的「口径与分数」
concl = '''    # 11 结论
    rows = []
    for c in L["claims"]:
        rows.append([c["id"], K.esc(_short_claim(c["text"])), c["kind"],
                     "/".join(c["source_ids"]), c.get("layer", "")])
    body.append(K.section("11", "结论清单（30 条，全部可回指）", f"""
{K.table(["ID", "结论", "类型", "来源", "层"], rows, cls="compact")}
{K.callout("本节只是索引：每条只留首句摘要，完整表述与支撑数字见上文对应章节，不在此重复。"
           "30 条结论对应 16 个来源、8 个数据层；r05 台账门禁与 r04 事实核查的结论见《技能调用审计.md》。", "healthy")}
"""))'''
assert concl in t
t = t.replace(concl, "    # 11 口径与分数（末尾）")

# ---- 3) 附录 C 删除
i = t.find('<details class="audit-ledger"><summary>附录 C · 复现命令</summary>')
assert i > 0
j = t.find("</details>", i) + len("</details>\n")
t = t[:i] + t[j:]

# ---- 4) 末尾追加 KPI 带（第 11 节）
anchor = "    body.append(_collapse_appendix(appendix))"
assert anchor in t
end_metrics = anchor + '''

    body.append(K.section("11", "口径与分数", f"""
{K.metric_strip([
        ("有效观测", f"{VALID_OBS:,}", f"L1+L2+L4+L5+L6；另弃用 B 级 {DISCARD} 条", "accent"),
        ("结论条数", str(len(L["claims"])), "每条挂来源与层号", ""),
        ("来源", str(len(L["sources"])), "部委 / 政府 / 交易所 / 研究机构", ""),
        ("保留率", f"{RETAIN:.0f}%", f"{VALID_OBS:,}/{VALID_OBS:,} 可回指", "healthy"),
        ("溯源率", f"{TRACE:.0f}%", "0 条无源结论", "healthy"),
    ])}
{K.callout("这几个数是这份报告的自检结果，放在最后：数据够不够、每个数字回不回得去、引用率多少。"
           "正文若与它们冲突，以正文的观测明细为准。", "healthy")}
"""))'''
t = t.replace(anchor, end_metrics, 1)

# ---- 5) TOC 与执行说明同步
t = t.replace("<a href=#s10>10 质量与冲突</a><a href=#s11>11 结论清单</a><a href=#appendix>附录 A/B/C</a>",
              "<a href=#s10>10 质量与冲突</a><a href=#s11>11 口径与分数</a><a href=#appendix>附录 A/B</a>")
t = t.replace("同品种同日省内价差 133.3%（C10）。数据层 8 个、有效观测 {VALID_OBS:,} 条、结论 30 条，全部可在附录回指。",
              "同品种同日省内价差 133.3%（C10）。数据层 8 个、有效观测 {VALID_OBS:,} 条；每条结论都已挂来源与层号，分数见文末第 11 节。")

# ---- 6) 去掉已无用的 _short_claim
k = t.find("def _short_claim(")
if k > 0:
    e = t.find("def build_r1()", k)
    t = t[:k] + t[e:]

p.write_text(t, encoding="utf-8")
print("patched render_r1: KPI 末尾 / 删结论清单 / 删附录C")
