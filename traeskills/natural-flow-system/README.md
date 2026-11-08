# 自然流·全体系 (Natural Flow · Complete System)

以 **Mikey「自然流」搭讪为主线**，融合 9 套情感 skill 的完整恋爱/两性操作系统。

**技术流为主，安全边界兜底。**

## 集成来源

| 模块 | 来源 skill | 贡献 |
|------|-----------|------|
| `a_mikey_system.md` | game-skill (Mikey) | 自然流搭讪体系 A1-A7（主线） |
| `b_tankman_system.md` | game-skill (Tankman/凡公子) | 两性博弈体系 B1-B5 |
| `c_girl_types.md` | game-skill | 17 种女生类型处理 |
| `d_error_ledger.md` | game-skill | 常见错误大全 |
| `e_axioms.md` | TDSKILL（兔导） | 10 公理底层认知（已去广告） |
| `f_golden_quotes.md` | game-skill | 原文金句录 |
| `g_analysis_framework.md` | dating-master（情场高手） | 四层分析框架（语用学/依恋/信号博弈论） |
| `h_signal_system.md` | simp-skill（追爱军师） | 信号分级 + 追求阶段 |
| `i_crisis_handbook.md` | simp-skill | 危机处理手册 |
| `j_chat_analysis.md` | qingsheng（情圣）+ simp | 聊天截图/时间线/角色区分 |
| `k_display_date_sop.md` | dating-coach（综合恋爱教练） | 展示面/AI展示面/约会SOP/流量排查 |
| `l_safety_boundaries.md` | guanxi-skills（关系攻略师） | 安全边界/同意/反操控 |
| `m_expression_style.md` | tong-jincheng（童锦程）+ simp | 心法 + 表达 DNA + 情话生成 |
| `n_mikey_persona.md` | Mikey 案例蒸馏（本项目新增） | Mikey 人格：身份卡/履历/表达DNA/比喻库/核心心智 125 条（第一人称扮演） |
| `o_mikey_theory.md` | Mikey 案例蒸馏（本项目新增） | 道层：理论体系总纲（310 条心智模型） |
| `p_techniques.md` | Mikey 案例蒸馏（本项目新增） | 术+技术层：操作手册（六阶段打法 + 技术速查总表） |

## 目录结构

```
SKILL.md                        # 主入口（thin loader）
skill.yaml                      # 主路由表（触发词 → 模块）
modules/                        # 16 个模块
decision_trees/                 # 搭讪/约会决策树
templates/scripts.json          # 话术模板库
index/cross_mapping.csv         # Mikey vs Tankman 交叉对照
```

## 安装

复制整个目录到 `~/.claude/skills/natural-flow-system/`，重启 Claude Code。

## 使用

直接描述问题即可触发，例如：

- 「帮我想个开场白」→ 路由到话术模板 + 搭讪模块
- 「她回了我这句话什么意思」（贴聊天）→ 路由到四层分析 + 聊天分析
- 「搭讪御姐怎么办」→ 叠加加载搭讪 + 女生类型模块
- 「我总是不敢上去」→ 错误自查 + 心态模块

## 设计原则

1. **模块化按需路由**：主路由表 `skill.yaml` 根据触发词只加载相关模块，不一次性读全文。
2. **主线清晰**：Mikey 自然流是主线，其余为补充层（认知/分析/信号/危机/展示面/安全/表达）。
3. **安全兜底**：涉及越界信号时，安全边界模块优先级最高。
4. **去广告**：原 TDSKILL 的强制公众号广告已剥离。

## 知识产权

融合内容基于多位导师（Mikey、Tankman、兔导、童锦程等）的公开视频/文章提炼，知识产权归原作者。本 skill 仅作成年人 AI 辅助学习工具。
