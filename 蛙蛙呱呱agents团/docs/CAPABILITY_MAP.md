# 能力映射目录

> 由 `shared/capabilities/catalog.json` 生成（26 项能力）。
> 形态：**代码** = 有确定性命令与门禁；**规范** = 按能力卡规则执行，产物走角色 harness 验收。

## 一、总览

- 能力总数：**26**（代码 9 / 规范 17）
- 代码技能：`xhs` `selection` `tco` `deck` `brandcheck` `prdguard` `htmlreport` `miniapp` `imgops`
- 覆盖角色：12 个（R01/R02/R05/R06/R07/R08/R09/R10/R11/R12/R14/R15）

## 二、角色 → 能力映射

| 角色 | 能力 id | 形态 | 命令 / 用法 | 能力卡 |
|---|---|---|---|---|
| r01 | `strategic-growth-compass` | 规范 | 按卡执行 | `r01-waquanju-ceo/references/capabilities/strategic-growth-compass/README.md` |
| r02 | `business-ops-analysis` | 规范 | 按卡执行 | `r02-wapaibu-coo/references/capabilities/business-ops-analysis/README.md` |
| r05 | `industry-panorama-research` | 规范 | 按卡执行 | `r05-washenyuan-research/references/capabilities/industry-panorama-research/README.md` |
| r05 | `market-intelligence-radar` | 规范 | 按卡执行 | `r05-washenyuan-research/references/capabilities/market-intelligence-radar/README.md` |
| r05 | `tashan-research-skills` | 规范 | 按卡执行 | `r05-washenyuan-research/references/capabilities/tashan-research-skills/README.md` |
| r06 | `build-web-data-visualization` | 规范 | 按卡执行 | `r06-wadeqing-analyst/references/capabilities/build-web-data-visualization/README.md` |
| r06 | `data-processing` | 规范 | 按卡执行 | `r06-wadeqing-analyst/references/capabilities/data-processing/README.md` |
| r07 | `prd-authoring` | 代码 | `prdguard check / render` | `r07-wademing-pm/references/capabilities/prd-authoring/README.md` |
| r07 | `user-research-toolkit` | 规范 | 按卡执行 | `r07-wademing-pm/references/capabilities/user-research-toolkit/README.md` |
| r08 | `html-report-presentation` | 代码 | `htmlreport plan / html` | `r08-wajiancheng-mvp/references/capabilities/html-report-presentation/README.md` |
| r08 | `miniapp-builder` | 代码 | `miniapp plan / scaffold` | `r08-wajiancheng-mvp/references/capabilities/miniapp-builder/README.md` |
| r08 | `ppt-generator` | 代码 | `deck plan / html` | `r08-wajiancheng-mvp/references/capabilities/ppt-generator/README.md` |
| r08 | `rapid-prototype-craft` | 规范 | 按卡执行 | `r08-wajiancheng-mvp/references/capabilities/rapid-prototype-craft/README.md` |
| r09 | `frontend-design` | 规范 | 按卡执行 | `r09-wawenma-engineer/references/capabilities/frontend-design/README.md` |
| r09 | `web-app-development` | 规范 | 按卡执行 | `r09-wawenma-engineer/references/capabilities/web-app-development/README.md` |
| r10 | `brand-guardian` | 代码 | `brandcheck check` | `r10-wachengmei-design/references/capabilities/brand-guardian/README.md` |
| r10 | `design-system` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/design-system/README.md` |
| r10 | `ecommerce-designer` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/ecommerce-designer/README.md` |
| r10 | `image-ops` | 代码 | `imgops info / resize / crop / compress / pad / watermark` | `r10-wachengmei-design/references/capabilities/image-ops/README.md` |
| r10 | `whiteboard` | 规范 | 按卡执行 | `r10-wachengmei-design/references/capabilities/whiteboard/README.md` |
| r11 | `rednote-post` | 规范 | 按卡执行 | `r11-wadianti-copy/references/capabilities/rednote-post/README.md` |
| r11 | `xhs-content-skills` | 代码 | `xhs note / score / compliance` | `r11-wadianti-copy/references/capabilities/xhs-content-skills/README.md` |
| r12 | `marketing-toolkit` | 规范 | 按卡执行 | `r12-wayingliu-growth/references/capabilities/marketing-toolkit/README.md` |
| r14 | `omnichannel-commerce-assistant` | 规范 | 按卡执行 | `r14-wajiaoyi-commerce/references/capabilities/omnichannel-commerce-assistant/README.md` |
| r14 | `smart-product-selector` | 代码 | `selection score / profit` | `r14-wajiaoyi-commerce/references/capabilities/smart-product-selector/README.md` |
| r15 | `analyze-procurement` | 代码 | `tco compare / lifecycle` | `r15-wagongying-erp/references/capabilities/analyze-procurement/README.md` |

