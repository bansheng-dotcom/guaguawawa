# 20 角色提示词体系可行性报告

> 版本：v1.0 ｜ 日期：2026-11-10
> 范围：`d:\蛙蛙呱呱\蛙蛙呱呱agents团`（20 角色一人公司）
> 命题：单角色可被独立调用时，20 个角色是否都需要一套「模糊指令 → 提示词链」体系？需要几套？怎么落？

---

## 0. 结论摘要

1. **需要，而且单角色直调比编排更需要。**
   走模式 A 时没有 R01 兜底，模糊指令的澄清、补齐、拆解全部压在本角色身上；现有实现直接静默落到默认动作。

2. **但不能是 20 套。**
   现状已经做了 20 套的雏形：**15 份同名 `intent_compiler.py`、0 份相同**，加 5 个自定义命名，合计约 **3,993 行**意图编译代码；其中出现 4 行空壳、硬编码 `confidence: 0.92`、关键词未命中就换动作等问题。继续按角色复制只会放大碎片。

3. **可行方案：1 个共享 L02 内核 + 20 份声明式角色清单 + 20 个薄适配器。**
   不改现有技能、不改任务卡契约、不改 harness；每个角色保留独立调用入口，行为可解释、可回归。

4. **可行性评级**

| 维度 | 评级 | 说明 |
|---|---|---|
| 技术可行性 | A | 纯 stdlib + JSON，无新增依赖；接口可完全兼容现有 `_route() -> (skill, action, defaults)` |
| 契约兼容性 | A | 适配器保留旧类名与旧返回结构，139 个测试文件可零改动通过 |
| 收益/成本 | A- | 预计净减重复代码 ≥ 2,500 行，20 角色统一获得澄清与规格能力 |
| 实施风险 | B | 主要风险是 166 个技能动作命名异构、术语差异大，需要清单校验 |
| 结论 | **Go（有条件）** | 条件见第 8 节 |

---

## 1. 问题界定：先拆清「这套体系」指什么

「提示词体系」在三层上，20 个角色的需求强度完全不同：

| 层 | 内容 | 谁需要 | 现状 |
|---|---|---|---|
| **L0 角色宪法** | 边界、红线、不可做清单、交付标准 | 20/20 都需要 | `SKILL.md` + `ORG.md`，但厚度 5~142 行，极不均 |
| **L1 意图编译** | 模糊指令 → 结构化 Spec → 动作/DAG → 澄清问题 | 20/20 都需要 | 有 20 份实现，5 种命名，质量从 4 行到 409 行 |
| **L2 生成模板** | 具体写作/设计/研究/评审的提示词块与反例 | 约 11 个生成型角色 | 多数写在 `skills/*.py` 里，未抽成模板 |

**关键判断：**
- L1 是**公共能力**，应该只有一份内核；让 20 个角色各写一遍，是当前最大的工程债。
- L2 是**角色专有资产**，应该按角色差异化，不能统一，也不该统一。
- L0 是**治理资产**，必须硬编码拦截，不能交给提示词「劝」模型别越界。

---

## 2. 现状体检（基于仓库实测）

### 2.1 规模基线

| 指标 | 实测值 |
|---|---|
| 角色数 | 20 |
| 技能模块总数 | 166（单角色 7~19 个） |
| 角色 `agent.py` 行数 | 322~807 行 |
| `engines/` 文件数 | 242 |
| `engines/` 总行数 | 37,217 |
| 同名引擎重复 | `asset_bundle.py` ×18、`scenario_matrix.py` ×17、`session_memory.py` ×15、`slop_guard.py` ×15、`telemetry_watchdog.py` ×15、`intent_compiler.py` ×15 |
| 意图编译代码 | 约 3,993 行（15 份 intent_compiler + 5 份 prompter + r06/r07 自定义命名） |
| 测试文件（`tests/`） | 139 |

### 2.2 三个硬伤（可直接复现）

**硬伤 1：4 行空壳编译器**
[r12 `intent_compiler.py`](../r12-wayingliu-growth/engines/intent_compiler.py) 全文只有 4 行，无论输入什么都返回固定四阶段：

