---
name: web-app-development
description: Web 应用构建技能包。把「做个能用的 Web 应用」拆成三段可校验的交付：技术规格先把模块边界与输入输出契约定死，端到端功能切片保证一条链路真能跑通，认证与受保护路由保证越权进不去，交付前材料齐备。当需要建 Web 应用、定模块契约、做端到端切片、设计鉴权路由、或判断一个应用能不能交付时使用。不负责界面视觉规范（见 frontend-design）、不替代 TDD 与评审流程（见 tdd-review-pair）、不做运维监控。
license: MIT
compatibility: 通用。门禁在角色根目录 agent.py（spec spec / fullstack feature / fullstack auth）与 harness.py（materials / testreport），Python 3.10+、零第三方依赖；无 Python 环境时按 §8 转人工核对，此时不得标记「可交付」。
metadata:
  owner: r09
  version: "2.0.0"
  kind: skill
  triggers: "Web应用,技术规格,模块契约,端到端切片,鉴权,受保护路由,全栈"
  verify: python agent.py spec spec --input <技术规格.json>
  entry: "python agent.py fullstack feature"
  consumers: "r07,r08,r10"
  supersedes: "README.md"
---

# Web 应用构建（Web App Development）

> 一句话定位：**这个技能存在的意义，是防止「每个模块单独看都对，连起来跑不通」**。
> Web 应用最贵的失败不是某个函数写错，而是**契约不清**：
> 模块的输入输出没定死、端到端链路没人真跑、鉴权只在前端藏按钮。
> 这三件事都不会让编译报错，只会让上线后「点了没反应」「换个账号就能看别人数据」。

## §1 何时用 / 何时不用

**该用（用户真实会这么说）**
- 「做个 Web 应用」「这套模块怎么拆」
- 「端到端能不能跑通」「这块要不要登录」
- 「这个能不能交付了」

**不该用，转给谁**

| 用户其实想要 | 转给 | 理由 |
|---|---|---|
| 界面好不好看、间距字号 | 本角色的 `frontend-design` | 那是视觉与可用性规范 |
| 测试报告与代码评审流程 | 本角色的 `tdd-review-pair` | 那是验证流程 |
| 快速原型、先看个样子 | `r08` 的 `rapid-prototype` | 原型不追工程契约 |
| 监控、告警、备份 | `r20` 值守 | 那是运行期 |

**最小可开工输入**：**一句话说清"谁用、做什么、存什么"**。存什么决定模块边界。

---

## §2 前置输入与最省追问

| 输入 | 是否必需 | 缺失时怎么办 |
|---|---|---|
| 核心用户与主流程 | 必需 | 无流程无法切模块，必须问 |
| 数据实体（存什么） | 必需 | 无实体无法定契约 |
| 模块划分或技术栈约束 | 建议 | 缺则按"按实体分层"默认切分 |
| 鉴权要求（谁能看什么） | 必需（有用户系统时） | 缺则按"默认拒绝"处理并标注 |
| 部署环境 | 建议 | 缺则给环境无关的规格 |

**追问纪律**：最多一轮，只问**存什么、谁能看**。技术栈不追问，按现有约定。

---

## §3 执行流水线（Workflow）

### Step 1 · 技术规格：把模块契约定死
```bash
python agent.py spec spec --input <技术规格.json>
```
每个模块必须写清 **`inputs` 与 `outputs`**：

```json
{"modules": [
  {"name": "auth",    "inputs": ["credential"], "outputs": ["token"]},
  {"name": "billing", "inputs": ["token"],      "outputs": ["invoice"]}
]}
```

**判据**：每个模块的 outputs 必须能被下游的某个 inputs 消费；出现"孤儿输出"或"无源输入"即契约断裂。
门禁实测：缺 `inputs`/`outputs` 或结构不合法即 FAIL。

- **产出**：模块契约表
- **过关条件**：`agent.py spec spec` 退出码 0

### Step 2 · 端到端功能切片（一条链路真跑通）
```bash
python agent.py fullstack feature --input <功能切片.json>
```
一个切片必须覆盖：入口 → 业务逻辑 → 数据落库 → 返回可见结果。
**只做前端或只做后端都不算切片。**

