# 能力调用频次盘点（2026-11-11）

> 工具：`python scripts/capability_usage.py [--since 2026-11-01] [--json]`
> 数据源：`*/workspace/logs/*.jsonl` 与 `workspace/logs/*.jsonl`（只读，共 34 个文件 / 1488 条事件 / 坏行 0）
> 时间跨度：2026-11-08 → 2026-11-11（**只有 4 天**）

---

## 一、结论先说：调用数据不能用来给这 22 张卡排序

`47` 张能力里只有 `9` 张有调用记录，而这 9 张里 **8 张是刚升级的新包**（记录来自我自己的
selftest 与验证跑，不是真实业务调用）。唯一有记录的老卡是 `ppt-generator`（4 次）。

| 能力 | 归属 | 调用 | 通过 | 失败 | 说明 |
|---|---|---|---|---|---|
| `eval-report` | r19 | 45 | 45 | 0 | 新包，记录来自自检 |
| `decision-gate` | r01 | 31 | 1 | 30 | 新包，**失败 30 次是负向测试** |
| `hiring-scorecard` | r16 | 29 | 29 | 0 | 新包，自检 |
| `po-validate` | r15 | 29 | 29 | 0 | 新包，自检 |
| `model-audit` | r03 | 22 | 0 | 22 | 新包，**全部是负向测试** |
| `order-lifecycle` | r14 | 20 | 20 | 0 | 新包，自检 |
| `qbr-health` | r13 | 20 | 20 | 0 | 新包，自检 |
| `tdd-review-pair` | r09 | 20 | 20 | 0 | 新包，自检 |
| `ppt-generator` | r08 | 4 | 4 | 0 | **唯一有真实记录的老卡** |

> `decision-gate` 与 `model-audit` 的高失败率不是缺陷，是**负向测试被执行过**的证明。
> 这正是"有测试"和"没测试"的区别——没测试的卡不会有失败记录。

**所以"按调用量给 22 张卡排序"这条路走不通**：分母全是 0，排序没有信息量。

---

## 二、真正的发现：目录与实际调用脱节

盘点跑出了 **35 组"日志里有、目录没登记"的 (角色, skill, action)**。它们才是真实高频工作：

| 角色 | skill.action | 调用 | 对应能力卡 |
|---|---|---|---|
| r18 | `quality.check` | **185** | 未登记（`data-validation` 只登记了 r06 的 `quality:audit`） |
| r17 | `integration.workflow` | **86** | 未登记 |
| r07 | `prd.prd` | **68**（48 通过 / 20 失败） | 未登记（`prd-authoring` 登记的是 `prdguard:check`） |
| r17 | `approval.publish` | **66** | 未登记 |
| r18 | `incremental.backfill` | **65** | 未登记 |
| r18 | `catalog.lineage` | **65** | 未登记 |
| r10 | `logo.logo` | **55** | 未登记 |
| r11 | `copy.article` | **51** | 未登记 |
| r12 | `diagnose.diagnose` | **48** | 未登记 |
| r19 | `release.candidate` | **45** | 未登记 |
| r19 | `modelcard.card` | **45** | 未登记 |
| r08 | `slice.mvp` | **41** | 未登记 |
| r14 | `payment.refund` | **32** | 未登记 |
| r14 | `signature.document` | **32** | 未登记 |
| r02 | `schedule.wbs` | **29** | 未登记 |

**这意味着**：团队实际干的活大量走"角色级技能"，而能力目录登记的是另一套东西。
22 张旧卡里的 `analyze-procurement`、`brand-guardian`、`image-ops`、`miniapp-builder`、
`office-plugin`、`html-report-presentation`、`smart-product-selector`、`xhs-content-skills`
**一次都没被调用过**，而 `r18 quality.check` 被调了 185 次却没有对应能力卡。

> 这不是"旧卡没用"，是**目录没跟上实际工作**。在修好这个映射之前，
> 任何"按使用率决定升级顺序"的结论都不可信。

---

## 三、第二个发现：9 张 skill 卡没有夹具，所以从来没法自检

对比一下两类卡的差别：

| 类型 | 数量 | 有 clean/dirty 夹具 | 能写 `--self-test` |
|---|---|---|---|
| 角色级 harness 门禁 | 20 个角色 | ✅ `examples/*_dirty.json` 成对齐全 | ✅ 容易 |
| 9 张 skill 旧卡 | 9 | ❌ **没有**（如 r14 `selection` 无任何 fixture） | ❌ 必须先造夹具 |

这就是 9 张 skill 卡一直停在 E 级的技术原因：**它们的门禁存在，但没有可断言的输入**。
新 20 包之所以能快速做到 100 分，是因为 16 个直接复用了既有成对夹具。

---

## 四、本轮已修复的问题（2026-11-11）