```python
class IntentCompiler:
    def compile_intent(self, intent_text):
        return ["Discover", "Hypothesis", "A/B Test", "Analyze"]
```

**硬伤 2：假置信度**
[r02 `prompter.py`](../r02-wapaibu-coo/engines/prompter.py) 用关键词判 6 个分支，却把置信度写死为 `0.92`。这意味着所有下游都无法用置信度做「不确定就追问」的决策。

**硬伤 3：未命中就静默换动作**
[r06 `agent.py`](../r06-wadeqing-analyst/agent.py) 的 `_route()` 在 16 条关键词全不命中时，直接返回 `("quality", "audit", {})`。用户说「看看这数据有没有问题」以外的任何模糊表达，都会被当成数据质检，且没有任何提示。

### 2.3 两个结构性错配

1. **编译器与主链路脱节**：R02、R03、R04 的 `agent.py` 完全没有引用 `engines/`；R04 只在测试与演进脚本里用。也就是说，部分角色「有编译器，但真实调用不走它」。
2. **命名不统一，无法复用**：同一个职责出现 `compile_intent`、`decompile_intent`、`compile`、`compile_intent_to_dag` 四种方法名，类名有 `IntentCompiler`、`ResearchIntentCompiler`、`VisualIntentCompiler`、`IntentDAGCompiler`、`AnalysisIntentDecompiler`。这已经是「20 套系统」的既成事实，只是每套都不完整。

### 2.4 全角色逐项摸底

| 角色 | 技能数 | SKILL.md 行数 | 意图编译形态 | 主链路接入 | 分档 |
|---|---:|---:|---|---|---|
| R01 CEO | 8 | 83 | `prompter.py` 61 行 | 是（10 处） | C 编排型 |
| R02 COO | 7 | 97 | `prompter.py` 49 行 | 否（0 处） | C 编排型 |
| R03 CFO | 8 | 88 | `prompter.py` 123 行 | 否（0 处） | B 计算型 |
| R04 Reviewer | 7 | 93 | `intent_compiler.py` 164 行 | 仅测试/脚本 | C 评审型 |
| R05 Research | 7 | 112 | `intent_compiler.py` 324 行 | 是 | A 生成型 |
| R06 Analyst | 19 | 137 | `intent_decompiler.py` 283 行 | 是（6 处） | B 计算型 |
| R07 PM | 9 | 102 | `intent_dag_compiler.py` 293 行 | 是（5 处） | A 生成型 |
| R08 MVP | 7 | 89 | `intent_compiler.py` 195 行 | 是 | A 生成型 |
| R09 Engineer | 8 | 124 | `intent_compiler.py` 123 行 | 是（6 处） | A 生成型 |
| R10 Design | 10 | 108 | `intent_compiler.py` 139 行 + `prompter.py` | 是 | A 生成型 |
| R11 Copy | 8 | **5** | `intent_compiler.py` 155 行 | 是 | A 生成型 |
| R12 Growth | 9 | 58 | `intent_compiler.py` **4 行** | 是 | A 生成型 |
| R13 CSM | 8 | 70 | `intent_compiler.py` 124 行 | 是 | A 生成型 |
| R14 Commerce | 8 | 84 | `intent_compiler.py` 139 行 | 是 | B 计算型 |
| R15 ERP | 7 | 87 | `intent_compiler.py` 138 行 | 是 | B 计算型 |
| R16 HR | 7 | 100 | `intent_compiler.py` 225 行 | 是 | B 计算型 |
| R17 Automation | 8 | 104 | `intent_compiler.py` 150 行 | 是 | C 编排型 |
| R18 DataEng | 7 | 127 | `intent_compiler.py` 383 行 | 是（5 处） | B 计算型 |
| R19 ML | 7 | 142 | `intent_compiler.py` 409 行 | 是 | A 生成型 |
| R20 SRE | 7 | 123 | `intent_compiler.py` 272 行 | 是 | B 计算型 |

> 说明：分档定义见第 3 节；「主链路接入」按 `agent.py` 对 `engines/` 的引用计数判断。

---

## 3. 20 个角色到底需不需要？——需要，但厚度不同

### 3.1 三档需求模型

