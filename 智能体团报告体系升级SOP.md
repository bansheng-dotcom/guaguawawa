# 智能体团报告体系升级 SOP（v2 版）

> 依据《智能体团报告体系升级方案 v2 · 更优解》制定。
> 适用对象：20 个角色的报告链路（`core/report_bridge.py` + `core/report_renderer.py` + `REPORT-STANDARD.md`）。
> 总工期 **14 人日**，2 人并行约 **1.5—2 周**。
> 核心纪律：**每个阶段必须有自动化闸门；过不了闸门不进下一阶段。人签字不算过。**

---

## 0. 前置条件

| 项 | 要求 | 谁来确认 |
|---|---|---|
| 代码基线 | `git status` 干净，`guagua.py check` 20/20 通过 | 执行人 |
| 分支 | 从 `main` 拉 `feat/report-kernel`，**全程只在此分支** | 执行人 |
| 冻结窗口 | P0—P2 期间不改 `core/report_renderer.py` 的渲染逻辑 | R01 |
| 备份 | `git tag pre-report-upgrade` | 执行人 |
| 环境 | Python 3.12、可写 `workspace/`、可跑 `pytest` | 执行人 |

**角色分工**

| 角色 | 职责 | 交付 |
|---|---|---|
| R01 蛙全局 | 排期、冻结窗口、P3 验收签字 | 升级计划表、验收记录 |
| R06 蛙得清 | P0 影子运行、黄金测试、内核维护 | kernel 代码、契约测试报告 |
| R05 蛙深远 | P1 首个分析型角色迁移、spec 试点 | r05 spec + 迁移 diff |
| R04 蛙挑刺 | 纪律检查：闸门是否真跑过、报告是否合规 | 审计记录（只记录，不代改） |

---

## 1. 阶段总览

| 阶段 | 目标 | 人日 | 退出条件（硬） |
|---|---|---|---|
| **P0** | 内核下沉 + 影子运行 + 黄金测试框架 | 3 | r06 新旧输出 diff = 0 |
| **P1** | 5 个原型 + A 类 5 角色迁移 | 3 | 契约测试 15/15；首页四分数 |
| **P2** | B/C 类 15 角色模板化迁移 | 3 | 20/20 有 spec，无 `degraded` |
| **P3** | L1→L2→L3 路由 + `guagua report` | 3 | 一个跨域项目端到端跑通 |
| **P4** | 缓存 + 三阶段门禁 + CI 退出检查 | 2 | 命中率 ≥80%；legacy 清零 |

---

## 2. P0 · 内核下沉与影子运行（3 人日）

**目标**：把 reportkit 变成 `core/report_kernel`，但**不改任何一个角色的行为**——先证明"新旧一致"。

### 步骤

1. **建目录，迁模块**（0.5 天）

```bash
mkdir -p core/report_kernel
# store.py metrics.py fidelity.py layers.py snapshot.py annotations.py guard.py
```

迁入时只做三件事：改 import 路径、去掉 CLI 依赖、补 `__init__.py` 导出。

2. **改 `report_bridge.emit` 签名（向后兼容）**（0.5 天）

```python
def emit(..., dataset=None, spec=None, legacy=False):
    if legacy or spec is None:
        return _emit_legacy(...)        # 原逻辑原样保留
    contract = kernel.layers.build(role, result, dataset, spec)
    return _emit_contract(contract)
```

3. **建黄金测试框架**（1 天）

```bash
fixtures/r06/{normal.json, empty.json, failure.json}
scripts/contract_test.py --role r06 --compare legacy,kernel
```

规范化规则（写死在脚本里，避免"手工对齐"）：
- 去时间戳、去绝对路径、去随机 id；
- 数字统一保留 2 位、百分比统一符号；
- HTML 只比 `<body>` 的结构哈希，不比 CSS。

4. **r06 影子运行**（1 天）

r06 同时产出 legacy 与 kernel 两份，跑上面三个 fixture。

### 产物

```
core/report_kernel/*.py            (~900 行，迁入)
scripts/contract_test.py           (~120 行)
fixtures/r06/*.json                (3 个)
reports/p0_golden_diff.md          (差异报告)
```

### DoD（三条全绿）

- [ ] `contract_test.py --role r06` → **3/3 PASS，diff = 0**
- [ ] `guagua.py check` 仍 20/20
- [ ] r06 现有报告内容无变化（人工抽 1 份比对）

### 回滚

删分支即可；主分支未被改动。

---

## 3. P1 · 原型 + A 类五角色（3 人日）

