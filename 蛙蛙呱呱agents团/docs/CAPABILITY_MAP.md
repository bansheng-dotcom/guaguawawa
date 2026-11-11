# 能力映射目录（22 项）

> 由 `shared/capabilities/catalog.json` 生成；能力卡在 `rXX-*/references/capabilities/<id>/README.md`。
> 形态：**代码** = 有确定性命令与门禁；**规范** = 按能力卡规则执行，产物走角色 harness 验收。

## 一、总览

- 能力总数：**22**（代码 5 / 规范 17）
- 覆盖角色：12 个（R01/R02/R05/R06/R07/R08/R09/R10/R11/R12/R14/R15）

## 二、角色 → 能力映射

| 角色 | 能力 id | 形态 | 命令 / 用法 | 能力卡 |
|---|---|---|---|---|
| r01 蛙全局 CEO | `strategic-growth-compass` | 规范 | 按卡执行 | `r01-waquanju-ceo/references/capabilities/strategic-growth-compass/README.md` |
| r02 蛙排布 COO | `business-ops-analysis` | 规范 | 按卡执行 | `r02-wapaibu-coo/references/capabilities/business-ops-analysis/README.md` |
| r05 蛙深远 研究 | `industry-panorama-research` | 规范 | 按卡执行 | `r05-washenyuan-research/references/capabilities/industry-panorama-research/README.md` |
| r05 蛙深远 研究 | `market-intelligence-radar` | 规范 | 按卡执行 | `r05-washenyuan-research/references/capabilities/market-intelligence-radar/README.md` |
| r05 蛙深远 研究 | `tashan-research-skills` | 规范 | 按卡执行 | `r05-washenyuan-research/references/capabilities/tashan-research-skills/README.md` |
| r06 蛙得清 数据 | `build-web-data-visualization` | 规范 | 按卡执行 | `r06-wadeqing-analyst/references/capabilities/build-web-data-visualization/README.md` |
| r06 蛙得清 数据 | `data-processing` | 规范 | 按卡执行 | `r06-wadeqing-analyst/references/capabilities/data-processing/README.md` |
| r07 蛙得明 产品 | `user-research-toolkit` | 规范 | 按卡执行 | `r07-wademing-pm/references/capabilities/user-research-toolkit/README.md` |
| r08 蛙建成 MVP | `ppt-generator` | 代码 | `deck plan / html` | `r08-wajiancheng-mvp/references/capabilities/ppt-generator/README.md` |
| r08 蛙建成 MVP | `rapid-prototype-craft` | 规范 | 按卡执行 | `r08-wajiancheng-mvp/references/capabilities/rapid-prototype-craft/README.md` |
| r09 蛙稳码 工程 | `frontend-design` | 规范 | 按卡执行 | `r09-wawenma-engineer/references/capabilities/frontend-design/README.md` |
| r09 蛙稳码 工程 | `web-app-development` | 规范 | 按卡执行 | `r09-wawenma-engineer/references/capabilities/web-app-development/README.md` |
| r10 蛙成美 设计 | `brand-guardian` | 代码 | `brandcheck check` | `r10-wachengmei-design/references/capabilities/brand-guardian/README.md` |
| r10 蛙成美 设计 | `design-system` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/design-system/README.md` |
| r10 蛙成美 设计 | `ecommerce-designer` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/ecommerce-designer/README.md` |
| r10 蛙成美 设计 | `whiteboard` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/whiteboard/README.md` |
| r11 蛙点题 内容 | `rednote-post` | 规范 | 按卡执行 | `r11-wadianti-copy/references/capabilities/rednote-post/README.md` |
| r11 蛙点题 内容 | `xhs-content-skills` | 代码 | `xhs note / score / compliance` | `r11-wadianti-copy/references/capabilities/xhs-content-skills/README.md` |
| r12 蛙引流 增长 | `marketing-toolkit` | 规范 | 按卡执行 | `r12-wayingliu-growth/references/capabilities/marketing-toolkit/README.md` |
| r14 蛙交易 交易 | `omnichannel-commerce-assistant` | 规范 | 按卡执行 | `r14-wajiaoyi-commerce/references/capabilities/omnichannel-commerce-assistant/README.md` |
| r14 蛙交易 交易 | `smart-product-selector` | 代码 | `selection score / profit` | `r14-wajiaoyi-commerce/references/capabilities/smart-product-selector/README.md` |
| r15 蛙供应 供应链 | `analyze-procurement` | 代码 | `tco compare / lifecycle` | `r15-wagongying-erp/references/capabilities/analyze-procurement/README.md` |

## 三、代码技能明细

| 技能 | 角色 | 动作 | 核心门禁 | 实现文件 |
|---|---|---|---|---|
| `xhs` | R11 | note / score / compliance | 标题 ≤20、正文 550–650、8 项快检 ≥7、CTA 黑名单、绝对化/收入/联系方式 | `r11-wadianti-copy/skills/s11_xhs.py` |
| `selection` | R14 | score / profit | 五维加权（120% 归一化）、SP-09 假设卡、毛利 30%/15% | `r14-wajiaoyi-commerce/skills/s09_selection.py` |
| `tco` | R15 | compare / lifecycle | landed cost 九项、可用数量、资金占用、MOQ/交期/不良率、TCO 三类成本 | `r15-wagongying-erp/skills/s08_tco.py` |
| `deck` | R08 | plan / html | 6–30 页、一页一观点、标题 ≤20 不重复、封面/行动页、单文件离线 | `r08-wajiancheng-mvp/skills/s08_deck.py` |
| `brandcheck` | R10 | check | 颜色/字体对 DESIGN.md 令牌、对比度 ≥4.5、主色 ≤8 | `r10-wachengmei-design/skills/s14_brandcheck.py` |

回归：`tests/test_capability_fusions.py`（10 例，跑真实 CLI）、`tests/test_capabilities.py`（目录完整性/无痕迹）。

## 四、还没做好的（按优先级）

### P0 · 能力缺口

| 项 | 现状 | 影响 | 建议 |
|---|---|---|---|
| 4 项 MCP 能力（美图图像/视频、火山数据集、AgentEarth、Taro 小程序） | **未内化，已整体移除**；无替代实现 | 图像编辑、外部数据检索、小程序构建这三类任务目前只能走 R10/R09 的手工流程 | 若确需，评估自建轻量版（如 R10 本地抠图/改图、R05 公开数据检索），不要接回外部客户端 |
| 5 个未纳入插件（deep-research、html-report、lark、office、prd-authoring） | 只做了说明，未建能力卡 | 与 R05/R08/R02/R07 有重叠，未形成规范 | 先各写一张能力卡并入目录；lark 如需同步再评估 |
| 5 个代码技能未接意图路由 | 只接了契约/门禁/直接命令，`run --task` 关键词路由未覆盖 | 任务卡自动路由可能落到 fallback | 在 5 个角色 `_INTENT_ROUTES` 各加 2–3 条关键词 |
| `aihive generate` 真实链路未验证 | 无 API Key，只验证了 blocked/preview 分支 | 首次真实出图可能有参数/价格差异 | 有 Key 后跑一次 `--no-download` 最简任务 |

### P1 · 深度缺口

| 项 | 现状 |
|---|---|
| 17 项规范卡 | 只沉淀了定位 + 4 条规则；上游的多文件流程、模板、脚本未逐条吸收（如研究 20 技能、可视化 18 技能） |
| 31 套品牌设计基线 / H3 规范 / AI Hive 客户端 | 资产保留并在 `THIRD_PARTY_NOTICES.md` 标注来源，但**不是重写** |
| 端到端 | 新技能只有 CLI 级测试，没有 `guagua.py plan/dispatch` 的跨角色用例 |

### P2 · 工程卫生

| 项 | 现状 |
|---|---|
| 工作区运行态 | `workspace/**` 仍有未跟踪文件，未加 `.gitignore` 规则 |
| 归档体积 | 每轮重打两个 zip 进 git，仓库持续变大 |
| 能力卡版本 | 目录无 version 字段，规则变更无版本可追溯 |

## 五、维护方式

1. 新增能力：在 `shared/capabilities/catalog.json` 加条目 → 在归属角色 `references/capabilities/<id>/README.md` 写卡；
2. 升级为代码：写 `skills/sXX_<name>.py`（NAME/DESC/add_parser/run）→ 注册 `skills/__init__.py` → 加契约 → 加测试；
3. 提交前跑：`python -m pytest tests -q` 与 `python guagua.py check`，并确保 `tests/test_capabilities.py` 的零痕迹用例通过。