| 档位 | 角色 | 产物性质 | L1 编译 | L2 生成模板 | 判断 |
|---|---|---|---|---|---|
| **A 生成型** | R05、R07、R08、R09、R10、R11、R12、R13、R19 | 方案、文本、代码、图、模型实验 | 必需 | **必需且要厚**（风格、反例、平台约束） | 最需要这套体系 |
| **B 计算型** | R03、R06、R14、R15、R16、R18、R20 | 账本、指标、核对、巡检 | 必需 | **不需要长篇提示**，需要输出契约 + 口径 + 反例 | 需要 L1，不需要 L2 |
| **C 编排/评审型** | R01、R02、R04、R17 | 任务卡、评审结论、编排图 | **最重**（拆解质量决定全链路） | 需要评审/编排模板 | L1 权重最高 |

### 3.2 直接回答

- **20/20 都需要 L1**：因为没有 L1，单角色直调只能靠关键词撞动作，撞不中就静默走默认动作（已实证）。
- **只有约 11 个需要厚 L2**：B 档角色如果强行加「写作型提示词」，只会增加塑料感，和 SOP 的 L05「反 AI 味」目标相反。
- **0 个需要独立实现 L1**：角色差异放进清单（词表、动作、必填字段、红线），代码只有一份。

---

## 4. 方案对比

| 方案 | 做法 | 成本 | 风险 | 结论 |
|---|---|---|---|---|
| A. 20 套独立体系 | 每个角色补齐自己的编译器和提示词库 | 极高，重复代码继续膨胀 | 术语漂移、假置信度、不可回归 | **不可行**（现状已证明） |
| B. 只做 R01 一套 | 编排器统一澄清与拆解，单角色保持现状 | 低 | 模式 A 仍然瞎猜；用户直接点 R06 时体验不变 | **不满足需求** |
| C. 共享内核 + 20 清单 | 1 份 L02 内核 + 20 份 JSON 清单 + 薄适配器 | 中 | 需要一次性梳理 166 个动作 | **推荐** |

### 4.1 方案 C 架构

```
用户模糊指令（单角色直调 / R01 派单）
        │
        ▼
┌─────────────────────────────────────────────┐
│ shared/prompt_kernel/  （唯一内核，纯 stdlib）│
│  1. load_profile(role_id)                   │
│  2. extract_spec(intent, profile)           │
│  3. detect_missing(spec, profile)           │
│  4. build_questions(missing, max=3)         │
│  5. plan_route(spec, profile.actions)       │
│  6. build_dag(steps, deps)                  │
│  7. render_prompt_blocks(spec, profile)     │
│  8. score_confidence(spec, profile)  ← 可复算 │
└─────────────────────────────────────────────┘
        │  PromptPlan（JSON，可落盘）
        ▼
rXX/engines/intent_compiler.py  （10~20 行适配器，保留旧类名）
        ▼
rXX/agent.py  _route()  →  (skill, action, defaults)  ← 契约不变
        ▼
skills/ → harness 门禁 → workspace/artifacts/{task_id}/prompt_plan.md
```

### 4.2 角色清单（每角色一份，≤80 行）

```json
{
  "role_id": "r06",
  "domain": "数据分析",
  "lexicon": {
    "metric": {"gmv": ["gmv", "成交额", "销售额"], "cvr": ["转化率", "cvr"]},
    "dimension": {"channel": ["渠道", "来源"], "city": ["城市"]},
    "time": {"last_7d": ["上周", "近7天"], "last_30d": ["上月", "近30天"]}
  },
  "actions": [
    {"skill": "explore", "action": "trend",  "when": ["趋势", "走势"], "required": ["dataset", "metric", "time"], "defaults": {"date": "date", "value": "amount"}},
    {"skill": "quality", "action": "audit",  "when": ["质检", "脏数据"], "required": ["dataset"], "defaults": {}}
  ],
  "spec_fields": {"required": ["dataset", "metric", "time"], "optional": ["dimension", "comparison"]},
  "assumptions": {"time": "last_30d"},
  "clarify": {"max_questions": 3, "never_silent_default": true},
  "output_contract": {"format": "md", "must_include": ["口径", "样本量", "结论", "置信区间"]},
  "redlines": ["不得外推无数据覆盖的时间窗", "不得省略样本量"],
  "l2_prompt_blocks": []
}
```

