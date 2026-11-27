# 引擎台账（ENGINE-LEDGER）

> 由 `python scripts/check_engine_variants.py --write` 生成，禁止手改。
> T0 结论：143 个同名引擎并非字节级复制，只有 telemetry_watchdog 的 r11/r12 可安全收敛；
> 其余登记为 domain_variant 并冻结哈希，禁止再新增未登记副本。

## 汇总

- 总数：143
- 已收敛到 shared：2
- 领域变体：141
- 近似副本（≥0.98）：0

## 按引擎

| 引擎 | 副本数 | shared | 变体 | 最高相似度 |
|---|---:|---:|---:|---:|
| `session_memory` | 16 | 0 | 16 | 0.946 |
| `telemetry_watchdog` | 16 | 2 | 14 | 0.973 |
| `scenario_matrix` | 17 | 0 | 17 | 0.861 |
| `diff_patch_engine` | 15 | 0 | 15 | 0.926 |
| `reflexive_healer` | 14 | 0 | 14 | 0.882 |
| `asset_bundle` | 18 | 0 | 18 | 0.942 |
| `spec_ledger` | 11 | 0 | 11 | 0.898 |
| `verify_loop` | 19 | 0 | 19 | 0.950 |
| `auto_evolve_runner` | 17 | 0 | 17 | 0.966 |

## 明细

