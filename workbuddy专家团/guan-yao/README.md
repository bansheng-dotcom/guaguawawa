# 观爻 · 术数占卜专家团

十六门中国传统术数全开的占卜专家团：**脚本确定性起盘 + 典籍原文佐证 + 五师分断交叉验证**，给吉凶、应期与趋避。

## 类型

Team 型（多角色协作，主理人编排 + 5 位专精成员）

## 成员

| Agent ID | 花名 | 职业 | 拿手 |
|---|---|---|---|
| `guan-yao-team-lead` | 观爻 | **总断全局** | 选术派单、交叉验证、融合交付、降级裁决 |
| `mingli-master` | 司命 | **星命推运** | 八字、紫微斗数、七政四余、八字合婚、大运流年 |
| `gua-master` | 演爻 | **卦象断事** | 六爻纳甲、梅花易数、小六壬、失物寻人 |
| `sanshi-master` | 运筹 | **三式定时** | 大六壬、奇门遁甲、太乙神数、金口诀、应期方位 |
| `kanyu-master` | 寻龙 | **堪舆择日** | 八宅/玄空飞星、二十四山、建除黄道择日 |
| `xiangzi-master` | 鉴形 | **相字察微** | 相术、测字、天文占、灵棋/易林/解梦 |

## 功能

- **自动选术**：只说「帮我算算」也行，主理人先问事、再荐 2-3 个候选术法，不逼用户选术语。
- **确定性起盘**：`skills/观爻卜算/scripts/cast.py` 统一入口，覆盖梅花（时间/数字/物数/声音/字占/端法）、小六壬、六爻、八字（含流年/流月/合婚/真太阳时/时辰范围枚举）、紫微（含流年化忌扫描/验前事）、七政四余、大六壬、金口诀、奇门、太乙、风水、择日（单日/按月）。
- **典籍原文断卦**：`classical_search.py` 按关键词/段落 ID 检索典籍 txt，每条 `[原文]` 附「书名:行号」可回查，查不到就明说「依 XX 法推演，非直接引文」。
- **四层证据 + 三级标注**：代码输出 / 原文映照 / 原文推演 / 逻辑推演分层呈现；每条结论标 `[原文]`/`[规则推演]`/`[主观推断]`，并附白话解读。
- **强制 gate**：断前排盘自检（`libs/gate/precheck.py`）+ 断后质检七项（`libs/gate/review.py`），不过则补齐再交付。
- **交叉验证**：同侧对（梅花/六爻/小六壬、八字/紫微、六壬/奇门）比吉凶；互补对（成败 + 时机方位）只做互补陈述；冲突即明说并降级。
- **诚实边界**：附 MingLi-Bench 实测命中率（36.2%，随机线 25%），无信号问题（学历/性格/精确年份生平）直接说「给不出确定答案」，不硬猜。

## 使用示例

- 这次跳槽能不能成？什么时候动比较合适
- 帮我排八字，看事业方向和近三年流年
- 下个月想搬家，帮我挑个吉日
- 我和他还有没有可能，他现在怎么想的
- 家里钥匙找不到了，大概在哪个方向

## 依赖

起盘脚本需要 Python 3.10+ 与以下包：

```bash
pip install lunar_python ephem cn2an bidict drawsvg py-iztro
```

`numpy` 仅 `taiyi --game` 用，可选。缺依赖时脚本会报错或降级（如无 `lunar_python` 时农历换算退用公历并打印警告）。

## 典籍库（IMA 知识库，不随包分发）

断卦引原文依赖 **IMA 知识库「卜算适配知识库」**（`knowledge_base_id: ima_kb_lXz71gfe`，干净 txt + `[分类] 书名.txt` 命名 + `r_XXX_*.md` 案例层）：

- 主源：通过 ima-mcp 连接器 `search_knowledge(knowledge_base_id="ima_kb_lXz71gfe", query=...)` 语义检索典籍原文与相似案例，注明出处书名。
- 降级：ima-mcp 不可用时，退回本地 `D:\卜算\国学czhengli\txt\`（Grep 或 `classical_search.py`）。
- 仍找不到则降级：只用 `references/` 速查表 + 规则推演，并在每条结论标 `[规则推演]`/`[主观推断]`，**不会编造经文**。

## 头像

头像已自动生成在 `avatars/`（`team.png` + 6 张成员头像）。如需替换：PNG/JPG，512×512，单张 ≤500KB。

## 目录结构

```
guan-yao/
├── .codebuddy-plugin/plugin.json
├── agents/                  # 6 个 Agent 定义
├── avatars/                 # 7 张头像
└── skills/观爻卜算/          # 内置技能（SKILL.md + docs/ + references/ + scripts/）
    ├── docs/                # 16 术分术法文档（起盘/断卦/自检/输出格式）
    ├── references/          # 23 份速查表
    └── scripts/             # cast.py + classical_search.py + libs/（引擎/规则/gate）
```

## 安装 / 注册

```bash
python scripts/validate_expert.py <expert-dir>
python scripts/register_expert.py <expert-dir>
```

## 打包分享

```bash
python scripts/package_expert.py <expert-dir>
```

## 免责

以上内容属传统术数文化研习，仅供娱乐与文化参考，不构成医疗、法律、投资、婚姻等任何专业决策依据。重大事项请咨询相应专业人士、理性判断。