生成型角色额外有 `l2_prompt_blocks`（风格、平台约束、反例、禁用词），计算型角色该字段为空——这就是「厚度差异」的落点。

### 4.3 关键机制

| 机制 | 规则 |
|---|---|
| 澄清 | 缺必填字段 → 最多 3 问；问题必须带候选项，不能开放式追问 |
| 假设 | 不可问但可默认 → 写入 `assumptions[]` 并在产物首屏标注 |
| 置信度 | `matched_required / total_required`，可复算，禁止常量 |
| 路由 | 只允许命中 `profile.actions` 中已注册的 `(skill, action)`；启动时全量校验 |
| 未命中 | 返回 `needs_clarification=true`，**禁止静默落到默认动作** |
| 降级 | 内核不可用 → 旧关键词路由；旧路由未命中 → 澄清，不再默认 |
| 红线 | 从清单读取，交给 harness 硬拦截，不写进提示词「请求」模型遵守 |

---

## 5. 技术可行性验证

### 5.1 接口零破坏

现状：`agent.py` 的 `_route(intent)` 返回 `(skill_name, action, defaults)`，`run_task()` 再合并端口参数。
方案 C 的适配器可以继续返回同一三元组，只在 `defaults` 前插入一次编译：

```python
def _route(intent: str):
    plan = compile_intent(intent, load_profile(ROLE))
    if plan["needs_clarification"]:
        raise ClarifyRequired(plan["questions"], plan["assumptions"])
    return plan["route"]["skill"], plan["route"]["action"], plan["route"]["params"]
```

- 成功路径：返回值结构不变，`run_task()` 无需改动。
- 失败路径：新增 `ClarifyRequired` 异常，`agent.py` 捕获后输出结构化问题并退出码 2；这是新增分支，不影响既有任务卡。
- `manifest` / `demo` / `test` 等 CLI 子命令不受影响。

### 5.2 依赖可行性

- 仓库无 `requirements.txt`，引擎层以标准库为主；清单用 **JSON**，不引入 PyYAML。
- 不强制依赖 LLM：第一版用「词表 + 正则 + 动作目录」即可跑通；LLM 只作为可选增强（缺字段时的改写与追问），不可用时自动降级。
- 落盘产物 `prompt_plan.md` 与现有 `workspace/artifacts/{task_id}/` 结构一致。

### 5.3 与现有 SOP 的关系

SOP 已把「L02 意图解构」定义为第 1 轮基石，并要求每个角色有 `engines/intent_compiler.py`。本方案**不新增第 11 层**，而是把 L02 从「20 份手写关键词 DAG」升级为「1 份内核 + 20 份清单」，属于存量层升级，符合十维演进模型。

### 5.4 已有可复用资产

- `skills/` 已暴露 166 个动作，可直接生成动作目录初稿。
- 139 个测试文件可作为零回归基线。
- `harness/`、`contracts/` 已具备验收能力，编译器只负责「说清楚要做什么」，不替代门禁。

---

## 6. 评测与验收标准

### 6.1 回归集设计

- **规模**：20 角色 × 10 条 = 200 条模糊指令。
- **三类分布**：极短（≤6 字）、歧义（一词多解）、跨域（命中 2 个以上动作词）。
- **来源**：每角色从 `SKILL.md` 的能力域反向生成，避免只测典型案例。

### 6.2 五条硬指标（机器可测）

| # | 指标 | 通过线 |
|---|---|---|
| 1 | 澄清可用 | 20/20 角色 `clarify --intent` 可运行，问题数 ≤3 |
| 2 | 禁止静默默认 | 200 条模糊指令中，静默落到默认动作的次数 = 0 |
| 3 | 假设显式 | 每条输出满足 `assumptions` 非空 或 `questions` 非空 |
| 4 | 置信度可复算 | 同一输入两次运行 confidence 相同，且等于字段匹配率 |
| 5 | 零回归 | 139 个既有测试文件全部通过；`run --task` 同输入同输出 |

### 6.3 代码收敛指标

- 15 份 `intent_compiler.py` → 1 份内核 + 20 个 ≤20 行适配器。
- 内核 ≤400 行，单角色清单 ≤80 行。
- 净减少重复代码 ≥ 2,500 行（不含清单新增）。

