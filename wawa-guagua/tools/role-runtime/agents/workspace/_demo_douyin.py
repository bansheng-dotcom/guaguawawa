# -*- coding: utf-8 -*-
"""演示：抖音店铺上月销售额 -10% 的根因归因（合成数据 + 真实 R06 技能）。

构造一份「抖店」两个月的经营数据（前月=基线 100000，上月=90000，-10%），
埋入一个真实驱动因素：直播渠道爆款商品A转化率腰斩。
流程：构造数据 → 按流量来源贡献分解 → 按商品下钻 → 流量×转化×客单价三因子分解。
"""
import argparse
import os
import sys

_AGENTS = r"D:\一人公司\agents"
_R06 = os.path.join(_AGENTS, "r06-wadeqing-analyst")
for _p in (_R06, _AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skills import s04_rootcause, _common as c  # noqa: E402

OUT = os.path.join(_AGENTS, "workspace", "artifacts", "douyin_demo")
os.makedirs(OUT, exist_ok=True)


def ns(**kw):
    return argparse.Namespace(**kw)


def build_data(path):
    """channel, product, month, visitors, orders, revenue。
    前月总收入 100000；上月 90000（-10%）。直播的爆款商品A 腰斩是主因。
    """
    rows = [
        # 直播（驱动因素：商品A 前月30000→上月15000）
        dict(channel="直播", product="商品A", month="前月", visitors=25000, orders=667, revenue=30000),
        dict(channel="直播", product="商品A", month="上月", visitors=25000, orders=333, revenue=15000),
        dict(channel="直播", product="商品B", month="前月", visitors=15000, orders=222, revenue=10000),
        dict(channel="直播", product="商品B", month="上月", visitors=15000, orders=222, revenue=10000),
        dict(channel="直播", product="商品C", month="前月", visitors=10000, orders=111, revenue=5000),
        dict(channel="直播", product="商品C", month="上月", visitors=10000, orders=111, revenue=5000),
        # 短视频（持平）
        dict(channel="短视频", product="综合", month="前月", visitors=40000, orders=625, revenue=25000),
        dict(channel="短视频", product="综合", month="上月", visitors=40000, orders=625, revenue=25000),
        # 商品卡（持平）
        dict(channel="商品卡", product="综合", month="前月", visitors=50000, orders=500, revenue=20000),
        dict(channel="商品卡", product="综合", month="上月", visitors=50000, orders=500, revenue=20000),
        # 达人（上涨，部分对冲）
        dict(channel="达人", product="综合", month="前月", visitors=20000, orders=200, revenue=10000),
        dict(channel="达人", product="综合", month="上月", visitors=30000, orders=300, revenue=15000),
    ]
    c.write_csv(path, ["channel", "product", "month", "visitors", "orders", "revenue"], rows)
    return rows


def three_factor(rows):
    """销售额 = 访客数 × 转化率 × 客单价；对每个渠道做 before→after 驱动分解。"""
    agg = {}
    for r in rows:
        a = agg.setdefault(r["channel"], {"before": [0, 0, 0.0], "after": [0, 0, 0.0]})
        v, o, rev = int(r["visitors"]), int(r["orders"]), float(r["revenue"])
        key = "before" if r["month"] == "前月" else "after"
        a[key][0] += v
        a[key][1] += o
        a[key][2] += rev
    out = []
    for ch, d in agg.items():
        v0, o0, r0 = d["before"]
        v1, o1, r1 = d["after"]
        conv0 = o0 / v0 if v0 else 0.0
        conv1 = o1 / v1 if v1 else 0.0
        aov0 = r0 / o0 if o0 else 0.0
        aov1 = r1 / o1 if o1 else 0.0
        # 连锁替代法：先流量，再转化，再客单价
        contrib_visit = (v1 - v0) * conv0 * aov0
        contrib_conv = v0 * (conv1 - conv0) * aov0
        contrib_aov = v0 * conv0 * (aov1 - aov0)
        out.append({
            "channel": ch,
            "revenue_before": round(r0, 2), "revenue_after": round(r1, 2),
            "delta": round(r1 - r0, 2),
            "visitors_before": v0, "visitors_after": v1,
            "conv_before_pct": round(conv0 * 100, 2), "conv_after_pct": round(conv1 * 100, 2),
            "aov_before": round(aov0, 2), "aov_after": round(aov1, 2),
            "contrib_visit": round(contrib_visit, 2),
            "contrib_conv": round(contrib_conv, 2),
            "contrib_aov": round(contrib_aov, 2),
        })
    return out


def build_report(decomp_ch, decomp_prod, factors, out_path):
    L = []
    L.append("# [R06 蛙得清] 抖音店铺上月销售额 -10% 根因归因（演示）\n")
    L.append("> 数据为**合成演示数据**（前月 10 万 → 上月 9 万，-10%），仅演示真实分析流程。\n")

    # 三因子分解
    L.append("## 第一步：销售公式三因子分解（流量 × 转化 × 客单价）\n")
    L.append("| 渠道 | 前月收入 | 上月收入 | Δ收入 | 访客数变化 | 转化率变化 | 客单价变化 | 流量贡献 | 转化贡献 | 客单价贡献 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for f in sorted(factors, key=lambda x: -abs(x["delta"])):
        L.append(
            f"| {f['channel']} | {f['revenue_before']:,.0f} | {f['revenue_after']:,.0f} "
            f"| {f['delta']:+,.0f} "
            f"| {f['visitors_before']:,}→{f['visitors_after']:,} "
            f"| {f['conv_before_pct']}%→{f['conv_after_pct']}% "
            f"| {f['aov_before']:.0f}→{f['aov_after']:.0f} "
            f"| {f['contrib_visit']:+,.0f} | {f['contrib_conv']:+,.0f} | {f['contrib_aov']:+,.0f} |"
        )
    L.append("")

    # 渠道贡献分解
    total_ch = decomp_ch["total_change"]
    L.append("## 第二步：按流量来源的贡献分解（谁在拖累整体 -10%）\n")
    L.append("| 流量来源 | 前月 | 上月 | Δ | 贡献度 |")
    L.append("|---|---|---|---|---|")
    for s in decomp_ch["segments"]:
        if s["delta"] < 0:
            flag = " ← 主要拖累" if abs(s["delta"]) >= abs(total_ch) * 0.5 else " ← 拖累"
        elif s["delta"] > 0:
            flag = " ← 部分对冲"
        else:
            flag = ""
        L.append(f"| {s['segment']} | {s['before']:,.0f} | {s['after']:,.0f} | {s['delta']:+,.0f} | {s['contribution_pct']:+.1f}%{flag} |")
    L.append("")

    # 商品下钻
    total_prod = decomp_prod["total_change"]
    L.append("## 第三步：下钻到直播渠道内部——哪个商品塌了\n")
    L.append("| 商品 | 前月 | 上月 | Δ | 贡献度 |")
    L.append("|---|---|---|---|---|")
    for s in decomp_prod["segments"]:
        flag = " ← 根因" if s["delta"] < 0 and abs(s["delta"]) >= abs(total_prod) * 0.5 else ""
        L.append(f"| {s['segment']} | {s['before']:,.0f} | {s['after']:,.0f} | {s['delta']:+,.0f} | {s['contribution_pct']:+.1f}%{flag} |")
    L.append("")

    # 结论
    L.append("## 结论（不超过数据边界）\n")
    L.append("1. 整体 -10% 中，**直播渠道贡献 -150%**（-15,000），被达人渠道 +50%（+5,000）部分对冲，短视频/商品卡持平。")
    L.append("2. 直播下跌**几乎全部来自转化率**（2.0% → 1.33%），访客数没掉、客单价没变——即「人还在看，但下单变少」。")
    L.append("3. 直播内部，**商品A（爆款）销售额腰斩**（30,000 → 15,000），商品B/C 持平 → 根因锁定商品A（下架/断货/差评/改价）。")
    L.append("4. **待你补真数据验证的假设**：商品A 是否下架、断货、差评、提价，或直播间场次/主播更换。")
    L.append("")
    L.append("## 换真实数据怎么接\n")
    L.append("- 把「抖店-罗盘」导出替换 `douyin_sales.csv`，列名对齐 `channel/product/month/visitors/orders/revenue`。")
    L.append("- 若有真实「流量来源」「商品SKU」「直播场次」维度，第二步/第三步的下钻会自动换成真实口径。")
    L.append("")
    c.write_text(out_path, "\n".join(L))
    return "\n".join(L)


def main():
    csv_path = os.path.join(OUT, "douyin_sales.csv")
    rows = build_data(csv_path)

    decomp_ch = s04_rootcause.run(ns(action="decompose", input=csv_path, dim="channel",
                                    value="revenue", period="month", before="前月", after="上月"))
    # 直播渠道内部按商品下钻
    live_rows = [r for r in rows if r["channel"] == "直播"]
    live_csv = os.path.join(OUT, "douyin_live_products.csv")
    c.write_csv(live_csv, ["channel", "product", "month", "visitors", "orders", "revenue"], live_rows)
    decomp_prod = s04_rootcause.run(ns(action="decompose", input=live_csv, dim="product",
                                      value="revenue", period="month", before="前月", after="上月"))

    factors = three_factor(rows)

    c.write_json(os.path.join(OUT, "decompose_channel.json"), decomp_ch)
    c.write_json(os.path.join(OUT, "decompose_product.json"), decomp_prod)
    c.write_json(os.path.join(OUT, "three_factor.json"), factors)

    report = build_report(decomp_ch, decomp_prod, factors,
                          os.path.join(OUT, "analysis_report.md"))

    c.emit({"out_dir": OUT, "overall_delta": decomp_ch["total_change"],
            "live_contribution": decomp_ch["segments"][0],
            "root_product": decomp_prod["segments"][0]})


if __name__ == "__main__":
    main()
