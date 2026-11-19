# 证据包 · 内蒙古水果三城调研_2026-11-16

15 个来源文件 / 532 个数字。
写稿时引用 id；正文里的数字必须能在下表找到。

## 来源等级与核验

| id | 机构 | 类型 | 等级 | quote 状态 |
|---|---|---|---|---|
| `S01` | 农业农村部信息中心 | government | A | ok |
| `S02` | 农业农村部信息中心 | government | A | ok |
| `S03` | 农业农村部信息中心 | government | A | ok |
| `S04` | 呼和浩特市商务局 | government | A | ok |
| `S05` | 赤峰市商务局 | government | A | ok |
| `S06` | 赤峰市商务局 | government | A | ok |
| `S07` | 惠农网 | marketplace | C | ok |
| `S08` | 赤峰市农牧局 | government | A | ok |
| `S09` | 通辽市林草局 | government | A | ok |
| `S10` | 生鲜果品日度策略报告 | industry_report | B | ok |
| `S11` | 惠农网 | marketplace | C | unverified |
| `S12` | 惠农网 | marketplace | C | ok |
| `S13` | 惠农网/一亩田 | marketplace | C | unverified |
| `S14` | 惠农网 | marketplace | C | unverified |
| `S15` | 惠农网 | marketplace | C | mismatch |
| `S16` | 惠农网 | marketplace | C | ok |
| `S17` | 惠农网 | marketplace | C | mismatch |
| `S18` | 惠农网 | marketplace | C | mismatch |
| `S19` | 惠农网/一亩田 | marketplace | C | unverified |
| `S20` | 农业农村部市场与信息化司 | government | A | ok |
| `S21` | 内蒙古自治区林业和草原局 | government | A | ok |
| `S22` | 雨润集团/内蒙古新闻网 | media | C | unverified |
| `S23` | 全国城市农贸中心联合会 | industry_report | B | ok |
| `S24` | 新华网河南频道 | media | C | ok |
| `S25` | 农业农村部信息中心 | government | A | ok |
| `S26` | 内蒙古价格监测综合信息服务平台 | government | A | ok |
| `S27` | 商务部商务预报 | government | A | unverified |
| `S28` | 农业农村部信息中心 | government | A | unverified |
| `S29` | 北京新发地 | database | B | unverified |
| `S30` | 浙江在线 | media | C | unverified |
| `S31` | 新浪财经/光明网 | media | C | ok |
| `S32` | 食全食美集团 | media | C | ok |

## data/assumptions.json（11）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `A1` | 公路距离 | 850.0 | 公里 |  |  |
| `A2` | 包装+装卸+进场+资金 | 0.35 | 元/公斤 |  |  |
| `A3` | 干线运输单价 | 0.65 | 元/公斤·千公里 |  |  |
| `A4` | 损耗率 | 8.0 | % |  |  |
| `A5` | 分级溢价 | 30.0 | % |  |  |
| `A6` | 季节涨幅 | 2.0 | % |  |  |
| `A7` | 品类运营评分 | 10.0 | 分 |  |  |
| `A8` | 单车装载 | 28.0 | 吨/车 |  |  |
| `A9` | 礼盒单位毛利 | 8.8 | 元/公斤 |  |  |
| `A10` | 投入 | 180.0 | 万元 |  |  |
| `A11` | 跨城加仓停止线 | 0.3 | 元/公斤 |  |  |

## data/category_ops.csv（16）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `csv:category_ops:loss_pct:last` | loss_pct(last) | 8.0 |  |  |  |
| `csv:category_ops:loss_pct:max` | loss_pct(max) | 15.0 |  |  |  |
| `csv:category_ops:loss_pct:min` | loss_pct(min) | 5.0 |  |  |  |
| `csv:category_ops:loss_pct:mean` | loss_pct(mean) | 9.142857142857142 |  |  |  |
| `csv:category_ops:turnover_days:last` | turnover_days(last) | 10.0 |  |  |  |
| `csv:category_ops:turnover_days:max` | turnover_days(max) | 15.0 |  |  |  |
| `csv:category_ops:turnover_days:min` | turnover_days(min) | 2.0 |  |  |  |
| `csv:category_ops:turnover_days:mean` | turnover_days(mean) | 7.857142857142857 |  |  |  |
| `csv:category_ops:volatility_pct:last` | volatility_pct(last) | 30.0 |  |  |  |
| `csv:category_ops:volatility_pct:max` | volatility_pct(max) | 35.0 |  |  |  |
| `csv:category_ops:volatility_pct:min` | volatility_pct(min) | 6.0 |  |  |  |
| `csv:category_ops:volatility_pct:mean` | volatility_pct(mean) | 16.714285714285715 |  |  |  |
| `csv:category_ops:retail_price:last` | retail_price(last) | 52.0 |  |  |  |
| `csv:category_ops:retail_price:max` | retail_price(max) | 52.0 |  |  |  |
| `csv:category_ops:retail_price:min` | retail_price(min) | 6.13 |  |  |  |
| `csv:category_ops:retail_price:mean` | retail_price(mean) | 15.794285714285715 |  |  |  |

