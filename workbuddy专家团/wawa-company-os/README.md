# 蛙蛙呱呱（wawa-company-os）

由 `蛙蛙呱呱.zip`（一人公司 2.0 · 20 角色 Agent 框架）转化而来的 WorkBuddy **Team 型专家团**。1 位主理人 + 19 位职能角色，覆盖决策治理、战略数据、产品技术、市场客户、交易组织、自动化可靠性六大能力层。

## 团队口令与展示描述（创始人原文）

> 20 只蜡笔小蛙蛙排排坐，把小点子孵上线，撑起一整家呱呱公司，交作业先请挑刺蛙盖小红章。
>
> 呱一声全编排排坐
> 把小点子孵上线
> 呱呱呱呱呱呱呱呱

- **花名 / 展示名**：蛙蛙呱呱（Wawa Guagua），`displayName` 与 `profession` 保持一致（Team 型规范）。
- **能力介绍（创始人最终指定）**：`displayDescription.zh` 已改为三行团队口令「呱一声全编排排坐／把小点子孵上线／呱呱呱呱呱呱呱呱」，JSON 中以 `\n` 换行；上方第一段 44 字作为团队介绍原文保留，不再作面板展示。三行合计 25 字符（8+7+8 加 2 个换行），低于「中文 40–50 字」规范，`validate_expert.py` L157–159 会给 1 条 warning（warning 不阻断校验与注册）；该字数口径由创始人指定豁免。
- **擅长领域（呱设）**：`tags` 仍为固定 3 个，已按创始人「OOC 呱设」把业务化标签换成可爱短描述——「呱一声全编排呱 / 小点子孵上线呱 / 挑刺蛙盖红章呱」，分别对应跨域编排、想法孵化上线、独立评审盖章三项能力；英文同节拍带 `ribbit`。原标签（一人公司经营 / 跨域任务编排 / 独立评审门禁）作为历史口径记录于此。
- **内部唯一标识**：`wawa-company-os`（`name` / `agentName` / 目录名 / Agent MD 文件名）不可改，改标识需重建专家包。
- **交作业规矩**：任何交付在收口前须经 R04 蛙挑刺独立复核并盖「小红章」，pass/fail 由主理人原文透传。

## 基本信息

- **类型**：Team（`expertType: "team"`）
- **分类**：12-IndustryConsultant（主输出为跨职能经营决策，服务创始人）
- **主理人**：蛙全局 / 首席经营编排官（`wawa-company-os-team-lead`）
- **独立评审**：R04 蛙挑刺（`wawa-independent-reviewer`），唯一有资格签 pass/fail 的角色

## 目录结构

```
.codebuddy-plugin/plugin.json   展示字段 / 20 成员 / teamInfo
settings.json                   主理人入口
agents/                         1 主理人 MD + 19 角色 MD（含能力、端口、SOP、输出规范、SendMessage 回传）
skills/wawa-company-protocol/   协作协议 Skill
  references/                   ORG / PROTOCOL / REPORT-STANDARD / TEAM / 5 份 SOP / 20 份角色 SKILL.md / 20 份能力说明书 / 20 份 yaml 配置 / registry.py / protocol.py
avatars/                        21 张统一画风头像（团队 + 主理人 + 19 角色）
```

## 使用示例

- 我要把一个小想法做成能收款的生意。请按 GSD 五相环拆解，给我 30 天任务卡、依赖波次和验收标准，标出需要我签字的事项。
- 拿这份经营数据做复盘：请数据分析、财务合规、增长、客户成功各出结论，交叉验证后由独立评审给 pass/fail，不许和稀泥。
- 上线前做全角色体检：PRD、原型、工程门禁、合规红线、备份恢复逐项打勾，给整改清单和放行条件。

## 协作机制
主理人按 GSD 五相环（Discuss → Plan → Execute → Verify → Ship）建立团队、下发任务卡六段、按依赖波次调度成员；成员通过 SendMessage 回传完整产出；R04 独立评审的裁决由主理人**原文透传**给用户；不可逆决策升级创始人，不代签。

## 头像
头像直接复用资料包自带的 21 张统一画风（蜡笔方头蛙贴纸风，512×512 PNG，单张 ≤500KB）图片，已在 `avatars/` 按 Agent ID 重命名。可手动替换：PNG/JPG、512×512、≤500KB。原始生成 prompt 见 `skills/wawa-company-protocol/references/avatar-prompts.json`。

## 安装与注册
专家包已放在专家目录并注册到 `marketplace.json`：

```
C:\Users\18238\.workbuddy\plugins\marketplaces\my-experts\plugins\wawa-company-os
```

重新校验 / 注册 / 打包：

```bash
python3 scripts/validate_expert.py <expert-dir>
python3 scripts/register_expert.py <expert-dir>
python3 scripts/package_expert.py <expert-dir> [output-dir]
```

## 与已有专家团的关系
本包使用独立标识 `wawa-company-os`，成员 Agent ID 统一加 `wawa-` 前缀，与专家目录中已有的 `one-person-company-20`（旧版一人公司 20 角色包）**互不冲突、互不覆盖**。两者可并存；如需下线旧包，请在【专家中心 - 我的专家】自行处理。

## 资料来源与边界
来源：`D:/卜算/蛙蛙呱呱.zip` → `agents/`（2026-11-08 版本）。源项目的 Python 运行时未随包分发；本包完整保留角色能力、组织章程、协同协议、汇报标准与全部 SOP，见 `skills/wawa-company-protocol/references/`。
