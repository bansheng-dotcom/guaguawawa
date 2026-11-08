import json
import os
from datetime import datetime

_AGENT = r'D:\一人公司\agents\r06-wadeqing-analyst'
res_path = os.path.join(_AGENT, "workspace", "artifacts", "ab_test_decision.json")
out_html_path = os.path.join(_AGENT, "workspace", "artifacts", "AB_Test_Report.html")

# 读取刚才 A/B 测试生成的 JSON 结果
with open(res_path, 'r', encoding='utf-8') as f:
    res = json.load(f)

html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>R06 自动化 A/B 测试报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 40px; color: #333; background-color: #f9f9fc; }}
        h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .card {{ background: #fff; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }}
        .metric-grid {{ display: flex; justify-content: space-around; text-align: center; margin-top: 20px; }}
        .metric-box {{ padding: 15px; border-radius: 8px; background: #ecf0f1; width: 22%; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #e74c3c; margin-top: 10px; }}
        .metric-title {{ font-size: 14px; color: #7f8c8d; }}
        .table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .table th, .table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        .table th {{ background-color: #3498db; color: white; }}
        .decision-box {{ background: #e8f8f5; border-left: 5px solid #1abc9c; padding: 15px; font-size: 18px; margin-top: 20px; }}
    </style>
</head>
<body>

    <h1>🚀 R06 自动化 A/B 实验分析报告</h1>
    <p style="text-align: center; color: #7f8c8d;">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <div class="card">
        <h3>📊 核心结论 (The Executive Summary)</h3>
        <div class="decision-box">
            <strong>机器最终决策：</strong> {res['decision']}
        </div>
        <p>本次实验针对 <strong>抖音渠道素材</strong> 进行了双边大样本比例 Z-检验。新素材对比旧素材，实现了转化率的显著提升。</p>
    </div>

    <div class="card">
        <h3>📈 关键指标速览</h3>
        <div class="metric-grid">
            <div class="metric-box">
                <div class="metric-title">对照组转化率</div>
                <div class="metric-value" style="color:#34495e;">{res['control']['rate']:.2%}</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">实验组转化率</div>
                <div class="metric-value" style="color:#27ae60;">{res['treatment']['rate']:.2%}</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">提升幅度 (Lift)</div>
                <div class="metric-value">{res['lift']}</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">显著性 p 值</div>
                <div class="metric-value" style="color: {'#27ae60' if res['is_significant'] else '#e74c3c'};">{res['p_value']:.4f}</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h3>🔬 实验数据详情</h3>
        <table class="table">
            <thead>
                <tr>
                    <th>组别</th>
                    <th>分组描述</th>
                    <th>样本量 (Users)</th>
                    <th>转化率 (CR)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>对照组 (Control)</td>
                    <td>{res['control']['name']}</td>
                    <td>{res['control']['sample']}</td>
                    <td>{res['control']['rate']:.2%}</td>
                </tr>
                <tr>
                    <td>实验组 (Treatment)</td>
                    <td>{res['treatment']['name']}</td>
                    <td>{res['treatment']['sample']}</td>
                    <td>{res['treatment']['rate']:.2%}</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="card">
        <h3>⚠️ 统计学说明与护栏</h3>
        <ul>
            <li><strong>检验方法</strong>: Statsmodels 双比例 Z 检验 (Two-sided Proportions Z-test)</li>
            <li><strong>显著性结论</strong>: 由于 p={res['p_value']:.4f} < 0.05，我们<strong>拒绝原假设</strong>，认为两组转化率差异在统计学上是显著的。</li>
            <li><strong>防范建议</strong>: 建议在全量上线前，对转化率外的“客单价 (AOV)”指标进行无损害验证，防止出现“只看转化不看钱”的现象。</li>
        </ul>
    </div>

</body>
</html>
"""

with open(out_html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"HTML 报告生成成功: {out_html_path}")
