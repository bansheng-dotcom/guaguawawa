---
name: wawa-company-protocol
description: 一人公司 20 角色协作的权威契约与能力基线。当专家团成员需要确认职责边界、交接端口、任务卡六段、验收门禁、汇报格式、报告深度、咨询级报告标准或角色能力口径时加载。
---

# 蛙蛙呱呱 · 协作协议与能力基线

本 Skill 是专家团的**只读事实来源**，由源项目 `蛙蛙呱呱/agents/` 转化而来。所有角色定义、SOP、输出规范都以此为准；Agent MD 是执行提要，本目录是完整契约。

## 查什么读什么

| 问题 | 文件 |
|---|---|
| 谁负责什么、向谁汇报、输入/输出端口、明确不做、升级路径 | `references/ORG.md`（组织章程，唯一权威） |
| 任务怎样展开、下发、失败怎样移交、多角色怎样编排、验收协议 | `references/PROTOCOL.md`（模式 A/B/C） |
| 汇报写什么、什么文笔、什么排版、三层报告结构 | `references/REPORT-STANDARD.md` |
| 20 角色能力、端口、技术来源（机器可读唯一事实来源） | `references/registry.py`、`references/protocol.py` |
| 每个角色的 7 域能力 / 21 动作 / harness 契约 / 案例 | `references/roles/rXX-*/SKILL.md`、`00-capability-charter.md` |
| 角色配置（花名、职责、语言、缓存策略） | `references/configs/rXX.yaml` |
| 跨域编排实例（营收最大化：R07→R06→R08→R04） | `references/TEAM.md` |
| 全角色商业分析与决策级报告标准（5 阶段生命周期） | `references/docs/SOP_BUSINESS_ANALYSIS_AND_REPORTING.md` |
| 咨询级深度报告（杜邦分解、情景推演、视觉资产审计） | `references/docs/SOP_CONSULTING_REPORT_UPGRADE.md` |
| 报告厚度与深度（六步深度链、共享层三件套） | `references/docs/SOP_REPORT_DEPTH.md` |
| 智能体能力升级方法论（体检→对标→硬化→注入→闭环→沉淀） | `references/docs/SOP_AGENT_META_UPGRADE.md` |
| 自主治理 OS（PII 门禁、工单、Tokenomics、熔断自进化、Cockpit） | `references/docs/SOP_AUTONOMOUS_GOVERNANCE_OS.md` |
| 报告渲染桥接、能力说明书模板、头像风格锚定 | `references/REPORT-BRIDGE-GUIDE.md`、`references_TEMPLATE_00-capability-charter.md`、`avatar-prompts.json` |

## 五条不可突破的铁律
1. **编排器必须瘦**：只加载上下文 → 派发正确角色 → 回收结果 → 更新状态，不写产出、不替执行者判断。
2. **单一主责**：一个文件/一个职能只有一个 owner；「共同负责」＝没人负责。
3. **生成与校验分离**：谁生成谁负责，R04 独立评审，自评不算数，`reviewer == producer` 即 FAIL。
4. **一切带终止条件**：成功标准全命中才收口；杀死标准触发即强制终止转复盘。
5. **不可逆仅创始人签发**：资金、合同、裁员关停、生产库不可逆变更，AI 不代签。

## 上下文隔离与移交
Agent 之间不共享内存，只通过共享工作区与任务卡协作。移交必须携带 `context_summary + artifacts + acceptance + call_chain`；禁止自调用、最大调用深度 2、总移交 > 3 次升级重拆。任何移交、验收、失败都必须留事件，没有事件等于没发生。

## 边界说明
源项目自带的 Python 运行时（`agent.py` / `harness.py` / `core/charts/` 等）**不随本专家包分发**；本包交付的是角色能力、协作契约与 SOP，供 WorkBuddy 团队协作机制直接调用。需要复现原框架的确定性计算时，按 `references/roles/rXX-*/SKILL.md` 的动作与阈值说明重建。


## 全量能力资产（R09 内置）

本节由 R09 蛙稳码执行「能力资产全量内置」后追加；上文全部契约章节（查什么读什么 / 五条铁律 / 上下文隔离与移交 / 边界说明）原文保留。上文「边界说明」中「Python 运行时不随本专家包分发」为**首次转化（仅 76 文件 / 368 KiB）时的旧表述**，本次内置后已失效，以本节为准。