---

## 7. 分期落地

| 阶段 | 内容 | 交付物 | 退出条件 |
|---|---|---|---|
| P0 基线 | 固化现有 139 个测试结果；导出 20 角色「动作目录 + 必填字段」初稿 | `docs/baseline.md`、`actions_catalog.json` | 基线可复跑 |
| P1 内核 + 双试点 | 内核 + R06（计算型）、R11（生成型）两份清单 | `shared/prompt_kernel/`、2 份 profile | 两个试点通过 6.2 全部指标 |
| P2 全量铺开 | 其余 18 角色清单 + 适配器；旧类名保留 | 20 份 profile、20 个适配器 | 200 条回归集通过率 100% |
| P3 沉淀 | 失败样本 → few-shot；成功拆解 → 流程模板（对齐 AWM） | `cases/prompt_regressions/` | 同类模糊指令二次命中率提升 |

> 为避免一次性改动过大，P2 按 A/B/C 三档顺序推进：先生成型（收益最大），再计算型（最需要确定性），最后编排/评审型（改动面最大）。

---

## 8. 风险清单与对策

| 风险 | 触发场景 | 对策 |
|---|---|---|
| 166 个动作命名异构 | 清单里写了不存在的 action | 启动时全量校验；校验失败直接报错，不带病运行 |
| 角色术语差异 | 同一词在 R06 指指标、在 R14 指订单状态 | 术语表放进各自 profile，禁止共享全局词表 |
| LLM 输出不稳定 | 追问或改写漂移 | 规则优先、结构化输出、golden test 固定样例 |
| 置信度造假 | 又出现常量 0.92 | 由公式计算 + 单测断言「非常量」 |
| 红线被提示词软化 | 财务/资金/越权场景 | 红线只走 harness 硬拦截；编译器无权放行 |
| 回归面积过大 | 20 角色同时改 | 适配器保留旧类名与旧三元组；按档位分批 |
| 清单与 SKILL 漂移 | 技能改了清单没改 | CI 校验 `actions_catalog.json` 与 `SKILL_BY_NAME` 一致 |

---

## 9. 决策建议

**结论：Go。**

三个前置条件（缺一不可）：

1. **只允许一套内核**。20 个角色各自实现 L1 的方案不再接受；角色差异只能进清单。
2. **每个角色必须有 10 条模糊指令回归**。没有回归的角色不允许接入编译器。
3. **编译器不得替代 harness**。红线、金额、越权、合规仍由硬门禁拦截，提示词只负责表达，不负责执法。

明确不做：

- 不为 B 档计算型角色编写长篇写作提示词。
- 不新增第 11 层演进阶段；本方案属于 L02 升级。
- 不在第一版引入 LLM 强依赖；规则可跑通后再加可选增强。

---

## 附录 A：证据索引

| 结论 | 证据位置 |
|---|---|
| 单角色路由靠关键词，未命中静默换动作 | `r06-wadeqing-analyst/agent.py` `_route()` |
| 4 行空壳编译器 | `r12-wayingliu-growth/engines/intent_compiler.py` |
| 硬编码置信度 0.92 | `r02-wapaibu-coo/engines/prompter.py` |
| 15 份同名编译器、哈希全不同 | `r*/engines/intent_compiler.py`（MD5 实测） |
| 242 个引擎文件、37,217 行 | `r*/engines/*.py` 统计 |
| 部分角色主链路不引用 engines | `r02`、`r03`、`r04` 的 `agent.py` |
| 技能总数 166 | `r*/skills/s*.py` 统计 |
| 测试基线 139 个文件 | `r*/tests/*.py` 统计 |
| L02 在 SOP 中的定位 | `SOP_AGENT_EVOLUTION_UNIVERSAL.md` 第四节 |

## 附录 B：统计口径

- 技能数：`skills/` 下排除 `_*.py` 的模块数。
- 引擎接入：`agent.py` 中 `from engines|import engines|engines.` 的匹配次数。
- 重复度：同名文件按 MD5 比对，15 份 `intent_compiler.py` 无一份相同。
- 行数：按物理行统计，含注释与空行。
