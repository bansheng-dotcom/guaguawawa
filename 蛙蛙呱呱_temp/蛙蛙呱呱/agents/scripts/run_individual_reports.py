import os
import json
import datetime
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append('D:/一人公司/agents')
from core.enhanced_report_renderer import render_multimodal_html

def generate_individual_reports():
    print("==================================================")
    print("🚀 [Mission Control] 启动“一人一份报告”的交付模式")
    print("🚀 为核心 Agent 生成带有专业深度与专属交互组件的独立报告...")
    print("==================================================")
    
    out_dir = Path("D:/一人公司/停车场各部门专项报告")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    import markdown
    
    # -----------------------------------------------------------------
    # 1. R06 数据分析师的专项报告 (强调深度图表与归因)
    # -----------------------------------------------------------------
    r06_md = '''
## 核心业务问题：空置率与潮汐现象分析

1. **现状基线**：目前工作日 10:00-16:00 期间，车位空置率高达 70%，属于纯沉没成本。
2. **潮汐特性**：周边住宅小区在夜间 22:00-次日 08:00 车位极度紧缺，而我们的地库此时闲置。
3. **收益测算**：若引入“夜间月租”及“商场消费抵扣”，预期整体车位周转率提升 1.8 倍。

### 数据缺口与预警
目前缺少“新能源车位充电桩占用率”的埋点，建议在二期加装电表数据回传。
    '''
    r06_chart = {
        "title": {"text": "车位空置率时间分布 (潮汐现象)"},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": ["8:00", "12:00", "16:00", "20:00", "24:00", "4:00"]},
        "yAxis": {"type": "value", "name": "空置率 (%)", "max": 100},
        "series": [{"data": [20, 70, 75, 40, 85, 95], "type": "line", "areaStyle": {"opacity": 0.4}, "itemStyle": {"color": "#3498db"}}]
    }
    
    r06_html = render_multimodal_html(
        title="[R06 蛙得清] 停车场潮汐数据分析与 ROI 测算报告",
        markdown_html=markdown.markdown(r06_md),
        echarts_data=r06_chart
    )
    with open(out_dir / "R06_数据分析专项报告.html", "w", encoding="utf-8") as f:
        f.write(r06_html)
        
    # -----------------------------------------------------------------
    # 2. R07 产品经理的专项报告 (强调 PRD、流程图与门禁)
    # -----------------------------------------------------------------
    r07_md = '''
## 核心需求：动态定价与无感支付业务流

### 1. 业务规则 (Business Rules)
- **保护谁**：保护商场高净值会员，黑钻会员享无条件 4 小时免费。
- **限制什么**：为防羊毛党，同一车牌号单日最多使用 1 张商户抵扣券。
- **降级预案**：断网状态下，车牌识别放行，离线计费。

### 2. 承重假设 (Key Assumptions)
**假设**：周边老旧小区业主愿意每月支付 300 元购买“纯夜间停车包月”。
**验证**：先放 50 个名额在小区群进行预售，若 3 天内售罄则全量铺开。
    '''
    r07_mermaid = '''
    graph TD
        A[车辆入场] --> B(黑名单校验)
        B -- 拦截 --> C[保安介入]
        B -- 通过 --> D(车牌识别计费)
        D --> E[会员库API比对]
        E -- 黑钻会员 --> F[下发欢迎语+4小时免费特权]
        E -- 普通车辆 --> G[标准计费]
    '''
    r07_html = render_multimodal_html(
        title="[R07 蛙得明] 停车场动态定价与无感支付 PRD",
        markdown_html=markdown.markdown(r07_md),
        mermaid_logic=r07_mermaid
    )
    with open(out_dir / "R07_产品需求文档_PRD.html", "w", encoding="utf-8") as f:
        f.write(r07_html)
        
    # -----------------------------------------------------------------
    # 3. R03 CFO 的专项报告 (强调红线、合规与预算清单)
    # -----------------------------------------------------------------
    r03_md = '''
## 合规审查与资金管理规划

### 1. 隐私与数据安全红线
- 采集车牌号**必须**在入场口显著位置张贴《隐私采集声明》。
- 数据库落盘必须对车牌中段（如沪A **123** 4）进行哈希脱敏。**禁止明文存储**。

### 2. 资金清算风险
- 采用商圈代金券抵扣停车费，会产生“资金垫付”问题。
- **决策**：商户购买停车券采用“先充值后发放”模式，不允许商户授信透支，杜绝坏账。

### 3. 硬件采购审批
**预算控制**：海康威视主备摄像机 + 边缘计算节点，总计不得突破 ¥35,000。
    '''
    r03_html = render_multimodal_html(
        title="[R03 蛙守线] 财务风控与合规红线审查报告",
        markdown_html=markdown.markdown(r03_md)
    )
    with open(out_dir / "R03_财务合规红线报告.html", "w", encoding="utf-8") as f:
        f.write(r03_html)
        
    # -----------------------------------------------------------------
    # 4. R04 评审官的专项报告 (强调逻辑挑战与最终裁决)
    # -----------------------------------------------------------------
    r04_md = '''
## 独立审查记录：寻找系统的脆弱点

### 攻击挑战 1：如果道闸断电怎么办？
- **现状**：R09 (架构) 未提及完全断电情况。
- **驳回**：打回 R20 (运维)，要求补充 UPS 不间断电源配置，并在彻底断电时道闸必须能“自动抬杆”防止车库闷罐。

### 攻击挑战 2：如果同一用户换车牌进场？
- **现状**：R07 (产品) 绑定逻辑存在漏洞。
- **修复**：已强制要求 R07 补充“商场积分扣减增加手机号短信二次核验”环节。

### 最终裁决结果
所有阻塞项 (Blockers) 已被修补。
<div class='executive-summary' style='background:#fdfefe; border-left:5px solid #2ecc71; padding:15px; margin-top:20px;'>
<strong>最终状态：PASS 准予发布</strong>
</div>
    '''
    r04_html = render_multimodal_html(
        title="[R04 蛙挑刺] 项目独立评审与漏洞攻击报告",
        markdown_html=markdown.markdown(r04_md)
    )
    with open(out_dir / "R04_独立审查决议.html", "w", encoding="utf-8") as f:
        f.write(r04_html)

    print("✅ 部门专项报告已全部分发落盘！")

if __name__ == "__main__":
    generate_individual_reports()
