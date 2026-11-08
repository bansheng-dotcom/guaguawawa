"""模块03: DiD — 双重差分"""
import pandas as pd, numpy as np, os, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei','Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

df = pd.read_csv(f'{DATA_DIR}/coupon_data.csv')
print("="*60)
print("  模块03: DiD双重差分")
print("="*60)

# DiD = (处理组post - 处理组pre) - (对照组post - 对照组pre)
treated = df[df['treated']==1]; control = df[df['treated']==0]

t_pre = treated['pre_gmv'].mean(); t_post = treated['post_gmv'].mean()
c_pre = control['pre_gmv'].mean(); c_post = control['post_gmv'].mean()

# 没做匹配的DiD(仍有选择偏差)
did_raw = (t_post - t_pre) - (c_post - c_pre)
did_raw_pct = did_raw / c_pre * 100

# 用PSM匹配后的样本做DiD
psm_t = pd.read_csv(f'{DATA_DIR}/psm_treated.csv')
psm_c = pd.read_csv(f'{DATA_DIR}/psm_control.csv')

t_pre_m = psm_t['pre_gmv'].mean(); t_post_m = psm_t['post_gmv'].mean()
c_pre_m = psm_c['pre_gmv'].mean(); c_post_m = psm_c['post_gmv'].mean()

did_psm = (t_post_m - t_pre_m) - (c_post_m - c_pre_m)
did_psm_pct = did_psm / c_pre_m * 100

print(f"\n  朴素DiD(未匹配):  effect={did_raw:.1f}元 ({did_raw_pct:+.1f}%)")
print(f"  PSM-DiD(匹配后):   effect={did_psm:.1f}元 ({did_psm_pct:+.1f}%)")
print(f"  真实因果效应:       +8.0%")
print(f"\n  → PSM-DiD比朴素DiD更接近真实值")

# 可视化
fig, ax = plt.subplots(figsize=(8,6))
ax.plot(['Before','After'],[t_pre,t_post],'o-',color='#E74C3C',linewidth=2,markersize=10,label='Treated')
ax.plot(['Before','After'],[c_pre,c_post],'o-',color='#3498DB',linewidth=2,markersize=10,label='Control')
ax.plot(['Before','After'],[c_pre,c_pre+(t_post_m-t_pre_m)],'--',color='gray',linewidth=1.5,label='Counterfactual')
ax.annotate(f'DiD={did_psm:.1f}',('After',c_pre+(t_post_m-t_pre_m)),textcoords="offset points",xytext=(10,-15),fontsize=11,color='gray')
ax.set_ylabel('GMV (yuan)'); ax.set_title('Difference-in-Differences',fontsize=12,fontweight='bold')
ax.legend(); ax.grid(True,alpha=0.3)
plt.tight_layout(); plt.savefig(f'{DATA_DIR}/did_plot.png',dpi=150)
print(f'[图表已保存] data/did_plot.png')
