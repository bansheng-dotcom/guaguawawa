# R07 产品工作流黄金样本（T5）

> 状态：**黄金草稿**。三份 HTML 均由 `pm_workflows` 真实跑 fixtures 生成，
> 不含项目资产；R01 签发后才算对外样本。

| 样本 | 链路 | 夹具 | 门禁 |
|---|---|---|---|
| `new-product-prd.html` | W1 discovery → W2 prd | `pm_workflows/fixtures/bundle_new_product.json` | discovery PASS + PRD 八门禁 8/8 + premortem 5/5 |
| `feature-prd.html` | W2 prd → W3 priority → W4 acceptance | `pm_workflows/fixtures/bundle_feature.json` | 八门禁 8/8 + 排序可解释 + 主路径/边界/失败态齐备 |
| `project-briefing.html` | W5 briefing | `pm_workflows/fixtures/bundle_briefing.json` | 不代决策（决策人=创始人）+ 回链 2 条 |

## 怎么重新生成

```bash
python r07-wademing-pm/agent.py workflows run \
  --input r07-wademing-pm/pm_workflows/fixtures/bundle_new_product.json \
  --flow all --out-dir r07-wademing-pm/_test_tmp/golden_new \
  --html r07-wademing-pm/golden/new-product-prd.html \
  --html-title "0→1 新品 PRD：自由职业者发票管家"
```

`bundle_feature.json` / `bundle_briefing.json` 同理，只改 `--input`、`--out-dir`、`--html`。

## 验收

```bash
python r07-wademing-pm/run_tests.py
python -m pytest r07-wademing-pm/tests -q -p no:cacheprovider
python scripts/validate_profiles.py --role r07
python scripts/check_role_thickness.py --check
```

## 说明

- HTML 内嵌每个包的完整 JSON 与逐条门禁，便于人工对照；渲染不含时间戳，可复算。
- 每次 `run` 还会在同目录产出 `workflow_manifest.json`（sha256 + 门禁 + 交接回链），
  `workflows audit --dir <目录>` 可只读复核。
- 黄金对照看的是门禁结论、章节结构与回链，不是渲染字节级样式。
