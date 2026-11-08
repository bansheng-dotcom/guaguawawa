"""
=============================================================================
模块03: 模型评估 — AUC/混淆矩阵/PR曲线/阈值调优
=============================================================================
AUC高但精确率低? → 样本不均衡的经典问题
需要做: 阈值调优 — 默认0.5不一定是最优的

评估维度:
    1. ROC-AUC: 排序能力(不依赖阈值)
    2. 混淆矩阵: TP/FP/TN/FN
    3. Precision/Recall/F1: 精确率vs召回率权衡
    4. PR曲线: 不均衡数据下比ROC更有信息量
    5. Lift曲线: "用模型预测 vs 随机抽取,提升多少?"
=============================================================================
"""

import numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import (roc_auc_score, roc_curve, confusion_matrix,
                              classification_report, precision_recall_curve,
                              average_precision_score)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("=" * 60)
print("  模块03: 模型评估")
print("=" * 60)
print()

# 加载预测结果
preds = np.load(f'{DATA_DIR}/predictions.npz')
rf_pred = preds['rf_pred']
lr_pred = preds['lr_pred']
y_test = preds['y_test']

# ===========================================================================
# 1. ROC-AUC
# ===========================================================================

rf_auc = roc_auc_score(y_test, rf_pred)
lr_auc = roc_auc_score(y_test, lr_pred)
rf_fpr, rf_tpr, _ = roc_curve(y_test, rf_pred)
lr_fpr, lr_tpr, _ = roc_curve(y_test, lr_pred)

print(f"  ROC-AUC: 逻辑回归={lr_auc:.4f} | 随机森林={rf_auc:.4f}")

# ===========================================================================
# 2. 混淆矩阵 + 分类报告
# ===========================================================================

print()
print("=" * 40)
print("  阈值=0.5 下的分类报告 (随机森林)")
print("=" * 40)

rf_pred_label = (rf_pred >= 0.5).astype(int)
print(classification_report(y_test, rf_pred_label, target_names=['未流失','流失']))

cm = confusion_matrix(y_test, rf_pred_label)
print(f"  混淆矩阵:")
print(f"    TN={cm[0,0]:,}  FP={cm[0,1]:,}")
print(f"    FN={cm[1,0]:,}  TP={cm[1,1]:,}")

# ===========================================================================
# 3. 阈值调优
# ===========================================================================

print()
print("=" * 40)
print("  阈值调优")
print("=" * 40)

# 不同阈值下的Precision/Recall
thresholds = np.arange(0.2, 0.8, 0.05)
best_f1, best_thresh = 0, 0.5

print(f"  {'阈值':<8} {'Precision':<12} {'Recall':<12} {'F1':<10} {'捕获率':<10}")
print(f"  {'-'*52}")

for thresh in thresholds:
    pred = (rf_pred >= thresh).astype(int)
    tp = ((pred == 1) & (y_test == 1)).sum()
    fp = ((pred == 1) & (y_test == 0)).sum()
    fn = ((pred == 0) & (y_test == 1)).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    capture_rate = tp / y_test.sum()

    if f1 > best_f1:
        best_f1 = f1
        best_thresh = thresh

    print(f"  {thresh:<8.2f} {precision:<12.4f} {recall:<12.4f} {f1:<10.4f} {capture_rate:<10.4f}")

print(f"\n  最优阈值: {best_thresh:.2f} (F1={best_f1:.4f})")

# ===========================================================================
# 可视化: 4图 (ROC + PR + 混淆矩阵 + Lift)
# ===========================================================================

fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# 图1: ROC曲线
ax1 = axes[0, 0]
ax1.plot(rf_fpr, rf_tpr, label=f'Random Forest (AUC={rf_auc:.4f})', linewidth=2, color='#E74C3C')
ax1.plot(lr_fpr, lr_tpr, label=f'Logistic Regression (AUC={lr_auc:.4f})', linewidth=2, color='#3498DB')
ax1.plot([0,1],[0,1],'k--', alpha=0.3, label='Random')
ax1.set_xlabel('False Positive Rate')
ax1.set_ylabel('True Positive Rate')
ax1.set_title('ROC Curve', fontsize=12, fontweight='bold')
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3)