门禁实测：`fullstack_feature_dirty` 会因切片字段缺失或链路不闭合而 FAIL。

- **产出**：功能切片定义 + 跑通记录
- **过关条件**：`agent.py fullstack feature` 退出码 0

### Step 3 · 认证与受保护路由（默认拒绝）
```bash
python agent.py fullstack auth --input <鉴权配置.json>
```
三条硬规则：

| 规则 | 说明 |
|---|---|
| **服务端校验** | 前端隐藏按钮不算鉴权；每个受保护接口必须服务端验 |
| **默认拒绝** | 未显式放行的路径一律拒绝，不是"默认放行再补" |
| **越权测试** | 用低权限账号访问高权限接口，必须被拒 |

门禁实测：`fullstack_auth_dirty` 因放行规则不完整或缺少服务端校验而 FAIL。

- **产出**：路由权限表 + 越权验证记录
- **过关条件**：`agent.py fullstack auth` 退出码 0

### Step 4 · 交付材料与测试报告
```bash
python harness.py materials  --input <材料清单.json>
python harness.py testreport --input <测试报告.json>
```
材料必须含：改动清单、复现步骤、验证命令、影响面。
测试报告必须含通过/失败/跳过计数与跳过原因（跳过不说明＝隐藏风险）。

- **产出**：材料清单 + 测试报告
- **过关条件**：两道均退出码 0

### Step 5 · 架构回看（上线前最后一遍）
```bash
python agent.py spec arch --input <架构.json>
```
检查依赖方向是否单向、有没有循环依赖、公共模块是否被下层反向依赖。

---

## §4 交付物清单

| # | 交付物 | 载体 | 骨架出处 |
|---|---|---|---|
| 1 | 模块契约表（每模块 inputs/outputs） | `.json` | `examples/spec_spec.json` |
| 2 | 端到端功能切片 + 跑通记录 | `.json` | `examples/fullstack_feature.json` |
| 3 | 路由权限表 + 越权验证记录 | `.json` | `examples/fullstack_auth.json` |
| 4 | 架构依赖图与回看结论 | `.json` | `examples/spec_arch.json` |
| 5 | 交付材料 + 测试报告 | `.json` | `examples/materials_good.json` / `testreport_good.json` |

- 命名：`webapp_<应用短码>_<YYYYMMDD>/`
- **五件齐全才可交付**；只有代码没有契约表不算。

---

## §5 质量门（一票否决，不过不给交付）

1. **每个模块都有 `inputs` 与 `outputs`**，无孤儿输出/无源输入（`spec spec`）；
2. **端到端切片链路闭合**：入口→逻辑→落库→可见结果（`fullstack feature`）；
3. **每个受保护接口都服务端校验**，不是前端隐藏（`fullstack auth`）；
4. **默认拒绝**：未显式放行的路径一律拒；
5. **越权测试通过**：低权限访问高权限接口被拒；
6. **测试报告含跳过原因**（`testreport`），材料含影响面（`materials`）；
7. **无循环依赖、无下层反向依赖**（`spec arch`）。

> 验收命令：`python agent.py spec spec|fullstack feature|fullstack auth|spec arch --input <json>`
> 命中任一项不过 → 回 §3 对应 Step 重做，**不允许把鉴权改成前端判断让门禁变绿**。

---

## §6 交付前自检清单

- [ ] 我能画出模块契约表，且每个 outputs 都有下游消费
- [ ] 没有"孤儿输出"（产出了但没人用）或"无源输入"（要了但没人给）
- [ ] 端到端切片我真跑过一遍，从入口到数据落库
- [ ] 每个受保护接口都在服务端验权，不是靠前端藏按钮
- [ ] 未显式放行的路径默认拒绝
- [ ] 我用低权限账号试过访问高权限接口，被拒绝了
- [ ] 测试报告有通过/失败/跳过计数，跳过项都有原因
- [ ] 交付材料写了改动清单、复现步骤、影响面
- [ ] 架构依赖单向，没有循环
- [ ] 四道门禁均退出码 0

---

