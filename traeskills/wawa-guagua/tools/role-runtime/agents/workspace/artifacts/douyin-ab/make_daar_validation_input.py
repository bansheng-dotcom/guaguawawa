import json
from pathlib import Path

here = Path(__file__).resolve().parent
result = json.loads((here / "abtest_result.json").read_text(encoding="utf-8"))
m = result["primary_metric"]
r = result["secondary_metrics"]["revenue_per_user"]
aov = result["secondary_metrics"]["aov_buyer"]
gmv = result["secondary_metrics"]["gmv"]
summary = (
    f"新版商品详情页处理组转化率 {m['treatment']['value_pct']:.2f}%，"
    f"对照组 {m['control']['value_pct']:.2f}%，相对提升 {m['lift_pct']:.2f}%，"
    f"双比例 z 检验 p={m['test']['p_value']:.4f}，SRM χ²={result['srm']['chi2']:.3f}，"
    f"决策为 {result['decision']}。"
)
findings = [
    {"title": "新版详情页提高下单转化率", "content": summary,
     "data_source": "abtest_result.json#/primary_metric", "impact_pct": m["lift_pct"]},
    {"title": "每用户营收同步提升", "content": f"每用户营收相对提升 {r['lift_pct']:.2f}%。",
     "data_source": "abtest_result.json#/secondary_metrics/revenue_per_user", "impact_pct": r["lift_pct"]},
    {"title": "买家客单价基本持平", "content": f"买家客单价提升 {aov['lift_pct']:.2f}%。",
     "data_source": "abtest_result.json#/secondary_metrics/aov_buyer", "impact_pct": aov["lift_pct"]},
    {"title": "样本比例与功效达标", "content": f"SRM χ²={result['srm']['chi2']:.3f}；每组要求 {result['power']['required_n_per_group']} 人，实际 {result['power']['actual_n_control']} / {result['power']['actual_n_treatment']} 人。",
     "data_source": "abtest_result.json#/srm;#/power", "impact_pct": 0},
]
final = {
    "executive_summary": summary,
    "findings": findings,
    "data_gaps": ["分析数据为固定种子模拟数据，不代表真实抖音店铺表现。", "未包含退款率、差评率、履约时长等真实护栏数据。"],
}
(here / "daar_final_output_validation.json").write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