内置基线：源侧能力资产 **1843 文件 / 5.69 MiB**（扩展名 .json 893 / .py 558 / .md 355 / .yaml 27 / 其他 10）；20 个角色目录合计 1731 文件。

### 目录拓扑

| 路径 | 内容 |
|---|---|
| `references/roles/rXX-*/` | 20 个角色全量入口：`agent.py` / `SKILL.md` / `cases` / `configs` / `contracts.py` / `harness.py` / `run_tests.py` / `tests` / `references` / `experience` / `examples`（以及 `skills` / `rules` / `knowledge.py` / `review.py` / `Makefile` / `requirements.txt` 等），保留源端子目录结构 |
| `references/agents/` | 公共运行时：`core` / `shared` / `scripts` / `configs` / `templates` / `tests` / `docs` / `orchestrations` / `styles` / 章程 `.md`（ORG / PROTOCOL / REPORT-STANDARD / TEAM / REPORT-BRIDGE-GUIDE / PROTOCOL_PATCH.diff / references_TEMPLATE）/ `__init__.py` |
| `references/`（根） | 首次转化已有的权威契约（ORG.md / PROTOCOL.md / REPORT-STANDARD.md / TEAM.md / registry.py / protocol.py / avatar-prompts.json / configs / docs），**本次未改动** |

角色 skill 注册路径 `references/roles/rXX/SKILL.md` 保持不变。公共运行时置于 `references/agents/` 而非 `skills/` 下另起一层，避免 26 份源 `SKILL.md` 被重复注册为新 skill。

### 调用示例（推荐：零配置启动器）

```bash
cd PKG/skills/wawa-company-protocol/references
python3 run_role.py r04-watiaoci-reviewer manifest
```

`references/run_role.py` 是 R09 收口内置的零配置启动器：先把 `references/` 与 `references/agents/` 插入 `sys.path`（等价于手工 `PYTHONPATH=<references>;<references/agents>`），再把目标角色目录追加到 `sys.path` 末尾（兼容 `r02` 等依赖「cwd 为角色目录」的脚本），随后 `runpy.run_path(target, run_name="__main__")` 执行 `roles/<rXX>/agent.py`。`runpy` 把 `__file__` 设为真实 `agent.py` 路径，故 `_REPO_ROOT = dirname(dirname(dirname(__file__)))` 仍推得 `references/`，`from agents.shared.chat_cli import ...` 与 `from core import ...` 均可解析。创始人**无需设置 PYTHONPATH**，20 个角色统一走这一个入口。

备选（直接执行 `agent.py`，**需自行设置 PYTHONPATH**）：

```bash
cd SKILL/references
python3 roles/r04-watiaoci-reviewer/agent.py manifest
PYTHONPATH="$PWD;$PWD/agents" python3 roles/r04-watiaoci-reviewer/agent.py manifest   # Windows 用 ; 分隔，POSIX 用 :
```

直接执行时 cwd 必须位于 `references/`：`agents` 包由 `references/agents/__init__.py` 声明，在此层才能解析 `from agents.shared...`。但 20 个角色的运行时引导实现不一致，不设 `PYTHONPATH` 时仅部分角色可直接运行（见「运行时注意」）。

### 排除清单与体积

未内置：`repo_python_xuexi/` / `workspace/` / `avatars/`，以及 `.git` / `__pycache__` / `.pytest_cache` / `.venv` / `node_modules` / `.dsh-acl-recovery` / `.claude`（路径任一段命中即跳过）。原因：**非角色能力资产**。体积按两种口径如实并列，两者都对，勿混用：

| 口径 | repo_python_xuexi | workspace | avatars | 合计 |
|---|---|---|---|---|
| 未过滤全量三块 | 742 文件 / 239.71 MiB | 1336 文件 / 16.65 MiB | 23 文件 / 5.61 MiB | **2101 文件 / 261.97 MiB（274.69 MB，10⁶ 口径）** |
| 已排除 `.git` / 缓存等对象 | 709 文件 / 173.75 MiB | 1336 文件 / 16.65 MiB | 23 文件 / 5.61 MiB | **2068 文件 / 196.01 MiB** |

