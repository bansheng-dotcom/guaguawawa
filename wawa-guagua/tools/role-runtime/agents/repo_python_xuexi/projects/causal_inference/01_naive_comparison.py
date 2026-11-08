"""模块01: 朴素对比 — 展示选择偏差"""
import pandas as pd, numpy as np, os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

df = pd.read_csv(f'{DATA_DIR}/coupon_data.csv')

print("="*60)
print("  模块01: 朴素对比 — 选择偏差演示")
print("="*60)

treated = df[df['treated']==1]; control = df[df['treated']==0]

# 朴素对比
t_gmv_change = (treated['post_gmv'].mean()/treated['pre_gmv'].mean() - 1)*100
c_gmv_change = (control['post_gmv'].mean()/control['pre_gmv'].mean() - 1)*100
naive_effect = t_gmv_change - c_gmv_change

print(f"  处理组(收券): pre={treated['pre_gmv'].mean():.1f} → post={treated['post_gmv'].mean():.1f} ({t_gmv_change:+.1f}%)")
print(f"  对照组(没收): pre={control['pre_gmv'].mean():.1f} → post={control['post_gmv'].mean():.1f} ({c_gmv_change:+.1f}%)")
print(f"  朴素估计的因果效应: {naive_effect:+.1f}%")
print(f"  真实因果效应(已知): +8.0%")
print(f"  偏差: {naive_effect-8:.1f}% ← 为什么高估?")
print(f"\n  原因: 处理组的基线GMV就比对照组高{((treated['pre_gmv'].mean()/control['pre_gmv'].mean())-1)*100:.1f}%")
print(f"  → 即使不发券,处理组的GMV增长也会高于对照组")
print(f"  → 朴素对比把'选择效应'当成了'因果效应'")