# 图2: PR曲线
ax2 = axes[0, 1]
rf_prec, rf_rec, _ = precision_recall_curve(y_test, rf_pred)
lr_prec, lr_rec, _ = precision_recall_curve(y_test, lr_pred)
rf_ap = average_precision_score(y_test, rf_pred)
lr_ap = average_precision_score(y_test, lr_pred)

ax2.plot(rf_rec, rf_prec, label=f'Random Forest (AP={rf_ap:.4f})', linewidth=2, color='#E74C3C')
ax2.plot(lr_rec, lr_prec, label=f'Logistic Regression (AP={lr_ap:.4f})', linewidth=2, color='#3498DB')
ax2.set_xlabel('Recall')
ax2.set_ylabel('Precision')
ax2.set_title('Precision-Recall Curve', fontsize=12, fontweight='bold')
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3)

# 图3: 混淆矩阵热力图
ax3 = axes[1, 0]
im = ax3.imshow(cm, cmap='Blues')
ax3.set_xticks([0,1]); ax3.set_yticks([0,1])
ax3.set_xticklabels(['Not Churn','Churn'])
ax3.set_yticklabels(['Not Churn','Churn'])
ax3.set_xlabel('Predicted'); ax3.set_ylabel('Actual')
ax3.set_title(f'Confusion Matrix (threshold=0.5)', fontsize=12, fontweight='bold')
for i in range(2):
    for j in range(2):
        ax3.text(j, i, f'{cm[i,j]:,}', ha='center', va='center', fontsize=16, fontweight='bold',
                 color='white' if cm[i,j] > cm.max()/2 else 'black')

# 图4: Lift曲线
ax4 = axes[1, 1]
# 按预测概率降序排列,看前x%用户捕获了多少真实流失
sorted_idx = np.argsort(rf_pred)[::-1]
sorted_y = y_test[sorted_idx]

cumulative_gains = []
for pct in np.arange(0.05, 1.05, 0.05):
    n_top = int(len(sorted_y) * pct)
    if n_top == 0: continue
    gain = sorted_y[:n_top].sum() / sorted_y.sum()
    cumulative_gains.append((pct, gain))

pcts, gains = zip(*cumulative_gains)
ax4.plot(pcts, gains, 'o-', color='#E74C3C', linewidth=2, label='Model')
ax4.plot([0,1],[0,1],'k--', alpha=0.3, label='Random (no model)')
ax4.fill_between(pcts, gains, pcts, alpha=0.2, color='#E74C3C')

# 标注关键点
top20_gain = gains[3]  # 20%位置
ax4.axvline(x=0.2, color='gray', linestyle=':', alpha=0.5)
ax4.annotate(f'Top 20% captures\n{top20_gain*100:.0f}% of churn', (0.2, top20_gain),
             textcoords="offset points", xytext=(30, -20), ha='center', fontsize=9,
             arrowprops=dict(arrowstyle='->', color='gray'))
ax4.set_xlabel('Percentage of Users Contacted')
ax4.set_ylabel('Percentage of Churn Captured')
ax4.set_title('Lift Curve', fontsize=12, fontweight='bold')
ax4.legend(fontsize=9)
ax4.grid(True, alpha=0.3)

plt.suptitle('用户流失预测模型评估仪表盘', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{DATA_DIR}/model_evaluation.png', dpi=150, bbox_inches='tight')
print(f"\n[图表已保存] data/model_evaluation.png")
print()
print("=" * 60)
print("  模块03完成 — 模型评估完毕")
print("  下一步: python 04_feature_importance.py")
print("=" * 60)
