"""
=============================================================================
模块04: 特征重要性 — SHAP值 + 树模型Feature Importance
=============================================================================
回答:"到底什么行为最预示用户要流失?"

两种方法:
    1. 随机森林内置特征重要性(基于基尼不纯度降低)
    2. SHAP值(基于博弈论,更精确但更慢)

输出:
    1. TOP15特征重要性柱状图
    2. 逻辑回归系数解读("recency每增加1天,流失概率增加X%")
=============================================================================
"""

import numpy as np
import pandas as pd
import os
import pickle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("=" * 60)
print("  模块04: 特征重要性分析")
print("=" * 60)
print()

# 加载数据
data = np.load(f'{DATA_DIR}/processed_data.npz')
X_test = data['X_test']
feature_names = data['feature_names']

with open(f'{DATA_DIR}/rf_model.pkl', 'rb') as f:
    rf = pickle.load(f)
with open(f'{DATA_DIR}/lr_model.pkl', 'rb') as f:
    lr = pickle.load(f)

# ===========================================================================
# 1. 随机森林特征重要性 (内置)
# ===========================================================================

print("[1] 随机森林 Feature Importance (TOP15)")

rf_importance = pd.DataFrame({
    'feature': feature_names,
    'importance': rf.feature_importances_
}).sort_values('importance', ascending=False)

print(f"\n  {'Rank':<6} {'Feature':<30} {'Importance':<12}")
print(f"  {'-'*48}")
for i, (_, row) in enumerate(rf_importance.head(15).iterrows()):
    print(f"  {i+1:<6} {row['feature']:<30} {row['importance']:<12.4f}")

# ===========================================================================
# 2. 逻辑回归系数解读
# ===========================================================================

print()
print("[2] 逻辑回归系数解读")

lr_coef = pd.DataFrame({
    'feature': feature_names,
    'coefficient': lr.coef_[0]
}).sort_values('coefficient', key=abs, ascending=False)

print(f"\n  {'Feature':<28} {'Coef':<10} {'解读':<40}")
print(f"  {'-'*78}")

for _, row in lr_coef.head(10).iterrows():
    feat = row['feature']
    coef = row['coefficient']
    if 'recency' in feat or 'decay' in feat:
        interp = '↑ → 流失风险增加 (越久没买越危险)'
    elif 'frequency' in feat or 'score' in feat:
        interp = '↓ → 流失风险降低 (买得多就稳)'
    elif 'decline' in feat or 'abandon' in feat:
        interp = '↑ → 流失风险增加 (行为在恶化)'
    elif 'leader' in feat:
        interp = '跟团长质量相关'
    else:
        interp = ''
    print(f"  {feat:<28} {coef:<+10.4f} {interp:<40}")

# ===========================================================================
# 3. SHAP值 (如果shap库可用)
# ===========================================================================

print()
print("[3] SHAP分析 (基于随机森林)")

try:
    import shap

    # 采样加速(全量太慢)
    shap_sample = X_test[:500] if len(X_test) > 500 else X_test
    explainer = shap.TreeExplainer(rf)
    shap_values = explainer.shap_values(shap_sample)

    # 取正类(流失)的SHAP值
    if isinstance(shap_values, list):
        shap_vals = shap_values[1]
    else:
        shap_vals = shap_values

    # TOP10 SHAP特征
    shap_importance = np.abs(shap_vals).mean(axis=0)
    shap_df = pd.DataFrame({'feature': feature_names, 'shap': shap_importance})
    shap_df = shap_df.sort_values('shap', ascending=False)

    print(f"\n  SHAP TOP10特征:")
    for i, (_, row) in enumerate(shap_df.head(10).iterrows()):
        print(f"    {i+1}. {row['feature']:<28} SHAP={row['shap']:.4f}")

    shap_available = True
except ImportError:
    print("  (shap库未安装,跳过SHAP分析。pip install shap)")
    shap_available = False
except Exception as e:
    print(f"  (SHAP计算出错: {e})")
    shap_available = False

# ===========================================================================
# 可视化
# ===========================================================================

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# 图1: RF特征重要性
ax1 = axes[0]
top15 = rf_importance.head(15).iloc[::-1]  # 倒序(重要的在顶部)
ax1.barh(range(len(top15)), top15['importance'].values, color='#3498DB', alpha=0.85, edgecolor='white')
ax1.set_yticks(range(len(top15)))
ax1.set_yticklabels(top15['feature'].values, fontsize=8)
ax1.set_xlabel('Importance')
ax1.set_title('Random Forest Feature Importance', fontsize=11, fontweight='bold')

# 图2: LR系数
ax2 = axes[1]
lr_top = lr_coef.head(15).iloc[::-1]
colors_lr = ['#E74C3C' if c > 0 else '#2ECC71' for c in lr_top['coefficient'].values]
ax2.barh(range(len(lr_top)), lr_top['coefficient'].values, color=colors_lr, alpha=0.85, edgecolor='white')
ax2.set_yticks(range(len(lr_top)))
ax2.set_yticklabels(lr_top['feature'].values, fontsize=8)
ax2.set_xlabel('Coefficient')
ax2.set_title('Logistic Regression Coefficients', fontsize=11, fontweight='bold')
ax2.axvline(x=0, color='black', linewidth=0.5)

# 图3: SHAP Summary (如果有)
ax3 = axes[2]
if shap_available:
    try:
        shap.summary_plot(shap_vals, shap_sample, feature_names=list(feature_names),
                          show=False, plot_size=None)
        ax3.set_title('SHAP Summary Plot', fontsize=11, fontweight='bold')
    except:
        ax3.text(0.5, 0.5, 'SHAP plot failed\n(compatibility issue)', ha='center', va='center', fontsize=10)
        ax3.set_title('SHAP (unavailable)', fontsize=11)
else:
    # 用RF importance填充
    ax3.barh(range(min(15, len(rf_importance))),
             rf_importance.head(15)['importance'].values[::-1],
             color='#9B59B6', alpha=0.85, edgecolor='white')
    ax3.set_yticks(range(min(15, len(rf_importance))))
    ax3.set_yticklabels(rf_importance.head(15)['feature'].values[::-1], fontsize=8)
    ax3.set_xlabel('Importance')
    ax3.set_title('Feature Importance (RF) — SHAP not installed', fontsize=11, fontweight='bold')

plt.suptitle('特征重要性分析 — 用户流失预测', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{DATA_DIR}/feature_importance.png', dpi=150, bbox_inches='tight')
print(f"\n[图表已保存] data/feature_importance.png")
print()
print("=" * 60)
print("  模块04完成 — 特征重要性分析完毕")
print("  下一步: python 05_business_output.py")
print("=" * 60)