| # | 问题 | 修复 |
|---|---|---|
| 1 | **目录与调用脱节**：38 组调用无能力卡 | 把调用量 ≥10 的 **34 组**写入 `catalog.observed_actions`（含 calls/ok/fail/last_seen/suggested_pack）；低于阈值的 4 组跳过 |
| 2 | **漂移无法自动发现** | 新增 `capability_usage.py --check`：有调用量 ≥ 阈值却未备案的 action 时退出码 1，可进 CI |
| 3 | **工具 bug：按 skill 全局聚合** | 改为 `(role, skill, action)` 三元组；并**去掉 skill 级兜底**（兜底会把同 skill 下未声明的 action 也计入，属虚增） |
| 4 | **entry 声明与实际调用不一致** | 记录 `catalog.entry_mismatch`（3 条：`model-audit` 的 `cfo.runway`、`hiring-scorecard` 的 `recruit.offer`、`eval-report` 的 `evaluation.scorer`） |
| 5 | **无法查看"已观测但无卡"的候选** | 新增 `python guagua.py capabilities --observed [--json]` |

修复后的自证：

```bash
python scripts/capability_usage.py --check        # exit 0：无未备案的高频调用
python guagua.py capabilities --observed         # 34 组候选，按真实调用量排序
```

**为什么用 `observed_actions` 而不是塞进 `capabilities`**：
它们还没有能力卡，混进 `capabilities` 会让"能力数"虚增、均分失真，
也会让 `--probe` 报 34 个"缺能力卡"。单独一段备案，既修好了测量仪器，又不污染口径。

---

## 五、修正后的升级路线（按性价比排序）

### Track A（先做，1–2 h，最高性价比）：把映射修对

不改任何代码，只做两件事：
1. 给 35 组未登记调用中的高频项（上表 15 条）在 `catalog.json` 登记为能力（`kind: skill`，
   `entry` 指向真实 `(role, skill, action)`，`status: active`）；
2. 修正已登记但 action 名不对的条目（如 `prd.prd` vs `prdguard.check`）。

**收益**：下一次盘点就能看到真实使用率；否则 22 张卡永远无法数据驱动排序。

### Track B（按"角色是否还有方法入口"升级，6–8 h）

既然 usage 不能排序，改用**结构性判据**：这张卡是否是某职能的**唯一方法入口**。

| 批次 | 卡片 | 判据 | 工作量 |
|---|---|---|---|
| **B1** | `web-app-development`、`frontend-design`（r09） | r09 只剩这两张 knowledge 卡；没有它们，"怎么建 Web 应用"无方法可依 | 2 包 |
| **B2** | `design-system`、`whiteboard`、`brand-guardian`、`image-ops`（r10） | r10 的设计系统/白板/品牌/图像处理与 `ecommerce-designer` 正交，是独立方法 | 4 包 |
| **B3** | `tashan-research-skills`、`industry-panorama-research`、`market-intelligence-radar`、`deep-research-assistant`（r05） | 都是具体研究方法；`evidence-ledger` 只管流程与来源 | 4 包 |
| **B4** | 9 张 skill 卡 | **每张必须先造 ≥2 正例 + ≥3 反例夹具**，否则无法自检 | 9 包 + 9×5 夹具 |
| **B5** | `strategic-growth-compass`、`business-ops-analysis`、`user-research-toolkit`、`build-web-data-visualization`、`rednote-post` | 单张，按需 | 5 包 |

**建议顺序：Track A → B1 → B2 → B4 → B3 → B5**。

理由：
- Track A 不做，后面全是拍脑袋；
- B1/B2 是"唯一入口"，缺了角色会答不上话；
- **B4 放中间**是因为它工作量最大（要造夹具），但它是唯一能让 9 张卡变成"可验证"的路径；
- B3/B5 是锦上添花，可按真实需求触发。

---

## 六、诚实的三条限制

1. **只有 4 天日志**：11-08 之前没有记录，无法判断更早的使用习惯。
2. **只有本机调用**：不含线上真实流量，也不含用户直接对话触发的调用
   （那部分走 `guagua.py call`，未必写同一份日志）。
3. **knowledge 卡天然零记录**：它们没有命令入口，所以永远不会出现在日志里。
   **零记录 ≠ 无价值**，本报告不据此判它们该降级。

---

## 七、复现方式

```bash
python scripts/capability_usage.py                 # 完整报告
python scripts/capability_usage.py --since 2026-11-01 --top 30
python scripts/capability_usage.py --json > usage.json
```

> 工具第一版有个真 bug：按 `(skill, action)` 全局聚合，把 r18 的 `quality.check`
> 错记到 r06 的 `data-validation` 上（两个角色重名 `quality`）。
> 已改为 `(role, skill, action)` 三元组，本报告是修正后的数字。