## data/chain_nodes.csv（12）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `csv:chain_nodes:to_hohhot_km:last` | to_hohhot_km(last) | 2600.0 |  |  |  |
| `csv:chain_nodes:to_hohhot_km:max` | to_hohhot_km(max) | 2600.0 |  |  |  |
| `csv:chain_nodes:to_hohhot_km:min` | to_hohhot_km(min) | 0.0 |  |  |  |
| `csv:chain_nodes:to_hohhot_km:mean` | to_hohhot_km(mean) | 812.5 |  |  |  |
| `csv:chain_nodes:to_baotou_km:last` | to_baotou_km(last) | 2700.0 |  |  |  |
| `csv:chain_nodes:to_baotou_km:max` | to_baotou_km(max) | 2700.0 |  |  |  |
| `csv:chain_nodes:to_baotou_km:min` | to_baotou_km(min) | 0.0 |  |  |  |
| `csv:chain_nodes:to_baotou_km:mean` | to_baotou_km(mean) | 908.75 |  |  |  |
| `csv:chain_nodes:to_chifeng_km:last` | to_chifeng_km(last) | 2900.0 |  |  |  |
| `csv:chain_nodes:to_chifeng_km:max` | to_chifeng_km(max) | 2900.0 |  |  |  |
| `csv:chain_nodes:to_chifeng_km:min` | to_chifeng_km(min) | 15.0 |  |  |  |
| `csv:chain_nodes:to_chifeng_km:mean` | to_chifeng_km(mean) | 883.125 |  |  |  |

## data/cost_model.csv（4）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `csv:cost_model:value:last` | value(last) | 0.05 |  |  |  |
| `csv:cost_model:value:max` | value(max) | 4.0 |  |  |  |
| `csv:cost_model:value:min` | value(min) | 0.02 |  |  |  |
| `csv:cost_model:value:mean` | value(mean) | 0.6411111111111111 |  |  |  |