## §7 易犯错误对照表

| # | 易犯错法 | 正确做法 |
|---|---|---|
| EX-01 | 只写模块名，不写 inputs/outputs | 契约必须成对，否则下游无法对接 |
| EX-02 | 出现孤儿输出（产出了没人用） | 要么删掉，要么补消费方 |
| EX-03 | 出现无源输入（要了没人给） | 要么补生产方，要么删掉该输入 |
| EX-04 | 只做前端或只做后端就叫"切片" | 切片必须链路闭合：入口→逻辑→落库→可见 |
| EX-05 | 前端隐藏按钮当鉴权 | 服务端必须验；前端隐藏只是体验 |
| EX-06 | 默认放行再补规则 | **默认拒绝**，显式放行 |
| EX-07 | 没做越权测试 | 低权限账号试高权限接口，必须被拒 |
| EX-08 | 测试跳过不说明原因 | 每条跳过都要原因（环境/废弃/待特性） |
| EX-09 | 材料不写影响面 | 下游不知道哪些模块会受影响 |
| EX-10 | 循环依赖 | 依赖必须单向；循环拆出公共模块 |
| EX-11 | 下层反向依赖上层 | 公共模块不许反向依赖业务层 |
| EX-12 | 只跑单测不做端到端 | 单测过 ≠ 链路通；必须有端到端验证 |

---

## §8 降级与边界

| 触发情况 | 处置 |
|---|---|
| `agent.py` 门禁跑不了 | 按 §6 人工核对，标注「未跑门禁」；**不得标记"可交付"** |
| 无鉴权需求（纯静态站） | 标注"无用户系统"，跳过 §3 Step 3，但 §4 交付物减项要写明 |
| 数据库不可用 | 用本地文件/SQLite 跑通切片，标注"生产库未接" |
| 只给需求没给数据实体 | 先让用户确认"存什么"，不猜 |
| 多前端（Web + 小程序） | 契约表共用一份，端到端切片每个端各跑一遍 |
| 上线与回滚 | 转 ops 域 / `r20`，本包只到"可交付" |
| 视觉规范 | 转本角色的 `frontend-design` |

**明确不做**
- 不做界面视觉规范（归 `frontend-design`）；
- 不做 TDD 与代码评审流程（归 `tdd-review-pair`）；
- 不做监控、告警、备份（归 `r20`）；
- 不承诺上线时间（归 `r02`）。

---

## §9 资源地图（按需读取，禁止全量加载）

| 什么时候需要 | 读哪个文件 |
|---|---|
| 契约设计、端到端切法、鉴权三规则、依赖方向 | `references/web-app-delivery.md` |
| 工程细节与子命令 | `../../../references/engineering-notes.md` |
| 门禁是否还有效（正/反例 fixture） | `scripts/gate_selftest.py --self-test` |
| 负向用例 | `tests/misuse.md` |
| 技术规格骨架 | `../../../examples/spec_spec.json` |
| 端到端切片骨架 | `../../../examples/fullstack_feature.json` |
| 鉴权配置骨架 | `../../../examples/fullstack_auth.json` |
| 架构骨架 | `../../../examples/spec_arch.json` |

**脚本清单**

| 脚本 | 用途 | 入口 |
|---|---|---|
| `scripts/gate_selftest.py` | 断言三道 `agent.py` 门禁对正/反例的退出码 | `--self-test` / `--verbose` |

---

## §10 变更记录

- **v2.0.0（2026-11-11）**：按 `docs/SKILL-LAYER-SPEC.md` v1.0 从能力卡升级为十节技能包。
  新增：§1 转交表、§2 最小可开工输入、§3 五步流水线（契约→端到端→鉴权→材料→架构回看）、
  §7 十二条错误表、§8 七种降级、`references/web-app-delivery.md`、
  `scripts/gate_selftest.py`（3 正例 + 3 反例）、`tests/misuse.md`。
  门禁复用 `agent.py spec/fullstack` 与 `harness.py materials/testreport`，未新增判定实现。
- v1.0（此前）：能力卡形态（`README.md`，约 0.86 KB，无 frontmatter/触发语/门禁声明）。
