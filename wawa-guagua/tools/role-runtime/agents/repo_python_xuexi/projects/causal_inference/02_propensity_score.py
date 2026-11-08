"""模块02: PSM — 倾向得分匹配"""
import pandas as pd, numpy as np, os, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors

plt.rcParams['font.sans-serif'] = ['SimHei','Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

df = pd.read_csv(f'{DATA_DIR}/coupon_data.csv')
print("="*60)
print("  模块02: PSM倾向得分匹配")
print("="*60)

# Step 1: 估计倾向得分
X = df[['pre_gmv','frequency','recency','city_tier']].values
y = df['treated'].values

ps_model = LogisticRegression(random_state=42)
ps_model.fit(X, y)
df['ps_score'] = ps_model.predict_proba(X)[:, 1]

print(f"  倾向得分分布: min={df['ps_score'].min():.3f} max={df['ps_score'].max():.3f}")

# Step 2: 1:1最近邻匹配
treated_idx = df[df['treated']==1].index
control_idx = df[df['treated']==0].index
control_ps = df.loc[control_idx, 'ps_score'].values.reshape(-1,1)

nn = NearestNeighbors(n_neighbors=1)
nn.fit(control_ps)

matched_control = []
for idx in treated_idx:
    dist, match_idx = nn.kneighbors([[df.loc[idx,'ps_score']]])
    matched_control.append(control_idx[match_idx[0][0]])
    # 不放回匹配: 删掉已匹配的对照
    control_idx = control_idx.drop(control_idx[match_idx[0][0]])
    if len(control_idx) == 0: break
    control_ps = df.loc[control_idx, 'ps_score'].values.reshape(-1,1)
    nn.fit(control_ps)

# Step 3: 匹配后对比
matched_t = df.loc[treated_idx[:len(matched_control)]]
matched_c = df.loc[matched_control]

t_change = (matched_t['post_gmv'].mean()/matched_t['pre_gmv'].mean()-1)*100
c_change = (matched_c['post_gmv'].mean()/matched_c['pre_gmv'].mean()-1)*100
psm_effect = t_change - c_change

print(f"  匹配后处理组(n={len(matched_t)}): pre={matched_t['pre_gmv'].mean():.1f}")
print(f"  匹配后对照组(n={len(matched_c)}): pre={matched_c['pre_gmv'].mean():.1f}")
print(f"  基线差异: {((matched_t['pre_gmv'].mean()/matched_c['pre_gmv'].mean())-1)*100:.1f}% (匹配前~15%)")
print(f"  PSM估计因果效应: {psm_effect:+.1f}% (真实=+8.0%)")

# 可视化: 匹配前后倾向得分分布
fig, axes = plt.subplots(1,2,figsize=(12,5))
axes[0].hist(df[df['treated']==1]['ps_score'],bins=30,alpha=0.6,label='Treated',color='#E74C3C')
axes[0].hist(df[df['treated']==0]['ps_score'],bins=30,alpha=0.6,label='Control',color='#3498DB')
axes[0].set_title('Before Matching'); axes[0].legend()
axes[1].hist(matched_t['ps_score'],bins=30,alpha=0.6,label='Treated',color='#E74C3C')
axes[1].hist(matched_c['ps_score'],bins=30,alpha=0.6,label='Control',color='#3498DB')
axes[1].set_title('After PSM Matching'); axes[1].legend()
plt.suptitle('PSM: 倾向得分分布 匹配前后对比',fontsize=14,fontweight='bold')
plt.tight_layout(); plt.savefig(f'{DATA_DIR}/psm_matching.png',dpi=150)
print(f'[图表已保存] data/psm_matching.png')

# 保存
matched_t.to_csv(f'{DATA_DIR}/psm_treated.csv',index=False,encoding='utf-8-sig')
matched_c.to_csv(f'{DATA_DIR}/psm_control.csv',index=False,encoding='utf-8-sig')