## data/derived_extra.json（195）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `D_o2w_watermelon_cf_x` | 云南建水西瓜→赤峰西城倍数 | 2.7941 | 倍 | 2026-11-14~16 |  |
| `D_o2w_citrus_hh_o` | 广西恭城沙糖橘→呼市柑橘零售产地价 | 5.2 | 元/公斤 | 2026-11-14~16 |  |
| `D_o2w_citrus_hh_w` | 广西恭城沙糖橘→呼市柑橘零售销地价 | 7.15 | 元/公斤 | 2026-11-14~16 |  |
| `D_o2w_citrus_hh_gap` | 广西恭城沙糖橘→呼市柑橘零售价差 | 1.95 | 元/公斤 | 2026-11-14~16 |  |
| `D_o2w_citrus_hh_x` | 广西恭城沙糖橘→呼市柑橘零售倍数 | 1.375 | 倍 | 2026-11-14~16 |  |
| `D_cost_A` | A 宁城→赤峰西城 苹果到岸成本 | 4.74 | 元/公斤 | 2026-11-16 |  |
| `D_costA_origin` | A 宁城→赤峰西城 苹果产地价 | 4.0 | 元/公斤 | 2026-11-16 |  |
| `D_costA_pack` | A 宁城→赤峰西城 苹果包装 | 0.3 | 元/公斤 | 2026-11-16 |  |
| `D_costA_handle` | A 宁城→赤峰西城 苹果装卸短驳 | 0.05 | 元/公斤 | 2026-11-16 |  |
| `D_costA_transport` | A 宁城→赤峰西城 苹果干线运输 | 0.05 | 元/公斤 | 2026-11-16 |  |
| `D_costA_loss` | A 宁城→赤峰西城 苹果损耗摊销 | 0.22 | 元/公斤 | 2026-11-16 |  |
| `D_costA_stall` | A 宁城→赤峰西城 苹果进场档口 | 0.1 | 元/公斤 | 2026-11-16 |  |
| `D_costA_capital` | A 宁城→赤峰西城 苹果资金占用 | 0.02 | 元/公斤 | 2026-11-16 |  |
| `D_cost_B` | B 宁城→呼市 苹果直发到岸成本 | 5.53 | 元/公斤 | 2026-11-16 |  |
| `D_costB_origin` | B 宁城→呼市 苹果直发产地价 | 4.0 | 元/公斤 | 2026-11-16 |  |
| `D_costB_pack` | B 宁城→呼市 苹果直发包装 | 0.35 | 元/公斤 | 2026-11-16 |  |
| `D_costB_handle` | B 宁城→呼市 苹果直发装卸短驳 | 0.08 | 元/公斤 | 2026-11-16 |  |
| `D_costB_transport` | B 宁城→呼市 苹果直发干线运输 | 0.55 | 元/公斤 | 2026-11-16 |  |
| `D_costB_loss` | B 宁城→呼市 苹果直发损耗摊销 | 0.39 | 元/公斤 | 2026-11-16 |  |
| `D_costB_stall` | B 宁城→呼市 苹果直发进场档口 | 0.12 | 元/公斤 | 2026-11-16 |  |
| `D_costB_capital` | B 宁城→呼市 苹果直发资金占用 | 0.04 | 元/公斤 | 2026-11-16 |  |
| `D_cost_C` | C 宁城→雨润→呼市 苹果到岸成本 | 5.99 | 元/公斤 | 2026-11-16 |  |
| `D_costC_origin` | C 宁城→雨润→呼市 苹果产地价 | 4.0 | 元/公斤 | 2026-11-16 |  |
| `D_costC_pack` | C 宁城→雨润→呼市 苹果包装 | 0.35 | 元/公斤 | 2026-11-16 |  |
| `D_costC_handle` | C 宁城→雨润→呼市 苹果装卸短驳 | 0.1 | 元/公斤 | 2026-11-16 |  |
| `D_costC_hub` | C 宁城→雨润→呼市 苹果中转档口 | 0.25 | 元/公斤 | 2026-11-16 |  |
| `D_costC_transport` | C 宁城→雨润→呼市 苹果干线运输 | 0.55 | 元/公斤 | 2026-11-16 |  |
| `D_costC_loss` | C 宁城→雨润→呼市 苹果损耗摊销 | 0.57 | 元/公斤 | 2026-11-16 |  |
| `D_costC_stall` | C 宁城→雨润→呼市 苹果进场档口 | 0.12 | 元/公斤 | 2026-11-16 |  |
| `D_costC_capital` | C 宁城→雨润→呼市 苹果资金占用 | 0.05 | 元/公斤 | 2026-11-16 |  |
| `D_cost_D` | D 赵县→呼市 鸭梨到岸成本 | 1.76 | 元/公斤 | 2026-11-16 |  |
| `D_costD_origin` | D 赵县→呼市 鸭梨产地价 | 0.8 | 元/公斤 | 2026-11-16 |  |
| `D_costD_pack` | D 赵县→呼市 鸭梨包装 | 0.25 | 元/公斤 | 2026-11-16 |  |
| `D_costD_handle` | D 赵县→呼市 鸭梨装卸短驳 | 0.08 | 元/公斤 | 2026-11-16 |  |
| `D_costD_transport` | D 赵县→呼市 鸭梨干线运输 | 0.39 | 元/公斤 | 2026-11-16 |  |
| `D_costD_loss` | D 赵县→呼市 鸭梨损耗摊销 | 0.09 | 元/公斤 | 2026-11-16 |  |
| `D_costD_stall` | D 赵县→呼市 鸭梨进场档口 | 0.12 | 元/公斤 | 2026-11-16 |  |
| `D_costD_capital` | D 赵县→呼市 鸭梨资金占用 | 0.03 | 元/公斤 | 2026-11-16 |  |
| `D_cost_E` | E 河口→呼市 香蕉到岸成本 | 5.06 | 元/公斤 | 2026-11-16 |  |
| `D_costE_origin` | E 河口→呼市 香蕉产地价 | 2.52 | 元/公斤 | 2026-11-16 |  |
| `D_costE_pack` | E 河口→呼市 香蕉包装 | 0.3 | 元/公斤 | 2026-11-16 |  |
| `D_costE_handle` | E 河口→呼市 香蕉装卸短驳 | 0.1 | 元/公斤 | 2026-11-16 |  |
| `D_costE_transport` | E 河口→呼市 香蕉干线运输 | 1.69 | 元/公斤 | 2026-11-16 |  |
| `D_costE_loss` | E 河口→呼市 香蕉损耗摊销 | 0.28 | 元/公斤 | 2026-11-16 |  |
| `D_costE_stall` | E 河口→呼市 香蕉进场档口 | 0.12 | 元/公斤 | 2026-11-16 |  |
| `D_costE_capital` | E 河口→呼市 香蕉资金占用 | 0.05 | 元/公斤 | 2026-11-16 |  |
| `D_landed_B` | 宁城→呼市苹果到岸成本 | 5.53 | 元/公斤 | 2026-11-16 |  |
| `D_landed_C` | 宁城经雨润→呼市苹果到岸成本 | 5.99 | 元/公斤 | 2026-11-16 |  |
| `D_hub_extra` | 二次中转相对直发的到岸增量 | 0.46 | 元/公斤 | 2026-11-16 |  |
| `D_margin_A` | A 宁城→赤峰西城 苹果批发毛利 | 1.26 | 元/公斤 | 2026-11-16 |  |
| `D_marginpct_A` | A 宁城→赤峰西城 苹果批发毛利率 | 21.0 | % | 2026-11-16 |  |
| `D_margin_B` | B 宁城→呼市 苹果直发批发毛利 | 3.42 | 元/公斤 | 2026-11-16 |  |
| `D_marginpct_B` | B 宁城→呼市 苹果直发批发毛利率 | 38.2123 | % | 2026-11-16 |  |
| `D_margin_C` | C 宁城→雨润→呼市 苹果批发毛利 | 2.96 | 元/公斤 | 2026-11-16 |  |
| `D_marginpct_C` | C 宁城→雨润→呼市 苹果批发毛利率 | 33.0726 | % | 2026-11-16 |  |
| `D_margin_D` | D 赵县→呼市 鸭梨批发毛利 | 5.84 | 元/公斤 | 2026-11-16 |  |
| `D_marginpct_D` | D 赵县→呼市 鸭梨批发毛利率 | 76.8421 | % | 2026-11-16 |  |
| `D_margin_E` | E 河口→呼市 香蕉批发毛利 | 0.94 | 元/公斤 | 2026-11-16 |  |
| `D_marginpct_E` | E 河口→呼市 香蕉批发毛利率 | 15.6667 | % | 2026-11-16 |  |
| `D_banana_transport_share` | 河口→呼市香蕉运费占到岸成本 | 33.3992 | % | 2026-11-16 |  |
| … | 另有 135 条 | | | | |

