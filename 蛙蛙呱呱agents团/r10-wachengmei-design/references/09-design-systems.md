# 模块I · 品牌设计系统库（31 套 DESIGN.md）

> 素材来源：[awesome-design-md](https://github.com/VoltAgent/awesome-design-md) 的 DESIGN.md 集合
> （Google Stitch 的 DESIGN.md 格式：九段式纯文本设计规范）。
> 落地位置：`r10-wachengmei-design/references/design-systems/<brand>.md`
> 解析与门禁代码：`shared/design_systems.py`（R10/R08 共用，纯标准库）

## 一、为什么放进 R10

R10 的职责是「把品牌简报变成可交付的视觉规范」，但过去每次都要从零编一套配色与字阶。
这 31 份文件是**已被验证的品牌级设计系统**，等于给 R10 一本可检索的参考图鉴：
先选基线（谁的气质最接近），再改动（换成客户品牌色），比"凭感觉配色"稳定得多。

## 二、库内清单（按分类）

| 分类 | 品牌 slug |
|---|---|
| AI / 模型 `ai` | `claude` `cohere` `elevenlabs` `minimax` `mistral.ai` `ollama` `opencode.ai` |
| 开发者工具 `devtools` | `cursor` `expo` `linear.app` `lovable` `mintlify` |
| 基础设施 / 数据 `infra` | `clickhouse` `composio` `hashicorp` `mongodb` |
| 设计 / 生产力 `design` | `airtable` `cal` `clay` `figma` `framer` `intercom` `miro` `notion` |
| 金融 / 加密 `fintech` | `coinbase` `kraken` |
| 企业 / 消费 `enterprise` | `airbnb` `apple` `bmw` `ibm` `nvidia` |

## 三、四个动作

```bash
python agent.py designsys list [--category ai] [--q 极简]
python agent.py designsys recommend --project <saas|devtools|ai|fintech|productivity|ecommerce|dashboard|creative|enterprise>
python agent.py designsys show --brand linear.app
python agent.py designsys apply --brand linear.app --out DESIGNS/linear [--force]
python agent.py designsys audit --brand claude        # 或 --input 某份 DESIGN.md
```

- `apply` 落盘两份产物：`DESIGN.md`（原文 + 溯源注释）与 `design_tokens.json`。
- 默认**不覆盖**已存在文件；要覆盖必须显式 `--force`（与 imaging/media 的防不可逆覆盖纪律一致）。
- `audit` 也可用于校验**客户自己写的** DESIGN.md，不限于库内品牌。

## 四、九段式门禁（确定性，不用模型）

| 检查 | 维度 | 判定 |
|---|---|---|
| 九段式章节齐全 | `doc.sections` | 缺任一 `## N.` 段即 FAIL |
| 色令牌 ≥6（`figma` 等刻意单色系统放宽到 4） | `design.color.tokens` | 支持 `#rrggbb` 与 `rgba()` |
| 字体族 ≥1 | `design.typography.fonts` | 从 `### Font Family` 小节解析 |
| 字阶表 ≥3 行 | `design.typography.scale` | 表格行数 |
| 组件样式 ≥2 | `design.components` | `## 4.` 下的 `###` 小节数 |
| Do's & Don'ts 存在 | `design.guardrails` | 第 7 段存在 |
| 响应式段存在 | `design.responsive` | 第 8 段存在 |
| Agent Prompt Guide 含 ≥3 个色值 | `design.prompt_guide` | 第 9 段 |

31 套素材当前 **31/31 PASS**（`tests/test_design_systems.py` 有回归）。

## 五、交给下游：令牌契约

`design_tokens.json` 的形状就是 R08 `design/token` 认的结构：

```json
{
  "design_system": {"slug": "linear.app", "name": "Linear", "style": "...", "category": "devtools"},
  "tokens": {
    "color":      [{"name": "Brand Indigo", "value": "#5e6ad2", "role": "Brand & Accent"}],
    "typography": [{"name": "font.1", "value": "Inter Variable"}],
    "spacing":    [{"name": "space.1", "value": "4px"}]
  },
  "components": [{"name": "Buttons", "platform": "web", "states": ["default", "hover", "focus", "disabled"]}],
  "source": {"kind": "awesome-design-md", "file": "linear.app.md", "lines": 356}
}
```

接力方式：

```bash
# R10 落盘
python guagua.py call r10 designsys apply --brand linear.app --out DESIGNS/linear
# R08 消费（DESIGN.md → 令牌 → 组件门禁）
python guagua.py call r08 design from-md --input DESIGNS/linear/DESIGN.md --out DESIGNS/linear/design_tokens.json
# R09 拿 design_tokens.json 实现前端；R11 拿 DESIGN.md 的版式语气写内容
```

## 六、扩展新的品牌

1. 把新 DESIGN.md 放进 `references/design-systems/<slug>.md`（保持九段式格式）；
2. 在 `shared/design_systems.py` 的 `CATALOG` 里加一条（name / category / zh / style / tags，
   必要时加 `palette_min`）；
3. 跑 `python -m pytest tests/test_design_systems.py -q`，门禁不过就说明文档结构缺段。

## 七、边界

- 库内文件是**设计参考规范**，不是授权素材：字体、图形、品牌 Logo 的使用权仍需单独确认，
  R10 不因为"库里有"就宣称客户可直接商用。
- 品牌决策（选哪套、改成什么样）属创始人/客户决策，R10 只给选项与依据。
- 不把 31 份原文塞进每次 Prompt：按需 `show`/`apply` 单份，避免上下文膨胀。
