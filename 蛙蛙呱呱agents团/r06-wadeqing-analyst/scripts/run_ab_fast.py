#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
from scipy import stats
import argparse
import sys
import json
import os

def run_ab_test(data_path, group_col, control_name, treatment_name, metric_col):
    df = pd.read_csv(data_path)
    
    control_data = df[df[group_col] == control_name][metric_col]
    treatment_data = df[df[group_col] == treatment_name][metric_col]
    
    n_c, n_t = len(control_data), len(treatment_data)
    conv_c, conv_t = control_data.sum(), treatment_data.sum()
    rate_c, rate_t = conv_c/n_c, conv_t/n_t
    
    # 执行 Z-test (大样本转化率检验)
    import statsmodels.api as sm
    count = np.array([conv_t, conv_c])
    nobs = np.array([n_t, n_c])
    z_stat, p_val = sm.stats.proportions_ztest(count, nobs, alternative='two-sided')
    
    lift = (rate_t - rate_c) / rate_c
    is_significant = p_val < 0.05
    
    result = {
        "status": "实验分析完成",
        "control": {"name": control_name, "sample": n_c, "rate": float(rate_c)},
        "treatment": {"name": treatment_name, "sample": n_t, "rate": float(rate_t)},
        "lift": f"{lift:.2%}",
        "p_value": float(p_val),
        "is_significant": bool(is_significant),
        "decision": "建议全量发布新素材" if is_significant and lift > 0 else "保持原状，放弃新素材"
    }
    return result

if __name__ == "__main__":
    import numpy as np # Ensure numpy is available for the script
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--control", required=True)
    parser.add_argument("--treatment", required=True)
    parser.add_argument("--metric", required=True)
    args = parser.parse_args()
    
    res = run_ab_test(args.input, args.group, args.control, args.treatment, args.metric)
    
    _AGENT = r'D:\一人公司\agents\r06-wadeqing-analyst'
    report_path = os.path.join(_AGENT, "workspace", "artifacts", "ab_test_decision.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
        
    print(json.dumps(res, ensure_ascii=False, indent=2))