## 三、代码技能明细

| 技能 | 角色 | 动作 | 核心门禁 | 实现文件 |
|---|---|---|---|---|
| `xhs` | R11 | note/score/compliance | 标题 ≤20、正文 550–650、8 项快检、CTA 黑名单、合规扫描 | `r11-wadianti-copy/skills/s11_xhs.py` |
| `selection` | R14 | score/profit | 五维加权（120% 归一化）、SP-09 假设卡、毛利红线 | `r14-wajiaoyi-commerce/skills/s09_selection.py` |
| `tco` | R15 | compare/lifecycle | landed cost 九项、可用数量、资金占用、TCO 三类成本 | `r15-wagongying-erp/skills/s08_tco.py` |
| `deck` | R08 | plan/html | 6–30 页、一页一观点、标题不重复、封面/行动页、单文件 | `r08-wajiancheng-mvp/skills/s08_deck.py` |
| `brandcheck` | R10 | check | 颜色/字体对 DESIGN.md、对比度 ≥4.5、主色 ≤8 | `r10-wachengmei-design/skills/s14_brandcheck.py` |
| `prdguard` | R07 | check/render | 产品契约四要素、P0 四段、非目标、边界、假设、来源可追溯 | `r07-wademing-pm/skills/s09_prdguard.py` |
| `htmlreport` | R08 | plan/html | 章节 ≥3、论点 ≥3、来源 ≥3；单文件渲染 + 打印样式 | `r08-wajiancheng-mvp/skills/s09_htmlreport.py` |
| `miniapp` | R08 | plan/scaffold | 2–20 页、路径/tabBar 校验；Taro 工程骨架 | `r08-wajiancheng-mvp/skills/s10_miniapp.py` |
| `imgops` | R10 | info/resize/crop/compress/pad/watermark | 不覆盖源文件、格式白名单、缺 Pillow 即 blocked | `r10-wachengmei-design/skills/s15_imgops.py` |

## 四、意图路由（已补齐）

| 角色 | 新增关键词 → 技能/动作 |
|---|---|
| R07 | prd 检查 → `prdguard check` |
| R08 | 幻灯片/PPT/deck → `deck plan`；HTML 报告 → `htmlreport plan`；小程序/Taro → `miniapp plan` |
| R10 | 品牌一致性/VI 检查 → `brandcheck check`；缩放/裁剪/水印 → `imgops` |
| R11 | 发布前检查/笔记评分 → `xhs score` |
| R14 | 选品/利润测算/VO — `selection score` |
| R15 | TCO/采购成本对比/报价对比 → `tco compare` |

## 五、还没做好的

### P0

| 项 | 现状 |
|---|---|
| `volcengine-pro-dataset`、`agent-earth`（外部数据检索类） | 未替代；离线无法自建数据服务 |
| `lark`、`office-plugin`、`deep-research-assistant` | 未纳入能力库（office/深度研究可与现有 R08/R05 能力合并） |
| `aihive generate` 真实链路 | 无 Key，仅验证 blocked/preview |

### P1

| 项 | 现状 |
|---|---|
| 17 张规范卡 | 只沉淀定位 + 4 条规则，上游多文件流程/模板未逐条吸收 |
| 31 套设计基线 / H3 规范 / AI Hive 客户端 | 资产保留并在 `THIRD_PARTY_NOTICES.md` 标注，非重写 |
| 端到端 | 新技能只有 CLI 级测试，无 `plan → dispatch` 跨角色用例 |

### P2

| 项 | 现状 |
|---|---|
| 工作区运行态 | `workspace/**` 未加 `.gitignore` 规则 |
| 归档体积 | 每轮重打 zip 进 git |
| 能力版本 | catalog 无 version 字段 |

## 六、维护

1. 新能力：`catalog.json` 加条目 + 写 `references/capabilities/<id>/README.md`；
2. 升级为代码：`skills/sXX_<name>.py` → 注册 `__init__` → 加契约 → 加路由 → 加测试；
3. 提交前：`pytest tests -q` + `python guagua.py check`。
