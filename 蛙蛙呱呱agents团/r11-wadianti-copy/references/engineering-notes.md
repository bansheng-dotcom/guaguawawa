---
name: r11-wadianti-copy
description: 内容主笔。本地支持文本格式、字数与平台长度检查；真实翻译服务、SEO平台数据、发布排期和内容投放未接入，属于 simulated 或 blocked。
---

---

## 能力域 → 技能子命令

| 能力域 | 技能 | 子命令 | 确定性口径 |
|---|---|---|---|
| 小红书发布包 | `xhs` | `note` / `score` / `compliance` | 标题 ≤20 字、前 10 字含核心词、正文 550–650 字、标签 3–8 且埋词闭环；8 项质量快检 ≥7 项通过；CTA 黑名单与四类诱导互动零命中；绝对化用语/收入表述/联系方式硬拦截；AI 内容须带 `#AI辅助创作` |

共 **9 技能 / 23 动作**（含 xhs 3 动作）。

## 能力库（自有）

本角色自有能力（规范或可执行技能），能力卡在 `references/capabilities/<id>/README.md`：

- `rednote-post` · 小红书笔记结构（规范；消费方：r10, r12）
- `xhs-content-skills` · 小红书发布包（代码：`xhs note / score / compliance`；消费方：r10, r12, r03）

查看：`python guagua.py capabilities --role r11`

## 能力库（自有）

本角色自有能力（规范或可执行技能），能力卡在 `references/capabilities/<id>/README.md`：

- `rednote-post` · 小红书笔记结构（规范；消费方：r10, r12）
- `xhs-content-skills` · 小红书发布包（代码：`xhs note / score / compliance`；消费方：r10, r12, r03）

查看：`python guagua.py capabilities --role r11`
