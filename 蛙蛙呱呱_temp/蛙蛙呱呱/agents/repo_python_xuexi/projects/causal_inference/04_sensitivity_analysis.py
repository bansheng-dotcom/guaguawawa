"""模块04: 敏感性分析 — "如果有未观测的混淆变量呢？" """
import pandas as pd, numpy as np, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

df = pd.read_csv(f'{DATA_DIR}/coupon_data.csv')
print("="*60)
print("  模块04: 敏感性分析")
print("="*60)

# 问题: 如果存在一个"未观测的混淆变量"(比如用户对价格的敏感度),
#       它同时影响"是否收到券"和"GMV变化"——
#       我们的PSM/DiD结论还靠谱吗？

# Rosenbaum bounds方法: 假设存在一个未观测的混淆变量U,
# 它使处理组和对照组的"被选中概率"差异为Γ倍
# 逐步增加Γ,看结论什么时候翻转

print("""
  Rosenbaum敏感性分析:

  核心问题: "如果存在一个遗漏变量,它让某些人获得优惠券的概率
           比别人高Γ(伽马)倍,我们的结论还成立吗?"

  方法: 对匹配后的处理组/对照组对做Wilcoxon符号秩检验,
       在不同Γ值下重新计算p值的上界和下界。

  Γ=1.0:  无隐藏偏差 — p值与原始检验相同
  Γ=1.5:  中等偏差 — 如果结论还能维持,p<0.05,说明结论比较稳健
  Γ=2.0+: 强偏差   — 如果到这步p>0.05,说明结论对未观测混淆敏感

  经验法则:
    - 如果Γ到1.5-2.0结论仍显著 → 结论稳健
    - 如果Γ=1.2就翻转 → 结论脆弱,需要更谨慎
""")

print("  (Rosenbaum bounds需要StatsModels或专门的sensitivity库,)")
print("  (这里展示方法论框架。实际工作中可以用R的rbounds包或Python的psmpy)")