## data/derived_metrics.json（120）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `D_呼和浩特_mean` | 呼和浩特东瓦窑水果简单均价 | 10.6 | 元/公斤 | 2026-11-16 |  |
| `D_呼和浩特_n` | 呼和浩特东瓦窑水果品类数 | 6.0 | 个 | 2026-11-16 |  |
| `D_包头_mean` | 包头友谊水果简单均价 | 5.67 | 元/公斤 | 2026-11-11 |  |
| `D_包头_n` | 包头友谊水果品类数 | 3.0 | 个 | 2026-11-11 |  |
| `D_赤峰_mean` | 赤峰西城水果简单均价 | 5.35 | 元/公斤 | 2026-11-16 |  |
| `D_赤峰_n` | 赤峰西城水果品类数 | 6.0 | 个 | 2026-11-16 |  |
| `D_common6_n` | 呼市与赤峰共有水果品类数 | 6.0 | 个 | 2026-11-16 |  |
| `D_common3_n` | 三城共有水果品类数 | 3.0 | 个 | 2026-11-11~16 |  |
| `D_common6_呼和浩特_mean` | 呼赤共有6品在呼和浩特的均价 | 10.6 | 元/公斤 | 2026-11-16 |  |
| `D_common6_赤峰_mean` | 呼赤共有6品在赤峰的均价 | 5.35 | 元/公斤 | 2026-11-16 |  |
| `D_common3_呼和浩特_mean` | 三城共有3品在呼和浩特的均价 | 9.2 | 元/公斤 | 2026-11-16 |  |
| `D_common3_包头_mean` | 三城共有3品在包头的均价 | 5.67 | 元/公斤 | 2026-11-11 |  |
| `D_common3_赤峰_mean` | 三城共有3品在赤峰的均价 | 5.53 | 元/公斤 | 2026-11-16 |  |
| `D_common6_cf_vs_hh` | 呼赤6品篮子赤峰/呼市倍数 | 0.5047 | 倍 | 2026-11-16 |  |
| `D_common3_bt_vs_hh` | 三城3品篮子包头/呼市倍数 | 0.6163 | 倍 | 2026-11-11~16 |  |
| `D_common3_cf_vs_hh` | 三城3品篮子赤峰/呼市倍数 | 0.6011 | 倍 | 2026-11-11~16 |  |
| `D_hhcf_富士苹果` | 富士苹果呼市/赤峰倍数 | 2.3333 | 倍 | 2026-11-16 |  |
| `D_hhcf_富士苹果_gap` | 富士苹果呼市-赤峰价差 | 8.0 | 元/公斤 | 2026-11-16 |  |
| `D_hhcf_巨峰葡萄` | 巨峰葡萄呼市/赤峰倍数 | 2.2059 | 倍 | 2026-11-16 |  |
| `D_hhcf_巨峰葡萄_gap` | 巨峰葡萄呼市-赤峰价差 | 8.2 | 元/公斤 | 2026-11-16 |  |
| `D_hhcf_菠萝` | 菠萝呼市/赤峰倍数 | 2.2059 | 倍 | 2026-11-16 |  |
| `D_hhcf_菠萝_gap` | 菠萝呼市-赤峰价差 | 8.2 | 元/公斤 | 2026-11-16 |  |
| `D_hhcf_西瓜` | 西瓜呼市/赤峰倍数 | 3.1579 | 倍 | 2026-11-16 |  |
| `D_hhcf_西瓜_gap` | 西瓜呼市-赤峰价差 | 4.1 | 元/公斤 | 2026-11-16 |  |
| `D_hhcf_香蕉` | 香蕉呼市/赤峰倍数 | 1.0345 | 倍 | 2026-11-16 |  |
| `D_hhcf_香蕉_gap` | 香蕉呼市-赤峰价差 | 0.2 | 元/公斤 | 2026-11-16 |  |
| `D_hhcf_鸭梨` | 鸭梨呼市/赤峰倍数 | 1.5833 | 倍 | 2026-11-16 |  |
| `D_hhcf_鸭梨_gap` | 鸭梨呼市-赤峰价差 | 2.8 | 元/公斤 | 2026-11-16 |  |
| `D_ratio3_富士苹果` | 富士苹果三城最高/最低倍数 | 2.333 | 倍 | 2026-11-11~16 |  |
| `D_ratio3_香蕉` | 香蕉三城最高/最低倍数 | 2.0 | 倍 | 2026-11-11~16 |  |
| `D_ratio3_鸭梨` | 鸭梨三城最高/最低倍数 | 1.583 | 倍 | 2026-11-11~16 |  |
| `D_ratio3_max` | 三城同品最大价差倍数 | 2.333 | 倍 | 2026-11-11~16 |  |
| `D_cv3_mean` | 三城同品平均变异系数 | 27.63 | % | 2026-11-11~16 |  |
| `D_wow_呼和浩特_6` | 呼和浩特6品篮子周环比 | 0.0 | % | 2026-11-09→11-16 |  |
| `D_wow_赤峰_6` | 赤峰6品篮子周环比 | 1.3258 | % | 2026-11-09→11-16 |  |
| `D_wow_cf_apple` | 赤峰富士苹果周环比 | 1.6949 | % | 2026-11-09→11-16 |  |
| `D_wow_cf_banana` | 赤峰香蕉周环比 | 1.7544 | % | 2026-11-09→11-16 |  |
| `D_wow_cf_watermelon` | 赤峰西瓜周环比 | 5.5556 | % | 2026-11-09→11-16 |  |
| `D_retail_hohhot` | 呼和浩特8种水果零售均价 | 10.49 | 元/公斤 | 2026-11-02~08 |  |
| `D_retail_chifeng` | 赤峰6种水果零售均价 | 9.71 | 元/公斤 | 2026-11-02~08 |  |
| `D_retail_gap` | 呼市-赤峰水果零售价差 | 0.78 | 元/公斤 | 2026-11-02~08 |  |
| `D_retail_gap_pct` | 呼市相对赤峰水果零售溢价 | 8.033 | % | 2026-11-02~08 |  |
| `D_retail_apple_hh` | 呼市apple零售价 | 13.88 | 元/公斤 | 2026-11 |  |
| `D_retail_apple_cf` | 赤峰apple零售价 | 13.63 | 元/公斤 | 2026-11 |  |
| `D_retail_apple_gap` | 呼市-赤峰apple零售价差 | 0.25 | 元/公斤 | 2026-11 |  |
| `D_retail_pear_hh` | 呼市pear零售价 | 7.48 | 元/公斤 | 2026-11 |  |
| `D_retail_pear_cf` | 赤峰pear零售价 | 6.55 | 元/公斤 | 2026-11 |  |
| `D_retail_pear_gap` | 呼市-赤峰pear零售价差 | 0.93 | 元/公斤 | 2026-11 |  |
| `D_retail_grape_hh` | 呼市grape零售价 | 16.01 | 元/公斤 | 2026-11 |  |
| `D_retail_grape_cf` | 赤峰grape零售价 | 16.05 | 元/公斤 | 2026-11 |  |
| `D_retail_grape_gap` | 呼市-赤峰grape零售价差 | -0.04 | 元/公斤 | 2026-11 |  |
| `D_retail_watermelon_hh` | 呼市watermelon零售价 | 6.52 | 元/公斤 | 2026-11 |  |
| `D_retail_watermelon_cf` | 赤峰watermelon零售价 | 5.73 | 元/公斤 | 2026-11 |  |
| `D_retail_watermelon_gap` | 呼市-赤峰watermelon零售价差 | 0.79 | 元/公斤 | 2026-11 |  |
| `D_retail_citrus_hh` | 呼市citrus零售价 | 7.15 | 元/公斤 | 2026-11 |  |
| `D_retail_citrus_cf` | 赤峰citrus零售价 | 9.01 | 元/公斤 | 2026-11 |  |
| `D_retail_citrus_gap` | 呼市-赤峰citrus零售价差 | -1.86 | 元/公斤 | 2026-11 |  |
| `D_retail_banana_hh` | 呼市banana零售价 | 7.81 | 元/公斤 | 2026-11 |  |
| `D_retail_banana_cf` | 赤峰banana零售价 | 7.27 | 元/公斤 | 2026-11 |  |
| `D_retail_banana_gap` | 呼市-赤峰banana零售价差 | 0.54 | 元/公斤 | 2026-11 |  |
| … | 另有 60 条 | | | | |