**目标**：把"20 份 spec"变成"5 个原型 + 差异"，先拿 A 类验证。

### 步骤

1. **定义 5 个原型**（0.5 天）

```
report_specs/archetypes/{analyst,decision,delivery,review,design}.yaml
```

2. **写 JSON Schema 锁死字段**（0.5 天）

```json
{
  "type": "object",
  "required": ["extends", "role"],
  "additionalProperties": false,
  "properties": {
    "extends": {"enum": ["analyst","decision","delivery","review","design"]},
    "role": {"type": "string", "pattern": "^r\\d{2}$"},
    "overrides": {"$ref": "#/definitions/overrides"}
  }
}
```

3. **写 scaffolder**（0.5 天）

```bash
python scripts/report_spec.py new --role r05 --archetype analyst
python scripts/report_spec.py check          # 全量校验
```

4. **迁移 A 类 5 个角色**（1.5 天）
   顺序：r06 → r05 → r03 → r18 → r19（从最熟的开始，每次只切 1 个）。

```bash
python scripts/contract_test.py --role r05 --fixtures fixtures/r05/*.json
```

### DoD

- [ ] 5 个原型 + 5 个 role spec 通过 `report_spec.py check`
- [ ] 5 个角色契约测试 **15/15 PASS**（每角色 3 fixture）
- [ ] 任一份 A 类报告首页出现 **保留率/溯源率/弃置率/覆盖** 四个数
- [ ] 任取一条结论能点回观测行（人工抽 3 条）

### 回滚

`configs/legacy_roles.txt` 加回角色名 → 走旧路径，无需回滚代码。

---

## 4. P2 · B/C 类十五角色（3 人日）

**目标**：用模板批量生成，人工只审差异。

### 步骤

1. **批量生成**（0.5 天）

```bash
for r in r01 r02 r07 r08 r12 r14; do python scripts/report_spec.py new --role $r --archetype decision; done
for r in r04 r09 r10 r11 r13 r15 r16 r17 r20; do python scripts/report_spec.py new --role $r --archetype delivery; done
```

2. **人工审差异**（1.5 天）
   每个 role 文件只允许 ≤15 行 `overrides`；超出即视为"想写逻辑"，退回模板。

3. **分批切换**（1 天）
   每批 3 个角色，切换后跑契约测试，全绿再下一批。

### DoD

- [ ] **20/20 角色有 spec**，`report_spec.py check` 全绿
- [ ] 构建时无 `degraded: true` 水印
- [ ] 契约测试 **60/60 PASS**（20 角色 × 3 fixture）
- [ ] `configs/legacy_roles.txt` 只剩本轮未切的角色

**反模式警报**：任何 role spec 出现 `sections` 全量重定义 → 直接打回（说明原型没覆盖够，改原型而不是改角色）。

---

## 5. P3 · 路由与三层报告（3 人日）

**目标**：让 R01 真正汇总，R04 真正核验，CLI 成为唯一入口。

### 步骤

1. **R01 aggregate**（1 天）

```python
# r01/agent.py
def aggregate(task_cards, ports):
    l1 = [read_contract(p) for p in ports if p.kind == "report"]
    return kernel.layers.aggregate(l1)      # 只合并，不新增数字
```

2. **L2 禁裸数字护栏**（0.5 天）

```python
# core/report_kernel/guard.py
def assert_no_literals(text, allowed): ...
```

构建时 L2 命中裸数字 → 直接抛错。

3. **R04 completeness audit**（1 天）

```bash
python guagua.py call r04 report audit --project <id>
```

按 tier 出分数，不阻断（当前 `warn`）。

4. **CLI 收口**（0.5 天）

```bash
guagua.py report build --project <id>    # L1×N → L2 → L3
guagua.py report seal  --project <id> --by 张三
guagua.py report diff  --project <id> --from a --to b
```

### DoD

- [ ] 一个真实跨域项目跑通：**L1×N + L2 + L3** 全部产出
- [ ] L2 正文无裸数字（guard 开启后构建成功）
- [ ] `guagua report build` 可重复执行，输出哈希稳定
- [ ] 删掉一个角色的 spec → 构建**失败并指出角色名**

### 回滚

`guagua report` 是新增命令，旧流程不受影响；R01 的 aggregate 用开关 `r01.aggregate: false` 关闭。

---

## 6. P4 · 缓存、门禁收紧、退出检查（2 人日）

### 步骤

1. **section 级缓存**（1 天）

```
key = sha256(spec_section + dataset_slice + template_version + kernel_version)
cache/sections/<key>.html
```

