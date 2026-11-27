# R03 黄金样本：月结包 + 合同审查包

> 两份 HTML 均由 `golden/build_golden.py` 调用本角色真实技能生成（非手写），
> 输入是仓库内 `examples/*.json` 夹具，不含项目资产。

| 样本 | 技能链 | 夹具 | 验收点 |
|---|---|---|---|
| `month-end-close.html` | financial.rollforward → financial.recon → financial.variance | `financial_rollforward.json` / `financial_recon.json` / `financial_variance.json` | roll-forward 恒等式；六桶对账与匹配率；重大差异 driver 为 why 非 what |
| `contract-review.html` | contract.scan → contract.redline → contract.policy | `contract_scan.json` / `contract_redline.json` / `contract_policy.json` | 12 条规则 + sign_gate；整改未闭合项；政策五字段可执行 |

## 怎么重新生成

```bash
python r03-washouxian-cfo/golden/build_golden.py
```

生成器用固定运行日、sha256 截断摘要，结果可复算；不含时间戳/随机数。

## 验收

```bash
python r03-washouxian-cfo/run_tests.py
python r03-washouxian-cfo/tests/test_thickness_samples.py   # 或 run_tests 的 T15
```

- golden 断言：≥2 份 HTML、每份 >1KB、含 `data-theme="light"` / `@page` / `thead/th`；
- misuse 断言：2 份误用输入分别被 `financial.rollforward` 的 `balance` 与
  `contract.policy` 的 `policy_field` 门禁拒绝。

## 说明

- 月结包如实记录未平账户与未归因差异（这是该技能的职责），因此综合结论为
  「已阻断放行」，不是伪造全绿；
- R03 只产校验与整改清单，不代签、不出具持牌意见。