| 引擎 | 角色 | 文件 | 行数 | 状态 | 同名最高相似度 |
|---|---|---|---:|---|---:|
| `asset_bundle` | r01-waquanju-ceo | `r01-waquanju-ceo/engines/asset_bundle.py` | 61 | domain_variant | 0.685 |
| `asset_bundle` | r02-wapaibu-coo | `r02-wapaibu-coo/engines/asset_bundle.py` | 38 | domain_variant | 0.865 |
| `asset_bundle` | r03-washouxian-cfo | `r03-washouxian-cfo/engines/asset_bundle.py` | 42 | domain_variant | 0.865 |
| `asset_bundle` | r05-washenyuan-research | `r05-washenyuan-research/engines/asset_bundle.py` | 376 | domain_variant | 0.890 |
| `asset_bundle` | r06-wadeqing-analyst | `r06-wadeqing-analyst/engines/asset_bundle.py` | 232 | domain_variant | 0.867 |
| `asset_bundle` | r07-wademing-pm | `r07-wademing-pm/engines/asset_bundle.py` | 323 | domain_variant | 0.916 |
| `asset_bundle` | r08-wajiancheng-mvp | `r08-wajiancheng-mvp/engines/asset_bundle.py` | 113 | domain_variant | 0.922 |
| `asset_bundle` | r10-wachengmei-design | `r10-wachengmei-design/engines/asset_bundle.py` | 124 | domain_variant | 0.892 |
| `asset_bundle` | r11-wadianti-copy | `r11-wadianti-copy/engines/asset_bundle.py` | 119 | domain_variant | 0.922 |
| `asset_bundle` | r12-wayingliu-growth | `r12-wayingliu-growth/engines/asset_bundle.py` | 193 | domain_variant | 0.880 |
| `asset_bundle` | r13-wakecheng-csm | `r13-wakecheng-csm/engines/asset_bundle.py` | 150 | domain_variant | 0.942 |
| `asset_bundle` | r14-wajiaoyi-commerce | `r14-wajiaoyi-commerce/engines/asset_bundle.py` | 153 | domain_variant | 0.942 |
| `asset_bundle` | r15-wagongying-erp | `r15-wagongying-erp/engines/asset_bundle.py` | 157 | domain_variant | 0.910 |
| `asset_bundle` | r16-warenshi-hr | `r16-warenshi-hr/engines/asset_bundle.py` | 133 | domain_variant | 0.921 |
| `asset_bundle` | r17-wazhiwang-automation | `r17-wazhiwang-automation/engines/asset_bundle.py` | 134 | domain_variant | 0.908 |
| `asset_bundle` | r18-washucang-dataeng | `r18-washucang-dataeng/engines/asset_bundle.py` | 271 | domain_variant | 0.880 |
| `asset_bundle` | r19-wazhimo-ml | `r19-wazhimo-ml/engines/asset_bundle.py` | 309 | domain_variant | 0.916 |
| `asset_bundle` | r20-washouzhi-sre | `r20-washouzhi-sre/engines/asset_bundle.py` | 217 | domain_variant | 0.880 |
| `auto_evolve_runner` | r01-waquanju-ceo | `r01-waquanju-ceo/auto_evolve_runner.py` | 343 | domain_variant | 0.934 |
| `auto_evolve_runner` | r05-washenyuan-research | `r05-washenyuan-research/auto_evolve_runner.py` | 1102 | domain_variant | 0.768 |
| `auto_evolve_runner` | r06-wadeqing-analyst | `r06-wadeqing-analyst/auto_evolve_runner.py` | 483 | domain_variant | 0.901 |
| `auto_evolve_runner` | r07-wademing-pm | `r07-wademing-pm/auto_evolve_runner.py` | 622 | domain_variant | 0.829 |
| `auto_evolve_runner` | r08-wajiancheng-mvp | `r08-wajiancheng-mvp/auto_evolve_runner.py` | 327 | domain_variant | 0.934 |
| `auto_evolve_runner` | r09-wawenma-engineer | `r09-wawenma-engineer/auto_evolve_runner.py` | 309 | domain_variant | 0.894 |
| `auto_evolve_runner` | r10-wachengmei-design | `r10-wachengmei-design/auto_evolve_runner.py` | 389 | domain_variant | 0.949 |
| `auto_evolve_runner` | r11-wadianti-copy | `r11-wadianti-copy/auto_evolve_runner.py` | 385 | domain_variant | 0.948 |
| `auto_evolve_runner` | r12-wayingliu-growth | `r12-wayingliu-growth/auto_evolve_runner.py` | 393 | domain_variant | 0.946 |
| `auto_evolve_runner` | r13-wakecheng-csm | `r13-wakecheng-csm/auto_evolve_runner.py` | 402 | domain_variant | 0.949 |
| `auto_evolve_runner` | r14-wajiaoyi-commerce | `r14-wajiaoyi-commerce/auto_evolve_runner.py` | 393 | domain_variant | 0.947 |
| `auto_evolve_runner` | r15-wagongying-erp | `r15-wagongying-erp/auto_evolve_runner.py` | 394 | domain_variant | 0.966 |
| `auto_evolve_runner` | r16-warenshi-hr | `r16-warenshi-hr/auto_evolve_runner.py` | 394 | domain_variant | 0.966 |
| `auto_evolve_runner` | r17-wazhiwang-automation | `r17-wazhiwang-automation/auto_evolve_runner.py` | 368 | domain_variant | 0.916 |
| `auto_evolve_runner` | r18-washucang-dataeng | `r18-washucang-dataeng/auto_evolve_runner.py` | 458 | domain_variant | 0.901 |
| `auto_evolve_runner` | r19-wazhimo-ml | `r19-wazhimo-ml/auto_evolve_runner.py` | 811 | domain_variant | 0.809 |
| `auto_evolve_runner` | r20-washouzhi-sre | `r20-washouzhi-sre/auto_evolve_runner.py` | 396 | domain_variant | 0.888 |
| `diff_patch_engine` | r05-washenyuan-research | `r05-washenyuan-research/engines/diff_patch_engine.py` | 270 | domain_variant | 0.899 |
| `diff_patch_engine` | r06-wadeqing-analyst | `r06-wadeqing-analyst/engines/diff_patch_engine.py` | 235 | domain_variant | 0.897 |
| `diff_patch_engine` | r07-wademing-pm | `r07-wademing-pm/engines/diff_patch_engine.py` | 335 | domain_variant | 0.855 |
| `diff_patch_engine` | r08-wajiancheng-mvp | `r08-wajiancheng-mvp/engines/diff_patch_engine.py` | 70 | domain_variant | 0.920 |
| `diff_patch_engine` | r10-wachengmei-design | `r10-wachengmei-design/engines/diff_patch_engine.py` | 84 | domain_variant | 0.884 |
| `diff_patch_engine` | r11-wadianti-copy | `r11-wadianti-copy/engines/diff_patch_engine.py` | 81 | domain_variant | 0.896 |
| `diff_patch_engine` | r12-wayingliu-growth | `r12-wayingliu-growth/engines/diff_patch_engine.py` | 94 | domain_variant | 0.898 |
| `diff_patch_engine` | r13-wakecheng-csm | `r13-wakecheng-csm/engines/diff_patch_engine.py` | 90 | domain_variant | 0.926 |
| `diff_patch_engine` | r14-wajiaoyi-commerce | `r14-wajiaoyi-commerce/engines/diff_patch_engine.py` | 99 | domain_variant | 0.926 |
| `diff_patch_engine` | r15-wagongying-erp | `r15-wagongying-erp/engines/diff_patch_engine.py` | 92 | domain_variant | 0.906 |
| `diff_patch_engine` | r16-warenshi-hr | `r16-warenshi-hr/engines/diff_patch_engine.py` | 106 | domain_variant | 0.897 |
| `diff_patch_engine` | r17-wazhiwang-automation | `r17-wazhiwang-automation/engines/diff_patch_engine.py` | 78 | domain_variant | 0.920 |
| `diff_patch_engine` | r18-washucang-dataeng | `r18-washucang-dataeng/engines/diff_patch_engine.py` | 331 | domain_variant | 0.861 |
| `diff_patch_engine` | r19-wazhimo-ml | `r19-wazhimo-ml/engines/diff_patch_engine.py` | 458 | domain_variant | 0.831 |
| `diff_patch_engine` | r20-washouzhi-sre | `r20-washouzhi-sre/engines/diff_patch_engine.py` | 251 | domain_variant | 0.899 |
| `reflexive_healer` | r05-washenyuan-research | `r05-washenyuan-research/engines/reflexive_healer.py` | 416 | domain_variant | 0.797 |
| `reflexive_healer` | r06-wadeqing-analyst | `r06-wadeqing-analyst/engines/reflexive_healer.py` | 238 | domain_variant | 0.880 |
| `reflexive_healer` | r08-wajiancheng-mvp | `r08-wajiancheng-mvp/engines/reflexive_healer.py` | 109 | domain_variant | 0.856 |
| `reflexive_healer` | r09-wawenma-engineer | `r09-wawenma-engineer/engines/reflexive_healer.py` | 120 | domain_variant | 0.856 |
| `reflexive_healer` | r10-wachengmei-design | `r10-wachengmei-design/engines/reflexive_healer.py` | 105 | domain_variant | 0.838 |
| `reflexive_healer` | r12-wayingliu-growth | `r12-wayingliu-growth/engines/reflexive_healer.py` | 6 | domain_variant | 0.146 |
| `reflexive_healer` | r13-wakecheng-csm | `r13-wakecheng-csm/engines/reflexive_healer.py` | 124 | domain_variant | 0.841 |
| `reflexive_healer` | r14-wajiaoyi-commerce | `r14-wajiaoyi-commerce/engines/reflexive_healer.py` | 136 | domain_variant | 0.841 |
| `reflexive_healer` | r15-wagongying-erp | `r15-wagongying-erp/engines/reflexive_healer.py` | 138 | domain_variant | 0.838 |
| `reflexive_healer` | r16-warenshi-hr | `r16-warenshi-hr/engines/reflexive_healer.py` | 178 | domain_variant | 0.834 |
| `reflexive_healer` | r17-wazhiwang-automation | `r17-wazhiwang-automation/engines/reflexive_healer.py` | 156 | domain_variant | 0.834 |
| `reflexive_healer` | r18-washucang-dataeng | `r18-washucang-dataeng/engines/reflexive_healer.py` | 296 | domain_variant | 0.882 |
| `reflexive_healer` | r19-wazhimo-ml | `r19-wazhimo-ml/engines/reflexive_healer.py` | 486 | domain_variant | 0.797 |
| `reflexive_healer` | r20-washouzhi-sre | `r20-washouzhi-sre/engines/reflexive_healer.py` | 256 | domain_variant | 0.882 |
| `scenario_matrix` | r04-watiaoci-reviewer | `r04-watiaoci-reviewer/engines/scenario_matrix.py` | 87 | domain_variant | 0.794 |
| `scenario_matrix` | r05-washenyuan-research | `r05-washenyuan-research/engines/scenario_matrix.py` | 241 | domain_variant | 0.827 |
| `scenario_matrix` | r06-wadeqing-analyst | `r06-wadeqing-analyst/engines/scenario_matrix.py` | 174 | domain_variant | 0.861 |
| `scenario_matrix` | r07-wademing-pm | `r07-wademing-pm/engines/scenario_matrix.py` | 89 | domain_variant | 0.823 |
| `scenario_matrix` | r08-wajiancheng-mvp | `r08-wajiancheng-mvp/engines/scenario_matrix.py` | 76 | domain_variant | 0.843 |
| `scenario_matrix` | r09-wawenma-engineer | `r09-wawenma-engineer/engines/scenario_matrix.py` | 84 | domain_variant | 0.845 |
| `scenario_matrix` | r10-wachengmei-design | `r10-wachengmei-design/engines/scenario_matrix.py` | 76 | domain_variant | 0.833 |
| `scenario_matrix` | r11-wadianti-copy | `r11-wadianti-copy/engines/scenario_matrix.py` | 96 | domain_variant | 0.829 |
| `scenario_matrix` | r12-wayingliu-growth | `r12-wayingliu-growth/engines/scenario_matrix.py` | 4 | domain_variant | 0.106 |
| `scenario_matrix` | r13-wakecheng-csm | `r13-wakecheng-csm/engines/scenario_matrix.py` | 105 | domain_variant | 0.838 |
| `scenario_matrix` | r14-wajiaoyi-commerce | `r14-wajiaoyi-commerce/engines/scenario_matrix.py` | 97 | domain_variant | 0.838 |
| `scenario_matrix` | r15-wagongying-erp | `r15-wagongying-erp/engines/scenario_matrix.py` | 108 | domain_variant | 0.808 |
| `scenario_matrix` | r16-warenshi-hr | `r16-warenshi-hr/engines/scenario_matrix.py` | 129 | domain_variant | 0.777 |
| `scenario_matrix` | r17-wazhiwang-automation | `r17-wazhiwang-automation/engines/scenario_matrix.py` | 92 | domain_variant | 0.845 |
| `scenario_matrix` | r18-washucang-dataeng | `r18-washucang-dataeng/engines/scenario_matrix.py` | 191 | domain_variant | 0.853 |
| `scenario_matrix` | r19-wazhimo-ml | `r19-wazhimo-ml/engines/scenario_matrix.py` | 276 | domain_variant | 0.803 |
| `scenario_matrix` | r20-washouzhi-sre | `r20-washouzhi-sre/engines/scenario_matrix.py` | 194 | domain_variant | 0.861 |
| `session_memory` | r04-watiaoci-reviewer | `r04-watiaoci-reviewer/engines/session_memory.py` | 113 | domain_variant | 0.894 |
| `session_memory` | r05-washenyuan-research | `r05-washenyuan-research/engines/session_memory.py` | 335 | domain_variant | 0.856 |
| `session_memory` | r06-wadeqing-analyst | `r06-wadeqing-analyst/engines/session_memory.py` | 496 | domain_variant | 0.811 |
| `session_memory` | r07-wademing-pm | `r07-wademing-pm/engines/session_memory.py` | 384 | domain_variant | 0.928 |
| `session_memory` | r08-wajiancheng-mvp | `r08-wajiancheng-mvp/engines/session_memory.py` | 93 | domain_variant | 0.923 |
| `session_memory` | r10-wachengmei-design | `r10-wachengmei-design/engines/session_memory.py` | 101 | domain_variant | 0.923 |
| `session_memory` | r11-wadianti-copy | `r11-wadianti-copy/engines/session_memory.py` | 155 | domain_variant | 0.907 |
| `session_memory` | r12-wayingliu-growth | `r12-wayingliu-growth/engines/session_memory.py` | 169 | domain_variant | 0.907 |
| `session_memory` | r13-wakecheng-csm | `r13-wakecheng-csm/engines/session_memory.py` | 142 | domain_variant | 0.896 |
| `session_memory` | r14-wajiaoyi-commerce | `r14-wajiaoyi-commerce/engines/session_memory.py` | 189 | domain_variant | 0.889 |
| `session_memory` | r15-wagongying-erp | `r15-wagongying-erp/engines/session_memory.py` | 126 | domain_variant | 0.946 |
| `session_memory` | r16-warenshi-hr | `r16-warenshi-hr/engines/session_memory.py` | 136 | domain_variant | 0.946 |
| `session_memory` | r17-wazhiwang-automation | `r17-wazhiwang-automation/engines/session_memory.py` | 143 | domain_variant | 0.938 |
| `session_memory` | r18-washucang-dataeng | `r18-washucang-dataeng/engines/session_memory.py` | 262 | domain_variant | 0.859 |
| `session_memory` | r19-wazhimo-ml | `r19-wazhimo-ml/engines/session_memory.py` | 379 | domain_variant | 0.928 |
| `session_memory` | r20-washouzhi-sre | `r20-washouzhi-sre/engines/session_memory.py` | 219 | domain_variant | 0.859 |
| `spec_ledger` | r05-washenyuan-research | `r05-washenyuan-research/engines/spec_ledger.py` | 227 | domain_variant | 0.802 |
| `spec_ledger` | r10-wachengmei-design | `r10-wachengmei-design/engines/spec_ledger.py` | 146 | domain_variant | 0.868 |
| `spec_ledger` | r12-wayingliu-growth | `r12-wayingliu-growth/engines/spec_ledger.py` | 330 | domain_variant | 0.855 |
| `spec_ledger` | r13-wakecheng-csm | `r13-wakecheng-csm/engines/spec_ledger.py` | 134 | domain_variant | 0.886 |
| `spec_ledger` | r14-wajiaoyi-commerce | `r14-wajiaoyi-commerce/engines/spec_ledger.py` | 124 | domain_variant | 0.898 |
| `spec_ledger` | r15-wagongying-erp | `r15-wagongying-erp/engines/spec_ledger.py` | 125 | domain_variant | 0.898 |
| `spec_ledger` | r16-warenshi-hr | `r16-warenshi-hr/engines/spec_ledger.py` | 396 | domain_variant | 0.872 |
| `spec_ledger` | r17-wazhiwang-automation | `r17-wazhiwang-automation/engines/spec_ledger.py` | 190 | domain_variant | 0.794 |
| `spec_ledger` | r18-washucang-dataeng | `r18-washucang-dataeng/engines/spec_ledger.py` | 322 | domain_variant | 0.881 |
| `spec_ledger` | r19-wazhimo-ml | `r19-wazhimo-ml/engines/spec_ledger.py` | 460 | domain_variant | 0.872 |
| `spec_ledger` | r20-washouzhi-sre | `r20-washouzhi-sre/engines/spec_ledger.py` | 274 | domain_variant | 0.881 |
| `telemetry_watchdog` | r04-watiaoci-reviewer | `r04-watiaoci-reviewer/engines/telemetry_watchdog.py` | 117 | domain_variant | 0.895 |
| `telemetry_watchdog` | r05-washenyuan-research | `r05-washenyuan-research/engines/telemetry_watchdog.py` | 262 | domain_variant | 0.875 |
| `telemetry_watchdog` | r06-wadeqing-analyst | `r06-wadeqing-analyst/engines/telemetry_watchdog.py` | 460 | domain_variant | 0.920 |
| `telemetry_watchdog` | r07-wademing-pm | `r07-wademing-pm/engines/telemetry_watchdog.py` | 490 | domain_variant | 0.881 |
| `telemetry_watchdog` | r08-wajiancheng-mvp | `r08-wajiancheng-mvp/engines/telemetry_watchdog.py` | 102 | domain_variant | 0.910 |
| `telemetry_watchdog` | r10-wachengmei-design | `r10-wachengmei-design/engines/telemetry_watchdog.py` | 99 | domain_variant | 0.906 |
| `telemetry_watchdog` | r11-wadianti-copy | `r11-wadianti-copy/engines/telemetry_watchdog.py` | 13 | shared_adapter | 0.943 |
| `telemetry_watchdog` | r12-wayingliu-growth | `r12-wayingliu-growth/engines/telemetry_watchdog.py` | 13 | shared_adapter | 0.943 |
| `telemetry_watchdog` | r13-wakecheng-csm | `r13-wakecheng-csm/engines/telemetry_watchdog.py` | 128 | domain_variant | 0.948 |
| `telemetry_watchdog` | r14-wajiaoyi-commerce | `r14-wajiaoyi-commerce/engines/telemetry_watchdog.py` | 143 | domain_variant | 0.948 |
| `telemetry_watchdog` | r15-wagongying-erp | `r15-wagongying-erp/engines/telemetry_watchdog.py` | 155 | domain_variant | 0.973 |
| `telemetry_watchdog` | r16-warenshi-hr | `r16-warenshi-hr/engines/telemetry_watchdog.py` | 161 | domain_variant | 0.973 |
| `telemetry_watchdog` | r17-wazhiwang-automation | `r17-wazhiwang-automation/engines/telemetry_watchdog.py` | 143 | domain_variant | 0.927 |
| `telemetry_watchdog` | r18-washucang-dataeng | `r18-washucang-dataeng/engines/telemetry_watchdog.py` | 279 | domain_variant | 0.906 |
| `telemetry_watchdog` | r19-wazhimo-ml | `r19-wazhimo-ml/engines/telemetry_watchdog.py` | 412 | domain_variant | 0.920 |
| `telemetry_watchdog` | r20-washouzhi-sre | `r20-washouzhi-sre/engines/telemetry_watchdog.py` | 273 | domain_variant | 0.906 |
| `verify_loop` | r02-wapaibu-coo | `r02-wapaibu-coo/verify_loop.py` | 94 | domain_variant | 0.826 |
| `verify_loop` | r03-washouxian-cfo | `r03-washouxian-cfo/verify_loop.py` | 110 | domain_variant | 0.826 |
| `verify_loop` | r04-watiaoci-reviewer | `r04-watiaoci-reviewer/verify_loop.py` | 164 | domain_variant | 0.906 |
| `verify_loop` | r05-washenyuan-research | `r05-washenyuan-research/verify_loop.py` | 181 | domain_variant | 0.950 |
| `verify_loop` | r06-wadeqing-analyst | `r06-wadeqing-analyst/verify_loop.py` | 299 | domain_variant | 0.750 |
| `verify_loop` | r07-wademing-pm | `r07-wademing-pm/verify_loop.py` | 214 | domain_variant | 0.923 |
| `verify_loop` | r08-wajiancheng-mvp | `r08-wajiancheng-mvp/verify_loop.py` | 187 | domain_variant | 0.949 |
| `verify_loop` | r09-wawenma-engineer | `r09-wawenma-engineer/verify_loop.py` | 185 | domain_variant | 0.948 |
| `verify_loop` | r10-wachengmei-design | `r10-wachengmei-design/verify_loop.py` | 188 | domain_variant | 0.950 |
| `verify_loop` | r11-wadianti-copy | `r11-wadianti-copy/verify_loop.py` | 192 | domain_variant | 0.946 |
| `verify_loop` | r12-wayingliu-growth | `r12-wayingliu-growth/verify_loop.py` | 194 | domain_variant | 0.903 |
| `verify_loop` | r13-wakecheng-csm | `r13-wakecheng-csm/verify_loop.py` | 189 | domain_variant | 0.949 |
| `verify_loop` | r14-wajiaoyi-commerce | `r14-wajiaoyi-commerce/verify_loop.py` | 201 | domain_variant | 0.950 |
| `verify_loop` | r15-wagongying-erp | `r15-wagongying-erp/verify_loop.py` | 203 | domain_variant | 0.940 |
| `verify_loop` | r16-warenshi-hr | `r16-warenshi-hr/verify_loop.py` | 199 | domain_variant | 0.950 |
| `verify_loop` | r17-wazhiwang-automation | `r17-wazhiwang-automation/verify_loop.py` | 199 | domain_variant | 0.944 |
| `verify_loop` | r18-washucang-dataeng | `r18-washucang-dataeng/verify_loop.py` | 195 | domain_variant | 0.894 |
| `verify_loop` | r19-wazhimo-ml | `r19-wazhimo-ml/verify_loop.py` | 195 | domain_variant | 0.949 |
| `verify_loop` | r20-washouzhi-sre | `r20-washouzhi-sre/verify_loop.py` | 195 | domain_variant | 0.897 |
