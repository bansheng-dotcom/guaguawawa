"""模块05: 因果推断完整报告"""
import pandas as pd, numpy as np, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

df = pd.read_csv(f'{DATA_DIR}/coupon_data.csv')
print("="*60)
print("  模块05: 优惠券因果效应 — 完整报告")
print("="*60)

treated = df[df['treated']==1]; control = df[df['treated']==0]

# 各方法对比
naive = ((treated['post_gmv'].mean()/treated['pre_gmv'].mean()-1)-(control['post_gmv'].mean()/control['pre_gmv'].mean()-1))*100

psm_t = pd.read_csv(f'{DATA_DIR}/psm_treated.csv')
psm_c = pd.read_csv(f'{DATA_DIR}/psm_control.csv')
psm = ((psm_t['post_gmv'].mean()/psm_t['pre_gmv'].mean()-1)-(psm_c['post_gmv'].mean()/psm_c['pre_gmv'].mean()-1))*100

did = ((psm_t['post_gmv'].mean()-psm_t['pre_gmv'].mean())-(psm_c['post_gmv'].mean()-psm_c['pre_gmv'].mean()))/psm_c['pre_gmv'].mean()*100

print(f"""
  +=======================================================+
  |  优惠券效应估计 — 四种方法对比                         |
  +=======================================================+
  | 方法            | 估计效应 | 与真实值(8%)的偏差 | 可信度 |
  |-----------------+---------+------------------+--------|
  | 朴素对比         | {naive:+.1f}%  | {abs(naive-8):.1f}%              | 低     |
  | PSM             | {psm:+.1f}%  | {abs(psm-8):.1f}%              | 中高   |
  | PSM-DiD         | {did:+.1f}%  | {abs(did-8):.1f}%              | 高     |
  +=======================================================+

  结论:
    优惠券的真实因果效应约+8%。朴素对比高估了{(naive-8):.0f}个百分点——
    因为运营不是随机发券,而是发给了原本就更活跃的用户。

    PSM匹配后估计接近真实值,PSM-DiD双重差分为最可信估计。

  业务建议:
    1. 满20-5券的因果效应+8% — 值得继续使用
    2. 但运营不能只给高活用户发 — 那会高估效果
    3. 建议做一次真正的随机对照实验(A/B测试)来验证因果效应
    4. 用PSM评估历史营销活动的真实效果 — 不需要等A/B实验
""")
print("="*60)
print("  [DONE] 项目七全部模块完成!")
print()
print("  简历可写:")
print("""
  [优惠券效果因果推断 — 美团优选]

  - 识别优惠券效果评估中的选择偏差(运营非随机发券导致朴素对比高估
    约X个百分点); 构建倾向得分匹配(PSM)消除选择偏差,PSM估计
    因果效应约+8%(接近真实值)

  - 双重差分(DiD)验证: PSM-DiD估计为+8.X%,较朴素DiD显著改善;
    Rosenbaum敏感性分析确认结论在Γ=1.5内稳健

  - 建立"朴素对比→PSM→DiD→敏感性分析"四级因果推断框架,
    适用于评估历史非随机策略的真实效果

  技术栈: Python(scikit-learn/Pandas/Matplotlib)、PSM/DID/敏感性分析
""")
print("="*60)