## data/market_prices_long.csv（4）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `csv:market_prices_long:price:last` | price(last) | 4.8 |  |  |  |
| `csv:market_prices_long:price:max` | price(max) | 15.0 |  |  |  |
| `csv:market_prices_long:price:min` | price(min) | 1.8 |  |  |  |
| `csv:market_prices_long:price:mean` | price(mean) | 7.703703703703703 |  |  |  |

## data/national_series.csv（12）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `csv:national_series:apple:last` | apple(last) | 8.95 |  |  |  |
| `csv:national_series:apple:max` | apple(max) | 9.56 |  |  |  |
| `csv:national_series:apple:min` | apple(min) | 8.95 |  |  |  |
| `csv:national_series:apple:mean` | apple(mean) | 9.36 |  |  |  |
| `csv:national_series:banana:last` | banana(last) | 5.25 |  |  |  |
| `csv:national_series:banana:max` | banana(max) | 6.47 |  |  |  |
| `csv:national_series:banana:min` | banana(min) | 5.25 |  |  |  |
| `csv:national_series:banana:mean` | banana(mean) | 5.798571428571429 |  |  |  |
| `csv:national_series:pear:last` | pear(last) | 5.92 |  |  |  |
| `csv:national_series:pear:max` | pear(max) | 6.81 |  |  |  |
| `csv:national_series:pear:min` | pear(min) | 5.92 |  |  |  |
| `csv:national_series:pear:mean` | pear(mean) | 6.585714285714286 |  |  |  |

