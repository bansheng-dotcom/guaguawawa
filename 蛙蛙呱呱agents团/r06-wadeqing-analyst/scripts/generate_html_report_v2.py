import json
import os

_AGENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO = os.path.dirname(_AGENT)
template_path = os.path.join(_AGENT, "templates", "business_report_template.html")
res_path = os.path.join(_REPO, "workspace", "artifacts", "ab_test_decision.json")
out_html_path = os.path.join(_REPO, "workspace", "artifacts", "Final_Business_Report.html")

with open(template_path, 'r', encoding='utf-8') as f:
    template = f.read()

with open(res_path, 'r', encoding='utf-8') as f:
    res = json.load(f)

# 填充模板逻辑 (简单的动态替换)
report = template.replace('{{CONTROL_RATE}}', f"{res['control']['rate']:.2%}")
report = report.replace('{{TREATMENT_RATE}}', f"{res['treatment']['rate']:.2%}")
report = report.replace('{{LIFT}}', res['lift'])
report = report.replace('{{DECISION}}', res['decision'])

with open(out_html_path, 'w', encoding='utf-8') as f:
    f.write(report)
print(f"专业报告已生成: {out_html_path}")
