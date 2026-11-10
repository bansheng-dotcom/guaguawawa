# scripts/run_parking_lot_case.py
import json
import os
import markdown
import sys

# 将仓库根加入路径以导入模块
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
from core.dynamic_orchestrator import MissionControl
from core.enhanced_report_renderer import render_multimodal_html

def run_parking_case():
    print("1. R01 首脑开始拆解停车场场景...")
    mc = MissionControl("智能停车场：闲置时段车位利用率与整体营收最大化方案")
    
    # 模拟 R01 动态下发任务
    mc.team_roster = ["r07(产品)", "r06(数据)", "r12(增长)", "r20(运维)", "r04(评审)"]
    mc.execution_plan = [
        {
            "step": 1,
            "type": "parallel",
            "agents": [
                {"role": "r07", "action": "设计峰谷动态定价与无感支付流程", "expected_output": ["prd.md"]},
                {"role": "r06", "action": "分析 24 小时车位占用率", "expected_output": ["occupancy_data.json"]},
                {"role": "r12", "action": "设计周边商圈异业合作(停车券抵扣)", "expected_output": ["growth_strategy.md"]},
                {"role": "r20", "action": "车牌识别与道闸高可用保障", "expected_output": ["sla_report.md"]}
            ]
        },
        {
            "step": 2,
            "type": "gate",
            "agents": [
                {"role": "r04", "action": "整体合规与业务逻辑硬门禁复核", "expected_output": ["final_verdict.json"]}
            ]
        }
    ]
    
    plan = mc._export_plan()
    
    print("2. 模拟各 Agent 执行并生成 Expected Outputs...")
    
    # 模拟 R06 的数据产出 (ECharts)
    echarts_data = {
        "title": {"text": "24小时车位占用率 (峰谷分析)"},
        "tooltip": {"trigger": "axis", "formatter": "{b} 时: {c}% 占用"},
        "xAxis": {"type": "category", "data": ["0:00", "4:00", "8:00", "12:00", "16:00", "20:00", "24:00"]},
        "yAxis": {"type": "value", "max": 100, "axisLabel": {"formatter": "{value} %"}},
        "series": [{
            "data": [10, 5, 85, 60, 95, 40, 15], 
            "type": "line", 
            "smooth": True, 
            "areaStyle": {"opacity": 0.3},
            "itemStyle": {"color": "#3498db"}
        }]
    }

    # 模拟 R07/R20 的流程图产出 (Mermaid)
    mermaid_logic = '''
    graph TD
        A[车辆入场] --> B(AI车牌识别与活体防伪)
        B --> C{识别成功?}
        C -- Yes --> D[道闸抬起 & 开始计费]
        C -- No --> E[降级：人工/扫码介入]
        D --> F[车位级雷达引导系统]
        F --> G[周边商圈消费抵扣 (API接口)]
        G --> H[无感支付 & 离场自动扣款]
    '''

    # 各 Agent 的文本报告汇总
    markdown_text = '''
## 🎯 业务目标
将当前日均 45% 的车位利用率提升至 75%，主要解决**夜间及工作日非高峰时段的闲置问题**，并优化早晚高峰的通行效率。

---

## 🛠️ 各节点执行报告

### 1. 【R07 产品经理 - 蛙得明】产品流程与动态定价设计
- **动态定价引擎**：工作日 8:00-10:00 采用高峰费率（+20%）；夜间 22:00-次日 6:00 采用极光包月套餐（低至 2 折），吸引周边老旧小区无固定车位的业主过夜停车。
- **无感体验**：ETC + 微信/支付宝免密支付双通道接入，将出场平均耗时从 15 秒缩短至 2 秒。

### 2. 【R06 数据分析师 - 蛙得清】占用率潮汐现象分析
*(参考上方数据看图)*
- **数据洞察**：每日呈现双峰结构（早 8 点和下午 16 点满载），但凌晨 0:00-6:00 占用率不足 10%。
- **ROI 测算**：通过开放 100 个夜间共享车位，预期每月可新增净利润 2.5 万元。

### 3. 【R12 增长黑客 - 蛙盈留】商圈异业合作
- **引流策略**：打通周边商场与超市的 CRM 系统。消费者单笔消费满 100 元，商场 API 自动调用停车系统，减免 2 小时停车费。
- **商户端**：推出“商户代发停车券” B端小程序，商户可批量采购停车时长发给访客。

### 4. 【R20 运维值守 - 蛙守值】SLA 与高可用兜底
- **弱网兜底**：若地库断网，车牌识别相机开启本地离线计费模式，恢复网络后自动同步账单。
- **硬件冗余**：入口双摄识别，主摄故障自动秒级切换副摄，保障 99.99% 的道闸抬杆率。

---

## 🛑 【R04 评审官 - 蛙挑刺】独立审查结论
- ✅ **数据合规门禁**：通过。未采集人脸，车牌数据已脱敏。
- ✅ **逻辑门禁**：通过。动态定价已设置最高限价，符合物价局规定。
- **裁决 (Verdict)**：**PASS**. 方案逻辑自洽，闭环完整，准予进入开发阶段。
'''
    
    print("3. 生成多模态企业级 HTML 报告...")
    md_html = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
    final_html = render_multimodal_html(
        title="智能停车场商业优化方案 (多 Agent 协同汇报)",
        markdown_html=md_html,
        echarts_data=echarts_data,
        mermaid_logic=mermaid_logic
    )
    
    out_dir = os.path.join(_REPO, "workspace", "artifacts")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "智能停车场商业优化方案.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(final_html)
    
    print(f"4. 报告生成完毕！路径: {out_path}")

if __name__ == "__main__":
    run_parking_case()