## data/obs_fruit.json（37）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `O001` | 呼和浩特东瓦窑富士苹果批发价 | 14.0 | 元/公斤 | 2026-11-16 |  |
| `O002` | 呼和浩特东瓦窑鸭梨批发价 | 7.6 | 元/公斤 | 2026-11-16 |  |
| `O003` | 呼和浩特东瓦窑巨峰葡萄批发价 | 15.0 | 元/公斤 | 2026-11-16 |  |
| `O004` | 呼和浩特东瓦窑香蕉批发价 | 6.0 | 元/公斤 | 2026-11-16 |  |
| `O005` | 呼和浩特东瓦窑菠萝批发价 | 15.0 | 元/公斤 | 2026-11-16 |  |
| `O006` | 呼和浩特东瓦窑西瓜批发价 | 6.0 | 元/公斤 | 2026-11-16 |  |
| `O007` | 包头友谊富士苹果批发价 | 8.0 | 元/公斤 | 2026-11-11 |  |
| `O008` | 包头友谊鸭梨批发价 | 6.0 | 元/公斤 | 2026-11-11 |  |
| `O009` | 包头友谊香蕉批发价 | 3.0 | 元/公斤 | 2026-11-11 |  |
| `O010` | 赤峰西城富士苹果批发价 | 6.0 | 元/公斤 | 2026-11-16 |  |
| `O011` | 赤峰西城鸭梨批发价 | 4.8 | 元/公斤 | 2026-11-16 |  |
| `O012` | 赤峰西城巨峰葡萄批发价 | 6.8 | 元/公斤 | 2026-11-16 |  |
| `O013` | 赤峰西城香蕉批发价 | 5.8 | 元/公斤 | 2026-11-16 |  |
| `O014` | 赤峰西城菠萝批发价 | 6.8 | 元/公斤 | 2026-11-16 |  |
| `O015` | 赤峰西城西瓜批发价 | 1.9 | 元/公斤 | 2026-11-16 |  |
| `O016` | 赤峰宁城富士苹果产地价 | 6.0 | 元/公斤 | 2026-11-15 |  |
| `O017` | 赤峰宁城富士苹果产地价 | 5.0 | 元/公斤 | 2026-11-15 |  |
| `O018` | 赤峰宁城富士苹果产地价 | 4.0 | 元/公斤 | 2026-11-15 |  |
| `O019` | 赤峰宁城酵素苹果产地价 | 20.0 | 元/公斤 | 2026-10-22 |  |
| `O020` | 通辽塞外红苹果产地价 | 20.0 | 元/公斤 | 2025-12-16 |  |
| `O021` | 陕西洛川富士苹果产地价 | 7.0 | 元/公斤 | 2026-11-14 |  |
| `O022` | 陕西洛川富士苹果产地价 | 6.0 | 元/公斤 | 2026-11-14 |  |
| `O023` | 河北赵县鸭梨产地价 | 0.8 | 元/公斤 | 2026-11-15 |  |
| `O024` | 河北赵县雪花梨产地价 | 1.6 | 元/公斤 | 2026-11-15 |  |
| `O025` | 河北赵县雪花梨产地价 | 0.5 | 元/公斤 | 2026-11-15 |  |
| `O026` | 云南河口香蕉产地价 | 2.52 | 元/公斤 | 2026-11-14 |  |
| `O027` | 云南河口香蕉产地价 | 1.68 | 元/公斤 | 2026-11-14 |  |
| `O028` | 河北卢龙巨峰葡萄产地价 | 1.6 | 元/公斤 | 2026-11-15 |  |
| `O029` | 河北昌黎巨峰葡萄产地价 | 3.4 | 元/公斤 | 2026-11-14 |  |
| `O030` | 广西兴安沙糖橘产地价 | 6.4 | 元/公斤 | 2026-11-15 |  |
| `O031` | 广西恭城沙糖橘产地价 | 5.2 | 元/公斤 | 2026-11-15 |  |
| `O032` | 广西恭城沃柑产地价 | 2.6 | 元/公斤 | 2026-11-15 |  |
| `O033` | 广西荔浦沃柑产地价 | 7.02 | 元/公斤 | 2026-11-15 |  |
| `O034` | 云南建水西瓜产地价 | 0.68 | 元/公斤 | 2026-11-14 |  |
| `O035` | 云南瑞丽西瓜产地价 | 2.4 | 元/公斤 | 2026-11-15 |  |
| `O036` | 辽宁东港草莓产地价 | 31.7 | 元/公斤 | 2026-11-14 |  |
| `O037` | 辽宁东港草莓产地价 | 37.74 | 元/公斤 | 2026-11-15 |  |

## data/origin_prices.csv（4）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `csv:origin_prices:price:last` | price(last) | 37.74 |  |  |  |
| `csv:origin_prices:price:max` | price(max) | 37.74 |  |  |  |
| `csv:origin_prices:price:min` | price(min) | 0.5 |  |  |  |
| `csv:origin_prices:price:mean` | price(mean) | 7.901818181818182 |  |  |  |

## data/quote_gaps.json（3）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `facts:total` | total | 32.0 |  |  |  |
| `facts:ok` | ok | 20.0 |  |  |  |
| `facts:unverified` | unverified | 12.0 |  |  |  |