主理人首次给创始人的 **196.01 MiB** 用的是第二行口径（173.75 + 16.65 + 5.61）。**两者差异来自 `repo_python_xuexi` 内的 `.git` / 缓存对象**：实算命中 `.git` 28 文件 + `.claude` 5 文件 = 33 文件 / 65.95 MiB；`workspace` 与 `avatars` 不含此类对象，两口径数字相同。

`workspace/` 未内置：`r04` 等角色 `agent.py` 的 `Workspace(os.path.join(_ROOT,"workspace"))` 会指向不存在的 `references/roles/workspace`，`manifest` 不写盘故不受影响，但 `run` / `demo` 等写 runlog 的子命令可能失败，需要时按需创建该目录。

### 命名统一

全包统一使用「蛙蛙呱呱」；对 `references/` 全目录做过一次 UTF-8 文本替换：把带「一人公司」后缀的旧全名统一改为「蛙蛙呱呱」，仅处理 .md/.py/.json/.yaml/.yml/.txt/.html/.css/.diff、跳过二进制、保留 UTF-8 BOM；本次实测命中 0 处 / 0 个文件（源侧与专家包既有文件均无该旧全名连写，替换为空操作）。

### 运行时注意（R09 20/20 实测，未修改任何源逻辑）

改用零配置启动器后，对 20 个角色逐个执行 `manifest`（不支持 `manifest` 者 fallback `--help`），两轮均 **20/20 EXIT=0**：

| 角色 | 子命令 | 退出码 |
|---|---|---|
| `r01-waquanju-ceo` | manifest | 0 |
| `r02-wapaibu-coo` | manifest | 0 |
| `r03-washouxian-cfo` | manifest | 0 |
| `r04-watiaoci-reviewer` | manifest | 0 |
| `r05-washenyuan-research` | manifest | 0 |
| `r06-wadeqing-analyst` | manifest | 0 |
| `r07-wademing-pm` | manifest | 0 |
| `r08-wajiancheng-mvp` | manifest | 0 |
| `r09-wawenma-engineer` | manifest | 0 |
| `r10-wachengmei-design` | manifest | 0 |
| `r11-wadianti-copy` | manifest | 0 |
| `r12-wayingliu-growth` | manifest | 0 |
| `r13-wakecheng-csm` | manifest | 0 |
| `r14-wajiaoyi-commerce` | manifest | 0 |
| `r15-wagongying-erp` | manifest | 0 |
| `r16-warenshi-hr` | manifest | 0 |
| `r17-wazhiwang-automation` | manifest | 0 |
| `r18-washucang-dataeng` | manifest | 0 |
| `r19-wazhimo-ml` | manifest | 0 |
| `r20-washouzhi-sre` | manifest | 0 |

两轮：A 清空 `PYTHONPATH`（严格零配置）、B 保留系统自带 `PYTHONPATH`，结果一致。20 个角色 stdout 均为 1 行能力清单 JSON（`r01`~`r03`、`r05`~`r20` 带 `__AGENT_RESULT__` 前缀，`r04` 为裸 JSON），**无角色需要 `--help` 兜底**。

首轮实测曾为 19/20：`r02-wapaibu-coo` 报 `ModuleNotFoundError: No module named 'skills'`。根因是该脚本 `from skills import SKILLS` 依赖 cwd 为角色目录（只把 `references/roles` 插入 `sys.path`、漏了自身目录），源项目靠 `cd r02 && python agent.py` 的 `sys.path[0]=''` 兜底；启动器统一 cwd=`references` 时失效。修补方式由**启动器**把目标角色目录追加到 `sys.path` 末尾，未改任何源 `agent.py`。此前 3 角色抽样中 `r01` 的 `core`、`r06` 的 `agents.shared` 失败，同样由启动器的路径引导解决。

`compileall -q references` 退出码 0；561 个 `.py`（内置 558 + 首次转化既有 2 + 新增 `run_role.py`）零编译失败，仅 `roles/r06-wadeqing-analyst/scripts/run_taobao_attribution.py:547` 有 1 条 `SyntaxWarning: invalid escape sequence '\w'`（警告，非语法错误）。
