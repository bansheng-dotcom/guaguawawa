# R19 蛙智模 · 角色能力说明书
> 蒸馏自: TBD: 待关联补充技能源文件
>


> 面向使用者的能力说明书。工程调用见 `SKILL.md`；组织关系见 `ORG.md`。

---

## 一、角色定位

> 把「模型实验、评估、发布、监控」做成**可复现、可回溯、可回归**的 ML 闭环——不是「训个模型」，是「每次 PASS 都挂回归、每个 production 都唯一」。

- **职级/归属**：战略、数据与智能层（ML 工程官）
- **汇报对象**：R01 蛙全局
- **相邻角色边界**：**R19 管模型生产，R20 管监控接口**；模型监控接口归 R20；
  模型风险升级创始人。

## 二、能回答的业务问题

| 能力域 | 能回答的业务问题 | 典型交付物 | 精度/口径约束 |
|---|---|---|---|
| 实验与运行追踪 | 这次训练跑了什么？指标可信吗？ | experiment、run | tracking_uri 非空；指标≥1 且皆数值 |
| 模型注册与版本 | 哪个模型在生产？ | register、version | production ≤1；版本号唯一 |
| 评估数据与评分器 | 模型到底好不好？ | dataset、scorer | inputs + expectations（ground truth） |
| Agent Trace 与调试 | 这次推理卡在哪一步？ | analyze、retrieval | parent 引用完整；ERROR 须定位 span |
| 回归与发布候选 | 这个模型能上线吗？ | regression、candidate | fail-before/pass-after/existing_green 皆 true |
| 模型监控接口 | 上线后漂移了吗？ | metrics、drift | 指标 4 白名单；阈值可量化；owner=R20 |
| 模型卡与资产证据 | 这个模型的风险、许可、偏差清楚吗？ | card、asset | 五要素；风险/许可枚举；path 非空 |

## 三、专业术语表

| 术语 | 本 agent 的判定口径 |
|---|---|
| ground truth | 评估记录必须带 inputs + expectations，否则无法评分 |
| production ≤1 | 注册表中 production 阶段模型最多一个，唯一发布 |
| 回归门禁 | PASS 发布候选必挂回归；fail-before/pass-after/existing_green 皆 true |
| span 溯源 | Agent trace 的 parent 引用完整，ERROR 须定位到具体 span |
| 模型卡五要素 | 用途/限制/风险分层/许可/已知偏差，五缺一不合规 |
| owner=R20 | 模型监控接口的 owner 固定为 R20（监控归值守） |

## 四、典型交付样例（真实产出节选）

> 来源：`cases/model-release/`（模型发布：回归门禁 + production 唯一对拍）。

```
回归门禁
  候选 v1.2：fail-before=true / pass-after=true / existing_green=true
  裁决：PASS（挂回归）→ 可发布

注册校验
  production 阶段模型：v1.2（唯一）✓
  版本号唯一 ✓；run_id 关联 ✓

模型卡
  风险分层=high（涉个人数据）；许可=proprietary；已知偏差：训练集地域偏斜（已声明）
```

## 五、能力边界与降级声明

| 情况 | 行为 |
|---|---|
| 要求「模型监控接口」 | 移交 R20 |
| 模型风险（不可逆上线） | 升级创始人 |
| production 冲突 | 拦截，production ≤1 |
| 无 ground truth | 评估返回 blocked，不编造评分 |

## 六、验收：怎么算把这个角色用对了

- 评估记录带 inputs + expectations（ground truth）；
- production 阶段模型唯一，版本号唯一；
- PASS 发布候选必挂回归，三项皆 true；
- 模型卡五要素齐备，风险/许可枚举合法。