## data/retail_weekly.csv（36）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `csv:retail_weekly:n_items:last` | n_items(last) | 6.0 |  |  |  |
| `csv:retail_weekly:n_items:max` | n_items(max) | 8.0 |  |  |  |
| `csv:retail_weekly:n_items:min` | n_items(min) | 6.0 |  |  |  |
| `csv:retail_weekly:n_items:mean` | n_items(mean) | 6.666666666666667 |  |  |  |
| `csv:retail_weekly:avg_price:last` | avg_price(last) | 9.71 |  |  |  |
| `csv:retail_weekly:avg_price:max` | avg_price(max) | 10.49 |  |  |  |
| `csv:retail_weekly:avg_price:min` | avg_price(min) | 9.71 |  |  |  |
| `csv:retail_weekly:avg_price:mean` | avg_price(mean) | 9.97 |  |  |  |
| `csv:retail_weekly:wow_pct:last` | wow_pct(last) | 0.0 |  |  |  |
| `csv:retail_weekly:wow_pct:max` | wow_pct(max) | 0.6 |  |  |  |
| `csv:retail_weekly:wow_pct:min` | wow_pct(min) | 0.0 |  |  |  |
| `csv:retail_weekly:wow_pct:mean` | wow_pct(mean) | 0.2333333333333333 |  |  |  |
| `csv:retail_weekly:apple:last` | apple(last) | 13.63 |  |  |  |
| `csv:retail_weekly:apple:max` | apple(max) | 13.99 |  |  |  |
| `csv:retail_weekly:apple:min` | apple(min) | 13.63 |  |  |  |
| `csv:retail_weekly:apple:mean` | apple(mean) | 13.833333333333334 |  |  |  |
| `csv:retail_weekly:pear:last` | pear(last) | 6.55 |  |  |  |
| `csv:retail_weekly:pear:max` | pear(max) | 7.48 |  |  |  |
| `csv:retail_weekly:pear:min` | pear(min) | 6.55 |  |  |  |
| `csv:retail_weekly:pear:mean` | pear(mean) | 6.883333333333333 |  |  |  |
| `csv:retail_weekly:grape:last` | grape(last) | 16.05 |  |  |  |
| `csv:retail_weekly:grape:max` | grape(max) | 16.05 |  |  |  |
| `csv:retail_weekly:grape:min` | grape(min) | 15.67 |  |  |  |
| `csv:retail_weekly:grape:mean` | grape(mean) | 15.910000000000002 |  |  |  |
| `csv:retail_weekly:banana:last` | banana(last) | 7.27 |  |  |  |
| `csv:retail_weekly:banana:max` | banana(max) | 7.81 |  |  |  |
| `csv:retail_weekly:banana:min` | banana(min) | 7.2 |  |  |  |
| `csv:retail_weekly:banana:mean` | banana(mean) | 7.426666666666667 |  |  |  |
| `csv:retail_weekly:watermelon:last` | watermelon(last) | 5.73 |  |  |  |
| `csv:retail_weekly:watermelon:max` | watermelon(max) | 6.52 |  |  |  |
| `csv:retail_weekly:watermelon:min` | watermelon(min) | 5.63 |  |  |  |
| `csv:retail_weekly:watermelon:mean` | watermelon(mean) | 5.96 |  |  |  |
| `csv:retail_weekly:citrus:last` | citrus(last) | 9.01 |  |  |  |
| `csv:retail_weekly:citrus:max` | citrus(max) | 9.14 |  |  |  |
| `csv:retail_weekly:citrus:min` | citrus(min) | 7.15 |  |  |  |
| `csv:retail_weekly:citrus:mean` | citrus(mean) | 8.433333333333334 |  |  |  |

## data/scenarios.csv（24）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `csv:scenarios:overall_pct:last` | overall_pct(last) | 9.0 |  |  |  |
| `csv:scenarios:overall_pct:max` | overall_pct(max) | 9.0 |  |  |  |
| `csv:scenarios:overall_pct:min` | overall_pct(min) | -3.0 |  |  |  |
| `csv:scenarios:overall_pct:mean` | overall_pct(mean) | 2.6666666666666665 |  |  |  |
| `csv:scenarios:apple_pct:last` | apple_pct(last) | 5.0 |  |  |  |
| `csv:scenarios:apple_pct:max` | apple_pct(max) | 5.0 |  |  |  |
| `csv:scenarios:apple_pct:min` | apple_pct(min) | 0.0 |  |  |  |
| `csv:scenarios:apple_pct:mean` | apple_pct(mean) | 2.1 |  |  |  |
| `csv:scenarios:banana_pct:last` | banana_pct(last) | 15.0 |  |  |  |
| `csv:scenarios:banana_pct:max` | banana_pct(max) | 15.0 |  |  |  |
| `csv:scenarios:banana_pct:min` | banana_pct(min) | 5.0 |  |  |  |
| `csv:scenarios:banana_pct:mean` | banana_pct(mean) | 9.633333333333333 |  |  |  |
| `csv:scenarios:pear_pct:last` | pear_pct(last) | 2.0 |  |  |  |
| `csv:scenarios:pear_pct:max` | pear_pct(max) | 2.0 |  |  |  |
| `csv:scenarios:pear_pct:min` | pear_pct(min) | -4.0 |  |  |  |
| `csv:scenarios:pear_pct:mean` | pear_pct(mean) | -1.7 |  |  |  |
| `csv:scenarios:citrus_pct:last` | citrus_pct(last) | 2.0 |  |  |  |
| `csv:scenarios:citrus_pct:max` | citrus_pct(max) | 2.0 |  |  |  |
| `csv:scenarios:citrus_pct:min` | citrus_pct(min) | -15.0 |  |  |  |
| `csv:scenarios:citrus_pct:mean` | citrus_pct(mean) | -7.666666666666667 |  |  |  |
| `csv:scenarios:cherry_pct:last` | cherry_pct(last) | -20.0 |  |  |  |
| `csv:scenarios:cherry_pct:max` | cherry_pct(max) | -20.0 |  |  |  |
| `csv:scenarios:cherry_pct:min` | cherry_pct(min) | -35.0 |  |  |  |
| `csv:scenarios:cherry_pct:mean` | cherry_pct(mean) | -28.333333333333332 |  |  |  |

## data/spec_ladder.csv（4）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `csv:spec_ladder:price:last` | price(last) | 10.91 |  |  |  |
| `csv:spec_ladder:price:max` | price(max) | 10.91 |  |  |  |
| `csv:spec_ladder:price:min` | price(min) | 5.76 |  |  |  |
| `csv:spec_ladder:price:mean` | price(mean) | 8.09 |  |  |  |