manifest 记录 `cache_hit / cache_miss`。

2. **三阶段门禁**（0.5 天）

```yaml
# configs/report_policy.yaml
stage: warn          # warn → dryrun → deny
tier_A: { retention_min: 0.95, trace_min: 1.0 }
tier_B: { retention_min: 0.90, trace_min: 1.0 }
tier_C: { retention_min: 0.90, trace_min: 1.0 }
```

按周提升 stage，每次提升前看一周违规清单。

3. **CI 退出检查**（0.5 天）

```yaml
# .github/workflows/report.yml（或本地 pre-commit）
- report_spec.py check
- contract_test.py --all
- test -s configs/legacy_roles.txt && exit 1     # 必须为空
- ! grep -r "import reportkit" --include=*.py
```

### DoD

- [ ] 缓存命中率 **≥80%**（改一个源后重渲，manifest 可查）
- [ ] `stage: warn` 下跑满一周，违规清单有人看过
- [ ] CI 四项检查全绿
- [ ] **删除 `reportkit/` 独立 CLI**，`guagua report` 成为唯一入口
- [ ] `grep -r "reportkit"` 命中 0

---

## 7. 总验收（8 条，全绿才算升级完成）

| # | 验收 | 命令 / 证据 |
|---|---|---|
| 1 | 20/20 角色有 spec 且无 degraded | `report_spec.py check` |
| 2 | 契约测试 60/60 | `contract_test.py --all` |
| 3 | L2 写裸数字 → 构建失败 | 故意加 `3.5%`，记录报错 |
| 4 | spec 多一个键 → 校验失败 | 故意加 `foo: bar` |
| 5 | 删角色 spec → 构建失败并定位 | 删 r13，记录报错 |
| 6 | 缓存命中率 ≥80% | manifest |
| 7 | legacy 清零 + import 清零 | CI |
| 8 | 连续 5 次构建，分数不下降 | `workspace/baseline/` 对比 |

---

## 8. 风险登记册

| 风险 | 触发信号 | 立即动作 | 责任人 |
|---|---|---|---|
| 原型覆盖不足，角色乱写 overrides | 某 role spec >15 行 | 打回，改原型 | R06 |
| 契约测试"对齐式通过"（改测试不改代码） | diff 报告被人为改小 | R04 审查测试脚本变更 | R04 |
| L2 汇总拖时间 | P3 超 2 天未完 | 降级：L2 先只出"各角色结论表" | R01 |
| 缓存键漏字段导致脏缓存 | 改数据后报告没变 | 立刻禁用缓存，查 key 组成 | R06 |
| 门禁收紧后交付卡住 | 一周内 deny 次数 >3 | 退回 dryrun 一周 | R01 |
| 迁移期两套并存过久 | legacy 名单 2 周未减少 | 冻结新需求，专职迁移 | R01 |

---

## 9. 节奏

| 时点 | 动作 | 产出 |
|---|---|---|
| 每日 10 分钟 | 站会：昨天切了哪个角色、契约测试是否全绿 | 一句话状态 |
| 每个阶段末 | 闸门执行 + R04 抽查 | 阶段验收记录 |
| 每周五 | 分数看板（20 角色 × 保留率/覆盖率） | 周报一页 |
| P4 结束 | 升级复盘 | 复盘文档 + 遗留项 |

---

## 10. 附录 A｜命令速查

```bash
# 规格
python scripts/report_spec.py new   --role r12 --archetype decision
python scripts/report_spec.py check

# 契约测试
python scripts/contract_test.py --role r06 --compare legacy,kernel
python scripts/contract_test.py --all

# 报告
python guagua.py report build --project <id>
python guagua.py report audit --project <id>
python guagua.py report seal  --project <id> --by 张三
python guagua.py report diff  --project <id> --from a --to b

# 体检
python guagua.py check
```

## 附录 B｜一份 role spec 的标准长相（不超过 15 行）

```yaml
extends: analyst
role: r05
title_prefix: 调研
overrides:
  sections:
    price_matrix: { min_tables: 2 }
  fidelity:
    retention_min: 0.95
```

## 附录 C｜阶段闸门检查单（打印贴墙）

- [ ] 契约测试全绿（不许"跳过"）
- [ ] `report_spec.py check` 全绿
- [ ] legacy 名单比上一阶段**减少**
- [ ] 抽 3 份报告人工看：首页四分数在、结论能点回观测
- [ ] R04 抽查：闸门是真跑的，不是补记录的

> 最后一条最重要：**闸门可以慢，但不能假。**
