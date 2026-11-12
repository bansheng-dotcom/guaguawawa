# -*- coding: utf-8 -*-
"""生成 R04 事实核查输入：把台账里的关键结论逐条挂到可定位的证据串上。

规则（与 r04 skills/s05_facts 一致）：
  numbers   = 结论里出现的全部数字，必须在 source 中逐字出现；
  source    = 该结论的复算证据行（层号 + 来源 + 计算式），不是结论本身；
  key_assertions = 可定位的关键断言片段。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
L = json.loads((ROOT / "data" / "证据台账.json").read_text(encoding="utf-8"))
M = json.loads((ROOT / "data" / "底稿指标.json").read_text(encoding="utf-8"))
BY_ID = {c["id"]: c for c in L["claims"]}

# 证据串：层号 + 观测统计 + 关键数值（与结论同源、同一精度）
EVID = {
    "C1": ("primary", "L1 全国日度（S1）：38 个交易日；首值 6.65（2026-09-15）、末值 6.62（2026-11-12）；"
                       "区间 6.47—6.78；振幅 4.79%；是否正常见 C31 同期基线"),
    "C2": ("primary", "L1 分月均值：9 月下半月 12 日 6.641；10 月 17 日 6.642；11 月 9 日 6.671；月均抬升 0.46%"),
    "C4": ("primary", "L2 周度篮子（S2）：基期 20260821-20260827；9 周累计 -4.47%；西瓜 +33.22%；富士苹果 -2.81%；鸭梨 -3.15%；"
                       "菠萝 -6.08%；香蕉 -7.41%；巨峰葡萄 -13.54%"),
    "C7": ("primary", "L4 呼市零售（S3）：2026-09-07~09-13 的 10.21 元/公斤；2026-11-02~11-08 的 10.49 元/公斤；"
                         "9 周 +2.74%；区间 10.21—10.49；全国批发端 -4.47%；传导差 7.21 个百分点"),
    "C10": ("primary", "L10 新发地分规格（S17）+ L6（S5）：2026-11-11 呼市 14.00 vs 赤峰 6.00，总差 8.00（2.33 倍）；"
                        "规格跨度 5.15（64.4%）；同规格区域溢价 3.09（38.6%）；赤峰高于最低 0.24；校验 8.00；旧口径 133.3%"),
    "C11": ("primary", "L6（S5）+ L10（S17）：57 个样本市场；呼市 14.00；全国中位数 8.00；"
                        "新发地最高规格 10.91（窗口）/10.30（当日）；同规格溢价 3.09（38.6%）；赤峰高于最低 0.24；呼市较中位数高 75.0%；赤峰 6.00"),
    "C12": ("primary", "L6（S4/S5）：57 个市场；min 3.40；p25 6.80；median 8.00；p75 10.00；max 14.00；极差 4.12 倍"),
    "C13": ("primary", "跨层（S3/S2/S5）：呼市苹果零售 13.88 ÷ 全国富士苹果批发 8.64 = 1.61 倍；"
                        "13.88 ÷ 赤峰产地 6.00 = 2.31 倍"),
    "C14": ("primary", "跨层（S3/S2）：批零价差 5.24 元/公斤；占零售价 37.8%；宁城折算 4.88 元/公斤"),
    "C15": ("primary", "L5 期货（S6/S7）：AP0 36 个交易日 7388→5964 元/吨，-19.27%，最大回撤 -25.85%；"
                        "CJ0 -12.43%"),
    "C18": ("primary", "L7（S9/S14）：内蒙古 2025 年 224.92 万吨；2024 年 201.56 万吨；+11.59%；"
                          "全国 35404.72 万吨（+4.24%）"),
    "C19": ("primary", "L7（S10）：宁城 25 万亩；盛果期 9.5 万亩；16.8 万吨；8.2 亿元；折算 4.88 元/公斤；"
                          "2024 年销售 16.79 万吨"),
    "C22": ("primary", "L7/跨层（S8/S13/S3）：人均 77.6 公斤；2374 万人；184.2 万吨；10.49 元/公斤；"
                          "193.2 亿元；敏感性 161.4—197.0 万吨"),
    "C24": ("primary", "L3（S15）：680 条报价；34 个品种序列；21 条常量；常量率 61.8%；苹果 18.00 vs 东瓦窑 14.00，差 28.6%"),
    "C31": ("primary", "L9 同期基线（S1/S18）：2026 窗口均值 6.6484；2025 年 7.0062（-5.11%）；"
                          "2024 年 7.2559（-8.37%）；2023 年 6.6167（+0.48%）；2022 年 6.5085（+2.15%）"),
    "C32": ("primary", "L10（S17）：2026 年 Φ70-84 报价 73 个交易日恒为 7.60；单日同比 +22.6%；窗口均值高规格 11.02→10.91（-1.0%）；"
                        "中规格 9.03→7.60（-15.8%）；低规格 6.78→5.76（-15.0%）"),
    "C33": ("primary", "L10（S17）：规格占 64.4%；区域溢价占 38.6%，折合 3.09 元/公斤；"
                        "冷链 750 km 约 0.21 元/公斤，不足以解释"),
}

FACTS = []
for cid, (stype, src) in EVID.items():
    claim = BY_ID[cid]["text"]
    nums = re.findall(r"\d+(?:\.\d+)?", claim)
    # 断言片段：从证据串里取（保证可在 source 中定位）
    parts = [p.strip() for p in re.split(r"[；：，]", src) if len(p.strip()) >= 6][:2]
    FACTS.append({"id": "F" + cid[1:], "claim_id": cid, "claim": claim,
                  "numbers": nums, "source": src, "source_type": stype,
                  "key_assertions": parts})

if __name__ == "__main__":
    out = ROOT / "data" / "facts_check.json"
    out.write_text(json.dumps({"facts": FACTS}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"facts {len(FACTS)} 条 -> {out}")
    for f in FACTS:
        missing = [n for n in f["numbers"] if n not in f["source"]]
        print(f"  {f['id']}: numbers={len(f['numbers'])} missing={missing}")
