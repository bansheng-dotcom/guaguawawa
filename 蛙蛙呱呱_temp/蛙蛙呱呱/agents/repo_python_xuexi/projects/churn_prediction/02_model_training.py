"""
=============================================================================
模块02: 模型训练 — 逻辑回归(基线) + 随机森林
=============================================================================
为什么选这两个模型?

    逻辑回归:
        - 输出概率(天然的流失概率)
        - 系数可解释("recency增加1天,流失log-odds增加0.08")
        - 作为baseline——新模型至少要比LR好

    随机森林:
        - 自动捕捉非线性+特征交互
        - 鲁棒、不易过拟合
        - 输出特征重要性(替代SHAP的快速方案)

训练策略:
    - 逻辑回归: L2正则化(防止过拟合), 类别权重balanced(处理不均衡)
    - 随机森林: n_estimators=200, max_depth限制防过拟合
    - 5折交叉验证评估稳定性
=============================================================================
"""

import numpy as np
import os
import pickle
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score, classification_report

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

print("=" * 60)
print("  模块02: 模型训练")
print("=" * 60)
print()

# 加载数据
data = np.load(f'{DATA_DIR}/processed_data.npz')
X_train = data['X_train']
X_test = data['X_test']
y_train = data['y_train']
y_test = data['y_test']

print(f"训练集: {len(X_train)} | 测试集: {len(X_test)}")
print(f"训练集流失率: {y_train.mean()*100:.1f}%")
print()

# ===========================================================================
# 模型1: 逻辑回归(基线)
# ===========================================================================

print("=" * 40)
print("  逻辑回归 (Baseline)")
print("=" * 40)

lr = LogisticRegression(
    penalty='l2',           # L2正则化
    C=0.5,                  # 正则化强度(越小越强)
    class_weight='balanced', # 处理样本不均衡
    solver='liblinear',
    random_state=42,
    max_iter=1000,
)

lr.fit(X_train, y_train)

# 训练集+测试集AUC
lr_train_auc = roc_auc_score(y_train, lr.predict_proba(X_train)[:, 1])
lr_test_auc = roc_auc_score(y_test, lr.predict_proba(X_test)[:, 1])

# 5折交叉验证
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
lr_cv_scores = cross_val_score(lr, X_train, y_train, cv=cv, scoring='roc_auc')

print(f"  训练集AUC: {lr_train_auc:.4f}")
print(f"  测试集AUC: {lr_test_auc:.4f}")
print(f"  5折CV AUC: {lr_cv_scores.mean():.4f} (+/- {lr_cv_scores.std()*2:.4f})")
print(f"  过拟合检查: train-test gap = {lr_train_auc - lr_test_auc:.4f}")

# ===========================================================================
# 模型2: 随机森林
# ===========================================================================

print()
print("=" * 40)
print("  随机森林 (Random Forest)")
print("=" * 40)

rf = RandomForestClassifier(
    n_estimators=200,       # 200棵树
    max_depth=10,           # 限制深度防过拟合
    min_samples_split=50,   # 节点最少样本数
    min_samples_leaf=20,    # 叶节点最少样本数
    class_weight='balanced',
    random_state=42,
    n_jobs=-1,              # 并行
)

rf.fit(X_train, y_train)

rf_train_auc = roc_auc_score(y_train, rf.predict_proba(X_train)[:, 1])
rf_test_auc = roc_auc_score(y_test, rf.predict_proba(X_test)[:, 1])

rf_cv_scores = cross_val_score(rf, X_train, y_train, cv=cv, scoring='roc_auc')

print(f"  训练集AUC: {rf_train_auc:.4f}")
print(f"  测试集AUC: {rf_test_auc:.4f}")
print(f"  5折CV AUC: {rf_cv_scores.mean():.4f} (+/- {rf_cv_scores.std()*2:.4f})")
print(f"  过拟合检查: train-test gap = {rf_train_auc - rf_test_auc:.4f}")

# ===========================================================================
# 模型对比
# ===========================================================================

print()
print("=" * 40)
print("  模型对比")
print("=" * 40)
print(f"  {'模型':<16} {'训练AUC':<10} {'测试AUC':<10} {'CV AUC':<14} {'Gap':<8}")
print(f"  {'-'*58}")
print(f"  {'逻辑回归':<16} {lr_train_auc:<10.4f} {lr_test_auc:<10.4f} {lr_cv_scores.mean():<14.4f} {lr_train_auc-lr_test_auc:<8.4f}")
print(f"  {'随机森林':<16} {rf_train_auc:<10.4f} {rf_test_auc:<10.4f} {rf_cv_scores.mean():<14.4f} {rf_train_auc-rf_test_auc:<8.4f}")

# 选最优模型
if rf_test_auc > lr_test_auc:
    best_model = rf
    model_name = 'RandomForest'
    best_auc = rf_test_auc
else:
    best_model = lr
    model_name = 'LogisticRegression'
    best_auc = lr_test_auc

print(f"\n  最优模型: {model_name} (测试AUC={best_auc:.4f})")

# ===========================================================================
# 保存模型
# ===========================================================================

with open(f'{DATA_DIR}/lr_model.pkl', 'wb') as f:
    pickle.dump(lr, f)
with open(f'{DATA_DIR}/rf_model.pkl', 'wb') as f:
    pickle.dump(rf, f)
with open(f'{DATA_DIR}/best_model.pkl', 'wb') as f:
    pickle.dump(best_model, f)

# 测试集预测(供后续模块使用)
rf_pred_proba = rf.predict_proba(X_test)[:, 1]
lr_pred_proba = lr.predict_proba(X_test)[:, 1]

np.savez(f'{DATA_DIR}/predictions.npz',
         rf_pred=rf_pred_proba, lr_pred=lr_pred_proba,
         y_test=y_test)

print(f"\n[模型已保存]")
print(f"  data/lr_model.pkl — 逻辑回归")
print(f"  data/rf_model.pkl — 随机森林")
print(f"  data/best_model.pkl — 最优模型({model_name})")
print(f"  data/predictions.npz — 测试集预测结果")
print()
print("=" * 60)
print("  模块02完成 — 模型训练完毕")
print("  下一步: python 03_model_evaluation.py")
print("=" * 60)