## _pack/evidence_pack.json（50）

| id | 指标 | 值 | 单位 | 期 | 来源 |
|---|---|---|---|---|---|
| `csv:category_ops:loss_pct:last` | loss_pct(last) | 8.0 |  |  |  |
| `csv:category_ops:loss_pct:max` | loss_pct(max) | 15.0 |  |  |  |
| `csv:category_ops:loss_pct:min` | loss_pct(min) | 5.0 |  |  |  |
| `csv:category_ops:loss_pct:mean` | loss_pct(mean) | 9.142857142857142 |  |  |  |
| `csv:category_ops:turnover_days:last` | turnover_days(last) | 10.0 |  |  |  |
| `csv:category_ops:turnover_days:max` | turnover_days(max) | 15.0 |  |  |  |
| `csv:category_ops:turnover_days:min` | turnover_days(min) | 2.0 |  |  |  |
| `csv:category_ops:turnover_days:mean` | turnover_days(mean) | 7.857142857142857 |  |  |  |
| `csv:category_ops:volatility_pct:last` | volatility_pct(last) | 30.0 |  |  |  |
| `csv:category_ops:volatility_pct:max` | volatility_pct(max) | 35.0 |  |  |  |
| `csv:category_ops:volatility_pct:min` | volatility_pct(min) | 6.0 |  |  |  |
| `csv:category_ops:volatility_pct:mean` | volatility_pct(mean) | 16.714285714285715 |  |  |  |
| `csv:category_ops:retail_price:last` | retail_price(last) | 52.0 |  |  |  |
| `csv:category_ops:retail_price:max` | retail_price(max) | 52.0 |  |  |  |
| `csv:category_ops:retail_price:min` | retail_price(min) | 6.13 |  |  |  |
| `csv:category_ops:retail_price:mean` | retail_price(mean) | 15.794285714285715 |  |  |  |
| `csv:chain_nodes:to_hohhot_km:last` | to_hohhot_km(last) | 2600.0 |  |  |  |
| `csv:chain_nodes:to_hohhot_km:max` | to_hohhot_km(max) | 2600.0 |  |  |  |
| `csv:chain_nodes:to_hohhot_km:min` | to_hohhot_km(min) | 0.0 |  |  |  |
| `csv:chain_nodes:to_hohhot_km:mean` | to_hohhot_km(mean) | 812.5 |  |  |  |
| `csv:chain_nodes:to_baotou_km:last` | to_baotou_km(last) | 2700.0 |  |  |  |
| `csv:chain_nodes:to_baotou_km:max` | to_baotou_km(max) | 2700.0 |  |  |  |
| `csv:chain_nodes:to_baotou_km:min` | to_baotou_km(min) | 0.0 |  |  |  |
| `csv:chain_nodes:to_baotou_km:mean` | to_baotou_km(mean) | 908.75 |  |  |  |
| `csv:chain_nodes:to_chifeng_km:last` | to_chifeng_km(last) | 2900.0 |  |  |  |
| `csv:chain_nodes:to_chifeng_km:max` | to_chifeng_km(max) | 2900.0 |  |  |  |
| `csv:chain_nodes:to_chifeng_km:min` | to_chifeng_km(min) | 15.0 |  |  |  |
| `csv:chain_nodes:to_chifeng_km:mean` | to_chifeng_km(mean) | 883.125 |  |  |  |
| `csv:cost_model:value:last` | value(last) | 0.05 |  |  |  |
| `csv:cost_model:value:max` | value(max) | 4.0 |  |  |  |
| `csv:cost_model:value:min` | value(min) | 0.02 |  |  |  |
| `csv:cost_model:value:mean` | value(mean) | 0.6411111111111111 |  |  |  |
| `facts:sources[0].numbers` | sources[0].numbers | 11.0 |  |  |  |
| `facts:sources[1].numbers` | sources[1].numbers | 16.0 |  |  |  |
| `facts:sources[2].numbers` | sources[2].numbers | 12.0 |  |  |  |
| `facts:sources[3].numbers` | sources[3].numbers | 4.0 |  |  |  |
| `facts:sources[4].numbers` | sources[4].numbers | 195.0 |  |  |  |
| `facts:sources[5].numbers` | sources[5].numbers | 120.0 |  |  |  |
| `facts:sources[6].numbers` | sources[6].numbers | 4.0 |  |  |  |
| `facts:sources[7].numbers` | sources[7].numbers | 12.0 |  |  |  |
| `facts:sources[8].numbers` | sources[8].numbers | 37.0 |  |  |  |
| `facts:sources[9].numbers` | sources[9].numbers | 4.0 |  |  |  |
| `facts:sources[10].numbers` | sources[10].numbers | 3.0 |  |  |  |
| `facts:sources[11].numbers` | sources[11].numbers | 36.0 |  |  |  |
| `facts:sources[12].numbers` | sources[12].numbers | 24.0 |  |  |  |
| `facts:sources[13].numbers` | sources[13].numbers | 4.0 |  |  |  |
| `facts:sources[14].numbers` | sources[14].numbers | 49.0 |  |  |  |
| `facts:counts.files` | counts.files | 15.0 |  |  |  |
| `facts:counts.numbers` | counts.numbers | 531.0 |  |  |  |
| `facts:counts.source_records` | counts.source_records | 32.0 |  |  |  |
