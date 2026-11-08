import pandas as pd
import numpy as np
import os

_AGENT = r'D:\一人公司\agents\r06-wadeqing-analyst'
out_path = os.path.join(_AGENT, "workspace", "artifacts", "douyin_ab_data.csv")

np.random.seed(42)
n_control = 1000
n_treatment = 1000

# 模拟对照组 (旧素材，受算法影响转化率低)
control_conversions = np.random.binomial(1, 0.04, n_control)
# 模拟实验组 (新素材，适应新算法，转化率提升)
treatment_conversions = np.random.binomial(1, 0.055, n_treatment)

df_control = pd.DataFrame({'user_id': range(1, n_control+1), 'group': '抖音_旧素材', 'converted': control_conversions})
df_treatment = pd.DataFrame({'user_id': range(n_control+1, n_control+n_treatment+1), 'group': '抖音_新素材', 'converted': treatment_conversions})

df = pd.concat([df_control, df_treatment])
df.to_csv(out_path, index=False)
print(f"AB 测试数据已生成: {out_path}")
