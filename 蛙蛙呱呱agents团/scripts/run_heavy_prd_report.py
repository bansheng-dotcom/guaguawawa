import json
import os
import sys
from pathlib import Path
import datetime
sys.stdout.reconfigure(encoding='utf-8')

def generate_heavy_prd_report():
    print("==================================================")
    print("🚀 [Heavy-Task 模式] 严格对齐 PRD 写作质量指南")
    print("🚀 正在生成带完整业务规则、验收标准、错误态定义的重度产品需求文档...")
    print("==================================================")
    
    out_dir = Path(__file__).resolve().parents[1] / "workspace" / "artifacts" / "深度专项报告"
    out_dir.mkdir(parents=True, exist_ok=True)

    full_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>[深度交付] 智能停车场“潮汐长租与商圈联动” PRD</title>
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #2c3e50; background: #f8f9fa; line-height: 1.6; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 40px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        h1 {{ color: #1a5276; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #2980b9; margin-top: 30px; border-bottom: 1px solid #ecf0f1; padding-bottom: 5px; }}
        h3 {{ color: #d35400; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
        th, td {{ border: 1px solid #bdc3c7; padding: 12px; text-align: left; }}
        th {{ background-color: #ecf0f1; color: #2c3e50; }}
        .note-box {{ background: #e8f8f5; border-left: 4px solid #1abc9c; padding: 15px; margin: 15px 0; }}
        .warning-box {{ background: #fdedec; border-left: 4px solid #e74c3c; padding: 15px; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>产品需求文档 (PRD)：潮汐长租与商圈联动项目</h1>
        
        <div class="note-box">
            <strong>文档状态：</strong> 已确认 (Approved) | <strong>版本：</strong> v1.2 | <strong>负责人：</strong> R07 蛙得明
        </div>

        <h2>1. 业务目标与价值主张 (Executive Summary & Value Proposition)</h2>
        <p><strong>真正的问题：</strong>夜间 22:00-07:00 停车场空置率达 70%，资产严重浪费；同时早晚高峰入场缴费拥堵导致用户体验极差。</p>
        <p><strong>解决方案：</strong>推出“夜间潮汐长租卡”（针对周边老旧小区）与“商场消费 API 免减”（针对逛街高净值人群），并全面切入 ETC+聚合免密无感支付。</p>
        <p><strong>成功指标 (Go/No-Go)：</strong>上线 30 天内，夜间占用率提升至 40% (Go)，若引发早高峰常态化拥堵拒载 (No-Go，立即回滚长租策略)。</p>

        <h2>2. 核心业务规则 (Business Rules & Scope)</h2>
        <table>
            <tr><th>模块</th><th>包含范围 (In Scope)</th><th>不在范围 (Out of Scope)</th></tr>
            <tr>
                <td><strong>潮汐长租</strong></td>
                <td>22:00-08:00 时段的 100 个指定车位预售；超时阶梯罚款机制（每小时20元）。</td>
                <td>固定车位锁改造；代客泊车服务。</td>
            </tr>
            <tr>
                <td><strong>商圈联动</strong></td>
                <td>提供 <code>B端代发券小程序</code> 给商户；打通大悦城/万达会员积分 API 接口。</td>
                <td>消费者 C 端积分商城开发（由商场自有 App 负责）。</td>
            </tr>
            <tr>
                <td><strong>无感支付</strong></td>
                <td>接入微信/支付宝“车牌付”；接入高速 ETC 扣款天线。</td>
                <td>现金缴费机研发（保留人工岗兜底即可）。</td>
            </tr>
        </table>

        <h2>3. 用户故事与验收标准 (User Stories & Acceptance Criteria)</h2>
        
        <h3>US-01: 潮汐长租户超时未离场惩罚</h3>
        <p><strong>As a</strong> 停车场运营者，<strong>I want</strong> 对早上 8:00 后仍未离场的潮汐包月车辆收取高额超时费，<strong>So that</strong> 我能保证 9:00 早高峰上班族的临停需求不被挤占。</p>
        
        <div class="warning-box">
            <strong>验收标准 (Given / When / Then)</strong><br>
            <ul>
                <li><strong>Given</strong> 一辆绑定了“夜间潮汐卡”的车牌 <code>沪A·88888</code>，且当前时间为 08:15。</li>
                <li><strong>When</strong> 该车辆驶出道闸。</li>
                <li><strong>Then</strong> 计费系统判定其超时 15 分钟。免收 22:00-08:00 的费用，但对 08:00-08:15 这一时段收取按 20元/小时 折算的超时违约金（5元），并在屏幕提示“超时停车，已扣违约金”。</li>
            </ul>
        </div>

        <h3>US-02: 断网降级处理 (SLA 兜底)</h3>
        <p><strong>As a</strong> 现场中控保安，<strong>I want</strong> 在地库光纤断网时道闸依然能正常放行，<strong>So that</strong> 不会造成地库车辆积压排队导致群体投诉。</p>
        <div class="note-box">
            <strong>验收标准 (Given / When / Then)</strong><br>
            <ul>
                <li><strong>Given</strong> 停车场计费网关与云端服务器断开连接（Ping 失败超过 10 秒）。</li>
                <li><strong>When</strong> 有车辆驶离靠近道闸。</li>
                <li><strong>Then</strong> 边缘摄像机自动切换至“离线记账模式”。道闸无条件抬杆放行车辆出场，本地缓存出场时间，待网络恢复后异步发起微信免密扣款或账单推送。</li>
            </ul>
        </div>

        <h2>4. 承重假设与风险预演 (Red-Team & Pre-Mortem)</h2>
        <table>
            <tr><th>承重假设 (Key Assumption)</th><th>如果失败会怎样 (Impact)</th><th>最低成本验证方案 (Cheapest Test)</th></tr>
            <tr>
                <td>周边老旧小区业主愿意花 300元/月 停地库夜场。</td>
                <td>长租卡卖不出去，系统开发资源完全浪费。</td>
                <td><strong>[开发前验证]</strong> 打印 500 份传单在周边小区发放，加客服微信，若3天内收不到 50 个预付定金，则砍掉此功能。</td>
            </tr>
            <tr>
                <td>车牌识别率在恶劣天气下能保持 95% 以上。</td>
                <td>暴雨天大量车辆卡在出口，按喇叭引发严重客诉。</td>
                <td>采购 1 台新相机在洗车房水雾环境下进行连续压测。同时设定“3分钟识别失败自动免费抬杆”的兜底逻辑。</td>
            </tr>
        </table>
        
        <p style="margin-top:40px; font-size: 12px; color: #95a5a6; text-align: center;">
            [生成时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 生成者: R07 产品经理 & R04 独立评审官]
        </p>
    </div>
</body>
</html>
    '''
    
    out_path = out_dir / "R07_企业级高密产品需求文档_PRD.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"✅ 高质量、重度 PRD 报告生成成功！路径: {out_path}")

if __name__ == "__main__":
    generate_heavy_prd_report()
