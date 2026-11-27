# R16 黄金样本：招聘与绩效包 + 薪酬准备包

> 由 `golden/build_golden.py` 调用本角色真实技能生成（非手写），
> 输入为 `examples/*.json` 干净夹具。

| 样本 | 技能链 | 夹具 | 验收点 |
|---|---|---|---|
| `hiring-performance-pack.html` | recruit.opening → applicant → offer → performance.appraisal | `opening.json` / `applicant.json` / `offer.json` / `appraisal.json` | 状态白名单、必填字段、Accepted 前置；评分区间与 KRA 完整性 |
| `payroll-compliance-pack.html` | payroll.input → payroll.calc | `payroll_input.json` / `payroll_calc.json` | 频率/组成项类型、source 溯源；毛额与净额恒等、制度字段可溯源 |

## 怎么重新生成

```bash
python r16-warenshi-hr/golden/build_golden.py
```

## 验收

```bash
python r16-warenshi-hr/run_tests.py
```

- golden：≥2 份 HTML、>1KB、含 `data-theme="light"` / `@page` / `thead/th`；
- misuse：`appraisal_missing_scorecard.json` 触发 `appraisal.kra_complete`；
  `payroll_net_mismatch.json` 触发 `payroll.net`。

## 说明

- 薪酬是「准备」不是「发放」：本包交 R03 与外部专业复核，不直接发薪；
- 招聘只产工件，不擅自发 Offer/入职；绩效不替人定档。
